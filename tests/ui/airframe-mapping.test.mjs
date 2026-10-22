import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { detectAirframeSegments } from '../../api/static/maintenance/airframe-mapping.mjs';
import { issueScenario } from '../../api/static/maintenance/component-explorer.mjs';
const ids = query => detectAirframeSegments(query).map(hit => hit.id);
test('wing controls map to their own regions and honor side aliases', () => {
 assert.deepEqual(ids('left wing flap stuck'), ['seg-wing-l-flaps']);
 assert.deepEqual(ids('RH aileron jammed'), ['seg-wing-r-aileron']);
 assert.deepEqual(ids('L/H spoiler fault'), ['seg-wing-l-spoiler']);
 assert.deepEqual(ids('starboard slat fault'), ['seg-wing-r-slats']);
});
test('unspecified wings highlight both sides rather than defaulting right', () => {
 assert.deepEqual(ids('wings fuel leak'), ['seg-wing-l-tank', 'seg-wing-r-tank']);
 assert.equal(ids('wing issue').length, 12);
});
test('engine numbers and cylinder numbers are distinct', () => {
 assert.deepEqual(ids('engine 1 oil leak'), ['seg-engine-l']);
 assert.deepEqual(ids('cylinder 2 intake leak'), ['seg-engine-l', 'seg-engine-r']);
});
test('every mapped region has real selectable SVG geometry', () => {
 const html = readFileSync(new URL('../../api/static/maintenance/index.html', import.meta.url), 'utf8');
 for (const query of ['wing issue','engine issue','cockpit display','nose landing gear','main brakes','tail elevator','rudder','apu','fuselage door']) {
  for (const id of ids(query)) assert(html.includes(`id="${id}"`), `${query}: missing ${id}`);
 }
});
test('wing controls retain their context in the internal view', () => {
 assert.equal(issueScenario('wing', 'left wing flap stuck').initial, 3);
 assert.equal(issueScenario('wing', 'RH slat stuck').initial, 0);
 assert.equal(issueScenario('engine', 'no oil leak'), null);
});
