"""Verify a deployed frontend's real local-backend connection without model calls."""
import argparse
import asyncio
import json
import re
from pathlib import Path
from urllib.parse import urljoin
from uuid import uuid4

import httpx


async def verify(base):
    report={'url':base,'checks':[]}
    async with httpx.AsyncClient(base_url=base,headers={'Origin':base},timeout=45) as client:
        for path in ['/','/maintenance/','/deployment-status.json','/maintenance/deployment-config.mjs','/api/maintenance/v1/health']:
            response=await client.get(path);response.raise_for_status()
            report['checks'].append({'path':path,'http':response.status_code})
            if path=='/deployment-status.json':assert response.json()['mode']=='live'
            if path.endswith('health'):assert response.json()['app_ready']
        # Verify actual stylesheet/module dependencies, not only the index status.
        html=(await client.get('/maintenance/')).text
        refs=re.findall(r'(?:src|href)=["\']([^"\']+)["\']',html)
        assets=[urljoin(base+'/maintenance/',ref) for ref in refs if not ref.startswith(('https:','http:','#')) and re.search(r'\.(css|mjs)(?:\?|$)',ref)]
        for asset in assets:
            response=await client.get(asset);response.raise_for_status()
            if '.mjs' in asset:assert 'javascript' in response.headers.get('content-type','')
        report['assets_checked']=len(assets)
        response=await client.post('/api/maintenance/v1/sessions',json={'domain':'aviation','title':'Vercel deployment verification'})
        response.raise_for_status();session=response.json()
        # First authenticated mutation establishes the HTTPS owner cookie.
        cookie=next(c for c in client.cookies.jar if c.name=='maintenance_owner')
        assert cookie.secure and cookie.has_nonstandard_attr('HttpOnly')
        assert cookie.get_nonstandard_attr('SameSite').lower()=='strict'
        report['cookie']={'secure':True,'httponly':True,'samesite':'strict'}
        for query,expected in [('intake leak','supported_historical'),('CYL #99 intake leak','insufficient_evidence')]:
            response=await client.get('/api/maintenance/v1/sessions/'+session['session_id']);response.raise_for_status();session=response.json()
            response=await client.post('/api/maintenance/v1/sessions/'+session['session_id']+'/messages',json={
                'text':query,'model':'extractive/v1','expected_revision':session['state_revision'],'idempotency_key':str(uuid4())})
            response.raise_for_status();run=response.json();events=[]
            async with client.stream('GET',run['events_url']) as stream:
                stream.raise_for_status()
                assert 'text/event-stream' in stream.headers.get('content-type','')
                async for line in stream.aiter_lines():
                    if line.startswith('data: '):
                        event=json.loads(line[6:]);events.append(event['type'])
                        if event['type'] in ['done','run_failed','run_cancelled']:break
            assert events[-1]=='done'
            response=await client.get('/api/maintenance/v1/sessions/'+session['session_id']);response.raise_for_status();answer=response.json()['answers'][-1]
            assert answer['status']==expected,(query,answer['status'])
            if expected=='insufficient_evidence':assert not answer['claims']
            report['checks'].append({'query':query,'status':answer['status'],'sse_events':events,'run_id':run['run_id']})
        response=await client.post('/api/maintenance/v1/sessions',headers={'Origin':'https://untrusted.example'},json={'domain':'aviation','title':'Rejected origin probe'})
        assert response.status_code==403
        report['untrusted_origin_http']=403
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('url')
    parser.add_argument('--output',type=Path,default=Path('/tmp/vercel-verification.json'))
    args=parser.parse_args()
    result=asyncio.run(verify(args.url.rstrip('/')))
    args.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))
