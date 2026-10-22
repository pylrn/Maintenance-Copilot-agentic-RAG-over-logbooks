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
    const answer = { answer_id: uid(), mode, status: matches.length ? 'partial_evidence' : 'insufficient_evidence',
      headline: matches.length ? `${matches.length} related demo ${matches.length === 1 ? 'case' : 'cases'} to explore` : 'No matching demo cases yet', findings: [], historical_actions: [],
      limitations: ['All rows and responses in demo mode are invented UI fixtures. No actual maintenance recommendation is produced.',
        'Aircraft model, applicability and the outcome of the recorded action are unknown.'],
      missing: ['Confirmed aircraft and engine configuration', 'Applicable approved documentation', 'Verified inspection observations'],
      allowed_actions: ['CHALLENGE', ...(matches.length >= 2 ? ['DISTINGUISH'] : []), 'SENSITIVITY', 'HYPOTHESIS'], simulated: true };
    if (mode === 'HYPOTHESIS') {
      answer.headline = 'Possible solutions — unverified';
      answer.limitations.unshift('This UI fixture does not generate repair hypotheses. The live service must provide a separately reviewed, bounded hypothesis envelope.');
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
