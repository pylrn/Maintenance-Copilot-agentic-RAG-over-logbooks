"""Opt-in live verification: creates ten isolated sessions on a local backend."""
import argparse
import asyncio
import json
import time
from pathlib import Path
from uuid import uuid4

import httpx

CASES = [
    ("intake leak", "supported_historical"),
    ("baffle crack", "supported_historical"),
    ("Right main gear brake pedal feels soft and spongy", "insufficient_evidence"),
    ("CYL #99 intake leak", "insufficient_evidence"),
    ("What is the approved torque specification in ft-lbs for the intake flange?", "insufficient_evidence"),
]


async def verify(base_url, model):
    results = []
    async with httpx.AsyncClient(base_url=base_url, headers={"Origin": base_url}, timeout=45) as client:
        for selected_model in [model, "extractive/v1"]:
            for query, expected in CASES:
                response = await client.post('/api/maintenance/v1/sessions', json={
                    'domain': 'aviation', 'title': 'Abstention verification'})
                response.raise_for_status()
                session = response.json()
                start = time.perf_counter()
                response = await client.post(f"/api/maintenance/v1/sessions/{session['session_id']}/messages", json={
                    'text': query, 'idempotency_key': str(uuid4()),
                    'expected_revision': session['state_revision'], 'model': selected_model})
                response.raise_for_status()
                run = response.json()
                terminal = None
                async with client.stream('GET', run['events_url']) as stream:
                    stream.raise_for_status()
                    async for line in stream.aiter_lines():
                        if line.startswith('data: '):
                            event = json.loads(line[6:])
                            if event['type'] in ['done', 'run_failed', 'run_cancelled']:
                                terminal = event['type']
                                break
                assert terminal == 'done', (query, terminal)
                response = await client.get(f"/api/maintenance/v1/sessions/{session['session_id']}")
                response.raise_for_status()
                answer = response.json()['answers'][-1]
                assert answer['status'] == expected, (query, selected_model, answer['status'], expected)
                if expected == 'insufficient_evidence':
                    assert not answer['claims'], query
                    assert not answer['visual_refs'], query
                    assert not answer['allowed_actions'], query
                    assert answer['what_can_be_concluded'] == ['No evidence found for this complaint in the historical records.'], query
                else:
                    assert answer['claims'], query
                    assert all(c['supports'] for c in answer['claims']), query
                row = dict(query=query, model=selected_model, expected=expected,
                    actual=answer['status'], claims=len(answer['claims']),
                    duration_seconds=round(time.perf_counter()-start, 3),
                    run_id=run['run_id'], session_id=session['session_id'],
                    summary=answer['summary'],
                    quoted_evidence=[{'record_id': s['record_id'], 'quote': s['quote']}
                        for claim in answer['claims'] for s in claim['supports']])
                results.append(row)
                print(json.dumps({k: row[k] for k in ['query','model','actual','claims','duration_seconds']}), flush=True)
    return results


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base-url', default='http://localhost:8000')
    parser.add_argument('--model', default='gemini-3.5-flash-lite')
    parser.add_argument('--output', type=Path, default=Path('/tmp/nexai-abstention-live.json'))
    args = parser.parse_args()
    results = asyncio.run(verify(args.base_url.rstrip('/'), args.model))
    args.output.write_text(json.dumps(results, indent=2)+'\n')
    print(f'PASS: {len(results)} live cases; evidence: {args.output}')
