// Proposed maintenance adapter. This is new code, not the original Talent controller.
const PREFIX = '/api/maintenance/v1';
export const uid = () => crypto.randomUUID();

// Incremental SSE decoder: UTF-8 is handled by TextDecoder; CR/LF, comments,
// multiline data and arbitrary network chunk boundaries are handled here.
export async function* decodeSSE(body) {
  const reader = body.getReader();
  const decoder = new TextDecoder();
  let pending = '', lines = [];
  function frame() {
    const result = { event: 'message', id: '', data: '' };
    const data = [];
    for (const line of lines) {
      if (line.startsWith(':')) continue;
      const split = line.indexOf(':');
      const field = split < 0 ? line : line.slice(0, split);
      let value = split < 0 ? '' : line.slice(split + 1);
      if (value.startsWith(' ')) value = value.slice(1);
      if (field === 'data') data.push(value);
      if (field === 'event') result.event = value;
      if (field === 'id' && !value.includes('\0')) result.id = value;
    }
    lines = [];
    result.data = data.join('\n');
    return data.length ? result : null;
  }
  try {
    for (;;) {
      const { value, done } = await reader.read();
      pending += done ? decoder.decode() : decoder.decode(value, { stream: true });
      let cut;
      while ((cut = pending.search(/[\r\n]/)) >= 0) {
        if (!done && pending[cut] === '\r' && cut === pending.length - 1) break;
        const line = pending.slice(0, cut);
        const width = pending[cut] === '\r' && pending[cut + 1] === '\n' ? 2 : 1;
        pending = pending.slice(cut + width);
        if (line === '') { const result = frame(); if (result) yield result; }
        else lines.push(line);
      }
      if (done) {
        // SSE dispatch requires an empty line. Do not release a truncated frame.
        return;
      }
    }
  } finally { await reader.cancel().catch(() => {}); reader.releaseLock(); }
}

export function checkedEvent(frame, runId, cursor) {
  const value = JSON.parse(frame.data);
  if (value.protocol_version !== 'maintenance/v1' || value.run_id !== runId ||
      !Number.isSafeInteger(value.sequence) || value.sequence < 1 ||
      frame.id !== String(value.sequence) || frame.event !== value.type) {
    throw new Error('Invalid event envelope');
  }
  if (value.sequence <= cursor) return null; // duplicate replay is harmless
  if (value.sequence !== cursor + 1) throw new Error('Event gap; replay required');
  return value;
}

export function createApi() {
  async function request(path, { method = 'GET', json, body, signal } = {}) {
    const response = await fetch(PREFIX + path, {
      method, credentials: 'same-origin', signal,
      headers: json === undefined ? {} : { 'Content-Type': 'application/json' },
      body: json === undefined ? body : JSON.stringify(json),
    });
    if (!response.ok) {
      const error = new Error(response.status === 409
        ? 'This investigation changed. Reload its history before retrying.'
        : `Request failed (${response.status})`);
      error.status = response.status;
      throw error;
    }
    if (response.status === 204) return null;
    return response.json();
  }
  function mutate(path, json, method = 'POST') { return request(path, { method, json }); }
  return {
    capabilities: () => request('/capabilities'),
    listSessions: () => request('/sessions'),
    session: id => request(`/sessions/${encodeURIComponent(id)}`),
    createSession: domain => mutate('/sessions', { domain }),
    message: (id, payload) => mutate(`/sessions/${encodeURIComponent(id)}/messages`, payload),
    action: (id, payload) => mutate(`/sessions/${encodeURIComponent(id)}/actions`, payload),
    search: spec => mutate('/search', spec),
    cancel: runId => mutate(`/runs/${encodeURIComponent(runId)}/cancel`, {}),
    record: support => request(`/records/${encodeURIComponent(support.domain)}/${encodeURIComponent(support.source_id)}?corpus_version=${encodeURIComponent(support.corpus_version)}`),
    pin: (id, record, selected, revision) => mutate(
      `/sessions/${encodeURIComponent(id)}/pins/${encodeURIComponent(record.domain)}/${encodeURIComponent(record.source_id)}`,
      { corpus_version: record.corpus_version, expected_revision: revision }, selected ? 'PUT' : 'DELETE'),
    upload: (id, file, revision) => {
      const body = new FormData(); body.set('file', file); body.set('expected_revision', String(revision));
      return request(`/sessions/${encodeURIComponent(id)}/attachments`, { method: 'POST', body });
    },
    async handover(id) {
      const response = await fetch(`${PREFIX}/sessions/${encodeURIComponent(id)}/handover`, { credentials: 'same-origin' });
      if (!response.ok) throw new Error(`Export failed (${response.status})`);
      return response.text();
    },
    async subscribe(runId, onEvent, { signal, after = 0, onRetry = () => {} } = {}) {
      let cursor = after;
      for (let attempt = 0; attempt < 4; attempt++) {
        try {
          const response = await fetch(`${PREFIX}/runs/${encodeURIComponent(runId)}/events?after=${cursor}`, {
            credentials: 'same-origin', signal, headers: { Accept: 'text/event-stream' },
          });
          if (!response.ok || !response.body || !response.headers.get('content-type')?.includes('text/event-stream')) {
            const error = new Error(`Event stream unavailable (${response.status})`);
            error.status = response.status; throw error;
          }
          for await (const frame of decodeSSE(response.body)) {
            const event = checkedEvent(frame, runId, cursor);
            if (!event) continue;
            await onEvent(event); cursor = event.sequence;
            if (event.type === 'done') return;
          }
          throw new Error('Event stream disconnected');
        } catch (error) {
          if (signal?.aborted || [401, 403, 404, 410].includes(error.status) || attempt === 3) throw error;
          onRetry(cursor);
          // Replay GET only; reconnecting never creates another model run.
          await new Promise((resolve, reject) => {
            const aborted = () => { clearTimeout(timer); reject(new DOMException('Aborted', 'AbortError')); };
            const timer = setTimeout(() => { signal?.removeEventListener('abort', aborted); resolve(); }, 300 * (attempt + 1));
            signal?.addEventListener('abort', aborted, { once: true });
          });
        }
      }
    },
  };
}
