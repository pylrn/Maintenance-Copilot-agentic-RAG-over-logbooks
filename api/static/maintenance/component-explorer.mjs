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
function el(tag, cls, text) { const n = document.createElement(tag); n.className = cls; if (text) n.textContent = text; return n; }
function diagram(kind) {
 const engine = `<path class="ce-shell" d="M90 126 Q130 70 260 92 L600 116 716 170 600 228 260 252 Q130 274 90 218Z"/><path class="ce-metal" d="M155 148 590 148 664 174 590 200 155 200Z"/><g stroke="#7b94a7" stroke-width="5">${Array.from({length:16},(_,i)=>`<path d="M${190+i*25} 145 l-10 ${i<8?-30:-18} M${190+i*25} 202 l-10 ${i<8?30:18}"/>`).join('')}</g><ellipse cx="145" cy="174" rx="27" ry="66" class="ce-metal"/><path d="M145 113V235M125 125l40 98M165 125l-40 98" stroke="#8ba1b2" stroke-width="4"/><path d="M260 76H410V118H495V160M495 188V278H260V105" class="ce-flow"/><rect x="218" y="40" width="85" height="57" rx="12" class="ce-reservoir"/><path d="M226 76h69" stroke="#c98534" stroke-width="3"/><circle cx="495" cy="174" r="18" class="ce-bearing"/>`;
 const wing = `<path class="ce-shell" d="M130 64 705 151 635 288 115 251Z"/><path class="ce-metal" d="M139 116 675 172 647 228 130 211Z"/><g stroke="#8ba1b2" stroke-width="3">${Array.from({length:9},(_,i)=>`<path d="M${177+i*53} ${74+i*8}l-12 ${174-i*9}"/>`).join('')}</g><path d="M140 116 675 172M130 211 647 228" stroke="#314f66" stroke-width="6"/><path d="M133 233 635 258" stroke="#c98534" stroke-width="9"/>`;
 const avionics = `<path class="ce-shell" d="M100 95Q400 10 700 95L730 269H70Z"/><rect x="127" y="111" width="173" height="114" rx="12" class="ce-metal"/><path d="M145 170h135m-67-42v80" stroke="#648ea5" stroke-width="2"/><path d="M300 170H420V85H595V234H420V170" class="ce-flow"/><rect x="365" y="141" width="103" height="65" rx="9" class="ce-metal"/><rect x="542" y="61" width="104" height="54" rx="9" class="ce-reservoir"/><rect x="535" y="222" width="126" height="58" rx="9" class="ce-metal"/>`;
 const structure = `<path class="ce-shell" d="M105 200Q140 55 410 65T710 200Q660 294 410 278T105 200Z"/><g fill="none" stroke="#8ba1b2" stroke-width="3">${[210,310,410,510,610].map(x=>`<ellipse cx="${x}" cy="174" rx="32" ry="90"/>`).join('')}<path d="M132 174H690M170 118H650M170 231H650"/></g>`;
 const points = kind==='engine'?[[260,66],[396,117],[495,174],[370,278]]:kind==='wing'?[[281,93],[390,160],[514,211],[408,253]]:kind==='avionics'?[[210,165],[416,172],[593,86],[595,249]]:[[185,174],[310,126],[510,229],[648,174]];
 return `<svg viewBox="0 0 800 330" role="img" aria-label="Illustrative ${kind} component schematic"><defs><pattern id="ce-grid" width="24" height="24" patternUnits="userSpaceOnUse"><path d="M24 0H0V24" fill="none" stroke="#dce5eb" stroke-width=".6"/></pattern></defs><rect width="800" height="330" fill="url(#ce-grid)"/>${{engine,wing,avionics,structure}[kind]}${points.map(([x,y],i)=>`<g class="ce-hotspot" data-part="${i}" role="button" tabindex="0" aria-label="Explore ${catalogs[kind][i][0]}"><circle cx="${x}" cy="${y}" r="16"/><text x="${x}" y="${y+5}" text-anchor="middle">${i+1}</text></g>`).join('')}<text x="24" y="309" class="ce-svg-note">ILLUSTRATIVE / NOT TO SCALE / CONFIGURATION UNKNOWN</text></svg>`;
}
export function renderComponentExplorer(component, name, query) {
 const kind = /engine/.test(component)?'engine':/wing/.test(component)?'wing':/cockpit|avionics/.test(component)?'avionics':'structure';
 document.getElementById('drilldownTitle').textContent = name.replace(/\(.*\)/,'').trim();
 document.getElementById('drilldownBadge').textContent = 'ILLUSTRATIVE';
 document.getElementById('drilldownBadge').className = 'drilldown-diag-badge';
 document.getElementById('drilldownText').textContent = 'Select a numbered region to explore its role. No live telemetry or model-specific geometry is connected.';
 const canvas = document.getElementById('drilldownCanvas'); canvas.replaceChildren();
 const top=el('div','ce-intro'); top.append(el('span','ce-eyebrow','COMPONENT ATLAS / '+kind.toUpperCase()),el('h3','','Explore the system beneath the surface'),el('p','','Select a region, trace its connections, and keep observations separate from possibilities.')); canvas.append(top);
 const layout=el('div','ce-layout'), drawing=el('div','ce-drawing'); drawing.innerHTML=diagram(kind);
 const sidebar=el('div','ce-parts'), detail=el('div','ce-part-detail'); detail.setAttribute('aria-live','polite');
 const select=i=>{ sidebar.querySelectorAll('button').forEach((b,j)=>b.setAttribute('aria-pressed',String(i===j))); drawing.querySelectorAll('.ce-hotspot').forEach((n,j)=>n.classList.toggle('selected',i===j)); detail.replaceChildren(el('span','ce-eyebrow',catalogs[kind][i][1]),el('h4','',catalogs[kind][i][0]),el('p','',catalogs[kind][i][2])); };
 catalogs[kind].forEach(([label,role],i)=>{const b=el('button','ce-part');b.type='button';b.append(el('span','ce-number',String(i+1)),el('span','',label),el('small','',role));b.onclick=()=>select(i);sidebar.append(b);});
 drawing.querySelectorAll('[data-part]').forEach(n=>{n.onclick=()=>select(Number(n.dataset.part));n.onkeydown=e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();select(Number(n.dataset.part));}};});
 sidebar.append(detail);layout.append(drawing,sidebar);canvas.append(layout);select(0);
 const context=el('p','ce-context');context.textContent=query.trim()?`Reported context: “${query.slice(0,300)}” · location and cause unverified.`:'No fault context selected. Exploring a component does not establish a fault.';canvas.append(context);
 if(kind==='engine') {
 const toggle=el('button','ce-progression-toggle','Explore oil-loss progression · unverified');toggle.type='button';toggle.setAttribute('aria-expanded','false');
 const panel=el('section','ce-progression');panel.hidden=true;
 panel.append(el('span','ce-eyebrow','CONDITIONAL SCENARIO / GENERAL EDUCATIONAL CONTEXT'),el('h3','','If an oil leak continues, what could follow?'),el('p','','Oil circulates through storage, supply, lubricated parts and return paths; it is not simply consumed at one endpoint. A visible leak does not identify its origin. This sequence is a conceptual scenario, not a diagnosis, forecast or log-derived finding.'));
 const branches=el('div','ce-branches');['Storage / reservoir','Lines / fittings / housings','Bearing spaces / seals / return'].forEach(t=>branches.append(el('span','',t)));panel.append(el('p','ce-eyebrow','POSSIBLE SOURCE AREAS — NONE CONFIRMED'),branches);
 const stages=[['Reported symptom','Oil leakage is the scenario input. Source, rate and quantity remain unknown.'],['If net oil loss continues','Available oil may decrease if loss exceeds replenishment. Leakage alone does not prove low pressure.'],['If lubrication becomes inadequate','Bearing cooling and lubrication may be impaired; temperature and wear may increase.'],['If severe impairment persists','Bearing damage and impaired engine operation are possible. This outcome is not inevitable.']];
 const controls=el('div','ce-stages'), output=el('div','ce-stage-detail');output.setAttribute('aria-live','polite');
 stages.forEach(([label,description],i)=>{const b=el('button','',`${String(i+1).padStart(2,'0')}  ${label}`);b.type='button';b.onclick=()=>{controls.querySelectorAll('button').forEach((v,j)=>v.setAttribute('aria-pressed',String(i===j)));output.replaceChildren(el('h4','',label),el('p','',description));};controls.append(b);});panel.append(controls,output);controls.firstChild.click();
 panel.append(el('p','ce-missing','Needed to assess this case: engine configuration, leak origin and rate, oil quantity trend, pressure/temperature indications, and applicable source records. No time-to-damage or failure probability is available.'));
 const link=el('a','ce-source','Basis: FAA Powerplant Handbook, Vol. 2 · lubrication systems');link.href=source;link.target='_blank';link.rel='noopener noreferrer';panel.append(link);
 toggle.onclick=()=>{panel.hidden=!panel.hidden;toggle.setAttribute('aria-expanded',String(!panel.hidden));};canvas.append(toggle,panel);
 } else {canvas.append(el('p','ce-context','Progression scenarios are currently available for engine oil loss only. No damage progression is inferred for this component.'));}
}
