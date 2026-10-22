import { test } from 'node:test';
import assert from 'node:assert/strict';
import { mkdtempSync, mkdirSync, writeFileSync, readFileSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join, resolve } from 'node:path';
import { spawnSync } from 'node:child_process';
const script = resolve('scripts/build_vercel.mjs');
function build(backend) {
  const root = mkdtempSync(join(tmpdir(), 'atlas-vercel-'));
  mkdirSync(join(root,'public/maintenance'),{recursive:true});
  for(const name of ['index.html','maintenance-ui.mjs','api-client.mjs','demo-adapter.mjs']) writeFileSync(join(root,'public/maintenance',name),'fixture');
  const result=spawnSync(process.execPath,[script],{cwd:root,env:{...process.env,MAINTENANCE_BACKEND_ORIGIN:backend},encoding:'utf8'});
  return {root,result};
}
test('static Vercel output discloses demo and missing backend',()=>{
  const {root,result}=build('');try{
    assert.equal(result.status,0,result.stderr);
    const c=JSON.parse(readFileSync(join(root,'.vercel/output/config.json')));
    assert.equal(c.version,3);assert.equal(c.routes[0].status,503);
    assert.match(readFileSync(join(root,'.vercel/output/static/maintenance/deployment-config.mjs'),'utf8'),/"demo"/);
    assert.equal(JSON.parse(readFileSync(join(root,'.vercel/output/static/deployment-status.json'))).backend_configured,false);
  }finally{rmSync(root,{recursive:true,force:true});}
});
test('live mode proxies API to explicit HTTPS origin and serves canonical maintenance path',()=>{
  const {root,result}=build('https://backend.example.test');try{
    assert.equal(result.status,0,result.stderr);
    const c=JSON.parse(readFileSync(join(root,'.vercel/output/config.json')));
    assert.equal(c.routes[0].dest,'https://backend.example.test/api/$1');
    assert.equal(c.routes[1].dest,'/maintenance/index.html');
    assert.match(readFileSync(join(root,'.vercel/output/static/deployment-config.mjs'),'utf8'),/"live"/);
  }finally{rmSync(root,{recursive:true,force:true});}
});
test('reject credential-bearing and local backend URLs',()=>{
  for(const origin of ['http://localhost:8000','https://127.0.0.1','https://user:secret@backend.example.test','https://backend.example.test/path']){
    const {root,result}=build(origin);try{assert.notEqual(result.status,0);}finally{rmSync(root,{recursive:true,force:true});}
  }
});
test('ignore rules cannot exclude the public maintenance directory',()=>{
  const ignores=readFileSync('.vercelignore','utf8').split('\n');
  assert.ok(ignores.includes('/maintenance/'));
  assert.ok(!ignores.includes('maintenance/'));
  assert.ok(ignores.includes('!/scripts/build_vercel.mjs'));
  const config=JSON.parse(readFileSync('vercel.json'));
  assert.equal(config.framework,null);
  assert.equal(config.buildCommand,'node scripts/build_vercel.mjs');
});
