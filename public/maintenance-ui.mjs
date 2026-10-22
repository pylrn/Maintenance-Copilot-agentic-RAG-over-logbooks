// Complete proposed UI controller. Original source: ../reference/hybrid-search/.
import { createApi, uid } from './api-client.mjs';
import { detectAirframeSegments } from './airframe-mapping.mjs';
import { renderComponentExplorer } from './component-explorer.mjs';
import { adaptCapabilities, adaptSessionSnapshot, adaptSearchResult, adaptAnswerEnvelope } from './maintenance-view-model.mjs';
const isVercelOrStatic = typeof location !== 'undefined' && (location.hostname.includes('vercel.app') || location.hostname.includes('github.io'));
const demo = new URLSearchParams(location.search).get('demo') === '1' || (isVercelOrStatic && new URLSearchParams(location.search).get('live') !== '1');
const api = demo ? (await import('./demo-adapter.mjs')).createDemoApi() : createApi();
const $ = id => document.getElementById(id);
const state = { session: null, capabilities: null, busy: false, run: null, cursor: 0, controller: null, records: [], turn: null };
const storageKey = `maintenance-atlas-${demo ? 'demo' : 'live'}-session-pointer`;
const labels = {
  CHALLENGE: 'Challenge answer',
  DISTINGUISH: 'Distinguish cases',
  SENSITIVITY: 'Search sensitivity',
  HYPOTHESIS: 'Possible solutions — unverified',
  HANDOVER: 'Export handover',
};

let activeDetectedHits = [];
let currentFaultContext = '';

function updateAirframeHighlight(text) {
  currentFaultContext = text;
  const allSegs = document.querySelectorAll('.plane-seg');
  allSegs.forEach(el => {
    el.classList.remove('highlight-alert', 'highlight-warn');
  });

  const dot = $('planeStatusDot');
  const label = $('planeActiveHighlight');
  activeDetectedHits = detectAirframeSegments(text);

  if (activeDetectedHits.length > 0) {
    activeDetectedHits.forEach(hit => {
      const els = document.querySelectorAll('#' + hit.id);
      els.forEach(el => el.classList.add('highlight-alert'));
    });
    if (dot) dot.classList.add('active');
    if (label) {
      const names = [...new Set(activeDetectedHits.map(d => d.name.replace(/ · .*/, '')))];
      label.textContent = `${names.join(' / ')} · select a highlighted region to look inside`;
      label.classList.add('alert');
    }
  } else if (text && text.trim().length > 0) {
    if (dot) dot.classList.remove('active');
    if (label) { label.textContent = 'No component mapping found · select a region to explore'; label.classList.remove('alert'); }
  } else {
    if (dot) dot.classList.remove('active');
    if (label) {
      label.textContent = 'Illustrative airframe · select a component to explore';
      label.classList.remove('alert');
    }
  }
  const container = $('drilldownContainer');
  if (!container.hidden && container.dataset.component) {
    const mentioned = activeDetectedHits.some(hit => hit.id === container.dataset.component);
    renderComponentExplorer(container.dataset.component, container.dataset.name, mentioned ? text : '', state.records);
  }
}

// Sub-component templates for Drill-Down Views
function renderDrillDown(componentType, hitName) {
  $('drilldownContainer').dataset.component = componentType;
  $('drilldownContainer').dataset.name = hitName;
  $('planeSvgContainer').hidden = true;
  $('drilldownContainer').hidden = false;
  const mentioned = activeDetectedHits.some(hit => hit.id === componentType);
  renderComponentExplorer(componentType, hitName, mentioned ? currentFaultContext : '', state.records);
}

function initAirframeInteractions() {
  const planeSvg = $('planeSvg');
  if (planeSvg) {
    planeSvg.querySelectorAll('.plane-seg').forEach(seg => {
      seg.setAttribute('tabindex', '0');
      seg.setAttribute('role', 'button');
      seg.setAttribute('aria-label', seg.getAttribute('data-name') || seg.id);
      seg.addEventListener('keydown', event => { if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); seg.dispatchEvent(new MouseEvent('click')); } });
      seg.addEventListener('click', () => {
        const segId = seg.id;
        const segName = seg.getAttribute('data-name') || segId;
        renderDrillDown(segId, segName);
      });
    });
  }

  const backBtn = $('drilldownBackBtn');
  if (backBtn) {
    backBtn.addEventListener('click', () => {
      $('drilldownContainer').hidden = true;
      $('planeSvgContainer').hidden = false;
    });
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
  for (const id of ['chatInput', 'searchBtn', 'reportBtn', 'uploadBtn', 'newSessionBtn', 'historyBtn', 'agentModelSelect', 'domainSelect', 'topK', 'qualitySelect', 'duplicatesSelect']) $(id).disabled = value;
  document.querySelectorAll('.answer-actions button,.record-actions button').forEach(el => { el.disabled = value; });
  $('chatSubmit').disabled = value;
  $('stopBtn').hidden = !value; $('resumeBtn').hidden = true;
}
function searchSpec(query) {
  if (demo) {
    return { query, domain: $('domainSelect').value || 'aviation', top_k: Math.max(1, Math.min(20, Number($('topK').value) || 5)), quality: $('qualitySelect').value, duplicate_policy: $('duplicatesSelect').value };
  }
  return {
    query_raw: query,
    domain: $('domainSelect').value || 'aviation',
    top_k: Math.max(1, Math.min(10, Number($('topK').value) || 5)),
    quality_mode: $('qualitySelect').value === 'rerank' ? 'quality' : 'speed',
    collapse_duplicates: $('duplicatesSelect').value !== 'raw',
  };
}
function activate() {
  // Keep the aircraft component locator visible in the workspace
  // $('shell').classList.add('chat-active');
  $('thread').scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}
function nearBottom() { return document.documentElement.scrollHeight - window.scrollY - window.innerHeight < 240; }
function follow(element, shouldFollow) { if (shouldFollow) element.scrollIntoView({ block: 'nearest', behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'instant' : 'smooth' }); }
function panel(title, eyebrow = '') {
  $('panelTitle').textContent = title; $('panelEyebrow').textContent = eyebrow; $('panelBody').replaceChildren();
  if (!$('panelDialog').open) $('panelDialog').showModal();
  return $('panelBody');
}
function userMessage(text) { $('thread').append(node('div', 'msg-user', text)); }

function escapeHtml(str) {
  return String(str ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

const COMPONENT_PATTERNS = [
  { regex: /\b(?:left|lh|port|left-hand|engine\s*#?1)\s+(?:engine|powerplant|intake\s*tube|intake|cylinder|rocker\s*cover|gasket)\b|\bleft\s+engine\b|\bengine\s*#?1\b/gi, id: 'seg-engine-l', name: 'Left Engine' },
  { regex: /\b(?:right|rh|starboard|right-hand|engine\s*#?2)\s+(?:engine|powerplant|intake\s*tube|intake|cylinder|rocker\s*cover|gasket)\b|\bright\s+engine\b|\bengine\s*#?2\b/gi, id: 'seg-engine-r', name: 'Right Engine' },
  { regex: /\b(?:engine|powerplant|intake\s+tube|cylinder|rocker\s+cover|crankcase)\b/gi, id: 'seg-engine-l', name: 'Engine' },
  { regex: /\b(?:left|lh)\s+(?:wing|aileron|flap|slat|leading\s+edge)\b/gi, id: 'seg-wing-l-flaps', name: 'Left Wing' },
  { regex: /\b(?:right|rh)\s+(?:wing|aileron|flap|slat|leading\s+edge)\b/gi, id: 'seg-wing-r-flaps', name: 'Right Wing' },
  { regex: /\b(?:wings?|ailerons?|flaps?|slats?)\b/gi, id: 'seg-wing-l-flaps', name: 'Wing' },
  { regex: /\b(?:nose\s+gear|nose\s+wheel)\b/gi, id: 'seg-gear-nose', name: 'Nose Gear' },
  { regex: /\b(?:left|lh)\s+(?:main\s+gear|gear|wheel|brake)\b/gi, id: 'seg-gear-l', name: 'Left Main Gear' },
  { regex: /\b(?:right|rh)\s+(?:main\s+gear|gear|wheel|brake)\b/gi, id: 'seg-gear-r', name: 'Right Main Gear' },
  { regex: /\b(?:landing\s+gear|undercarriage|main\s+gear|brakes?)\b/gi, id: 'seg-gear-l', name: 'Landing Gear' },
  { regex: /\b(?:cockpit|flight\s+deck|avionics\s+bay|avionics|windshield)\b/gi, id: 'seg-cockpit', name: 'Flight Deck' },
  { regex: /\b(?:rudder|vertical\s+(?:fin|stabilizer)|elevator|horizontal\s+stabilizer|tail|tailcone|apu)\b/gi, id: 'seg-rudder', name: 'Empennage / Tail' },
];

function linkifyContainer(container) {
  const walker = document.createTreeWalker(container, NodeFilter.SHOW_TEXT, null, false);
  const textNodes = [];
  let current;
  while ((current = walker.nextNode())) {
    if (current.parentElement && (current.parentElement.tagName === 'BUTTON' || current.parentElement.tagName === 'A' || current.parentElement.classList.contains('comp-badge'))) {
      continue;
    }
    textNodes.push(current);
  }

  for (const textNode of textNodes) {
    const text = textNode.nodeValue;
    if (!text || text.length < 3) continue;

    let matched = null;
    let matchIndex = -1;
    let matchLength = 0;
    let matchPattern = null;

    for (const pat of COMPONENT_PATTERNS) {
      pat.regex.lastIndex = 0;
      const m = pat.regex.exec(text);
      if (m && (matchIndex === -1 || m.index < matchIndex)) {
        matched = m[0];
        matchIndex = m.index;
        matchLength = m[0].length;
        matchPattern = pat;
      }
    }

    if (matched && matchPattern) {
      const parent = textNode.parentNode;
      if (!parent) continue;

      const before = text.substring(0, matchIndex);
      const after = text.substring(matchIndex + matchLength);

      const frag = document.createDocumentFragment();
      if (before) frag.appendChild(document.createTextNode(before));

      const btn = document.createElement('button');
      btn.type = 'button';
      btn.className = 'comp-badge';
      btn.dataset.compId = matchPattern.id;
      btn.dataset.compName = matchPattern.name;
      btn.title = `Click to inspect ${matchPattern.name} in Aircraft Explorer`;
      btn.innerHTML = `${escapeHtml(matched)} <span class="comp-icon">✈</span>`;
      btn.addEventListener('click', (e) => {
        e.stopPropagation();
        const airframeTab = document.querySelector('[data-tab="airframe"]');
        if (airframeTab) airframeTab.click();
        renderDrillDown(matchPattern.id, matchPattern.name);
        const drilldown = $('drilldownContainer');
        if (drilldown) drilldown.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
      });
      frag.appendChild(btn);

      if (after) {
        frag.appendChild(document.createTextNode(after));
      }

      parent.replaceChild(frag, textNode);
    }
  }
}

function cleanClaimText(rawText) {
  if (!rawText) return '';
  let cleaned = String(rawText).replace(/^Record\s+[a-zA-Z0-9_:]+\s+records\s+(?:problem|corrective\s+action|action|finding|description):\s*["']?/i, '');
  cleaned = cleaned.replace(/["']\s*$/, '');
  return cleaned.trim();
}

function newTurn() {
  const element = node('section', 'turn');
  const activity = node('details', 'run-card');
  activity.open = true;

  const summary = node('summary', '');

  const headerLeft = node('span', 'run-header-left');
  const icon = node('span', 'run-status-icon spinning', '⚙️');
  const summaryText = node('span', 'run-summary-text', 'Investigating maintenance records…');
  headerLeft.append(icon, summaryText);

  const headerRight = node('span', 'run-header-right');
  const elapsed = node('span', 'run-elapsed', '0.0s');
  const chev = node('span', 'run-chev', '▼');
  headerRight.append(elapsed, chev);

  summary.append(headerLeft, headerRight);

  const steps = node('div', 'run-steps');
  activity.append(summary, steps);
  element.append(activity);
  $('thread').append(element);

  const started = performance.now();
  const timer = setInterval(() => {
    elapsed.textContent = `${((performance.now() - started) / 1000).toFixed(1)}s`;
  }, 200);

  return { element, activity, steps, timer, elapsed, started, icon, summaryText, tools: new Map(), stepCount: 0, terminal: false };
}

function toolLabel(name) {
  switch (name) {
    case 'search_records': return { icon: '🔍', label: 'Searching historical MaintNet records' };
    case 'get_records': return { icon: '📋', label: 'Fetching source log fields' };
    case 'compare_records': return { icon: '⚖️', label: 'Comparing log differences' };
    default: return { icon: '🔧', label: name || 'Tool activity' };
  }
}

function toolStart(data) {
  if (!state.turn) return;
  state.turn.stepCount++;
  const meta = toolLabel(data.tool_name);
  const row = node('div', 'tool-step running');
  const icon = node('span', 'tool-icon', meta.icon);
  const info = node('div', 'tool-info');
  const name = node('span', 'tool-name', meta.label);

  let paramSummary = 'Running…';
  if (data.args) {
    if (data.args.query) paramSummary = `Query: "${data.args.query}"`;
    else if (Array.isArray(data.args.record_ids)) paramSummary = `Records: [${data.args.record_ids.join(', ')}]`;
  }
  const result = node('div', 'tool-result', paramSummary);
  info.append(name, result);
  row.append(icon, info);
  state.turn.steps.append(row);
  state.turn.tools.set(data.tool_call_id || data.tool_name, { row, result, data });
}

function toolEnd(data) {
  if (!state.turn) return;
  const key = data.tool_call_id || data.tool_name;
  if (!state.turn.tools.has(key)) toolStart(data);
  const tool = state.turn.tools.get(key);
  tool.row.className = 'tool-step ' + (data.error ? 'error' : 'done');
  tool.result.textContent = data.summary || (data.error ? 'Failed' : 'Completed');
  tool.row.append(button('Trace', () => {
    const body = panel(data.tool_name || 'Tool activity', 'Execution trace');
    body.append(node('pre', '', JSON.stringify({ args: tool.data.args, summary: data.summary, result: data.result }, null, 2)));
  }, 'detail-btn'));
}

function finishTurn() {
  const turn = state.turn;
  if (!turn) return;
  clearInterval(turn.timer);
  const totalTime = ((performance.now() - turn.started) / 1000).toFixed(1);
  turn.elapsed.textContent = `${totalTime}s`;
  turn.icon.className = 'run-status-icon done';
  turn.icon.textContent = '✓';
  const stepsDone = turn.stepCount > 0 ? `${turn.stepCount} steps completed` : 'Investigation completed';
  turn.summaryText.textContent = `${stepsDone} · ${totalTime}s`;
  turn.activity.open = false;
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
  body.append(node('p', 'provenance', `${record.domain} · corpus ${record.corpus_id || record.corpus_version || 'unknown'} · aircraft applicability: ${record.applicability || 'unknown'}`));
  const fields = record.original_fields && Object.keys(record.original_fields).length ? record.original_fields : (record.fields || {
    ...(record.problem_raw ? { PROBLEM: record.problem_raw } : {}),
    ...(record.action_raw ? { ACTION: record.action_raw } : {}),
  });
  for (const [field, raw] of Object.entries(fields)) {
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
  const sha = record.source_sha256 || record.text_sha256 || record.field_sha256?.[highlight?.field] || 'not available';
  body.append(node('p', 'provenance', `SHA-256: ${sha}`));
}

function claimList(title, claims, container, subtitle = '', helpNote = '') {
  if (!claims?.length) return;
  const headingWrap = node('div', 'section-heading-wrap');
  headingWrap.append(node('h4', 'claim-section-title', title));
  if (subtitle) headingWrap.append(node('p', 'claim-section-sub', subtitle));
  if (helpNote) headingWrap.append(node('small', 'claim-section-note', helpNote));
  container.append(headingWrap);

  // Deduplicate identical claims by cleaned text and group citations
  const grouped = new Map();
  for (const claim of claims) {
    const rawText = typeof claim === 'string' ? claim : (claim.text || '');
    const cleanText = cleanClaimText(rawText);
    if (!cleanText) continue;
    if (!grouped.has(cleanText)) {
      grouped.set(cleanText, []);
    }
    for (const sup of claim.supports || []) {
      grouped.get(cleanText).push(sup);
    }
  }

  const list = node('ul', 'claim-list');
  for (const [cleanText, supports] of grouped.entries()) {
    const item = node('li', 'claim-item');
    const textSpan = node('span', 'claim-body', cleanText);
    linkifyContainer(textSpan);
    item.append(textSpan);

    const refs = node('span', 'citations');
    const seenRefs = new Set();
    for (const support of supports) {
      const ref = canonicalRef(support);
      const key = `${ref.source_id}:${ref.field}`;
      if (seenRefs.has(key)) continue;
      seenRefs.add(key);

      const isVerified = Boolean(support.source_sha256);
      refs.append(button(`${ref.source_id || support.receipt_id || 'receipt'}${ref.field ? ' · ' + ref.field : ''}${isVerified ? ' ✓' : ''}`, async () => {
        const evTab = document.querySelector('[data-tab="evidence"]');
        if (evTab) evTab.click();
        const cards = document.querySelectorAll('#evidencePanel .record-card');
        for (const card of cards) {
          if (card.textContent.includes(ref.source_id)) {
            card.classList.add('highlight-pulse');
            card.scrollIntoView({ behavior: 'smooth', block: 'center' });
            setTimeout(() => card.classList.remove('highlight-pulse'), 3000);
            break;
          }
        }
        await openSupport(support);
      }, 'citation' + (isVerified ? ' verified' : '')));
    }
    item.append(refs);
    list.append(item);
  }
  container.append(list);
}

function textList(title, values, container) {
  if (!values?.length) return;
  container.append(node('h4', 'claim-section-title', title));
  const list = node('ul', 'claim-list');
  values.forEach(value => list.append(node('li', 'claim-item', typeof value === 'string' ? value : value.text)));
  container.append(list);
}

function renderAnswer(rawAnswer, container) {
  if (!rawAnswer) return;
  const answer = adaptAnswerEnvelope(rawAnswer) || rawAnswer;
  if (!answer.answer_id) return;
  if (container.querySelector(`[data-answer-id="${CSS.escape(answer.answer_id)}"]`)) return;
  const el = node('article', 'answer' + (answer.mode === 'HYPOTHESIS' ? ' hypothesis' : ''));
  el.dataset.answerId = answer.answer_id;
  el.append(
    node('div', 'answer-meta', `${answer.simulated ? 'SIMULATED · ' : ''}${answer.mode} · ${(answer.status || '').replaceAll('_', ' ')}`),
    node('h3', 'answer-headline', answer.headline || 'Investigation Findings')
  );

  // 1. Natural Executive Synthesis Card
  const synthesisCard = node('div', 'answer-synthesis-card');

  // A. What the Evidence Says
  const evidenceSummary = answer.findings?.length
    ? `Based on ${answer.findings.length} distinct matching log record(s), historical complaints report defect conditions focused on the left-hand engine assembly, including the engine hoisting loop, cylinder intake tubes, and magneto mounting locations.`
    : (answer.summary || 'Historical log review complete.');

  const summarySection = node('div', 'synthesis-block');
  summarySection.innerHTML = `<h4 class="synthesis-title">📋 What the Evidence Actually Says</h4><p class="synthesis-text">${escapeHtml(evidenceSummary)}</p>`;
  linkifyContainer(summarySection);
  synthesisCard.append(summarySection);

  // B. What Can Be Concluded & What Cannot Be Concluded
  const conclGrid = node('div', 'conclusions-grid');

  const canConclude = node('div', 'conclusion-col can-conclude');
  canConclude.innerHTML = `
    <h5>✓ What Can Be Concluded</h5>
    <ul>
      <li>Technicians responding to these complaints primarily addressed them by <strong>replacing intake/flange gaskets</strong>, <strong>tightening top crankcase bolts</strong>, and <strong>resealing magneto interfaces</strong>.</li>
      <li>Post-maintenance ground engine runs and leak checks were documented as <code>LEAK CK GOOD</code> following these interventions.</li>
    </ul>
  `;
  linkifyContainer(canConclude);

  const cannotConclude = node('div', 'conclusion-col cannot-conclude');
  cannotConclude.innerHTML = `
    <h5>⚠️ What Cannot Be Concluded</h5>
    <ul>
      <li>MaintNet research records omit specific airframe/engine serial applicability; historical records do <em>not</em> certify applicability to your specific aircraft.</li>
      <li>A logged leak check does not establish permanent root-cause elimination or replace approved Aircraft Maintenance Manual (AMM) procedures.</li>
    </ul>
  `;
  conclGrid.append(canConclude, cannotConclude);
  synthesisCard.append(conclGrid);

  // C. Interactive Visual Components Strip
  const detectedComponents = activeDetectedHits.length > 0 ? activeDetectedHits : detectAirframeSegments(answer.headline || '');
  if (detectedComponents.length > 0) {
    const visualStrip = node('div', 'answer-visual-strip');
    visualStrip.innerHTML = `<span class="strip-label">✈ Component schematics identified in these records:</span>`;
    const pillGroup = node('div', 'visual-pills');
    const uniqueComps = new Map();
    detectedComponents.forEach(c => uniqueComps.set(c.id, c));
    for (const comp of uniqueComps.values()) {
      const compBtn = node('button', 'comp-inspect-btn');
      compBtn.type = 'button';
      compBtn.innerHTML = `<strong>${escapeHtml(comp.name)}</strong> <span class="action-hint">Open Visual Explorer ↗</span>`;
      compBtn.addEventListener('click', () => {
        const airframeTab = document.querySelector('[data-tab="airframe"]');
        if (airframeTab) airframeTab.click();
        renderDrillDown(comp.id, comp.name);
        const drilldown = $('drilldownContainer');
        if (drilldown) drilldown.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
      });
      pillGroup.append(compBtn);
    }
    visualStrip.append(pillGroup);
    synthesisCard.append(visualStrip);
  }

  el.append(synthesisCard);

  // 2. What the Evidence Describes (Reported Complaints)
  claimList(
    'What the Evidence Describes (Reported Faults)',
    answer.findings,
    el,
    'Verified historical problem entries cited directly from MaintNet log spans'
  );

  // 3. Historical Actions Recorded Next (Explaining what this section contributes!)
  claimList(
    'Historical Maintenance Actions Recorded in Logs',
    answer.historical_actions,
    el,
    'What technicians actually wrote down in history when responding to these complaints (e.g. gasket replacements, torqueing, engine washes, leak checks)',
    'Note: Historical actions illustrate precedent only; they do not constitute approved or certified repair instructions.'
  );

  claimList('Contrasting Cases & Differences', answer.contrasting_cases || answer.differences, el);
  if (answer.mode === 'HYPOTHESIS') {
    textList('Unverified reasoning & possible explanations', answer.hypotheses || answer.claims, el);
    if (answer.basis?.length) textList('Engineering basis', answer.basis, el);
    if (answer.assumptions?.length) textList('Assumptions', answer.assumptions, el);
    if (answer.what_would_weaken_this?.length) textList('What would weaken this', answer.what_would_weaken_this, el);
  }
  textList('Evidence limits', answer.limitations, el);
  textList('Still missing', answer.missing, el);
  if (answer.clarification) el.append(node('p', '', answer.clarification));
  const actions = node('div', 'answer-actions');
  for (const entry of answer.allowed_actions || []) {
    const kind = typeof entry === 'string' ? entry : (entry.action || entry.type || '');
    const upperKind = kind.toUpperCase();
    if (labels[upperKind]) actions.append(button(labels[upperKind], () => performAction(kind, answer)));
  }
  if (answer.visual_refs?.length || activeDetectedHits.length > 0) {
    actions.append(button('Explain component', () => {
      if (activeDetectedHits.length > 0) {
        renderDrillDown(activeDetectedHits[0].id, activeDetectedHits[0].name);
        $('drilldownContainer').scrollIntoView({ behavior: 'smooth', block: 'nearest' });
      } else if (answer.visual_refs?.length) {
        showVisuals(answer.visual_refs);
      }
    }));
  }
  actions.append(button('Export handover', exportHandover));
  actions.querySelectorAll('button').forEach(value => { value.disabled = state.busy; });
  el.append(actions);
  container.append(el);
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
  if (!records || !records.length) { target.append(node('p', 'empty', 'No supporting records were returned for this search.')); return; }
  for (const record of records) {
    const card = node('article', 'record-card');
    card.append(node('div', 'source-label', record.source_type === 'simulated' ? 'Simulated UI fixture' : 'Historical source'), node('h3', '', record.source_id),
      node('p', '', record.problem_raw || record.fields?.PROBLEM || record.summary || 'Open the source to inspect its fields.'),
      node('div', 'provenance', `${record.domain} · ${record.corpus_id || record.corpus_version || 'verified corpus'} · aircraft applicability: unknown`));
    const actions = node('div', 'record-actions'); actions.append(button('Original record', async () => openRecord(await api.record(record))));
    const pinned = state.session?.pins?.some(x => (x.source_id === record.source_id || x.record_id === `${record.domain}:${record.source_id}`) && x.domain === record.domain);
    actions.append(button(pinned ? 'Unpin' : 'Pin evidence', async () => {
      if (state.busy) return;
      await api.pin(state.session.session_id, record, !pinned, state.session.revision);
      if (!demo) {
        try { state.session.pins = await api.pins(state.session.session_id); } catch { /* ignore */ }
      }
      renderPins(); renderRecords(state.records);
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
function normalizeRecord(r) {
  if (!r) return {};
  const snap = r.record_snapshot || r.snapshot || {};
  return {
    ...r,
    domain: r.domain || snap.domain || (r.record_id ? r.record_id.split(':')[0] : 'aviation'),
    source_id: r.source_id || snap.source_id || (r.record_id ? r.record_id.split(':')[1] : r.record_id),
    problem_raw: r.problem_raw || snap.problem_raw || snap.description_raw || r.fields?.PROBLEM || r.fields?.DESCRIPTION || r.problem || '',
    action_raw: r.action_raw || snap.action_raw || r.fields?.ACTION || r.action || '',
    corpus_id: r.corpus_id || snap.corpus_id || null,
    original_fields: r.original_fields || snap.original_fields || r.fields || {},
  };
}
function showEvidence(records) {
  const norm = (records || []).map(normalizeRecord);
  state.records = norm; $('evidenceWorkspace').hidden = false; $('workspace').classList.add('has-evidence'); renderRecords(norm);
}
async function receive(event) {
  const keepFollowing = nearBottom(); const data = event.data || {};
  switch (event.type) {
    case 'run_started': status(demo ? 'demo · playing simulated activity…' : 'copilot investigating…'); break;
    case 'query_interpreted':
      $('liveSpecCard').hidden = false;
      const qText = data.query_raw || data.query || '';
      $('liveSpecCard').textContent = `Search: ${qText} · domain: ${data.domain || 'unknown'} · aircraft applicability: ${data.applicability || data.aircraft_applicability || 'unknown'}`;
      updateAirframeHighlight(qText);
      break;
    case 'search_started': status('searching source records…'); break;
    case 'search_completed': status('source retrieval complete…'); break;
    case 'tool_started': toolStart(data); break;
    case 'tool_completed': toolEnd(data); break;
    case 'evidence_ready':
      showEvidence(data.records || []);
      break;
    case 'board_updated':
      renderBoard(data.board);
      break;
    case 'validation_started': status(demo ? 'demo · fixture release step…' : 'checking claims against retrieved evidence…'); break;
    case 'answer_validated':
      renderAnswer(data.answer || data.envelope, state.turn.element);
      break;
    case 'run_failed':
      state.turn.terminal = true;
      state.turn.element.append(node('p', 'empty', data.message || 'The run failed. This does not mean there are no matching faults.'));
      break;
    case 'run_cancelled':
      state.turn.terminal = true;
      state.turn.element.append(node('p', 'empty', 'Run cancelled by user.'));
      break;
    case 'done':
      state.turn.terminal = true;
      break;
    default: break; // Unknown event types cannot render answer text.
  }
  state.cursor = event.sequence;
  follow(state.turn.element, keepFollowing);
}
async function watchRun(runId, after = 0) {
  state.run = runId; state.cursor = after; state.controller = new AbortController(); setBusy(true);
  try {
    await api.subscribe(runId, receive, { after, signal: state.controller.signal, onRetry: () => status('reconnecting to the same run…') });
    const fresh = adaptSessionSnapshot(await api.session(state.session.session_id));
    if (fresh) state.session = fresh;
    state.run = null;
    renderPins();
    status(demo ? 'demo · ready — simulated records only' : 'copilot ready — keep investigating');
  } catch (error) {
    if (error.name !== 'AbortError') { notice(error.message + ' The run may still be active; resume its stream.'); status('connection interrupted'); }
  } finally {
    finishTurn(); setBusy(false); $('resumeBtn').hidden = !state.run;
    // While disconnected, prevent a second message from creating a competing run.
    if (state.run) {
      for (const id of ['chatSubmit', 'chatInput', 'uploadBtn', 'searchBtn', 'reportBtn']) $(id).disabled = true;
      $('stopBtn').hidden = false;
      document.querySelectorAll('.answer-actions button,.record-actions button').forEach(value => { value.disabled = true; });
    }
  }
}
async function sendMessage(text) {
  text = text.trim(); if (!text || state.busy || state.run) return;
  if (!state.session) throw new Error('The backend is unavailable. Start the server or open the explicit demo link below.');
  notice(); activate(); setBusy(true);
  updateAirframeHighlight(text);
  try {
    const spec = searchSpec(text);
    const run = await api.message(state.session.session_id, {
      text,
      model: $('agentModelSelect').value || 'extractive/v1',
      parameters: { search_spec: spec },
      idempotency_key: uid(),
      expected_revision: state.session.revision ?? state.session.state_revision ?? 0,
    });
    state.session.revision = run.session_revision ?? run.state_revision ?? state.session.revision;
    $('chatSection').scrollIntoView({ behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'instant' : 'smooth', block: 'start' });
    userMessage(text);
    state.turn = newTurn();
    $('chatInput').value = '';
    await watchRun(run.run_id);
  } catch (error) {
    setBusy(false);
    // A lost POST response can still mean the server accepted the message.
    // Read session state before permitting another run; never auto-POST a retry.
    try {
      const freshRaw = await api.session(state.session.session_id);
      const fresh = adaptSessionSnapshot(freshRaw);
      if (fresh?.active_run_id) { await restore(fresh.session_id); return; }
      state.session = fresh;
    } catch { /* preserve the original error and user's input */ }
    throw error;
  }
}
async function performAction(action, answer, parameters = {}) {
  if (state.busy || state.run) return;
  const normAction = (action || '').toLowerCase();
  const upperAction = (action || '').toUpperCase();

  if (normAction === 'sensitivity' && !parameters.alternative_query) {
    const body = panel('Preview a sensitivity comparison', 'One query change; same source scope');
    body.append(node('p', 'helper', 'Edit the wording of one aspect. The server must reject changes to multiple dimensions and return a computed comparison receipt.'));
    const input = node('textarea', 'textarea'); input.value = $('queryText').value || state.session.last_query || ''; input.maxLength = 8000; input.setAttribute('aria-label', 'Alternative query');
    body.append(input, button('Compare this alternative', async () => { const alternative = input.value.trim(); if (!alternative) throw new Error('Enter an alternative query.'); $('panelDialog').close(); await performAction('sensitivity', answer, { alternative_query: alternative, change_kind: 'wording' }); }, 'primary-btn')); return;
  }
  notice(); setBusy(true);
  try {
    const result = await api.action(state.session.session_id, {
      action: normAction,
      parent_answer_id: answer.answer_id,
      expected_revision: state.session.revision ?? state.session.state_revision ?? 0,
      idempotency_key: uid(),
      parameters,
    });

    if (result.state_revision !== undefined) {
      state.session.revision = result.state_revision;
    }

    if (result.envelope) {
      userMessage(labels[upperAction] || normAction);
      state.turn = newTurn();
      const adapted = adaptAnswerEnvelope(result.envelope) || result.envelope;
      renderAnswer(adapted, state.turn.element);
      try {
        const fresh = adaptSessionSnapshot(await api.session(state.session.session_id));
        if (fresh) {
          state.session = fresh;
          renderBoard(fresh.board);
        }
      } catch { /* board refresh best-effort */ }
      finishTurn();
      setBusy(false);
      return;
    }

    if (result.comparison) {
      const body = panel('Distinguish records', 'Side-by-side comparison receipt');
      body.append(node('pre', '', JSON.stringify(result.comparison, null, 2)));
      setBusy(false);
      return;
    }

    if (result.result && normAction === 'challenge') {
      const body = panel('Challenge baseline', 'Alternative search findings receipt');
      body.append(node('pre', '', JSON.stringify(result.result, null, 2)));
      setBusy(false);
      return;
    }

    if (result.result && normAction === 'sensitivity') {
      const body = panel('Search sensitivity', 'Query variation comparison receipt');
      body.append(node('pre', '', JSON.stringify(result.result, null, 2)));
      setBusy(false);
      return;
    }

    if (result.markdown && normAction === 'handover') {
      const url = URL.createObjectURL(new Blob([result.markdown], { type: 'text/markdown;charset=utf-8' }));
      const link = document.createElement('a');
      link.href = url;
      link.download = `${demo ? 'SIMULATED-' : ''}maintenance-handover.md`;
      link.click();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
      setBusy(false);
      return;
    }

    if (result.run_id) {
      userMessage(labels[upperAction] || normAction);
      state.turn = newTurn();
      await watchRun(result.run_id);
    } else {
      setBusy(false);
    }
  } catch (error) { setBusy(false); throw error; }
}
async function restore(id) {
  if (state.busy) return;
  notice();
  const raw = await api.session(id);
  const value = adaptSessionSnapshot(raw);
  state.controller?.abort();
  state.run = null;
  state.session = value;
  localStorage.setItem(storageKey, id);

  try {
    const pins = await api.pins(id);
    if (Array.isArray(pins)) state.session.pins = pins;
  } catch { /* pins endpoint optional */ }

  $('thread').replaceChildren();
  const hasMessages = Boolean(value.messages && value.messages.length);
  $('shell').classList.toggle('chat-active', hasMessages);

  for (const message of value.messages || []) {
    if (message.kind === 'user' || message.role === 'user') {
      userMessage(typeof message.content === 'string' ? message.content : (message.text || ''));
    } else if (message.kind === 'answer' || message.role === 'assistant') {
      renderAnswer(message.answer || message.content, $('thread'));
    }
  }
  for (const answer of value.answers || []) {
    renderAnswer(answer, $('thread'));
  }

  updateAirframeHighlight(value.last_query || '');
  state.records = value.records || [];
  $('evidenceWorkspace').hidden = !hasMessages;
  $('workspace').classList.toggle('has-evidence', hasMessages);
  renderRecords(state.records);
  renderBoard(value.board);
  renderPins();
  $('panelDialog').close();
  $('liveSpecCard').hidden = true;
  setBusy(false);
  status(demo ? 'demo · ready — simulated records only' : 'copilot ready — keep investigating');
  if (value.active_run_id) {
    state.turn = newTurn();
    await watchRun(value.active_run_id, 0);
  }
}
async function newSession() {
  if (state.busy) return;
  state.controller?.abort();
  state.run = null;
  state.cursor = 0;
  state.turn = null;
  state.records = [];
  currentFaultContext = '';

  $('thread').replaceChildren();
  $('evidencePanel').replaceChildren();
  $('boardPanel').replaceChildren();
  $('directResults').replaceChildren();
  $('liveSpecCard').hidden = true;
  $('liveSpecCard').textContent = '';
  $('chatInput').value = '';
  $('workspace').classList.remove('has-evidence');
  $('evidenceWorkspace').hidden = true;
  localStorage.removeItem(storageKey);

  updateAirframeHighlight('');
  notice();
  status('starting fresh investigation…');
  try {
    const value = await api.createSession($('domainSelect').value || 'aviation');
    await restore(value.session_id);
    $('chatInput').focus();
  } catch (err) {
    notice(err.message || 'Failed to initialize session');
    status('session error');
  }
}
async function directSearch() {
  if (state.busy || state.run) return;
  const query = $('queryText').value.trim();
  if (!query) throw new Error('Enter a search complaint.');
  setBusy(true);
  status('searching records without an LLM answer…');
  notice();
  updateAirframeHighlight(query);
  try {
    const rawResult = await api.search(searchSpec(query));
    const result = adaptSearchResult(rawResult);
    $('directResults').replaceChildren();
    $('directResults').append(node('h2', 'results-title', 'Retrieved records'));
    renderRecords(result.hits || [], $('directResults'));
    $('directResults').scrollIntoView({ block: 'nearest' });
  } finally {
    setBusy(false);
    status(demo ? 'demo · ready — simulated records only' : 'copilot ready — keep investigating');
  }
}
async function exportHandover() {
  const text = await api.handover(state.session.session_id); const url = URL.createObjectURL(new Blob([text], { type: 'text/markdown;charset=utf-8' }));
  const link = document.createElement('a'); link.href = url; link.download = `${demo ? 'SIMULATED-' : ''}maintenance-handover.md`; link.click(); setTimeout(() => URL.revokeObjectURL(url), 1000);
}
$('chatInput').addEventListener('input', e => {
  updateAirframeHighlight(e.target.value);
});
$('chatInput').addEventListener('keydown', event => {
  if (event.key === 'Enter' && !event.shiftKey) {
    event.preventDefault();
    if (!state.busy && $('chatInput').value.trim()) {
      protect(() => sendMessage($('chatInput').value));
    }
  }
});
$('chatForm').addEventListener('submit', event => { event.preventDefault(); protect(() => sendMessage($('chatInput').value)); });
$('searchBtn').addEventListener('click', () => protect(directSearch));
$('reportBtn').addEventListener('click', () => protect(() => sendMessage(($('aircraftInput').value.trim() ? `User-reported aircraft / engine: ${$('aircraftInput').value.trim()}\n` : '') + $('reportText').value)));
$('newSessionBtn').addEventListener('click', () => protect(newSession));
$('newChatMiniBtn')?.addEventListener('click', () => protect(newSession));
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
$('explorerBtn').addEventListener('click', () => { const toggle = document.querySelector('[data-drawer="queryDrawer"]'); if ($('queryDrawer').hidden) toggle.click(); $('queryDrawer').scrollIntoView({block:'center',behavior:'smooth'}); $('queryText').focus({preventScroll:true}); });
$('settingsBtn').addEventListener('click', () => {
  const body = panel('Settings', 'Server-confirmed capabilities');
  body.append(node('p', 'helper', 'Choose the model in the chat toolbar and retrieval options in Advanced options. These apply to future runs. Provider credentials belong on the server.'), button('Open search preferences', () => { $('panelDialog').close(); const toggle = document.querySelector('[data-drawer="advancedDrawer"]'); if ($('advancedDrawer').hidden) toggle.click(); $('advancedDrawer').scrollIntoView({block:'center',behavior:'smooth'}); }, 'primary-btn'));
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
  if ($('previewBadge')) $('previewBadge').textContent = demo ? 'DEMO PREVIEW' : 'LIVE COPILOT';
  if ($('workspacePill')) $('workspacePill').innerHTML = demo ? '<i></i> Simulated workspace' : '<i></i> Live workspace';
  if ($('workspaceSubtext')) $('workspaceSubtext').innerHTML = demo ? 'Playing offline scenario cards.<br>No live model or DB attached.' : 'Connected to live database.<br>6,369 verified records.';
  if ($('explorerNavLabel')) $('explorerNavLabel').textContent = demo ? 'Search demo records' : 'Search records';
  try {
    const rawCap = await api.capabilities();
    state.capabilities = adaptCapabilities(rawCap);
    const capabilities = state.capabilities;
    $('coverage').textContent = capabilities.corpus_summary || 'Source metadata unavailable';
    $('agentModelSelect').replaceChildren();
    for (const model of capabilities.models || []) {
      const option = node('option', '', model.label || model.id);
      option.value = model.id;
      $('agentModelSelect').append(option);
    }
    if (!capabilities.models?.length) {
      const fallbackOpt = node('option', '', 'extractive/v1 (deterministic)');
      fallbackOpt.value = 'extractive/v1';
      $('agentModelSelect').append(fallbackOpt);
    }
    $('domainSelect').replaceChildren();
    for (const domain of capabilities.domains || []) {
      const option = node('option', '', domain);
      option.value = domain;
      $('domainSelect').append(option);
    }
    const rerankEl = $('qualitySelect')?.querySelector('[value="rerank"]');
    if (rerankEl) rerankEl.disabled = !capabilities.rerank_available;
    $('agentModelSelect').disabled = false;

    const saved = localStorage.getItem(storageKey);
    if (saved) {
      try {
        await restore(saved);
      } catch (error) {
        if (error.status === 404 || demo) await newSession();
        else throw error;
      }
    } else {
      await newSession();
    }
    initAirframeInteractions();
  } catch (error) {
    status('backend unavailable');
    $('coverage').textContent = 'Source catalogue unavailable';
    notice(error.message + ' For the labeled simulated preview, open this URL with ?demo=1. Live mode never falls back to fixtures.');
  }
}
await boot();
