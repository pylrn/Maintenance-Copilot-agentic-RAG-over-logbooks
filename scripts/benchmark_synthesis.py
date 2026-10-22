"""Opt-in fixed-evidence model benchmark, paced below the supplied RPM limits.

This isolates selection/prompt quality from retrieval. Provider errors and safe
fallbacks are reported separately and never counted as model-quality successes.
"""
import argparse
import asyncio
import hashlib
import json
import time
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

from pydantic import SecretStr

from maintenance.agent_run import AgentRunner
from maintenance.answer_rendering import render_extractive_answer
from maintenance.answer_validation import validate_answer
from maintenance.benchmark_limits import BenchmarkLimits
from maintenance.models.provider import LLMProvider
from maintenance.synthesis import PROMPT_VERSION, EvidenceSelection, default_selection, selection_ids, synthesis_messages

ROOT = Path(__file__).resolve().parents[1]


def evidence_packet(case):
    packet = {}
    for record in case['records']:
        for field, text in [(record.get('field','PROBLEM'),record['problem']),('ACTION',record['action'])]:
            if text is None:continue
            eid=uuid5(NAMESPACE_URL,case['id']+record['id']+field)
            packet[eid]={'evidence_id':eid,'record_id':record['id'], 'corpus_id':uuid5(NAMESPACE_URL,'benchmark-corpus'),
                'field':field,'raw_text':text,'source_sha256':hashlib.sha256(text.encode()).hexdigest()}
    return packet


async def run(args):
    cases=json.loads((ROOT/'eval/synthesis/golden.json').read_text())
    report={'prompt_version':PROMPT_VERSION,'scope':'fixed synthetic evidence; not end-to-end retrieval accuracy',
        'reasoning_effort':args.reasoning_effort,
        'limits':{'global_rpm':4,'flash_rpm':2,'lite_rpm':4,'tpm_conservative_ceiling':45000,
                  'one_inflight':True,'retry_on_429':False,'warmup_seconds':args.cooldown,'reasoning_effort':args.reasoning_effort},'results':[]}
    limits=BenchmarkLimits()
    key=None
    if args.live:
        # Load only the requested server credential, never print it or the environment.
        for line in args.env_file.read_text().splitlines():
            if line.startswith('GEMINI_API_KEY='):
                key=line.split('=',1)[1].strip().strip('"').strip("'")
        if not key:raise SystemExit('GEMINI_API_KEY not found in the specified private env file')
        print(f'Initial quota cooldown: {args.cooldown}s',flush=True)
        await asyncio.sleep(args.cooldown)
    models=args.models if args.live else ['extractive/v1']
    for case in cases:
        evidence=evidence_packet(case)
        for model in models:
            if model in limits.disabled:
                report['results'].append({'case':case['id'],'model':model,'status':'skipped_after_rate_limit'})
                continue
            # Every UTF-8 input byte is conservatively budgeted as one token.
            input_bound = sum(len(m['content'].encode()) for m in synthesis_messages(case['query'],evidence)) + len(json.dumps(EvidenceSelection.model_json_schema()).encode())
            if input_bound > 8000:
                raise ValueError('benchmark input exceeds8000-byte conservative token bound')
            if args.live:
                delay=limits.delay(model,time.monotonic())
                if delay:
                    print(f'Pacing {model}: wait {delay:.1f}s',flush=True);await asyncio.sleep(delay)
                limits.record(model,time.monotonic())
                provider=LLMProvider(api_key=SecretStr(key),model_name=model,provider_type='gemini')
                # One request; no fallback model; max12s and3072 output/thought tokens.
                runner=AgentRunner(None,None,provider,synthesis_reasoning_effort=args.reasoning_effort)
                try:
                    selection,info=await runner.synthesize_conclusions(provider,case['query'],evidence)
                finally:
                    await provider.client.close()
                if info.get('fallback_reason')=='rate_limited':limits.disabled.add(model)
            else:
                selection=default_selection(evidence)
                info={'status':'deterministic_baseline','requested_model':model,'effective_model':model}
            released=render_extractive_answer(uuid5(NAMESPACE_URL,case['id']+model),'EVIDENCE',case['query'],
                {} if selection and selection.decision=='insufficient_evidence' else evidence,0,
                status='insufficient_evidence' if selection and selection.decision=='insufficient_evidence' else None,
                synthesis_selection=selection)
            validation=validate_answer(released,evidence,{},'EVIDENCE')
            model_success=info['status']=='validated_selection' if args.live else False
            row={'case':case['id'],'model':model,**info,'expected_decision':case['expected_decision'],
                'actual_decision':selection.decision if selection else None,
                'model_quality_pass':model_success and selection.decision==case['expected_decision'],
                'release_validation_pass':validation.is_valid,
                'source_selection_ids':[str(x)for x in selection_ids(selection)] if selection else [],
                'released_summary':released.summary,'released_can':released.what_can_be_concluded,
                'released_cannot':released.what_cannot_be_concluded}
            report['results'].append(row)
            args.output.parent.mkdir(parents=True,exist_ok=True)
            args.output.write_text(json.dumps(report,indent=2)+'\n')
            print(json.dumps({k:row.get(k) for k in ['case','model','effective_model','status','fallback_reason','actual_decision','model_quality_pass','latency_ms']}),flush=True)
    args.output.write_text(json.dumps(report,indent=2)+'\n')
    print('Report:',args.output)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--live',action='store_true')
    p.add_argument('--models',nargs='+',default=['gemini-3.8-flash','gemini-3.5-flash-lite'])
    p.add_argument('--reasoning-effort',choices=['minimal','low','medium','high'],default='low')
    p.add_argument('--env-file',type=Path,default=ROOT/'.env')
    p.add_argument('--cooldown',type=float,default=65)
    p.add_argument('--output',type=Path,default=Path('/tmp/nexai-synthesis-benchmark.json'))
    a=p.parse_args()
    if a.live and a.cooldown<60: p.error('live benchmark requires at least60 seconds initial quota cooldown')
    if len(a.models)>3:p.error('at most3 models per run')
    asyncio.run(run(a))
