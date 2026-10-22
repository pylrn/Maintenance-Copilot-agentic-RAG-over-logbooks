/** UI mention mapping only: no diagnosis or log interpretation. */
export function detectAirframeSegments(text) {
 const q=(text||'').toLowerCase().replace(/left[ -]hand|\bl\s*\/\s*h\b|\blh\b|\bport\b/g,'left').replace(/right[ -]hand|\br\s*\/\s*h\b|\brh\b|\bstarboard\b/g,'right');
 const hits=new Map();
 const add=(id,name)=>hits.set(id,{id,name});
 const sides=(noun)=>{
  if(new RegExp(`\\b(both|bilateral)\\b.{0,20}(?:${noun})`).test(q))return ['l','r'];
  const left=new RegExp(`\\bleft\\b[^,;.!]{0,16}(?:${noun})|(?:${noun})\\s+(?:on\\s+the\\s+)?left\\b`).test(q);
  const right=new RegExp(`\\bright\\b[^,;.!]{0,16}(?:${noun})|(?:${noun})\\s+(?:on\\s+the\\s+)?right\\b`).test(q);
  return left&&!right?['l']:right&&!left?['r']:['l','r'];
 };
 if(/\b(wings?|winglets?|slats?|flaps?|ailerons?|spoilers?|spars?|ribs?)\b|fuel tank|leading edge|trailing edge/.test(q)) {
  let parts=[];
  if(/winglet|wing\s*tip/.test(q))parts.push('tip');
  if(/slat|leading edge/.test(q))parts.push('slats');
  if(/flap/.test(q))parts.push('flaps');
  if(/aileron/.test(q))parts.push('aileron');
  if(/spoiler/.test(q))parts.push('spoiler');
  if(/fuel|tank|spar|rib|crack|fracture/.test(q))parts.push('tank');
  if(!parts.length)parts=['slats','tank','flaps','aileron','spoiler','tip'];
  for(const side of sides('wings?|winglets?|slats?|flaps?|ailerons?|spoilers?|spars?|ribs?'))for(const part of parts)add(`seg-wing-${side}-${part}`,`${side==='l'?'Left':'Right'} wing · ${{tip:'winglet',slats:'leading edge',tank:'wing box',flaps:'flaps',aileron:'aileron',spoiler:'spoilers'}[part]}`);
 }
 if(/engine|cylinder|intake|powerplant|manifold|gasket|propeller|rocker|carburetor|fuel pump|spark plug|oil.*leak|oil loss|thrust|blade/.test(q)) {
  const selected=/engine\s*#?\s*1\b/.test(q)?['l']:/engine\s*#?\s*2\b/.test(q)?['r']:sides('engines?|powerplants?');
  for(const side of selected)add(`seg-engine-${side}`,`Engine ${side==='l'?'1':'2'}`);
 }
 if(/cockpit|avionics|instrument|mfd|pfd|display|breaker/.test(q)){add('seg-cockpit','Flight deck');add('seg-avionics','Avionics bay');}
 if(/nose|radome|radar|pitot/.test(q))add('seg-nose','Nose & radome');
 if(/landing gear|undercarriage|wheel|brake/.test(q)){if(/nose/.test(q))add('seg-gear-nose','Nose gear');else for(const side of sides('gear|wheel|brake'))add(`seg-gear-${side}`,`${side==='l'?'Left':'Right'} main gear`);}
 if(/rudder|vertical fin/.test(q))add('seg-rudder','Rudder');
 if(/tail|elevator|stabilizer|horizontal/.test(q))for(const side of sides('tail|elevator|stabilizer'))add(`seg-${/elevator/.test(q)?'elevator':'tail'}-${side}`,`${side==='l'?'Left':'Right'} tailplane`);
 if(/apu|tail cone/.test(q))add('seg-apu','Tail cone / APU');
 if(/fuselage|cabin|keel|center box/.test(q)){add('seg-center-box','Center wing box');add('seg-fuselage-fwd','Forward fuselage');}
 if(/door/.test(q)){add('seg-door-fwd','Forward door');add('seg-door-aft','Aft door');}
 if(/windshield|windscreen/.test(q))add('seg-cockpit','Flight deck');
 return [...hits.values()];
}
