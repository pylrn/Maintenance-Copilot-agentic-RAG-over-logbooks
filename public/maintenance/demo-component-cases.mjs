import { airframeProfiles, getAirframeProfile } from './airframe-profiles.mjs';
import { detectAirframeSegments } from './airframe-mapping.mjs';
const observations={
 nose:'RECORDED SHELL AND ATTACHMENT AREA FOR ASSESSMENT. DAMAGE EXTENT NOT ESTABLISHED.',
 cockpit:'RECORDED AFFECTED PANE AND VISIBILITY REPORT. NO PANE OR HEATING FAILURE CONFIRMED.',
 avionics:'RECORDED THE REPORTED CONNECTION SYMPTOM. NO FAILED EQUIPMENT UNIT IDENTIFIED.',
 cabin_fwd:'RECORDED FORWARD WINDOW AND SEAL LOCATION. LEAK PATH NOT CONFIRMED.',
 cabin_aft:'RECORDED AFT CABIN LOCATION AND PRESSURE REPORT. LEAK SOURCE NOT ISOLATED.',
 center:'RECORDED CENTER BOX AREA FOR STRUCTURAL ASSESSMENT. CRACK DIMENSIONS NOT AVAILABLE.',
 apu:'RECORDED EXHAUST-AREA VIBRATION REPORT. MOUNT AND DUCT CONDITION NOT ESTABLISHED.',
 stabilizer:'RECORDED THE REPORTED TAILPLANE SURFACE AREA. INTERNAL DAMAGE NOT CONFIRMED.',
 elevator:'RECORDED MOVEMENT SYMPTOM. HINGE AND LINKAGE CONDITION REMAIN UNVERIFIED.',
 rudder:'RECORDED REPORTED HINGE PLAY. MEASURED PLAY AND APPLICABLE LIMITS NOT AVAILABLE.'
};
export const componentDemoRows=Object.entries(airframeProfiles).map(([key,p],i)=>({
 domain:'aviation',source_id:`DEMO-${String(i+11).padStart(3,'0')}`,corpus_version:'demo-v2',source_type:'simulated',source_sha256:null,
 fields:{IDENT:`DEMO-${String(i+11).padStart(3,'0')}`,PROBLEM:p.example.toUpperCase()+'.',ACTION:observations[key]}, demo_component_key:key
}));
export function matchComponentDemoRows(query) {
 const profiles=detectAirframeSegments(query).map(hit=>getAirframeProfile(hit.id)).filter(Boolean);
 // A generic mention is not a match for a specific symptom fixture.
 const matching=new Set(profiles.filter(p=>p.rules.some(r=>r.pattern.test(query))).map(p=>p.key));
 return componentDemoRows.filter(row=>matching.has(row.demo_component_key));
}
