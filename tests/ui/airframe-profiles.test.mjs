import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { airframeProfiles, getAirframeProfile, airframeProfileScenario } from '../../api/static/maintenance/airframe-profiles.mjs';
import { detectAirframeSegments } from '../../api/static/maintenance/airframe-mapping.mjs';
import { componentDemoRows, matchComponentDemoRows } from '../../api/static/maintenance/demo-component-cases.mjs';
const ids=q=>detectAirframeSegments(q).map(h=>h.id);
const segments={nose:'seg-nose',cockpit:'seg-cockpit',avionics:'seg-avionics',cabin_fwd:'seg-fuselage-fwd',cabin_aft:'seg-fuselage-aft',center:'seg-center-box',apu:'seg-apu',stabilizer:'seg-tail-l',elevator:'seg-elevator-r',rudder:'seg-rudder'};
test('ten regional cutaways have distinct scenes, parts and valid callouts',()=>{
 assert.equal(Object.keys(airframeProfiles).length,10);
 assert.equal(new Set(Object.values(airframeProfiles).map(p=>p.scene)).size,10);
 assert.equal(new Set(Object.values(airframeProfiles).map(p=>p.parts.map(x=>x[0]).join(','))).size,10);
 const html=readFileSync(new URL('../../api/static/maintenance/index.html',import.meta.url),'utf8');
 for(const [key,id] of Object.entries(segments)){
  const p=getAirframeProfile(id); assert.equal(p.key,key);assert.equal(p.points.length,p.parts.length);assert(html.includes(`id="${id}"`));
  const scenario=airframeProfileScenario(p,p.example);assert(scenario.parts.every(i=>i>=0&&i<p.parts.length));assert(scenario.effect);
 }
});
test('each regional issue maps to its region and its own invented demo record',()=>{
 for(const [key,p] of Object.entries(airframeProfiles)){
  const mapped=ids(p.example).map(getAirframeProfile).filter(Boolean).map(p=>p.key);
  assert(mapped.includes(key),`${key}: ${p.example} -> ${mapped}`);
  assert(matchComponentDemoRows(p.example).some(row=>row.demo_component_key===key),key);
 }
 assert.equal(new Set(componentDemoRows.map(r=>r.source_id)).size,10);
 assert(componentDemoRows.every(r=>r.source_type==='simulated'&&r.source_sha256===null));
});
test('aft cabins and tail wings do not light unrelated forward/main-wing regions',()=>{
 assert.deepEqual(ids('aft cabin pressure leak'),['seg-fuselage-aft']);
 assert.deepEqual(ids('forward cabin window seal leak'),['seg-fuselage-fwd']);
 assert.deepEqual(ids('left tail wing crack'),['seg-tail-l']);
 assert.deepEqual(ids('right elevator stiff movement'),['seg-elevator-r']);
 assert.deepEqual(ids('rudder hinge excessive play'),['seg-rudder']);
 assert.deepEqual(ids('APU oil leak'),['seg-apu']);
 assert.deepEqual(ids('vertical stabilizer damage'),['seg-rudder']);
});
test('an unrelated component has no profile and a negated report creates no issue scenario',()=>{
 assert.equal(getAirframeProfile('seg-engine-r'),null);
 assert.equal(airframeProfileScenario(getAirframeProfile('seg-nose'),'no radome damage'),null);
 assert.equal(airframeProfileScenario(getAirframeProfile('seg-rudder'),''),null);
 assert.deepEqual(getAirframeProfile('seg-tail-l').parts,getAirframeProfile('seg-tail-r').parts);
});
