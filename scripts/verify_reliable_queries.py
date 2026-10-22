"""End-to-end deterministic evidence/abstention regression; no provider requests."""
import asyncio
import json
from pathlib import Path
from uuid import uuid4

import httpx

CASES = [
    ('intake leak', 'supported_historical'),
    ('baffle crack', 'supported_historical'),
    ('baffle cracking', 'supported_historical'),
    ('R/H engine forward alternator attachment bolt loose.', 'supported_historical'),
    ('#3 brake is missing a screw.', 'supported_historical'),
    ('Right main gear brake pedal feels soft and spongy', 'insufficient_evidence'),
    ('CYL #99 intake leak', 'insufficient_evidence'),
    ('baffle crack with unfamiliar actuator failure', 'insufficient_evidence'),
    ('What is the approved torque specification in ft-lbs for the intake flange?', 'insufficient_evidence'),
    ('Is the aircraft safe to fly after this intake leak?', 'insufficient_evidence'),
]


async def main():
    results = []
    async with httpx.AsyncClient(base_url='http://localhost:8000', headers={'Origin':'http://localhost:8000'}, timeout=30) as client:
        for repeat in range(3):
            for query, expected in CASES:
                r = await client.post('/api/maintenance/v1/sessions',json={'domain':'aviation','title':'Evidence acceptance regression'})
                r.raise_for_status();session=r.json()
                r = await client.post(f"/api/maintenance/v1/sessions/{session['session_id']}/messages",json={
                    'text':query,'model':'extractive/v1','expected_revision':session['state_revision'],'idempotency_key':str(uuid4())})
                r.raise_for_status();run=r.json()
                async with client.stream('GET',run['events_url']) as stream:
                    stream.raise_for_status()
                    async for line in stream.aiter_lines():
                        if line.startswith('data: '):
                            event=json.loads(line[6:])
                            if event['type'] in ['done','run_failed','run_cancelled']:
                                assert event['type']=='done',event['type']
                                break
                r=await client.get(f"/api/maintenance/v1/sessions/{session['session_id']}");r.raise_for_status()
                answer=r.json()['answers'][-1]
                assert answer['status']==expected,(query,expected,answer['status'])
                if expected=='insufficient_evidence':
                    assert not answer['claims'] and not answer['visual_refs'] and not answer['allowed_actions']
                else:
                    assert answer['claims'] and answer['synthesis_evidence_ids']
                    for claim in answer['claims']:
                        for support in claim['supports']:
                            domain,ident=support['record_id'].split(':',1)
                            original=await client.get(f'/api/maintenance/v1/records/{domain}/{ident}',params={'corpus_id':support['corpus_id']})
                            original.raise_for_status();record=original.json()
                            raw=record['problem_raw' if support['field']=='PROBLEM' else 'action_raw']
                            assert raw[support['start']:support['end']]==support['quote']
                            assert record['field_sha256'][support['field']]==support['source_sha256']
                assert answer['generation']['status']=='not_requested'
                results.append({'repeat':repeat+1,'query':query,'expected':expected,'answer':answer,'run_id':run['run_id']})
                print(repeat+1,query,answer['status'],flush=True)
    path=Path('docs/verification/synthesis-results/reliable-query-regression.json')
    path.write_text(json.dumps(results,indent=2)+'\n')
    print(f'PASS {len(results)}/{len(results)}; zero model requests; source quotes checked against originals')


if __name__=='__main__':
    asyncio.run(main())
