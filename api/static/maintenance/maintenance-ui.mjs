// Complete proposed UI controller. Original source: ../reference/hybrid-search/.
import { createApi, uid } from './api-client.mjs';
const demo = new URLSearchParams(location.search).get('demo') === '1';
const api = demo ? (await import('./demo-adapter.mjs')).createDemoApi() : createApi();
const $ = id => document.getElementById(id);
const state = { session: null, capabilities: null, busy: false, run: null, cursor: 0, controller: null, records: [], turn: null };
const storageKey = `maintenance-atlas-${demo ? 'demo' : 'live'}-session-pointer`;
const labels = { CHALLENGE: 'Challenge answer', DISTINGUISH: 'Distinguish cases', SENSITIVITY: 'Search sensitivity', HYPOTHESIS: 'Possible solutions — unverified' };

// Map problem/query keywords to 2D aircraft schematic SVG segments
function detectAirframeSegments(text) {
  const query = (text || '').toLowerCase();
  const hits = [];
  if (/cylinder|intake|engine|powerplant|manifold|gasket|prop|rocker|carburetor|fuel pump|spark plug/i.test(query)) {
    if (/left|l\/h|#1|#3|engine 1/i.test(query)) hits.push({ id: 'seg-engine-l', name: 'Engine #1 (Left Powerplant)' });
    else hits.push({ id: 'seg-engine-r', name: 'Engine #2 (Right Powerplant)' });
  }
  if (/wing|slat|flap|aileron|spoiler|fuel tank/i.test(query)) {
    if (/left|l\/h/i.test(query)) hits.push({ id: 'seg-wing-l-inboard', name: 'Left Inboard Wing' });
    else hits.push({ id: 'seg-wing-r-inboard', name: 'Right Inboard Wing' });
  }
  if (/cockpit|avionics|windshield|instrument|mfd|pfd|pedal/i.test(query)) {
    hits.push({ id: 'seg-cockpit', name: 'Cockpit & Forward Avionics' });
  }
  if (/nose|radome|radar|nose gear|steer/i.test(query)) {
    hits.push({ id: 'seg-nose', name: 'Radome / Nose Cone' });
  }
  if (/tail|rudder|vertical fin|fin/i.test(query)) {
    hits.push({ id: 'seg-rudder', name: 'Vertical Stabilizer & Rudder' });
  }
  if (/elevator|stabilizer|horizontal/i.test(query)) {
    hits.push({ id: 'seg-tail-r', name: 'Right Horizontal Stabilizer' });
  }
  if (/apu|tail cone/i.test(query)) {
    hits.push({ id: 'seg-apu', name: 'APU & Tail Cone' });
  }
  if (/fuselage|cabin|door|window|keel/i.test(query)) {
    hits.push({ id: 'seg-fuselage-mid', name: 'Center Fuselage Section' });
  }
  return hits;
}

function updateAirframeHighlight(text) {
  const allSegs = document.querySelectorAll('.plane-seg');
  allSegs.forEach(el => el.classList.remove('highlight-alert', 'highlight-warn'));
  
  const dot = $('planeStatusDot');
  const label = $('planeActiveHighlight');
  const detected = detectAirframeSegments(text);

  if (detected.length > 0) {
    detected.forEach(hit => {
      const el = document.getElementById(hit.id);
      if (el) el.classList.add('highlight-alert');
    });
    if (dot) dot.classList.add('active');
    if (label) {
      label.textContent = `ALERT: Fault localized to ${detected.map(d => d.name).join(', ')}`;
      label.classList.add('alert');
    }
  } else if (text && text.trim().length > 0) {
    // Generic advisory highlight on engine / airframe
    const fallback = document.getElementById('seg-engine-r');
    if (fallback) fallback.classList.add('highlight-warn');
    if (dot) dot.classList.add('active');
    if (label) {
      label.textContent = `General airframe search active: ${text.slice(0, 45)}...`;
      label.classList.add('alert');
    }
  } else {
    if (dot) dot.classList.remove('active');
    if (label) {
      label.textContent = 'All systems nominal · awaiting fault input';
      label.classList.remove('alert');
    }
  }
}

function node(tag, className = '', text = '') { const element = document.createElement(tag); element.className = className; element.textContent = text; return element; }
function button(text, onClick, className = 'chip') { const value = node('button', className, text); value.type = 'button'; value.addEventListener('click', () => protect(onClick)); return value; }
function notice(text = '') { $('notice').textContent = text; $('notice').hidden = !text; }
function status(text) { $('chatStatus').textContent = text; }
async function protect(task) {
  try { await task(); }
  catch (error) { notice(error.message || 'The request could not be completed.'); }
}
function setBusy(value) {
  state.busy = value; $('shell').classList.toggle('is-busy', value);
  for (const id of ['chatInput', 'heroInput', 'searchBtn', 'reportBtn', 'uploadBtn', 'newSessionBtn', 'historyBtn', 'agentModelSelect', 'domainSelect', 'topK', 'qualitySelect', 'duplicatesSelect']) $(id).disabled = value;
  document.querySelectorAll('.answer-actions button,.record-actions button').forEach(el => { el.disabled = value; });
  $('chatSubmit').disabled = value; $('heroForm').querySelector('button').disabled = value;
  $('stopBtn').hidden = !value; $('resumeBtn').hidden = true;
}
function searchSpec(query) { return { query, domain: $('domainSelect').value || 'aviation', top_k: Math.max(1, Math.min(20, Number($('topK').value) || 5)), quality: $('qualitySelect').value, duplicate_policy: $('duplicatesSelect').value }; }
function activate() { $('shell').classList.add('chat-active'); }
function nearBottom() { return document.documentElement.scrollHeight - window.scrollY - window.innerHeight < 240; }
function follow(element, shouldFollow) { if (shouldFollow) element.scrollIntoView({ block: 'nearest', behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'instant' : 'smooth' }); }
function panel(title, eyebrow = '') {
  $('panelTitle').textContent = title; $('panelEyebrow').textContent = eyebrow; $('panelBody').replaceChildren();
  if (!$('panelDialog').open) $('panelDialog').showModal();
  return $('panelBody');
}
function userMessage(text) { $('thread').append(node('div', 'msg-user', text)); }
function newTurn() {
  const element = node('section', 'turn'); const activity = node('details', 'run-card'); activity.open = true;
  const summary = node('summary', '', 'Copilot activity'); const elapsed = node('span', 'run-elapsed', ''); summary.append(elapsed);
  const steps = node('div', 'run-steps'); activity.append(summary, steps); element.append(activity); $('thread').append(element);
  const started = performance.now(); const timer = setInterval(() => { elapsed.textContent = `${((performance.now() - started) / 1000).toFixed(1)}s`; }, 200);
  return { element, activity, steps, timer, elapsed, started, tools: new Map(), terminal: false };
}
function finishTurn() {
  const turn = state.turn; if (!turn) return;
  clearInterval(turn.timer); turn.elapsed.textContent = `${((performance.now() - turn.started) / 1000).toFixed(1)}s · client elapsed`;
  turn.activity.open = false;
}
function toolStart(data) {
  const row = node('div', 'tool-step running'); const line = node('div', 'tool-line');
  const name = node('span', 'tool-name', data.tool_name || 'Tool'); const result = node('div', 'tool-result', 'Running…');
  line.append(name); row.append(line, result); state.turn.steps.append(row);
  state.turn.tools.set(data.tool_call_id || data.tool_name, { row, result, data });
}
function toolEnd(data) {
  const key = data.tool_call_id || data.tool_name;
  if (!state.turn.tools.has(key)) toolStart(data);
  const tool = state.turn.tools.get(key); tool.row.className = 'tool-step ' + (data.error ? 'error' : 'done');
  tool.result.textContent = data.summary || 'Completed';
  tool.row.append(button('Inspect public inputs / result', () => {
    const body = panel(data.tool_name || 'Tool activity', 'Public tool trace');
    body.append(node('pre', '', JSON.stringify({ args: tool.data.args, summary: data.summary, result: data.result }, null, 2)));
  }, 'detail-btn'));
}
function canonicalRef(value) {
  const [domain, ...rest] = (value.record_id || '').split(':');
  return { ...value, domain: value.domain || domain, source_id: value.source_id || rest.join(':') };
}
async function openSupport(value) {
  const ref = canonicalRef(value);
  if (ref.kind && ref.kind !== 'log_span') {
    panel('Computed evidence receipt', ref.kind).append(node('pre', '', JSON.stringify(ref, null, 2))); return;
  }
  await openRecord(await api.record(ref), ref);
}
async function openRecord(record, highlight) {
  const body = panel(record.source_id, record.source_type === 'simulated' ? 'SIMULATED SOURCE · NOT MAINTNET' : 'Original source record');
  body.append(node('p', 'provenance', `${record.domain} · corpus ${record.corpus_version} · aircraft applicability: ${record.applicability || 'unknown'}`));
  for (const [field, raw] of Object.entries(record.fields || {})) {
    body.append(node('h3', '', field)); const pre = node('pre'); const chars = Array.from(String(raw ?? ''));
    if (highlight?.field === field && Number.isInteger(highlight.start) && Number.isInteger(highlight.end) &&
        highlight.start >= 0 && highlight.end <= chars.length && highlight.end > highlight.start &&
        chars.slice(highlight.start, highlight.end).join('') === highlight.quote) {
      pre.append(document.createTextNode(chars.slice(0, highlight.start).join('')),
        node('mark', '', chars.slice(highlight.start, highlight.end).join('')),
        document.createTextNode(chars.slice(highlight.end).join('')));
    } else pre.textContent = String(raw ?? '');
    body.append(pre);
  }
  body.append(node('p', 'provenance', `SHA-256: ${record.source_sha256 || 'not available (simulated UI fixture)'}`));
}
function claimList(title, claims, container) {
  if (!claims?.length) return;
  container.append(node('h4', '', title)); const list = node('ul');
  for (const claim of claims) {
    const item = node('li', '', claim.text); const refs = node('span', 'citations');
    for (const support of claim.supports || []) {
      const ref = canonicalRef(support); refs.append(button(`${ref.source_id || support.receipt_id || 'receipt'}${ref.field ? ' · ' + ref.field : ''}`, () => openSupport(support), 'citation'));
    }
    item.append(refs); list.append(item);
  }
  container.append(list);
}
function textList(title, values, container) {
  if (!values?.length) return;
  container.append(node('h4', '', title)); const list = node('ul');
  values.forEach(value => list.append(node('li', '', typeof value === 'string' ? value : value.text))); container.append(list);
}
function renderAnswer(answer, container) {
  if (container.querySelector(`[data-answer-id="${CSS.escape(answer.answer_id)}"]`)) return;
  const el = node('article', 'answer' + (answer.mode === 'HYPOTHESIS' ? ' hypothesis' : '')); el.dataset.answerId = answer.answer_id;
  el.append(node('div', 'answer-meta', `${answer.simulated ? 'SIMULATED · ' : ''}${answer.mode} · ${answer.status.replaceAll('_', ' ')}`), node('h3', '', answer.headline));
  claimList('What the records report', answer.findings, el); claimList('Actions recorded in history', answer.historical_actions, el);
  claimList('Contrasting cases', answer.contrasting_cases, el);
  // Hypotheses are rendered only inside a server-authorized HYPOTHESIS envelope.
  if (answer.mode === 'HYPOTHESIS') textList('Unverified reasoning', answer.hypotheses, el);
  textList('Evidence limits', answer.limitations, el); textList('Still missing', answer.missing, el);
  if (answer.clarification) el.append(node('p', '', answer.clarification));
  const actions = node('div', 'answer-actions');
  for (const entry of answer.allowed_actions || []) {
    const kind = typeof entry === 'string' ? entry : entry.type;
    if (labels[kind]) actions.append(button(labels[kind], () => performAction(kind, answer)));
  }
  if (answer.visual_refs?.length) actions.append(button('Explain component', () => showVisuals(answer.visual_refs)));
  actions.append(button('Export handover', exportHandover));
  actions.querySelectorAll('button').forEach(value => { value.disabled = state.busy; });
  el.append(actions); container.append(el);
}
function showVisuals(refs) {
  const body = panel('Component explanation', 'Reviewed educational context');
  body.append(node('p', 'helper', 'Historical log similarity does not establish aircraft applicability. This panel must not be used as an operating or repair procedure.'));
  for (const ref of refs) {
    body.append(node('h3', '', ref.caption || ref.asset_id), node('p', 'provenance', ref.applicability || 'Applicability unknown'));
    if (demo) { body.append(node('p', 'empty', 'No reviewed visual asset is included in the simulated demonstration.')); continue; }
    const img = document.createElement('img'); img.src = `/api/maintenance/v1/visuals/${encodeURIComponent(ref.asset_id)}`;
    img.alt = ref.caption || 'Reviewed component schematic'; img.style.maxWidth = '100%';
    img.onerror = () => { img.replaceWith(node('p', 'empty', 'The reviewed visual is unavailable.')); }; body.append(img);
    for (const support of ref.source_refs || []) body.append(button('Open supporting source', () => openSupport(support)));
  }
}
function renderRecords(records, target = $('evidencePanel')) {
  target.replaceChildren();
  if (!records.length) { target.append(node('p', 'empty', 'No supporting records were returned for this search.')); return; }
  for (const record of records) {
    const card = node('article', 'record-card');
    card.append(node('div', 'source-label', record.source_type === 'simulated' ? 'Simulated UI fixture' : 'Historical source'), node('h3', '', record.source_id),
      node('p', '', record.fields?.PROBLEM || record.summary || 'Open the source to inspect its fields.'),
      node('div', 'provenance', `${record.domain} · ${record.corpus_version} · model ${record.aircraft_model || 'unknown'}`));
    const actions = node('div', 'record-actions'); actions.append(button('Original record', async () => openRecord(await api.record(record))));
    const pinned = state.session?.pins?.some(x => x.source_id === record.source_id && x.domain === record.domain && x.corpus_version === record.corpus_version);
    actions.append(button(pinned ? 'Unpin' : 'Pin evidence', async () => {
      if (state.busy) return;
      await api.pin(state.session.session_id, record, !pinned, state.session.revision);
      state.session = await api.session(state.session.session_id); renderPins(); renderRecords(state.records);
      if (target !== $('evidencePanel')) renderRecords(records, target);
    }));
    card.append(actions); target.append(card);
  }
}
function renderPins() { $('pinCount').textContent = state.session?.pins?.length || 0; }
function renderBoard(board) {
  const el = $('boardPanel'); el.replaceChildren();
  for (const [key, title] of [['known', 'Known in this session'], ['reported', 'Reported in history'], ['missing', 'Missing']]) {
    const section = node('section', 'board-section'); section.append(node('h3', '', title));
    for (const item of board?.[key] || []) section.append(node('p', '', item.text), node('div', 'provenance', item.origin || 'Origin unavailable'));
    if (!board?.[key]?.length) section.append(node('p', 'empty', 'Nothing recorded yet.')); el.append(section);
  }
}
function showEvidence(records) {
  state.records = records; $('evidenceWorkspace').hidden = false; $('workspace').classList.add('has-evidence'); renderRecords(records);
}
async function receive(event) {
  const keepFollowing = nearBottom(); const data = event.data || {};
  switch (event.type) {
    case 'run_started': status(demo ? 'demo · playing simulated activity…' : 'copilot investigating…'); break;
    case 'query_interpreted': 
      $('liveSpecCard').hidden = false; 
      $('liveSpecCard').textContent = `Search: ${data.query || ''} · domain: ${data.domain || 'unknown'} · aircraft applicability: ${data.applicability || 'unknown'}`; 
      updateAirframeHighlight(data.query || '');
      break;
    case 'search_started': status('searching source records…'); break;
    case 'search_completed': status('source retrieval complete…'); break;
    case 'tool_started': toolStart(data); break;
    case 'tool_completed': toolEnd(data); break;
    case 'evidence_ready': showEvidence(data.records || []); break;
    case 'board_updated': renderBoard(data.board); break;
    case 'validation_started': status(demo ? 'demo · fixture release step…' : 'checking claims against retrieved evidence…'); break;
    case 'answer_validated': renderAnswer(data.answer, state.turn.element); break;
    case 'run_failed': state.turn.terminal = true; state.turn.element.append(node('p', 'empty', data.message || 'The run failed. This does not mean there are no matching faults.')); break;
    case 'run_cancelled': state.turn.terminal = true; state.turn.element.append(node('p', 'empty', 'Run cancelled by user.')); break;
    case 'done': state.turn.terminal = true; break;
    default: break; // Unknown event types cannot render answer text.
  }
  state.cursor = event.sequence; follow(state.turn.element, keepFollowing);
}
async function watchRun(runId, after = 0) {
  state.run = runId; state.cursor = after; state.controller = new AbortController(); setBusy(true);
  try {
    await api.subscribe(runId, receive, { after, signal: state.controller.signal, onRetry: () => status('reconnecting to the same run…') });
    state.session = await api.session(state.session.session_id); state.run = null; renderPins();
    status(demo ? 'demo · ready — simulated records only' : 'copilot ready — keep investigating');
  } catch (error) {
    if (error.name !== 'AbortError') { notice(error.message + ' The run may still be active; resume its stream.'); status('connection interrupted'); }
  } finally {
    finishTurn(); setBusy(false); $('resumeBtn').hidden = !state.run;
    // While disconnected, prevent a second message from creating a competing run.
    if (state.run) {
      for (const id of ['chatSubmit', 'chatInput', 'heroInput', 'uploadBtn', 'searchBtn', 'reportBtn']) $(id).disabled = true;
      $('heroForm').querySelector('button').disabled = true; $('stopBtn').hidden = false;
      document.querySelectorAll('.answer-actions button,.record-actions button').forEach(value => { value.disabled = true; });
    }
  }
}
async function sendMessage(text) {
  text = text.trim(); if (!text || state.busy || state.run) return;
  if (!state.session) throw new Error('The backend is unavailable. Start the server or open the explicit demo link below.');
  notice(); activate(); setBusy(true);
  try {
    const run = await api.message(state.session.session_id, { message: text, model: $('agentModelSelect').value,
      search_spec: searchSpec(text), idempotency_key: uid(), expected_revision: state.session.revision });
    state.session.revision = run.session_revision; userMessage(text); state.turn = newTurn(); $('chatInput').value = ''; $('heroInput').value = '';
    await watchRun(run.run_id);
  } catch (error) {
    setBusy(false);
    // A lost POST response can still mean the server accepted the message.
    // Read session state before permitting another run; never auto-POST a retry.
    try {
      const fresh = await api.session(state.session.session_id);
      if (fresh.active_run) { await restore(fresh.session_id); return; }
      state.session = fresh;
    } catch { /* preserve the original error and user's input */ }
    throw error;
  }
}
async function performAction(action, answer, parameters = {}) {
  if (state.busy || state.run) return;
  if (action === 'SENSITIVITY' && !parameters.alternative_query) {
    const body = panel('Preview a sensitivity comparison', 'One query change; same source scope');
    body.append(node('p', 'helper', 'Edit the wording of one aspect. The server must reject changes to multiple dimensions and return a computed comparison receipt.'));
    const input = node('textarea', 'textarea'); input.value = $('queryText').value || state.session.last_query || ''; input.maxLength = 8000; input.setAttribute('aria-label', 'Alternative query');
    body.append(input, button('Compare this alternative', async () => { const alternative = input.value.trim(); if (!alternative) throw new Error('Enter an alternative query.'); $('panelDialog').close(); await performAction(action, answer, { alternative_query: alternative, change_kind: 'wording' }); }, 'primary-btn')); return;
  }
  notice(); setBusy(true);
  try {
    const run = await api.action(state.session.session_id, { action, parent_answer_id: answer.answer_id,
      expected_revision: state.session.revision, idempotency_key: uid(), parameters });
    state.session.revision = run.session_revision; userMessage(labels[action]); state.turn = newTurn(); await watchRun(run.run_id);
  } catch (error) { setBusy(false); throw error; }
}
async function restore(id) {
  if (state.busy) return; notice(); const value = await api.session(id);
  state.controller?.abort(); state.run = null; state.session = value; localStorage.setItem(storageKey, id);
  $('thread').replaceChildren(); $('shell').classList.toggle('chat-active', value.messages.length > 0);
  for (const message of value.messages) { if (message.kind === 'user') userMessage(message.text); if (message.kind === 'answer') renderAnswer(message.answer, $('thread')); }
  state.records = value.records || []; $('evidenceWorkspace').hidden = !value.messages.length; $('workspace').classList.toggle('has-evidence', Boolean(value.messages.length));
  renderRecords(state.records); renderBoard(value.board); renderPins(); $('panelDialog').close();
  $('liveSpecCard').hidden = true; setBusy(false); status(demo ? 'demo · ready — simulated records only' : 'copilot ready — keep investigating');
  if (value.active_run) { state.turn = newTurn(); await watchRun(value.active_run.run_id, 0); }
}
async function newSession() { if (state.busy) return; const value = await api.createSession($('domainSelect').value || 'aviation'); await restore(value.session_id); $('directResults').replaceChildren(); }
async function directSearch() {
  if (state.busy || state.run) return; const query = $('queryText').value.trim(); if (!query) throw new Error('Enter a search complaint.');
  setBusy(true); status('searching records without an LLM answer…'); notice();
  try { const result = await api.search(searchSpec(query)); $('directResults').append(node('h2', 'results-title', 'Retrieved records')); renderRecords(result.records || [], $('directResults')); $('directResults').scrollIntoView({ block: 'nearest' }); }
  finally { setBusy(false); status(demo ? 'demo · ready — simulated records only' : 'copilot ready — keep investigating'); }
}
async function exportHandover() {
  const text = await api.handover(state.session.session_id); const url = URL.createObjectURL(new Blob([text], { type: 'text/markdown;charset=utf-8' }));
  const link = document.createElement('a'); link.href = url; link.download = `${demo ? 'SIMULATED-' : ''}maintenance-handover.md`; link.click(); setTimeout(() => URL.revokeObjectURL(url), 1000);
}
$('heroForm').addEventListener('submit', event => { event.preventDefault(); protect(() => sendMessage($('heroInput').value)); });
$('chatForm').addEventListener('submit', event => { event.preventDefault(); protect(() => sendMessage($('chatInput').value)); });
$('searchBtn').addEventListener('click', () => protect(directSearch));
$('reportBtn').addEventListener('click', () => protect(() => sendMessage(($('aircraftInput').value.trim() ? `User-reported aircraft / engine: ${$('aircraftInput').value.trim()}\n` : '') + $('reportText').value)));
$('newSessionBtn').addEventListener('click', () => protect(newSession));
$('resumeBtn').addEventListener('click', () => protect(async () => { state.turn = newTurn(); await watchRun(state.run, state.cursor); }));
async function cancelRun() {
  if (!state.run) return;
  await api.cancel(state.run); status('cancellation requested — awaiting server…');
  if (!state.busy) { state.turn = newTurn(); await watchRun(state.run, state.cursor); }
}
$('stopBtn').addEventListener('click', () => protect(cancelRun));
document.addEventListener('keydown', event => { if (event.key === 'Escape' && !$('panelDialog').open) protect(cancelRun); });
$('panelCloseBtn').addEventListener('click', () => $('panelDialog').close());
document.querySelectorAll('[data-drawer]').forEach(toggle => toggle.addEventListener('click', () => {
  const open = !$(toggle.dataset.drawer).hidden; document.querySelectorAll('[data-drawer]').forEach(other => { $(other.dataset.drawer).hidden = true; other.setAttribute('aria-expanded', 'false'); });
  $(toggle.dataset.drawer).hidden = open; toggle.setAttribute('aria-expanded', String(!open));
}));
document.querySelectorAll('[data-tab]').forEach(tab => tab.addEventListener('click', () => {
  $('evidencePanel').hidden = tab.dataset.tab !== 'evidence'; 
  $('boardPanel').hidden = tab.dataset.tab !== 'board';
  if ($('airframePanel')) {
    $('airframePanel').hidden = tab.dataset.tab !== 'airframe';
    if (tab.dataset.tab === 'airframe' && !$('panelAirframeSvgWrap').hasChildNodes()) {
      const clone = $('planeSvg').cloneNode(true);
      clone.id = 'planeSvgSidePanel';
      $('panelAirframeSvgWrap').appendChild(clone);
    }
  }
  document.querySelectorAll('[data-tab]').forEach(x => x.classList.toggle('active', x === tab));
}));
$('historyBtn').addEventListener('click', () => protect(async () => {
  const body = panel('Investigation history', demo ? 'Browser-only demo history' : 'Server-owned session history'); body.append(node('p', 'empty', 'Loading…'));
  const result = await api.listSessions(); body.replaceChildren();
  for (const item of result.items || []) { const entry = button('', () => restore(item.session_id), 'history-item'); entry.append(node('strong', '', item.title || 'Untitled investigation'), node('small', '', `Revision ${item.revision}`)); body.append(entry); }
  if (!result.items?.length) body.append(node('p', 'empty', 'No investigations yet.'));
}));
$('pinsBtn').addEventListener('click', () => { const body = panel('Pinned evidence', 'Bookmarks · not approved repairs'); renderRecords(state.session?.pins || [], body); });
$('storyBtn').addEventListener('click', () => {
  const body = panel('How Maintenance Atlas works', 'Evidence before explanation');
  for (const text of ['Search retrieves source records; deterministic services handle filtering, deduplication and calculations.', 'The LLM drafts narrow claims from fetched evidence. The server checks the claims before releasing an answer.', 'User observations, historical reports and missing information remain separate. Possible solutions require your explicit click.', demo ? 'This preview plays invented UI fixtures. It runs no search model, language model or production validator.' : 'No generated draft or private model reasoning is streamed into the conversation.']) body.append(node('p', 'helper', text));
});
$('explorerBtn').addEventListener('click', () => { const toggle = document.querySelector('[data-drawer="queryDrawer"]'); if ($('queryDrawer').hidden) toggle.click(); $('queryText').focus(); });
$('settingsBtn').addEventListener('click', () => {
  const body = panel('Settings', 'Server-confirmed capabilities');
  body.append(node('p', 'helper', 'Choose the model in the chat toolbar and retrieval options in Advanced options. These apply to future runs. Provider credentials belong on the server.'), node('pre', '', JSON.stringify(state.capabilities, null, 2)));
});
$('uploadBtn').addEventListener('click', () => $('fileInput').click());
$('fileInput').addEventListener('change', () => protect(async () => {
  const file = $('fileInput').files[0]; $('fileInput').value = ''; if (!file || state.busy) return;
  if (file.size > 5 * 1024 * 1024) throw new Error('The attachment exceeds the 5 MB limit.');
  if (!/\.(txt|md|pdf)$/i.test(file.name)) throw new Error('Select a TXT, Markdown or PDF file.');
  setBusy(true);
  try { const result = await api.upload(state.session.session_id, file, state.session.revision);
    state.session = await api.session(state.session.session_id); renderBoard(state.session.board);
    const body = panel('Attachment received', 'User-uploaded context · unverified'); body.append(node('p', 'helper', result.status || 'Uploaded'));
    if (result.text) { body.append(node('pre', '', result.text), button('Use this as a fault report', () => { $('reportText').value = result.text; $('panelDialog').close(); const toggle = document.querySelector('[data-drawer="reportDrawer"]'); if ($('reportDrawer').hidden) toggle.click(); }, 'primary-btn')); }
  } finally { setBusy(false); }
}));
async function boot() {
  $('environmentLabel').textContent = demo ? 'SIMULATED UI DEMO · NOT LIVE DATA' : 'LIVE API MODE';
  try {
    state.capabilities = await api.capabilities(); const capabilities = state.capabilities;
    $('coverage').textContent = capabilities.corpus_summary || 'Source metadata unavailable';
    for (const model of capabilities.models || []) { const option = node('option', '', model.label || model.id); option.value = model.id; $('agentModelSelect').append(option); }
    for (const domain of capabilities.domains || []) { const option = node('option', '', domain); option.value = domain; $('domainSelect').append(option); }
    $('qualitySelect').querySelector('[value="rerank"]').disabled = !capabilities.rerank_available;
    for (const example of capabilities.examples || []) $('starters').append(button(example.query, () => sendMessage(example.query), 'chip'));
    $('agentModelSelect').disabled = !capabilities.models?.length;
    if (!capabilities.models?.length || !capabilities.domains?.length) throw new Error('The service has no configured model or source domain.');
    const saved = localStorage.getItem(storageKey);
    if (saved) { try { await restore(saved); } catch (error) { if (error.status === 404 || demo) await newSession(); else throw error; } }
    else await newSession();
  } catch (error) {
    status('backend unavailable'); $('coverage').textContent = 'Source catalogue unavailable';
    notice(error.message + ' For the labeled simulated preview, open this URL with ?demo=1. Live mode never falls back to fixtures.');
  }
}
await boot();
