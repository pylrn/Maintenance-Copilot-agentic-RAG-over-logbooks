// UI fixtures ONLY: all rows, their matches and their events are simulated.
// No MaintNet file, retrieval engine, LLM, validator or production database is used.
import { uid } from './api-client.mjs';
import { componentDemoRows, matchComponentDemoRows } from './demo-component-cases.mjs';
const KEY = 'maintenance-atlas-explicit-demo-v2';
const copy = value => structuredClone(value);
const rows = [
  { domain: 'aviation', source_id: 'DEMO-001', corpus_version: 'aviation-v1', source_type: 'simulated', source_sha256: null,
    fields: { IDENT: 'DEMO-001', PROBLEM: '#2 INTAKE IS LEAKING.', ACTION: 'REMOVED & REPLACED #2 INTAKE GASKET.' } },
  { domain: 'aviation', source_id: 'DEMO-002', corpus_version: 'aviation-v1', source_type: 'simulated', source_sha256: null,
    fields: { IDENT: 'DEMO-002', PROBLEM: '#2 INTAKE IS LEAKING.', ACTION: 'REMOVED & REPLACED #2 INTAKE GASKET.' } },
  { domain: 'aviation', source_id: 'DEMO-003', corpus_version: 'aviation-v1', source_type: 'simulated', source_sha256: null,
    fields: { IDENT: 'DEMO-003', PROBLEM: 'L/H ENG #2 INTAKE LEAKING.', ACTION: 'REMOVED TUBE, FOUND TO BE CRACKED. REMOVED TUBE FROM CO' } },
  { domain: 'aviation', source_id: 'DEMO-004', corpus_version: 'aviation-v1', source_type: 'simulated', source_sha256: null,
    fields: { IDENT: 'DEMO-004', PROBLEM: '#2 ROCKER COVER GASKET LEAKING.', ACTION: 'REMOVED & REPLACED #2 ROCKER COVER GASKET.' } },
  { domain: 'aviation', source_id: 'DEMO-005', corpus_version: 'aviation-v1', source_type: 'simulated', source_sha256: null,
    fields: { IDENT: 'DEMO-005', PROBLEM: 'L/H WING FUEL LEAK AT INBOARD TANK ACCESS PANEL.', ACTION: 'RESEALED ACCESS PANEL AND PERFORMED PRESSURE LEAK CHECK.' } },
  { domain: 'aviation', source_id: 'DEMO-006', corpus_version: 'aviation-v1', source_type: 'simulated', source_sha256: null,
    fields: { IDENT: 'DEMO-006', PROBLEM: 'COCKPIT PFD INTERMITTENT BLANK SCREEN UPON STARTUP.', ACTION: 'RESEATED AVIONICS CIRCUIT BREAKER AND DISPLAY CONNECTOR.' } },
];
rows.push(
 {domain:'aviation',source_id:'DEMO-007',corpus_version:'demo-v2',source_type:'simulated',source_sha256:null,fields:{IDENT:'DEMO-007',PROBLEM:'OIL LEAK REPORTED BENEATH ENGINE 1. ORIGIN NOT CONFIRMED.',ACTION:'LOGGED OIL QUANTITY AND LEAK LOCATION FOR FURTHER ASSESSMENT.'}},
 {domain:'aviation',source_id:'DEMO-008',corpus_version:'demo-v2',source_type:'simulated',source_sha256:null,fields:{IDENT:'DEMO-008',PROBLEM:'OIL RESIDUE REPORTED NEAR AN ENGINE OIL LINE CONNECTION.',ACTION:'RECORDED CONNECTION AREA AS A POSSIBLE SOURCE. LEAK CAUSE AND OUTCOME NOT ESTABLISHED.'}}
);
rows.push(...componentDemoRows);
function match(query, topK = 5) {
 const text=(query||'').toLowerCase();
 let selected;
 const componentMatches=matchComponentDemoRows(query);
 if(componentMatches.length) selected=componentMatches;
 else if (/oil/.test(text)) selected=rows.filter(r=>r.source_id==='DEMO-007'||r.source_id==='DEMO-008');
 else if (/wing|fuel leak/.test(text)) selected=rows.filter(r=>r.source_id==='DEMO-005');
 else if (/cockpit|display|screen|avionics/.test(text)) selected=rows.filter(r=>r.source_id==='DEMO-006');
 else {
 const words=text.match(/[a-z0-9#]+/g)?.filter(x=>x.length>2&&!['the','from','there','with','that','have','please','show','find','engine','left','right'].includes(x))||[];
 selected=words.length?rows.filter(row=>words.some(word=>`${row.fields.PROBLEM} ${row.fields.ACTION}`.toLowerCase().includes(word))):[];
 }
 return selected.slice(0,topK);
}
export function createDemoApi() {
  let db;
  try { db = JSON.parse(localStorage.getItem(KEY)); } catch { /* reset only malformed demo data */ }
  db ||= { sessions: {}, runs: {} };
  function save() { localStorage.setItem(KEY, JSON.stringify(db)); }
  function session(id) { if (!db.sessions[id]) throw new Error('Demo session not found'); return db.sessions[id]; }
  function check(id, revision) { const value = session(id); if (value.revision !== revision) throw new Error('Demo state changed; restore the session and retry.'); return value; }
  function support(row, field) { return { kind: 'log_span', domain: row.domain, source_id: row.source_id,
    corpus_version: row.corpus_version, evidence_id: row.source_id, record_id: `aviation:${row.source_id}`,
    field, start: 0, end: Array.from(row.fields[field]).length, quote: row.fields[field], source_sha256: null, source_type: 'simulated' }; }
  function makeRun(id, payload, action = false) {
    const current = check(id, payload.expected_revision);
    if (current.active_run) throw new Error('Wait for the active demo run.');
    const query = payload.message || current.last_query || '';
    if (!action) {
      current.last_query = query; current.title = query.slice(0, 64);
      current.messages.push({ kind: 'user', text: query });
    }
    const mode = action ? payload.action : 'EVIDENCE';
    const matches = match(query, payload.search_spec?.top_k);
    const distinctActs = matches.map(r => r.fields.ACTION).filter(Boolean);
    const distinctProbs = matches.map(r => r.fields.PROBLEM).filter(Boolean);
    const qLower = (query || '').toLowerCase();

    let whatCan = [];
    if (matches.length > 0) {
      if (distinctActs.length > 0) {
        whatCan.push(`Technicians responding to these complaints documented corrective actions including: ${distinctActs.slice(0, 3).map(a => `<strong>${a}</strong>`).join(', ')}.`);
        const checks = distinctActs.filter(a => /leak|check|ck|ran|ops|test/i.test(a));
        if (checks.length > 0) {
          whatCan.push(`Post-maintenance operational runs and leak checks were recorded in history (e.g. <code>${checks[0].slice(0, 60)}</code>).`);
        }
      } else {
        whatCan.push(`Historical records document recorded maintenance events matching terms in ${matches.length} case(s).`);
      }
    } else {
      whatCan.push('No evidence found for this complaint in the historical records.');
    }

    const answer = {
      answer_id: uid(),
      mode,
      status: matches.length ? 'supported_historical' : 'insufficient_evidence',
      headline: matches.length ? `Found ${matches.length} relevant historical maintenance record(s) matching complaint.` : 'No matching maintenance records found in authorized corpus',
      summary: matches.length
        ? `Based on ${matches.length} distinct matching log record(s), historical complaints report ${distinctProbs[0] || query} with recorded corrective actions.`
        : 'No historical maintenance records found matching this fault complaint.',
      what_can_be_concluded: whatCan,
      what_cannot_be_concluded: [
        'Historical records omit specific airframe/engine serial applicability; historical records do not certify applicability to your specific aircraft.',
        'Historical log entries document past technician actions as written; they do not replace approved Aircraft Maintenance Manual (AMM) procedures.'
      ],
      findings: [],
      historical_actions: [],
      limitations: ['All rows and responses in demo mode are illustrative UI fixtures. No actual maintenance recommendation is produced.',
        'Aircraft model, applicability and the outcome of the recorded action are unknown.'],
      missing: ['Confirmed aircraft and engine configuration', 'Applicable approved documentation', 'Verified inspection observations'],
      allowed_actions: ['CHALLENGE', ...(matches.length >= 2 ? ['DISTINGUISH'] : []), 'SENSITIVITY', 'HYPOTHESIS'],
      simulated: true
    };

    if (mode === 'HYPOTHESIS') {
      answer.headline = 'Troubleshooting & Physical Mechanisms';
      if (/fuel|gas|smell|fume/i.test(qLower)) {
        answer.summary = `Troubleshooting assessment for '${query.slice(0, 50)}' grounded in FAA Aviation Maintenance Technician handbooks (FAA-H-8083) and AC 43.13-1B.`;
        answer.possible_explanations = [
          'Fuel injector boss or primer line connection seal relaxation allowing localized seeping under delivery pressure.',
          'Deteriorated fuel strainer bowl gasket or drain valve O-ring seal leaking into lower cowl cavity.',
          'Vapor migration through cowl ventilation passages into cabin air heat exchanger interface.'
        ];
        answer.basis = [
          '[FAA-H-8083-32B Powerplant Handbook, Ch. 2 Fuel Metering](https://www.faa.gov/sites/faa.gov/files/regulations_policies/handbooks_manuals/aviation/FAA-H-8083-32-AMT-Powerplant-Vol-2.pdf) - Fuel distribution lines and injection systems.',
          '[FAA AC 43.13-1B Section 8 Fuel Systems](https://www.faa.gov/regulations_policies/advisory_circulars/index.cfm/go/document.information/documentID/99861) - Fuel line inspection, clamp integrity, and leak limits.'
        ];
        answer.information_needed = [
          'Pressurize fuel system with auxiliary electric pump and perform mirror/flashlight leak inspection.',
          'Conduct carbon monoxide (CO) detector check during taxi ground run with cabin heat on.'
        ];
        answer.what_would_weaken_this = [
          'Zero fuel odor detected with fuel selector positioned to OFF.',
          'Odor identified as hydraulic fluid or hot electrical insulation rather than aviation gasoline.'
        ];
      } else if (/gear|brake|shimmy|tire|wheel/i.test(qLower)) {
        answer.summary = `Troubleshooting assessment for '${query.slice(0, 50)}' grounded in FAA Airframe Handbook (FAA-H-8083-31B) and AC 43.13-1B.`;
        answer.possible_explanations = [
          'Trapped air or vapor bubble in brake hydraulic supply lines causing compressible fluid displacement (spongy pedal feel).',
          'Internal hydraulic fluid bypass across worn master cylinder piston seals under applied pedal pressure.',
          'Excessive brake disc / lining wear or caliper binding requiring excessive fluid volume displacement before pad contact.'
        ];
        answer.basis = [
          '[FAA-H-8083-31B Airframe Handbook, Ch. 13 Landing Gear & Braking](https://www.faa.gov/documentlibrary/media/advisory_circular/ac_65-15a.pdf) - Master cylinder operation, brake bleeding, and caliper overhaul.',
          '[FAA AC 43.13-1B Ch. 9 Landing Gear Maintenance](https://www.faa.gov/regulations_policies/advisory_circulars/index.cfm/go/document.information/documentID/99861) - Hydraulic system bleeding, fluid specification (MIL-PRF-5606), and lining wear limits.'
        ];
        answer.information_needed = [
          'Perform reverse-pressure brake bleeding to purge trapped air bubbles from the brake caliper to the reservoir.',
          'Inspect master cylinder rod seal for fluid weepage and verify return spring mechanism travel.',
          'Measure brake lining thickness and rotor dishing with micrometer against manufacturer wear limits.'
        ];
        answer.what_would_weaken_this = [
          'Pedal remains firm and holds full pressure indefinitely without bottoming out.',
          'Brake line pressure gauges confirm instantaneous hydraulic pressure rise upon initial pedal displacement.'
        ];
      } else {
        answer.summary = `Troubleshooting analysis for '${query.slice(0, 50)}' grounded in FAA Aviation Maintenance Technician handbooks (FAA-H-8083) and AC 43.13-1B.`;
        answer.possible_explanations = [
          'Thermal cycling causing fastener torque relaxation at gasket/seal junctions under operating cycles.',
          'Localized sealing interface corrosion or flange warping preventing uniform gasket seating.',
          'Secondary migration from overhead component seals pooling at lower interfaces.'
        ];
        answer.basis = [
          '[FAA-H-8083-32B Powerplant Handbook, Ch. 1 & 10](https://www.faa.gov/sites/faa.gov/files/regulations_policies/handbooks_manuals/aviation/FAA-H-8083-32-AMT-Powerplant-Vol-2.pdf) - Induction sealing, cylinder assemblies, and lubrication circuits.',
          '[FAA AC 43.13-1B Aircraft Inspection & Repair](https://www.faa.gov/regulations_policies/advisory_circulars/index.cfm/go/document.information/documentID/99861) - Torque relaxation, gasket replacement, and leak check procedures.'
        ];
        answer.information_needed = [
          'Clean and degrease component area, apply developer powder, and perform ground run to trace exact origin.',
          'Verify fastener torque values against engine manufacturer overhaul manual specifications.'
        ];
        answer.what_would_weaken_this = [
          'Component joint verified dry with leak originating entirely from remote breather or accessory pad.',
          'Ground run under pressure fails to replicate any fluid egress.'
        ];
      }
      answer.assumptions = [
        'Operating parameters conform to approved aircraft operating handbook (POH/AFM) limitations.',
        'Hydraulic fluid and component hardware strictly match approved type certificate specifications.'
      ];
      answer.limits = [
        'UNVERIFIED HYPOTHESIS: Conceptual engineering troubleshooting only, NOT certified AMM maintenance instructions.',
        'Do not perform aircraft maintenance without applicable approved type certificate manuals and licensed A&P signoff.'
      ];
    } else if (mode === 'SENSITIVITY') {
      answer.headline = 'Sensitivity action received — simulated demonstration';
      answer.limitations.unshift('No sensitivity metric has been computed here. The live service must return a validated search-comparison receipt.');
    } else if (mode === 'CHALLENGE') {
      answer.headline = 'Challenge: the rows do not establish a successful repair';
    } else if (mode === 'DISTINGUISH') {
      answer.headline = 'Distinguish the reported complaints in the simulated rows';
    }
    if (mode !== 'HYPOTHESIS' && mode !== 'SENSITIVITY') {
      answer.findings = matches.map(row => ({ claim_id: uid(), text: `${row.source_id} reports: ${row.fields.PROBLEM}`,
        supports: [support(row, 'PROBLEM')] }));
      if (mode === 'EVIDENCE') answer.historical_actions = matches.map(row => ({ claim_id: uid(),
        text: `${row.source_id} records: ${row.fields.ACTION}`, supports: [support(row, 'ACTION')] }));
    }
    const runId = uid(); const events = [];
    const add = (type, data) => events.push({ protocol_version: 'maintenance/v1', run_id: runId,
      sequence: events.length + 1, type, created_at: new Date().toISOString(), data });
    add('run_started', { mode, simulated: true });
    add('query_interpreted', { query, domain: 'aviation', applicability: 'unknown' });
    add('tool_started', { tool_call_id: 'fixture-search', tool_name: 'search_simulated_rows', args: { query } });
    add('tool_completed', { tool_call_id: 'fixture-search', tool_name: 'search_simulated_rows', summary: `${matches.length} simulated rows matched`, result: { record_ids: matches.map(x => x.source_id), simulated: true } });
    add('evidence_ready', { records: matches });
    add('validation_started', { summary: 'Fixture playback — no production validator is running' });
    const board = { known: [{ text: query, origin: 'User-reported query; not independently verified' }],
      reported: matches.map(row => ({ text: row.fields.PROBLEM, origin: row.source_id + ' · simulated' })),
      missing: answer.missing.map(text => ({ text, origin: 'Unavailable in simulated records' })) };
    add('board_updated', { board }); add('answer_validated', { answer }); add('done', {});
    db.runs[runId] = { id, events, delivered: 0, answer, records: matches, board, committed: false };
    current.active_run = { run_id: runId }; current.revision++; save();
    return { run_id: runId, session_revision: current.revision };
  }
  return {
    async capabilities() { return { models: [{ id: 'fixture-playback', label: 'simulated playback · no LLM' }],
      domains: ['aviation'], corpus_summary: `${rows.length} invented demo records · live logbook connection in progress`,
      examples: [{ query: 'Engine 1 oil leak', source_type: 'simulated' }, { query: 'Low compression at cylinder 2', source_type: 'simulated' }],
      rerank_available: false, visual_available: false, simulated: true }; },
    async listSessions() { return { items: Object.values(db.sessions).map(x => ({ session_id: x.session_id, title: x.title, revision: x.revision })).reverse() }; },
    async session(id) { return copy(session(id)); },
    async createSession(domain) {
      const id = uid(); db.sessions[id] = { session_id: id, domain, title: 'New simulated investigation', revision: 0,
        messages: [], records: [], board: { known: [], reported: [], missing: [] }, pins: [], active_run: null };
      save(); return copy(db.sessions[id]);
    },
    async message(id, payload) { return makeRun(id, payload); },
    async action(id, payload) {
      if (!session(id).messages.some(x => x.answer?.answer_id === payload.parent_answer_id)) throw new Error('Parent answer is not in this investigation');
      return makeRun(id, payload, true);
    },
    async subscribe(runId, onEvent, { signal, after = 0 } = {}) {
      for (;;) {
        if (signal?.aborted) throw new DOMException('Aborted', 'AbortError');
        const run = db.runs[runId]; if (!run) throw new Error('Demo run not found');
        const event = run.events.find(x => x.sequence > after); if (!event) return;
        await new Promise(resolve => setTimeout(resolve, 130));
        if (signal?.aborted) throw new DOMException('Aborted', 'AbortError');
        // Cancellation may have replaced the pending fixture event while waiting.
        if (db.runs[runId].events.find(x => x.sequence === event.sequence) !== event) continue;
        run.delivered = event.sequence;
        if (event.type === 'done' && !run.committed) {
          const value = session(run.id);
          if (!run.cancelled) { value.messages.push({ kind: 'answer', answer: run.answer }); value.records = run.records; value.board = run.board; }
          value.active_run = null; value.revision++; run.committed = true; save();
        }
        await onEvent(copy(event)); after = event.sequence;
        if (event.type === 'done') return;
      }
    },
    async cancel(runId) {
      const run = db.runs[runId]; if (!run || run.committed) return;
      run.cancelled = true; run.events = run.events.slice(0, run.delivered);
      for (const type of ['run_cancelled', 'done']) run.events.push({ protocol_version: 'maintenance/v1', run_id: runId,
        sequence: run.events.length + 1, type, created_at: new Date().toISOString(), data: {} }); save();
    },
    async search(spec) { return { records: copy(match(spec.query, spec.top_k)), simulated: true }; },
    async record(ref) { const row = rows.find(x => x.source_id === ref.source_id); if (!row) throw new Error('Demo row not found'); return copy(row); },
    async pin(id, record, selected, revision) {
      const value = check(id, revision); value.pins = value.pins.filter(x => x.source_id !== record.source_id);
      if (selected) value.pins.push(copy(record)); value.revision++; save(); return copy(value);
    },
    async upload(id, file, revision) {
      const value = check(id, revision);
      if (!/\.(txt|md)$/i.test(file.name)) throw new Error('Demo mode supports text files only. PDF extraction requires the live service.');
      const text = (await file.text()).slice(0, 8000);
      value.board.known.push({ text, origin: 'User-uploaded text · unverified · ' + file.name }); value.revision++; save();
      return { text, source_type: 'user_upload', status: 'extracted' };
    },
    async handover(id) {
      const value = session(id); return '# SIMULATED Maintenance Atlas handover\n\n' +
        'Invented UI fixtures only. No maintenance recommendation.\n\n' +
        value.messages.filter(x => x.answer && x.answer.mode !== 'HYPOTHESIS').map(x =>
          '## ' + x.answer.headline + '\n\n' + x.answer.findings.map(c => c.text + ' [' + c.supports.map(s => s.source_id).join(', ') + ']').join('\n') + '\n\n' + x.answer.limitations.join('\n')).join('\n\n');
    },
  };
}
