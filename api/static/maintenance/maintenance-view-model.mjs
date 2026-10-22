// Canonical view-model adapter for Maintenance Atlas.
// Normalizes wire contracts from FastAPI backend into UI consumption shapes.

export function adaptCapabilities(raw) {
  if (!raw) return { models: [], domains: ['aviation'], rerank_available: false, corpus_summary: 'Source metadata unavailable' };

  const models = (raw.configured_models || []).map(m => ({ id: m, label: m }));
  const domains = raw.domains && raw.domains.length ? raw.domains : ['aviation'];
  const rerankAvailable = Boolean(raw.reranker_available);

  let corpusSummary = '6,169 aviation · 200 facility records';
  if (Array.isArray(raw.corpora) && raw.corpora.length) {
    const parts = raw.corpora.map(c => `${(c.record_count || 0).toLocaleString()} ${c.domain}`);
    corpusSummary = parts.join(' · ') + ' records';
  }

  return {
    models,
    domains,
    rerank_available: rerankAvailable,
    corpus_summary: corpusSummary,
    provider_configured: Boolean(raw.provider_configured),
    workflows_ready: Boolean(raw.workflows_ready),
    agent_ready: Boolean(raw.agent_ready),
    enabled_modes: raw.enabled_modes || [],
  };
}

export function adaptSessionSnapshot(raw) {
  if (!raw) return null;
  const board = raw.board || [];
  return {
    session_id: raw.session_id,
    revision: raw.state_revision ?? 0,
    state_revision: raw.state_revision ?? 0,
    domain: raw.domain || 'aviation',
    title: raw.title || 'Untitled investigation',
    aircraft_profile: raw.aircraft_profile || {},
    messages: raw.messages || [],
    answers: (raw.answers || []).map(adaptAnswerEnvelope),
    board: {
      known: board.filter(b => b.column === 'known'),
      reported: board.filter(b => b.column === 'reported'),
      missing: board.filter(b => b.column === 'missing'),
      raw: board,
    },
    pins: raw.pins || [],
    active_run_id: raw.active_run_id || null,
  };
}

export function adaptSearchResult(raw) {
  if (!raw || !Array.isArray(raw.hits)) return { hits: [], trace: raw?.trace || null, timings: raw?.timings_ms || {} };
  const hits = raw.hits.map(h => {
    const snap = h.record_snapshot || h.snapshot || {};
    return {
      record_id: h.record_id,
      score: h.score,
      channels: h.channels || {},
      rank: h.rank,
      domain: snap.domain || (h.record_id.split(':')[0] || 'aviation'),
      source_id: snap.source_id || (h.record_id.split(':')[1] || h.record_id),
      corpus_id: snap.corpus_id || null,
      problem_raw: snap.problem_raw || snap.description_raw || '',
      action_raw: snap.action_raw || null,
      field_sha256: snap.field_sha256 || {},
      original_fields: snap.original_fields || {},
    };
  });
  return { hits, trace: raw.trace, timings: raw.timings_ms };
}

export function adaptAnswerEnvelope(env) {
  if (!env) return null;
  const claims = env.claims || [];
  return {
    answer_id: env.answer_id,
    run_id: env.run_id,
    mode: env.mode || 'EVIDENCE',
    status: env.status || 'supported_historical',
    headline: env.headline || '',
    claims,
    findings: claims.filter(c => c.claim_type === 'historical_problem' || c.claim_type === 'finding'),
    actions: claims.filter(c => c.claim_type === 'historical_action' || c.claim_type === 'action'),
    differences: claims.filter(c => c.claim_type === 'comparison' || c.claim_type === 'difference'),
    limitations: env.limitations || [],
    missing: env.missing || [],
    clarification: env.clarification || null,
    visual_refs: env.visual_refs || [],
    allowed_actions: env.allowed_actions || [],
  };
}

// Unicode code point slicing matching Python's str offsets
export function getUnicodeSpan(text, start, end) {
  if (!text) return '';
  const points = Array.from(text);
  return points.slice(start, end).join('');
}
