// Authored generic cutaways: not aircraft-specific maintenance or fault-location evidence.
const airframeSource='https://www.faa.gov/documentlibrary/media/advisory_circular/ac_65-15a.pdf';
const part=(name,role,description)=>[name,role,description+' The installed design and condition are unverified.'];
const profile=(name,caption,parts,points,scene,example,rules=[])=>({name,caption,parts,points,scene,example,rules,source:airframeSource});
const skin='class="ce-shell"',metal='class="ce-metal"';
export const airframeProfiles={
 nose:profile('Radome & nose assembly','Nose section · shell and equipment interface',[
  part('Radome shell','Outer enclosure','The translucent shell is drawn around the forward equipment space.'),part('Radar antenna mount','Equipment support','The dish and its support are shown behind the shell.'),part('Radome attachment ring','Body interface','The aft ring joins the illustrated nose to the fuselage.')],[[240,125],[412,165],[600,176]],
  `<path ${skin} d="M610 65Q238 43 100 165Q241 289 610 267Z"/><ellipse cx="606" cy="166" rx="27" ry="101" fill="none" stroke="#729484" stroke-width="7"/><path d="M550 165H412" stroke="#6d8e7e" stroke-width="11"/><path d="M406 102Q351 165 406 228Q477 165 406 102Z" fill="#afccbc" stroke="#70937f" stroke-width="3"/><path d="M412 166 288 97M412 166 272 166M412 166 288 237" stroke="#b4cdbf" stroke-dasharray="5 5" fill="none"/>`,
  'Radome crack near the attachment ring',[
   {pattern:/radar|antenna/i,areas:[1],text:'A radar symptom is reported. The antenna/mount is a visual reference; power, signal and configuration are unresolved.'},
   {pattern:/crack|dent|impact/i,areas:[0,2],text:'Surface damage is reported at the nose. Shell extent and attachment condition are not established.'}]),
 cockpit:profile('Flight deck glazing','Cockpit section · windshield and frame',[
  part('Windshield panes','Glazing','The dark panes show the forward viewing surfaces.'),part('Frame & seals','Pane interfaces','The pale border shows the surrounding interface.'),part('Heating connection','Electrical interface','The amber line marks an illustrative connection.')],[[295,147],[472,109],[603,228]],
  `<path ${skin} d="M100 267 147 82Q400 20 653 82L700 267Z"/><path d="M179 111 372 83 372 222 137 222Z M400 83 615 109 660 222 400 222Z" fill="#6c9b90" stroke="#c2d7ca" stroke-width="12"/><path d="M604 214V260H482" class="ce-flow"/><path d="M182 239H651" stroke="#879e91" stroke-width="4"/>`,
  'Cockpit windshield crack',[
   {pattern:/crack|windshield|windscreen/i,areas:[0,1],text:'A glazing symptom is reported. Pane, seal and frame condition need source evidence.'},
   {pattern:/heat|fog|ice/i,areas:[0,2],text:'The report concerns visibility or heating. No heating circuit failure is confirmed.'}]),
 avionics:profile('Forward avionics bay','Equipment bay · racks and connections',[
  part('Equipment racks','Installed units','The stacked blocks represent equipment positions.'),part('Power distribution','Supply interface','The upper enclosure represents a generic supply interface.'),part('Data connectors','Signal interfaces','The lower ports represent cable connections.')],[[258,152],[559,97],[550,243]],
  `<rect ${skin} x="115" y="48" width="573" height="236" rx="18"/><rect x="149" y="75" width="249" height="179" rx="9" fill="#abc3b5"/>${[91,142,193].map(y=>`<rect ${metal} x="164" y="${y}" width="216" height="42" rx="5"/><path d="M177 ${y+15}h101" stroke="#7f9d8b" stroke-width="3"/>`).join('')}<rect x="480" y="64" width="150" height="66" rx="7" fill="#eddfc6" stroke="#ad976a"/><path d="M400 100H469M400 155H550V234" class="ce-flow"/><rect ${metal} x="479" y="215" width="151" height="48" rx="6"/>`,
  'Avionics connector intermittent',[
   {pattern:/connector|signal|intermittent|data/i,areas:[0,2],text:'Intermittent data or connection behavior is reported. A failed unit cannot be identified from the symptom alone.'},
   {pattern:/power|breaker|voltage/i,areas:[1],text:'A supply symptom is reported. Breaker state and voltage readings have not been established.'}]),
 cabin_fwd:profile('Forward cabin section','Forward fuselage · glazing and floor cutaway',[
  part('Window surrounds','Skin openings','The cutaway shows the frames around the forward windows.'),part('Floor beam supports','Cabin floor','The lower members outline the floor support area.'),part('Sidewall interfaces','Interior boundary','The sidewall band marks a generic interior interface.')],[[287,115],[371,233],[558,167]],
  `<path ${skin} d="M95 158Q104 62 229 63H674V267H218Q97 264 95 158Z"/>${[226,335,444,553].map(x=>`<path d="M${x} 69V258" stroke="#9ab5a3" stroke-width="6"/><rect x="${x+13}" y="95" width="53" height="41" rx="14" fill="#c2ddd1" stroke="#6f9985"/>`).join('')}<path d="M137 217H657M153 237H651" stroke="#698e78" stroke-width="8"/><path d="M155 161H647" stroke="#b79b67" stroke-width="4" stroke-dasharray="9 6"/>`,
  'Forward cabin window seal leak',[
   {pattern:/window|seal|leak/i,areas:[0,2],text:'A forward-cabin window or seal symptom is reported. The entry path and affected interface remain unconfirmed.'},
   {pattern:/floor|vibrat|loose/i,areas:[1],text:'A floor-area symptom is reported. No loose or damaged support is confirmed.'}]),
 cabin_aft:profile('Aft cabin & pressure boundary','Aft fuselage · tapering section',[
  part('Aft skin & frames','Outer framework','The tapering cutaway shows the rear cabin framework.'),part('Rear pressure boundary','Cabin boundary','The curved end panel marks the illustrated rear boundary.'),part('Aft floor interface','Interior support','The lower beams show the rear floor interface.')],[[255,101],[568,169],[330,238]],
  `<path ${skin} d="M111 64H441Q632 67 696 162Q628 270 441 270H111Z"/>${[172,270,368].map(x=>`<path d="M${x} 72V259" stroke="#91af9a" stroke-width="6"/>`).join('')}<path d="M505 83Q620 166 505 252" fill="#c8dfcf" stroke="#76977e" stroke-width="5"/><path d="M130 229H470" stroke="#6b8e76" stroke-width="9"/><path d="M130 133H472M130 183H494" stroke="#b0c7b6" stroke-width="3"/>`,
  'Aft cabin pressure leak',[
   {pattern:/pressure|pressuri|leak/i,areas:[0,1],text:'Pressure loss is reported near the aft cabin. The rear boundary is shown for orientation, not as an identified leak source.'},
   {pattern:/floor|rattle/i,areas:[2],text:'An aft-floor symptom is reported. The affected attachment or support is not established.'}]),
 center:profile('Center wing box & keel','Wing-to-fuselage intersection · structural cutaway',[
  part('Carry-through structure','Wing junction','The central members show the illustrated wing junction.'),part('Keel beam','Lower structure','The longitudinal beam is drawn beneath the junction.'),part('Floor attachments','Upper interfaces','The upper fittings show attachment locations in this illustration.')],[[406,150],[418,249],[276,88]],
  `<path ${skin} d="M84 117 397 77 716 119 716 218 398 262 84 218Z"/><path d="M113 139 396 108 686 143M113 199 397 234 686 199" stroke="#688f78" stroke-width="12"/><path d="M273 106V219M400 96V237M532 110V219" stroke="#9eb8a4" stroke-width="9"/><path d="M192 255H613" stroke="#53795f" stroke-width="14"/><rect x="252" y="65" width="46" height="43" rx="5" fill="#e7dac0" stroke="#ab9466"/>`,
  'Center wing box crack',[
   {pattern:/crack|fracture|corrosion/i,areas:[0,1],text:'A structural symptom is reported at the center box. Crack extent, corrosion depth and the affected load path are unknown.'}]),
 apu:profile('Tail cone & APU compartment','Rear equipment space · inlet, unit and exhaust',[
  part('APU enclosure','Equipment area','The circular unit is shown inside the tail cone.'),part('Inlet path','Air interface','The upper duct is the illustrated inlet.'),part('Exhaust & mounts','Rear interface','The outlet and lower supports are shown together.')],[[355,169],[311,83],[588,183]],
  `<path ${skin} d="M91 69H379Q618 70 714 167Q620 265 379 265H91Z"/><path d="M298 64V120H357" class="ce-flow"/><rect ${metal} x="202" y="118" width="281" height="112" rx="51"/><circle cx="287" cy="174" r="39" fill="#a8c7b2" stroke="#6e957c" stroke-width="6"/><path d="M483 145H605L662 169 605 198H483" fill="#c6d8cc" stroke="#7f9f89" stroke-width="3"/><path d="M233 230 212 254M439 230 461 254" stroke="#62856c" stroke-width="11"/>`,
  'APU exhaust vibration in tail cone',[
   {pattern:/exhaust|vibrat|mount/i,areas:[2],text:'An exhaust-area or vibration symptom is reported. Mount and duct condition are not established.'},
   {pattern:/start|apu|inlet/i,areas:[0,1],text:'An APU symptom is reported. The unit and inlet are shown as possible investigation areas, not diagnosed failures.'}]),
 stabilizer:profile('Horizontal stabilizer structure','Tailplane · fixed surface and root joint',[
  part('Stabilizer skin','Fixed surface','The tapered panel shows the fixed tailplane surface.'),part('Spar reinforcement','Internal support','The internal members show the illustrated support region.'),part('Root fitting','Fuselage joint','The inboard fitting marks the attachment in this layout.')],[[467,145],[367,181],[180,183]],
  `<path ${skin} d="M131 76 701 161 634 267 131 251Z"/><path d="M157 129 671 183M157 216 642 234" stroke="#668c77" stroke-width="7"/>${[245,347,449,551].map((x,i)=>`<path d="M${x} ${96+i*15}V${247-i*4}" stroke="#9bb7a3" stroke-width="4"/>`).join('')}<rect x="121" y="126" width="68" height="107" rx="9" fill="#d4c5a6" stroke="#9e8a61"/>`,
  'Left horizontal stabilizer crack',[
   {pattern:/crack|corrosion|dent|damage/i,areas:[0,1,2],text:'A tailplane structural symptom is reported. Surface damage and internal load-path damage must remain distinct until inspected.'}]),
 elevator:profile('Elevator control assembly','Tail trailing edge · hinge and input linkage',[
  part('Elevator panel','Moving tail surface','The lower panel shows the illustrated movable surface.'),part('Hinge supports','Pivot line','The upper fittings mark the illustrated pivot.'),part('Input linkage','Control connection','The amber linkage represents the input connection.')],[[493,233],[488,117],[265,188]],
  `<path ${skin} d="M111 72 687 112 655 145 115 127Z"/><path ${metal} d="M128 153 655 170 618 278 145 244Z"/><path d="M141 140 649 156" stroke="#668d76" stroke-width="7"/>${[190,357,524].map(x=>`<rect x="${x}" y="126" width="30" height="47" rx="6" fill="#d5c4a3" stroke="#9a8457"/>`).join('')}<path d="M264 85V201L350 220" class="ce-flow"/><path d="M696 214q23-31-5-55" fill="none" stroke="#92ad9b" stroke-width="2"/>`,
  'Right elevator stiff movement',[
   {pattern:/stiff|stuck|jam|movement|play|vibrat/i,areas:[0,1,2],text:'Abnormal elevator movement is reported. The panel, hinge and input connection are candidates; none is confirmed failed.'}]),
 rudder:profile('Vertical fin & rudder','Vertical tail · fixed fin and hinged surface',[
  part('Rudder surface','Moving vertical panel','The narrow rear panel is the illustrated rudder.'),part('Hinge attachments','Vertical pivot','The three fittings mark the pivot line.'),part('Control input','Base connection','The amber connection marks a generic control input.')],[[567,160],[493,135],[484,256]],
  `<path ${skin} d="M163 272 375 56 483 62 497 272Z"/><path ${metal} d="M506 64 595 99 625 272 510 272Z"/><path d="M491 70V267" stroke="#6a8e77" stroke-width="6"/>${[106,168,227].map(y=>`<rect x="478" y="${y}" width="40" height="20" rx="5" fill="#dccaa9" stroke="#a28a59"/>`).join('')}<path d="M285 267H554L555 231" class="ce-flow"/><path d="M273 234 396 91M334 244 425 96" stroke="#aac4af" stroke-width="4"/>`,
  'Rudder hinge excessive play',[
   {pattern:/hinge|play/i,areas:[1],text:'Rudder hinge play is reported. The amount, limit comparison and affected fitting are not available.'},
   {pattern:/stuck|stiff|jam|pedal|movement/i,areas:[0,1,2],text:'A rudder control symptom is reported. The mechanical and input paths require evidence before isolating a cause.'}])
};
airframeProfiles.apu.source='https://www.faa.gov/sites/faa.gov/files/regulations_policies/handbooks_manuals/aviation/FAA-H-8083-32-AMT-Powerplant-Vol-2.pdf';
export function getAirframeProfile(component) {
 const key=({ 'seg-nose':'nose','seg-cockpit':'cockpit','seg-avionics':'avionics','seg-fuselage-fwd':'cabin_fwd','seg-fuselage-aft':'cabin_aft','seg-center-box':'center','seg-apu':'apu','seg-rudder':'rudder' })[component] || (/^seg-tail-[lr]$/.test(component)?'stabilizer':/^seg-elevator-[lr]$/.test(component)?'elevator':null);
 return key?{...airframeProfiles[key],key}:null;
}
export function airframeProfileScenario(profile, query) {
 const q=(query||'').trim();
 if(!q || /\b(no|without|not)\b.{0,24}\b(leak|crack|fault|damage|play)/i.test(q))return null;
 const rule=profile.rules.find(r=>r.pattern.test(q));
 const parts=rule?.areas || profile.parts.map((_,i)=>i);
 const structural=['center','stabilizer'].includes(profile.key) && /crack|fracture|corrosion/i.test(q);
 const effects={
  nose:'A damaged radome does not by itself establish radar failure. Shell extent, attachment condition and relevant equipment observations are needed to assess consequences.',
  cockpit:'The impact on visibility or pane heating is not established. The affected layer, reported visibility and heating observations are needed; a failure timeline cannot be inferred.',
  avionics:'The record does not identify a failed unit. Whether the interruption repeats or affects other equipment requires actual event and connection observations.',
  cabin_fwd:'The leak path and material involved are not established. Further effects depend on the entry point, extent and actual inspection findings.',
  cabin_aft:'Continuing leakage could impair pressure retention if the report is confirmed. The leak rate, affected boundary and measured pressure trend remain unknown.',
  center:'Structural significance cannot be inferred from the component name. Location, material, damage extent and inspection findings are needed.',
  apu:'Vibration or an unsuccessful start does not identify a damaged APU. Actual indications, the operating context and mount/inlet/exhaust observations are needed.',
  stabilizer:'Whether the fixed surface or its attachment is affected needs inspection evidence. Further damage or timing cannot be predicted from this report.',
  elevator:'Whether commanded travel is restricted remains unresolved. Actual travel, measured hinge play and linkage findings are needed before assessing consequences.',
  rudder:'Reported play does not establish loss of control or an impending failure. Measured play, the affected fitting and applicable limits remain missing.'
 };
 return {title:`Reported ${profile.name.toLowerCase()} issue`,parts,initial:parts[0],summary:rule?.text || 'This region is mentioned in the report. The internal source and extent are not identified.',effect:structural?'If structural damage progresses, the affected load path may be impaired. Location, extent, material and loading are needed to assess significance; progression and timing are not established.':effects[profile.key],source:structural?'https://www.faa.gov/documentlibrary/media/advisory_circular/ac_23-13a.pdf':null};
}
