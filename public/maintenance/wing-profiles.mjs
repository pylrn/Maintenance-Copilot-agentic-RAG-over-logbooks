// Authored generic cutaways. Region names describe illustrations, not model-specific hardware.
const controlSource = 'https://www.faa.gov/documentlibrary/media/advisory_circular/ac_65-15a.pdf';
const row = (name, role, text) => [name, role, `${text} Exact design and condition are unverified.`];
const link = '<path d="M160 110H640" fill="none" stroke="#78968a" stroke-width="5" stroke-dasharray="8 5"/>';
export const wingProfiles = {
 flaps: {
  name:'Flap mechanism',caption:'Trailing-edge section · track-guided movement',
  parts:[row('Flap panel','Moving surface','The illustrated panel extends behind the wing.'),row('Drive linkage','Movement input','Shows a generic drive connection.'),row('Track & carriage','Guided travel','Shows the panel support and travel path.')],
  points:[[530,227],[302,151],[432,175]],
  scene:`<path class="ce-shell" d="M80 95Q360 30 694 116L635 151H110Z"/><path d="M120 125H625" stroke="#638978" stroke-width="6"/><path d="M248 129Q296 199 429 204M377 130Q426 218 557 228" fill="none" stroke="#7f9d91" stroke-width="9"/><path class="ce-metal" d="M367 196 664 228 627 272 344 244Z"/><path d="M251 127 316 164 415 210" class="ce-flow"/><circle cx="432" cy="197" r="12" fill="#f4e4c9" stroke="#b38745" stroke-width="3"/><path d="M610 177l39 15m-13-13 13 13-17 1" stroke="#a3b8a9" fill="none" stroke-width="2"/>`
 },
 aileron: {
  name:'Aileron assembly',caption:'Outboard trailing edge · hinged surface',
  parts:[row('Aileron panel','Moving surface','The illustrated surface pivots about its hinge line.'),row('Hinge fittings','Pivot supports','Shows the attachment and pivot region.'),row('Control connection','Movement input','Shows a generic input linkage.')],
  points:[[509,216],[399,149],[250,184]],
  scene:`<path class="ce-shell" d="M90 66 695 108 656 149 105 135Z"/><path class="ce-metal" d="M105 157 656 171 626 275 130 239Z"/><path d="M118 146 651 160" stroke="#577d6c" stroke-width="6"/>${[194,400,591].map(x=>`<rect x="${x}" y="130" width="23" height="47" rx="7" fill="#efdfc2" stroke="#a88b58"/><circle cx="${x+11}" cy="151" r="6" fill="#8d7755"/>`).join('')}<path d="M250 90 250 204 322 214" class="ce-flow"/><path d="M650 231q35-18 12-50" fill="none" stroke="#9ab2a3" stroke-width="2"/>`
 },
 spoiler: {
  name:'Spoiler assembly',caption:'Upper wing surface · raised panel cutaway',
  parts:[row('Spoiler panel','Raised surface','Shows a panel above the wing surface.'),row('Actuator connection','Movement input','Shows an illustrative drive attachment.'),row('Hinge line','Panel attachment','Shows the pivot along the panel edge.')],
  points:[[459,105],[361,192],[555,228]],
  scene:`<path class="ce-shell" d="M95 204 672 164 715 267 125 293Z"/><path class="ce-metal" d="M224 210 577 231 625 92 321 65Z"/><path d="M224 210 577 231" stroke="#507564" stroke-width="8"/><path d="M300 259 405 130" stroke="#ae8a4d" stroke-width="15"/><path d="M322 230 395 142" stroke="#eedcb9" stroke-width="8"/><circle cx="298" cy="258" r="9" fill="#708f7d"/>${link}`
 },
 slats: {
  name:'Leading-edge slat',caption:'Forward wing section · extension gap',
  parts:[row('Slat surface','Forward element','Shows the movable leading-edge element.'),row('Support track','Guided travel','Shows a generic support and extension path.'),row('Wing nose interface','Adjacent structure','Shows the gap between the illustrated slat and wing.')],
  points:[[167,153],[334,160],[455,151]],
  scene:`<path class="ce-shell" d="M390 103Q533 80 711 165L711 226Q506 197 390 203Q321 158 390 103Z"/><path class="ce-metal" d="M110 91Q240 84 294 133L268 219Q130 225 92 174Q62 123 110 91Z"/><path d="M248 146 419 136M239 181 422 187" stroke="#8ea99a" stroke-width="9"/><path d="M251 146 340 141" stroke="#b48e50" stroke-width="7"/><path d="M323 85v40m0 69v46" stroke="#b2c6b7" stroke-width="2" stroke-dasharray="5 5"/>`
 },
 tank: {
  name:'Wing box & tank region',caption:'Internal volume · structure and fuel interfaces',
  parts:[row('Tank enclosure','Contained volume','Shows an illustrative enclosed tank region.'),row('Spars & ribs','Support framework','Shows internal structural members.'),row('Access covers','Enclosure interfaces','Shows an illustrative access opening.'),row('Feed & vent paths','Fluid interfaces','Shows schematic connections, not an actual routing.')],
  points:[[313,162],[455,140],[572,204],[211,236]],
  scene:`<path class="ce-shell" d="M100 68 700 124 642 267 112 244Z"/><path d="M125 129 673 167 644 240 123 213Z" fill="#b8dac777" stroke="#7baf96"/><g stroke="#709482" stroke-width="4">${[200,300,400,500,600].map((x,i)=>`<path d="M${x} ${78+i*9}l-8 ${157-i*11}"/>`).join('')}</g><path d="M118 109 685 151M120 218 649 239" stroke="#537963" stroke-width="6"/><ellipse cx="572" cy="207" rx="40" ry="19" fill="#edf5ee" stroke="#72927b" stroke-width="3"/><path d="M158 145V264H319" class="ce-flow"/>`
 },
 tip: {
  name:'Winglet & tip structure',caption:'Outer wing section · attachment cutaway',
  parts:[row('Winglet shell','Outer surface','Shows the upright tip surface.'),row('Root attachment','Joining region','Shows where this illustration meets the wing.'),row('Internal reinforcement','Support framework','Shows a generic internal support arrangement.')],
  points:[[502,93],[400,232],[479,160]],
  scene:`<path class="ce-shell" d="M97 215 371 183 456 229 371 289 111 269Z"/><path class="ce-metal" d="M369 221Q411 168 446 53L543 43Q554 153 468 255Z"/><path d="M400 222Q456 167 485 67" fill="none" stroke="#6e927e" stroke-width="7"/><path d="M411 197 503 173M430 157 521 126M445 113 531 84" stroke="#98b3a0" stroke-width="4"/><path d="M366 226 453 259" stroke="#b8955c" stroke-width="11"/>`
 }
};
export function getWingProfile(component) {
 const key = component.match(/^seg-wing-[lr]-(flaps|aileron|spoiler|slats|tank|tip)$/)?.[1];
 return key ? { ...wingProfiles[key], key, source:controlSource } : null;
}
export function wingProfileScenario(profile, query) {
 const q=(query||'').trim();
 if(!q || /\b(no|without|not)\b.{0,24}\b(leak|crack|fault|damage)/i.test(q))return null;
 const named=profile.parts.findIndex(([label])=>q.toLowerCase().includes(label.toLowerCase()));
 const parts=named>=0?[named]:profile.parts.map((_,i)=>i);
 return {title:`Reported ${profile.name.toLowerCase()} issue`,parts,initial:parts[0],summary:`The report mentions this region. The highlighted ${named>=0?'item is':'items are'} a visual reference, not a confirmed failed part. ${/flap|aileron|spoiler|slat/.test(profile.key)?'Actual versus commanded position and the inspection findings are still missing.':'Exact location, extent and inspection findings are still missing.'}`,effect:'The reported symptom alone does not establish further damage or a timeline. Log evidence and the applicable aircraft configuration are needed to assess consequences.',source:null};
}
