import { getAirframeProfile, airframeProfileScenario } from './airframe-profiles.mjs';
import { getWingProfile, wingProfileScenario } from './wing-profiles.mjs';
// Authored illustrative geometry. No sensor, source-record, or aircraft-model authority.
const source = 'https://www.faa.gov/sites/faa.gov/files/regulations_policies/handbooks_manuals/aviation/FAA-H-8083-32-AMT-Powerplant-Vol-2.pdf';
const catalogs = {
 engine: [
  ['Reservoir', 'Storage', 'Stores the oil supply. A reported leak does not establish whether the reservoir is its origin.'],
  ['Supply circuit', 'Transfer', 'Pump, filter, cooler and connecting lines form the illustrative supply circuit. Fittings and housings are separate possible source areas.'],
  ['Bearing spaces', 'Lubrication', 'Oil lubricates and carries heat away from bearings. Seals and return paths depend on the engine configuration.'],
  ['Return circuit', 'Recovery', 'Scavenge paths return oil from bearing spaces. A visible drip may travel from another location before appearing here.']
 ],
 wing: [
  ['Leading edge', 'Forward structure', 'Generic leading-edge region. Slat configuration and internal equipment vary by aircraft.'],
  ['Spar & ribs', 'Load path', 'Spars and ribs form the illustrated internal framework. This drawing does not identify a crack, station or measured stress.'],
  ['Wing box', 'Enclosed structure', 'Illustrative wing-box area. Tank boundaries, plumbing and access locations require the applicable aircraft documentation.'],
  ['Trailing edge', 'Control surfaces', 'Generic flap and aileron region. No actuator condition or control-system fault has been established.']
 ],
 avionics: [
  ['Display', 'Presentation', 'A reported display symptom does not establish a failed display unit.'],
  ['Data interface', 'Signal path', 'Illustrates connections between display and avionics. Actual bus topology is configuration dependent.'],
  ['Power supply', 'Electrical supply', 'Illustrative power interface. No voltage readings or breaker state are available.'],
  ['Avionics units', 'Processing', 'Generic equipment blocks. This is not a wiring diagram or a component replacement recommendation.']
 ],
 structure: [
  ['Outer surface', 'Exterior', 'Illustrative exterior region. No damage is inferred from selecting this component.'],
  ['Internal frame', 'Support', 'Generic internal support arrangement; geometry and material are unknown.'],
  ['Attachment', 'Interface', 'Connections depend on the aircraft configuration. Exact fasteners and access points are not mapped.'],
  ['Adjacent structure', 'Context', 'Surrounding structure is shown for orientation only.']
 ]
};
// A query selects an illustrative scenario, never a diagnosed internal defect.
export function issueScenario(kind, query) {
 const q=(query||'').toLowerCase();
 if (!q.trim() || /\b(no|without|not)\b.{0,24}\b(leak|crack|fault|damage)/.test(q)) return null;
 if(kind==='engine' && /oil/.test(q) && /leak|loss|residue|drip/.test(q)) return {title:'Oil leak · origin unconfirmed',parts:[0,1,2,3],initial:1,summary:'Oil is reported outside the system. Storage, supply connections, seals and return paths are possible source areas; the drawing cannot identify which is leaking.',effect:'If net oil loss continues and lubrication becomes inadequate, bearing cooling may decline and wear or damage may follow. No timeline or inevitable outcome is established.',source};
 if(kind==='wing' && /fuel/.test(q) && /leak|loss/.test(q)) return {title:'Reported wing leak · source unconfirmed',parts:[2],initial:2,summary:'The wing-box area is highlighted as an illustrative tank region. The exact tank boundary, leak path and failed part are unknown.',effect:'Continued fuel loss could reduce available fuel. Escaping fuel exposed to an ignition source can create a fire hazard. Neither outcome nor timing is predicted for this case.',source:'https://www.faa.gov/lessons_learned/transport_airplane/accidents/B18616'};
 if(kind==='wing' && /crack|fracture/.test(q)) return {title:'Reported cracking · extent unknown',parts:[1],initial:1,summary:'The spar-and-rib region is an illustrative structural reference. The crack location, size and load path are not established.',effect:'If a structural crack grows, load-carrying capability can be affected. Growth rate and significance require configuration-specific assessment.',source:'https://www.faa.gov/documentlibrary/media/advisory_circular/ac_23-13a.pdf'};
 if(kind==='wing' && /flap|aileron|spoiler|slat/.test(q)) return {title:'Reported wing control issue',parts:[/slat/.test(q)?0:3],initial:/slat/.test(q)?0:3,summary:'The named control-surface region is highlighted. The actuator, linkage, electrical supply and exact failure location have not been identified.',effect:'A symptom alone does not establish further damage. Surface position, commanded versus observed movement, and applicable inspection findings are needed to assess what could follow.',source:null};
 if(kind==='wing' && /wing/.test(q)) return {title:'Reported wing issue · area unconfirmed',parts:[0,1,2,3],initial:1,summary:'The report refers to the wing without identifying an internal source. These regions are candidates for orientation, not diagnosed failures.',effect:'Further complications cannot be inferred until the symptom, location, extent and aircraft configuration are established.',source:null};
 if(kind==='avionics' && /blank|display|screen|pfd|intermittent/.test(q)) return {title:'Reported display interruption',parts:[0,1,2],initial:0,summary:'A blank screen is the reported symptom. The display, data interface and power supply are candidate areas, not confirmed failed units.',effect:'The missing information is what remains visible, whether other displays are affected, and whether power or data interruptions were recorded. Further damage cannot be inferred from this symptom.',source:null};
 return null;
}
function el(tag, cls, text) { const n = document.createElement(tag); n.className = cls; if (text) n.textContent = text; return n; }
function diagram(kind, profile = null) {
 const items=profile?.parts || catalogs[kind];
 const engine = `<path class="ce-shell" d="M90 126 Q130 70 260 92 L600 116 716 170 600 228 260 252 Q130 274 90 218Z"/><path class="ce-metal" d="M155 148 590 148 664 174 590 200 155 200Z"/><g stroke="#7b94a7" stroke-width="5">${Array.from({length:16},(_,i)=>`<path d="M${190+i*25} 145 l-10 ${i<8?-30:-18} M${190+i*25} 202 l-10 ${i<8?30:18}"/>`).join('')}</g><ellipse cx="145" cy="174" rx="27" ry="66" class="ce-metal"/><g transform="translate(145 174) scale(.38 1)"><g class="ce-rotor">${Array.from({length:10},(_,i)=>`<path d="M0 -8 Q22 -42 9 -59 Q-6 -40 -4 -12Z" transform="rotate(${i*36})" fill="#7899aa"/>`).join('')}<circle r="9" fill="#345a70"/></g></g><path d="M260 76H410V118H495V160M495 188V278H260V105" class="ce-flow"/><rect x="218" y="40" width="85" height="57" rx="12" class="ce-reservoir"/><path d="M226 76h69" stroke="#c98534" stroke-width="3"/><circle cx="495" cy="174" r="18" class="ce-bearing"/>`;
 const wing = `<path class="ce-shell" d="M130 64 705 151 635 288 115 251Z"/><path class="ce-metal" d="M139 116 675 172 647 228 130 211Z"/><g stroke="#8ba1b2" stroke-width="3">${Array.from({length:9},(_,i)=>`<path d="M${177+i*53} ${74+i*8}l-12 ${174-i*9}"/>`).join('')}</g><path d="M140 116 675 172M130 211 647 228" stroke="#314f66" stroke-width="6"/><path d="M133 233 635 258" stroke="#c98534" stroke-width="9"/>`;
 const avionics = `<path class="ce-shell" d="M100 95Q400 10 700 95L730 269H70Z"/><rect x="127" y="111" width="173" height="114" rx="12" class="ce-metal"/><path d="M145 170h135m-67-42v80" stroke="#648ea5" stroke-width="2"/><path d="M300 170H420V85H595V234H420V170" class="ce-flow"/><rect x="365" y="141" width="103" height="65" rx="9" class="ce-metal"/><rect x="542" y="61" width="104" height="54" rx="9" class="ce-reservoir"/><rect x="535" y="222" width="126" height="58" rx="9" class="ce-metal"/>`;
 const structure = `<path class="ce-shell" d="M105 200Q140 55 410 65T710 200Q660 294 410 278T105 200Z"/><g fill="none" stroke="#8ba1b2" stroke-width="3">${[210,310,410,510,610].map(x=>`<ellipse cx="${x}" cy="174" rx="32" ry="90"/>`).join('')}<path d="M132 174H690M170 118H650M170 231H650"/></g>`;
 const points = profile?.points || (kind==='engine'?[[260,66],[396,117],[495,174],[370,278]]:kind==='wing'?[[281,93],[390,160],[514,211],[408,253]]:kind==='avionics'?[[210,165],[416,172],[593,86],[595,249]]:[[185,174],[310,126],[510,229],[648,174]]);
 return `<svg viewBox="0 0 800 330" role="img" aria-label="Illustrative ${profile?.name || kind} schematic"><defs><pattern id="ce-grid" width="24" height="24" patternUnits="userSpaceOnUse"><path d="M24 0H0V24" fill="none" stroke="#dce5eb" stroke-width=".6"/></pattern></defs><rect width="800" height="330" fill="url(#ce-grid)"/>${profile?.scene || {engine,wing,avionics,structure}[kind]}${points.map(([x,y],i)=>`<ellipse class="ce-region" data-zone="${i}" cx="${x}" cy="${y}" rx="48" ry="27"/>`).join('')}${points.map(([x,y],i)=>`<g class="ce-hotspot" data-part="${i}" role="button" tabindex="0" aria-label="Explore ${items[i][0]}"><circle cx="${x}" cy="${y}" r="16"/><text x="${x}" y="${y+5}" text-anchor="middle">${i+1}</text></g>`).join('')}<text x="24" y="309" class="ce-svg-note">ILLUSTRATIVE / NOT TO SCALE / CONFIGURATION UNKNOWN</text></svg>`;
}
export function renderComponentExplorer(component, name, query, records = []) {
 const kind = /engine/.test(component)?'engine':/wing/.test(component)?'wing':/cockpit|avionics/.test(component)?'avionics':'structure';
 const airframeProfile = getAirframeProfile(component);
 const profile = getWingProfile(component) || airframeProfile;
 const items = profile?.parts || catalogs[kind];
 const genericScenario = issueScenario(kind, query);
 let scenario = airframeProfile ? airframeProfileScenario(airframeProfile, query) : profile ? wingProfileScenario(profile, query) : genericScenario;
 if(profile?.key === 'tank' && genericScenario) {
   if(/fuel/i.test(query) && /leak|loss/i.test(query)) scenario={...genericScenario,parts:[0,2,3],initial:2};
   else if(/crack|fracture/i.test(query)) scenario={...genericScenario,parts:[1],initial:1};
 }

 document.getElementById('drilldownTitle').textContent = name.replace(/\(.*\)/,'').trim();
 document.getElementById('drilldownBadge').textContent = 'ILLUSTRATIVE';
 document.getElementById('drilldownBadge').className = 'drilldown-diag-badge';
 document.getElementById('drilldownText').textContent = 'Select a numbered region to explore its role. No live telemetry or model-specific geometry is connected.';
 const canvas = document.getElementById('drilldownCanvas'); canvas.replaceChildren();
 const top=el('div','ce-intro'); top.append(el('span','ce-eyebrow',profile?.caption.toUpperCase() || 'COMPONENT ATLAS / '+kind.toUpperCase()),el('h3','',profile?.name || (scenario ? scenario.title : 'Inside this component')),el('p','',scenario ? 'Red marks possible source areas for your reported issue, not confirmed damage.' : 'Select a numbered region to explore its role.')); canvas.append(top);
 const layout=el('div','ce-layout'), drawing=el('div','ce-drawing'); drawing.innerHTML=diagram(kind, profile);
 if(profile){const reference=el('a','ce-profile-reference','Illustrative layout · FAA airframe reference');reference.href=profile.source;reference.target='_blank';reference.rel='noopener noreferrer';drawing.append(reference);}
 let noteFocus = null;
 drawing.querySelectorAll('[data-zone]').forEach(n=>n.classList.toggle('ce-region-alert',Boolean(scenario?.parts.includes(Number(n.dataset.zone)))));
 const sidebar=el('div','ce-parts'), detail=el('div','ce-part-detail'); detail.setAttribute('aria-live','polite');
 const select=i=>{ sidebar.querySelectorAll('.ce-part').forEach((b,j)=>b.setAttribute('aria-pressed',String(i===j))); drawing.querySelectorAll('.ce-hotspot').forEach((n,j)=>n.classList.toggle('selected',i===j)); detail.replaceChildren(el('span','ce-eyebrow',items[i][1]),el('h4','',items[i][0]),el('p','',items[i][2])); if(noteFocus) noteFocus.textContent=`Selected: ${items[i][0]} · condition unverified`; };
 items.forEach(([label,role],i)=>{const b=el('button','ce-part');b.type='button';b.append(el('span','ce-number',String(i+1)),el('span','',label),el('small','',role));if(scenario?.parts.includes(i)) b.classList.add('ce-part-suspect'); b.onclick=()=>select(i);sidebar.append(b);});
 drawing.querySelectorAll('[data-part]').forEach(n=>{n.classList.toggle('ce-suspect', Boolean(scenario?.parts.includes(Number(n.dataset.part))));n.onclick=()=>select(Number(n.dataset.part));n.onkeydown=e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();select(Number(n.dataset.part));}};});
 sidebar.append(detail);layout.append(drawing,sidebar);canvas.append(layout);select(scenario?.initial ?? 0);
 const context=el('p','ce-context');context.textContent=query.trim()?`Reported context: “${query.slice(0,300)}” · location and cause unverified.`:'No fault context selected. Exploring a component does not establish a fault.';top.append(context);
 if(scenario) {
 const note=el('aside','ce-issue-note');note.setAttribute('aria-label','Issue explanation');
 noteFocus=el('p','ce-issue-focus',`Selected: ${items[scenario.initial][0]} · condition unverified`);noteFocus.setAttribute('aria-live','polite');note.append(noteFocus);
 note.append(el('span','ce-eyebrow','REPORTED ISSUE / ILLUSTRATIVE SCENARIO'),el('h4','','What this could mean'),el('p','',scenario.summary));
 const reveal=el('button','ce-impact-toggle','What could follow?');reveal.type='button';reveal.setAttribute('aria-expanded','false');
 const effect=el('div','ce-impact');effect.hidden=true;effect.append(el('p','',scenario.effect),el('small','','Possibilities only · configuration, cause and severity are unverified.'));
 if(scenario.source){const link=el('a','ce-source','Educational source · FAA');link.href=scenario.source;link.target='_blank';link.rel='noopener noreferrer';effect.append(link);}
 reveal.onclick=()=>{effect.hidden=!effect.hidden;reveal.setAttribute('aria-expanded',String(!effect.hidden));};note.append(reveal,effect);sidebar.append(note);
 }

 const logNote=el('aside','ce-logs-note');logNote.setAttribute('aria-label','Matching historical records');
 logNote.append(el('span','ce-eyebrow','WHAT MATCHING LOGS RECORD / HISTORICAL EVIDENCE'));
 const recList=Array.isArray(records)?records:[];
 const compWords=(name||component||'').toLowerCase().split(/[\s-_/]+/).filter(w=>w.length>3);
 const matching=recList.filter(r=>{
   const text=(r.problem_raw||r.description_raw||r.summary||'').toLowerCase();
   return compWords.some(w=>text.includes(w));
 });
 const displayRecs=matching.length?matching.slice(0,2):recList.slice(0,1);
 if(displayRecs.length>0){
   for(const rec of displayRecs){
     const pText=rec.problem_raw||rec.description_raw||rec.summary||'Record text unavailable';
     logNote.append(el('h4','',`${rec.domain||'Source'} record [${rec.source_id}]`));
     logNote.append(el('p','',`Observed fault: “${pText.slice(0,220)}${pText.length>220?'…':''}”`));
     if(rec.action_raw){
       logNote.append(el('p','',`Recorded action: “${rec.action_raw.slice(0,220)}${rec.action_raw.length>220?'…':''}”`));
     }
   }
   logNote.append(el('small','','Historical log similarity does not establish aircraft applicability.'));
 }else{
   logNote.append(el('p','','No retrieved historical records currently loaded for this component. Run a search or prompt the copilot to view matching cases.'));
 }
 sidebar.append(logNote);
}
