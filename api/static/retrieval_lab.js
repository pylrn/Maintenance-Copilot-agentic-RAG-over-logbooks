// Maintenance Atlas - Retrieval Lab Workbench JS

let currentHits = [];
let projectionData = null;
let currentHighlightedIds = new Set();
let canvasScale = 1;
let canvasOffset = { x: 0, y: 0 };
let isDragging = false;
let dragStart = { x: 0, y: 0 };

async function sha256Hex(text) {
  if (typeof text !== "string") return null;
  try {
    const encoder = new TextEncoder();
    const data = encoder.encode(text);
    const hashBuffer = await crypto.subtle.digest("SHA-256", data);
    const hashArray = Array.from(new Uint8Array(hashBuffer));
    return hashArray.map((b) => b.toString(16).padStart(2, "0")).join("");
  } catch (e) {
    return null;
  }
}

document.addEventListener("DOMContentLoaded", () => {
  initTabs();
  initQueryRunner();
  initProjectionViewer();
  initRecordBrowser();
  initStorageView();
  initModal();
});

// Tab Navigation
function initTabs() {
  const tabs = document.querySelectorAll(".nav-tab");
  tabs.forEach((tab) => {
    tab.addEventListener("click", () => {
      tabs.forEach((t) => t.classList.remove("active"));
      tab.classList.add("active");
      const targetId = tab.dataset.tab;
      document.querySelectorAll(".tab-pane").forEach((pane) => {
        pane.classList.remove("active");
      });
      const activePane = document.getElementById(targetId);
      if (activePane) {
        activePane.classList.add("active");
      }
      if (targetId === "pane-projection" && !projectionData) {
        loadProjection();
      } else if (targetId === "pane-projection") {
        drawProjection();
      } else if (targetId === "pane-records") {
        loadRecords(1);
      } else if (targetId === "pane-storage") {
        loadStorage();
      }
    });
  });
}

// 1. Retrieval Workbench & Query Runner
function initQueryRunner() {
  const searchBtn = document.getElementById("searchBtn");
  const queryInput = document.getElementById("queryInput");
  const domainSelect = document.getElementById("domainSelect");
  const intentSelect = document.getElementById("intentSelect");
  const topkInput = document.getElementById("topkInput");
  const dedupCheck = document.getElementById("dedupCheck");
  const rerankCheck = document.getElementById("rerankCheck");
  const componentFilter = document.getElementById("componentFilter");
  const symptomFilter = document.getElementById("symptomFilter");

  // Sample Query Chips
  document.querySelectorAll(".sample-chip").forEach((chip) => {
    chip.addEventListener("click", () => {
      queryInput.value = chip.dataset.query;
      domainSelect.value = chip.dataset.domain || "aviation";
      executeSearch();
    });
  });

  searchBtn.addEventListener("click", () => executeSearch());
  queryInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      executeSearch();
    }
  });

  const clearBtn = document.getElementById("clearBtn");
  if (clearBtn) {
    clearBtn.addEventListener("click", () => {
      queryInput.value = "";
      componentFilter.value = "";
      symptomFilter.value = "";
      document.getElementById("resultsList").innerHTML = `
        <div style="background:#fff;border:1px solid var(--border-light);border-radius:var(--radius-md);padding:40px;text-align:center;color:var(--text-dim);">
          Ready to search. Enter a query on the left and click "Search Records".
        </div>`;
    });
  }

  const headerRefreshBtn = document.getElementById("headerRefreshBtn");
  if (headerRefreshBtn) {
    headerRefreshBtn.addEventListener("click", () => {
      const activeTab = document.querySelector(".nav-tab.active")?.dataset.tab;
      if (activeTab === "pane-workbench") {
        if (queryInput.value.trim()) executeSearch();
      } else if (activeTab === "pane-projection") {
        loadProjection();
      } else if (activeTab === "pane-records") {
        loadRecords(currentRecordPage);
      } else if (activeTab === "pane-storage") {
        loadStorage();
      }
    });
  }

  const copyBtn = document.getElementById("copyJsonBtn");
  if (copyBtn) {
    copyBtn.addEventListener("click", () => {
      const text = document.getElementById("rawJsonPre")?.textContent || "";
      if (text) {
        navigator.clipboard.writeText(text);
        copyBtn.textContent = "Copied!";
        setTimeout(() => (copyBtn.textContent = "Copy Full JSON"), 1500);
      }
    });
  }

  const downloadBtn = document.getElementById("downloadJsonBtn");
  if (downloadBtn) {
    downloadBtn.addEventListener("click", () => {
      const text = document.getElementById("rawJsonPre")?.textContent || "";
      if (text) {
        const blob = new Blob([text], { type: "application/json" });
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `search-result-${Date.now()}.json`;
        a.click();
        URL.revokeObjectURL(url);
      }
    });
  }

  const exportFeedbackBtn = document.getElementById("exportFeedbackBtn");
  if (exportFeedbackBtn) {
    exportFeedbackBtn.addEventListener("click", () => {
      const allFeedback = [];
      for (let i = 0; i < localStorage.length; i++) {
        const key = localStorage.key(i);
        if (key && key.startsWith("feedback::")) {
          try {
            allFeedback.push(JSON.parse(localStorage.getItem(key)));
          } catch (e) {
            // ignore malformed
          }
        }
      }
      const blob = new Blob([JSON.stringify(allFeedback, null, 2)], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `retrieval-human-feedback-${Date.now()}.json`;
      a.click();
      URL.revokeObjectURL(url);
    });
  }

  async function executeSearch() {
    const raw = queryInput.value.trim();
    if (!raw) return;

    searchBtn.disabled = true;
    searchBtn.textContent = "Executing...";

    const payload = {
      query_raw: raw,
      domain: domainSelect.value,
      intent: intentSelect.value,
      top_k: parseInt(topkInput.value, 10) || 6,
      collapse_duplicates: dedupCheck.checked,
      quality_mode: rerankCheck.checked,
      filters: {
        component: componentFilter.value.trim().toLowerCase() || null,
        symptom: symptomFilter.value.trim().toLowerCase() || null,
      },
    };

    let data = null;
    let clientMs = 0;
    try {
      const t0 = performance.now();
      const res = await fetch("/api/maintenance/v1/search", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Origin": window.location.origin,
        },
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        alert(`Search failed (${res.status}): ${err.error || err.message || "Unknown error"}`);
        return;
      }

      data = await res.json();
      clientMs = performance.now() - t0;
    } catch (err) {
      console.error("Search network fetch error:", err);
      alert(`Network error during search: ${err.message}`);
      return;
    } finally {
      searchBtn.disabled = false;
      searchBtn.textContent = "Search Records";
    }

    try {
      await renderSearchResults(data, clientMs);
    } catch (renderErr) {
      console.error("Render error in renderSearchResults:", renderErr);
      alert(`UI rendering error: ${renderErr.message}`);
    }
  }
}

async function renderSearchResults(data, clientMs = 0) {
  if (!data) return;
  currentHits = data.hits || [];
  currentHighlightedIds = new Set(currentHits.map((h) => h.record_id));

  // Redraw projection scatter with newly highlighted hits
  drawProjection();

  // Helper safely setting text
  const setText = (id, text) => {
    const el = document.getElementById(id);
    if (el) el.textContent = text;
  };

  // 1. Prominent timing banner
  setText("timeClientVal", `${clientMs.toFixed(1)} ms`);
  const timings = data.timings_ms || {};
  setText("timeServerVal", `${(timings.total || 0).toFixed(1)} ms`);
  setText("timeEmbedVal", `${(timings.embedding || 0).toFixed(1)} ms`);
  const recallMs =
    (timings.raw_bm25 || 0) +
    (timings.normalized_bm25 || 0) +
    (timings.dense_cosine || 0) +
    (timings.fusion || 0) +
    (timings.compatibility_filtering || 0);
  setText("timeRecallVal", `${recallMs.toFixed(1)} ms`);
  setText("timeRerankVal", `${(timings.rerank || 0).toFixed(1)} ms`);

  const degradedEl = document.getElementById("degradedSummaryVal");
  if (degradedEl) {
    if (data.degraded_branches && data.degraded_branches.length > 0) {
      degradedEl.textContent = data.degraded_branches.join(", ");
      degradedEl.style.color = "var(--accent-amber)";
    } else {
      degradedEl.textContent = "none";
      degradedEl.style.color = "var(--brand-green)";
    }
  }

  // 2. Active filters bar
  const filtersBar = document.getElementById("activeFiltersBar");
  if (filtersBar && data.spec) {
    filtersBar.innerHTML = `
      <span style="color:var(--text-dim);font-weight:600;">Active filters:</span>
      <span class="filter-badge">domain=${escapeHtml(data.spec.domain)}</span>
      <span class="filter-badge">intent=${escapeHtml(data.spec.intent)}</span>
      <span class="filter-badge">collapse_duplicates=${data.spec.collapse_duplicates}</span>
      ${data.spec.filters?.component ? `<span class="filter-badge">component=${escapeHtml(data.spec.filters.component)}</span>` : ""}
      ${data.spec.filters?.symptom ? `<span class="filter-badge">symptom=${escapeHtml(data.spec.filters.symptom)}</span>` : ""}
      ${data.spec.quality_mode ? `<span class="filter-badge" style="border-color:var(--accent-blue);color:var(--accent-blue);">quality_mode=true</span>` : ""}
    `;
  }

  // 3. Results List
  const resultsContainer = document.getElementById("resultsList");
  if (!resultsContainer) return;
  resultsContainer.innerHTML = "";

  if (currentHits.length === 0) {
    resultsContainer.innerHTML = `
      <div style="background:#fff;border:1px solid var(--border-light);border-radius:var(--radius-md);padding:40px;text-align:center;color:var(--text-dim);">
        No records matched query and filters.
      </div>`;
  } else {
    for (let idx = 0; idx < currentHits.length; idx++) {
      const hit = currentHits[idx];
      const card = document.createElement("div");
      card.className = "result-card";

      const domain = hit.record_id.startsWith("aviation:") ? "aviation" : "facility";
      const sourceId = hit.record_id.split(":")[1] || "";
      const snapshot = hit.record_snapshot || {};
      const fileSha = snapshot.source_file_sha256 || "";

      // Tier: backend is lowercase ("direct", "related", "tangential", "rejected")
      const tierRaw = (hit.compatibility?.tier || "unknown").toLowerCase();
      let tierClass = "tier-tangential";
      if (tierRaw === "direct") tierClass = "tier-direct";
      else if (tierRaw === "related") tierClass = "tier-related";

      const dupCount = hit.duplicate_count || 1;
      const dupPill = dupCount > 1
        ? `<span class="score-pill" title="${escapeHtml((hit.duplicate_ids || []).join(', '))}" style="font-size:10px;">${dupCount} duplicates</span>`
        : "";

      // Channel ranks row
      const ranks = hit.channel_ranks || {};
      const scores = hit.channel_scores || {};
      const channelsHtml = Object.keys(ranks).map((ch) => {
        const r = ranks[ch] ?? "-";
        const s = scores[ch] !== undefined ? scores[ch].toFixed(3) : "-";
        return `<span class="channel-badge">${escapeHtml(ch)}: #${r} (${s})</span>`;
      }).join(" ");

      // Facts & compatibility: show actual string values ("agreement", "difference", "unknown")
      const facts = hit.compatibility?.facts || {};
      const factComp = facts.component || "unknown";
      const factSymp = facts.symptom || "unknown";
      const factNum = facts.number || "unknown";
      const factNeg = facts.negation || "unknown";
      const factLat = facts.laterality || "unknown";

      const limitations = hit.compatibility?.limitations || [];
      const limitationsHtml = limitations.length > 0
        ? `<div style="margin-top:6px;color:var(--text-dim);font-size:11px;"><strong>Limitations:</strong> ${escapeHtml(limitations.join("; "))}</div>`
        : "";

      // Evidence Boxes: render each real source field separately with label OUTSIDE exact quote
      // Offsets strictly: [0, Array.from(rawFieldText).length]
      // Correct uppercase recorded SHA from snapshot.field_sha256 (PROBLEM, ACTION, DESCRIPTION)
      // WebCrypto SHA256 computed on TextEncoder(rawFieldText), verified badge ONLY on exact equality!
      const fieldHashes = snapshot.field_sha256 || {};
      const fieldsToRender = [];
      if (domain === "aviation") {
        if (snapshot.problem_raw !== undefined && snapshot.problem_raw !== null) {
          fieldsToRender.push({
            name: "PROBLEM",
            text: snapshot.problem_raw,
            recordedSha: fieldHashes.PROBLEM || "",
          });
        }
        if (snapshot.action_raw !== undefined && snapshot.action_raw !== null && snapshot.action_raw !== "") {
          fieldsToRender.push({
            name: "ACTION",
            text: snapshot.action_raw,
            recordedSha: fieldHashes.ACTION || "",
          });
        }
      } else {
        if (snapshot.problem_raw !== undefined && snapshot.problem_raw !== null) {
          fieldsToRender.push({
            name: "DESCRIPTION",
            text: snapshot.problem_raw,
            recordedSha: fieldHashes.DESCRIPTION || "",
          });
        }
      }

      let evidenceBoxesHtml = "";
      for (const f of fieldsToRender) {
        const computedSha = await sha256Hex(f.text);
        const isVerified = Boolean(
          computedSha &&
          f.recordedSha &&
          computedSha.toLowerCase() === f.recordedSha.toLowerCase()
        );
        const statusBadge = isVerified
          ? `<span class="verified-badge">✓ SHA256 Verified</span>`
          : `<span class="score-pill" style="color:var(--text-dim);font-size:10px;">Recorded source hash</span>`;

        evidenceBoxesHtml += `
          <div class="evidence-box">
            <div class="evidence-header">
              <span style="font-weight:700;font-size:11px;color:var(--text-dim);">FIELD EVIDENCE: ${escapeHtml(f.name)}</span>
              ${statusBadge}
            </div>
            <div class="quote-text">${escapeHtml(f.text)}</div>
            <div style="display:flex;justify-content:space-between;margin-top:6px;font-size:10px;color:var(--text-dim);flex-wrap:wrap;gap:6px;">
              <span>Offsets: [0, ${Array.from(f.text).length}]</span>
              <span title="${escapeHtml(f.recordedSha)}">Recorded field SHA: <span style="font-family:var(--font-mono);">${f.recordedSha ? f.recordedSha.slice(0, 16) + '...' : '-'}</span></span>
              <span title="${escapeHtml(fileSha)}">Recorded file provenance SHA: <span style="font-family:var(--font-mono);">${fileSha ? fileSha.slice(0, 12) + '...' : '-'}</span></span>
              <span>Record: <span style="font-family:var(--font-mono);">${escapeHtml(hit.record_id)}</span> (Corpus: ${(hit.corpus_id || '').slice(0, 8)})</span>
            </div>
          </div>
        `;
      }

      // Feedback state from localStorage
      const feedbackKey = `feedback::${hit.record_id}::${data.spec?.query_raw || ''}`;
      let savedFeedback = null;
      try {
        const item = localStorage.getItem(feedbackKey);
        if (item) savedFeedback = JSON.parse(item).feedback;
      } catch (e) {
        // ignore
      }

      card.innerHTML = `
        <div class="result-card-header">
          <div class="result-title-box">
            <div style="display:flex;align-items:center;gap:6px;">
              <span style="font-weight:700;font-size:14px;color:var(--text-main);">#${idx + 1}</span>
              <span class="badge ${domain === 'aviation' ? 'badge-aviation' : 'badge-facility'}">${domain}</span>
              <span style="font-family:var(--font-mono);font-weight:700;color:var(--text-main);">${escapeHtml(hit.record_id)}</span>
            </div>
            <div class="result-subtitle">Corpus: ${(hit.corpus_id || "").slice(0, 8)}... | CSV Row: ${snapshot.csv_row || "-"}</div>
          </div>
          <div class="result-badges">
            <span class="tier-pill ${tierClass}">${escapeHtml(tierRaw.toUpperCase())}</span>
            ${dupPill}
            <span class="score-pill">RRF: ${hit.rrf_score.toFixed(4)}</span>
          </div>
        </div>

        <div class="channel-badges-row">
          ${channelsHtml || '<span class="channel-badge">no channel ranks</span>'}
        </div>

        <details class="accordion">
          <summary>Why ranked here? Facts & Compatibility</summary>
          <div class="accordion-body">
            <div class="facts-grid">
              <div class="fact-item"><span>Component</span><strong>${escapeHtml(factComp)}</strong></div>
              <div class="fact-item"><span>Symptom</span><strong>${escapeHtml(factSymp)}</strong></div>
              <div class="fact-item"><span>Number</span><strong>${escapeHtml(factNum)}</strong></div>
              <div class="fact-item"><span>Negation</span><strong>${escapeHtml(factNeg)}</strong></div>
              <div class="fact-item"><span>Laterality</span><strong>${escapeHtml(factLat)}</strong></div>
            </div>
            ${limitationsHtml}
          </div>
        </details>

        ${evidenceBoxesHtml}

        <div class="result-footer">
          <div class="feedback-controls">
            <span style="color:var(--text-dim);font-weight:600;">Feedback:</span>
            <button class="btn-feedback ${savedFeedback === 'relevant' ? 'active' : ''}" data-feedback="relevant" type="button">👍 Relevant</button>
            <button class="btn-feedback ${savedFeedback === 'not_relevant' ? 'active' : ''}" data-feedback="not_relevant" type="button">👎 Not relevant</button>
            <button class="btn-feedback ${savedFeedback === 'unsure' ? 'active' : ''}" data-feedback="unsure" type="button">Unsure</button>
          </div>
          <button class="btn-record-link" type="button">Inspect Raw Record &amp; SHA256 →</button>
        </div>
      `;

      // Wire card click
      card.addEventListener("click", (e) => {
        // If clicking feedback buttons or summary accordion, don't open modal
        if (e.target.closest(".feedback-controls") || e.target.closest("summary") || e.target.closest("details")) {
          return;
        }
        openRecordModal(domain, sourceId, hit.corpus_id, hit.record_snapshot);
      });

      // Wire feedback buttons
      const fbBtns = card.querySelectorAll(".btn-feedback");
      fbBtns.forEach((btn) => {
        btn.addEventListener("click", (e) => {
          e.stopPropagation();
          const fbType = btn.dataset.feedback;
          fbBtns.forEach((b) => b.classList.remove("active"));
          btn.classList.add("active");
          const payload = {
            search_id: data.search_id || null,
            query: data.spec?.query_raw || "",
            domain,
            record_id: hit.record_id,
            corpus_id: hit.corpus_id,
            source_id: sourceId,
            feedback: fbType,
            rrf_score: hit.rrf_score,
            tier: tierRaw,
            versions: data.versions || {},
            timestamp: new Date().toISOString(),
          };
          try {
            localStorage.setItem(feedbackKey, JSON.stringify(payload));
          } catch (err) {
            console.warn("localStorage quota exceeded:", err);
          }
        });
      });

      resultsContainer.appendChild(card);
    }
  }

  // 4. Waterfall Stages Table
  const stagesTbody = document.getElementById("stagesTableBody");
  if (stagesTbody) {
    stagesTbody.innerHTML = "";
    const totalTime = timings.total || 1.0;
    const stages = data.trace?.stages || [];
    stages.forEach((st) => {
      const tr = document.createElement("tr");
      const pct = Math.min(100, Math.max(0, (st.duration_ms / totalTime) * 100)).toFixed(1);

      const details = st.details || {};
      let statusNote = "";
      if (st.stage === "record_fetch") {
        statusNote = `<span class="score-pill" style="font-size:10px;">in-memory snapshot (db_fetch: not_executed_in_search)</span>`;
      } else if (st.stage === "rerank") {
        statusNote = `<span class="score-pill" style="font-size:10px;">${escapeHtml(String(details.status || "skipped"))}</span>`;
      } else if (details.status) {
        statusNote = `<span class="score-pill" style="font-size:10px;">${escapeHtml(String(details.status))}</span>`;
      }

      tr.innerHTML = `
        <td>
          <div><strong>${escapeHtml(st.stage)}</strong></div>
          <div style="margin-top:2px;">${statusNote}</div>
        </td>
        <td style="font-family:var(--font-mono);">${st.duration_ms.toFixed(2)} ms</td>
        <td style="width:110px;">
          <div class="timing-bar-wrap">
            <div class="timing-bar" style="width: ${pct}%;"></div>
          </div>
          <div style="font-size:10px;color:var(--text-dim);">${pct}%</div>
        </td>
        <td style="font-family:var(--font-mono);color:var(--text-muted);">${st.count_in ?? "-"}</td>
        <td style="font-family:var(--font-mono);color:var(--accent-blue);font-weight:600;">${st.count_out ?? "-"}</td>
      `;
      stagesTbody.appendChild(tr);
    });
  }

  // 5. Raw JSON Pre
  const rawPre = document.getElementById("rawJsonPre");
  if (rawPre) {
    rawPre.textContent = JSON.stringify(data, null, 2);
  }
}

// 2. 2D Projection Explorer
function initProjectionViewer() {
  const canvas = document.getElementById("projectionCanvas");
  if (!canvas) return;

  const refreshBtn = document.getElementById("refreshProjectionBtn");
  const repSelect = document.getElementById("projectionRepSelect");
  const domainFilter = document.getElementById("projectionDomainFilter");
  const maxPointsInput = document.getElementById("projectionMaxPoints");

  refreshBtn.addEventListener("click", () => loadProjection());
  repSelect.addEventListener("change", () => loadProjection());
  domainFilter.addEventListener("change", () => drawProjection());
  maxPointsInput.addEventListener("change", () => loadProjection());

  window.addEventListener("resize", debounce(() => drawProjection(), 150));

  // Mouse pan & zoom on canvas
  canvas.addEventListener("mousedown", (e) => {
    isDragging = true;
    dragStart = { x: e.clientX - canvasOffset.x, y: e.clientY - canvasOffset.y };
  });

  window.addEventListener("mousemove", (e) => {
    if (!isDragging) return;
    canvasOffset.x = e.clientX - dragStart.x;
    canvasOffset.y = e.clientY - dragStart.y;
    drawProjection();
  });

  window.addEventListener("mouseup", () => {
    isDragging = false;
  });

  canvas.addEventListener("wheel", (e) => {
    e.preventDefault();
    const zoomFactor = e.deltaY < 0 ? 1.15 : 0.85;
    canvasScale = Math.min(10, Math.max(0.2, canvasScale * zoomFactor));
    drawProjection();
  });

  // Click on canvas to select point
  canvas.addEventListener("click", (e) => {
    if (!projectionData || !projectionData.points) return;
    const rect = canvas.getBoundingClientRect();
    const clickX = e.clientX - rect.left;
    const clickY = e.clientY - rect.top;

    const hit = findNearestPoint(clickX, clickY);
    if (hit) {
      openRecordModal(hit.domain, hit.source_id, hit.corpus_id, hit);
    }
  });
}

async function loadProjection() {
  const rep = document.getElementById("projectionRepSelect").value;
  const maxPoints = parseInt(document.getElementById("projectionMaxPoints").value, 10) || 10000;

  const btn = document.getElementById("refreshProjectionBtn");
  btn.disabled = true;
  btn.textContent = "Loading...";

  try {
    const res = await fetch(`/api/maintenance/v1/lab/projection?representation=${encodeURIComponent(rep)}&max_points=${maxPoints}`, {
      headers: { "Origin": window.location.origin }
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      alert(`Projection load failed (${res.status}): ${err.error || "Unknown error"}`);
      return;
    }

    projectionData = await res.json();
    renderProjectionMetadata(projectionData);
    resetCanvasView();
    drawProjection();
  } catch (err) {
    console.error("Projection fetch error:", err);
  } finally {
    btn.disabled = false;
    btn.textContent = "Refresh Projection";
  }
}

function renderProjectionMetadata(data) {
  document.getElementById("pcaMethodVal").textContent = data.method;
  const ev = data.explained_variance || [0, 0];
  document.getElementById("pcaVarVal").textContent = `PC1: ${(ev[0] * 100).toFixed(1)}% | PC2: ${(ev[1] * 100).toFixed(1)}% (Total: ${(data.total_explained_variance * 100).toFixed(1)}%)`;
  document.getElementById("pcaRevisionVal").textContent = `${data.model_id} (${(data.model_revision || "").slice(0, 8)})`;
  document.getElementById("pcaSourceHashVal").textContent = (data.source_hash || "").slice(0, 16) + "...";
  document.getElementById("pcaPointsCountVal").textContent = `${data.total_points} records plotted`;
}

function resetCanvasView() {
  canvasScale = 1;
  canvasOffset = { x: 0, y: 0 };
}

function drawProjection() {
  const canvas = document.getElementById("projectionCanvas");
  if (!canvas || !projectionData || !projectionData.points) return;

  const ctx = canvas.getContext("2d");
  const width = canvas.clientWidth;
  const height = canvas.clientHeight;
  canvas.width = width;
  canvas.height = height;

  ctx.clearRect(0, 0, width, height);

  const points = projectionData.points;
  if (points.length === 0) return;

  // Find min/max bounds
  let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;
  for (const pt of points) {
    if (pt.x < minX) minX = pt.x;
    if (pt.x > maxX) maxX = pt.x;
    if (pt.y < minY) minY = pt.y;
    if (pt.y > maxY) maxY = pt.y;
  }

  const rangeX = (maxX - minX) || 1;
  const rangeY = (maxY - minY) || 1;
  const pad = 40;

  const domainFilter = document.getElementById("projectionDomainFilter").value;

  // Transformation helper
  function toCanvasCoords(pt) {
    const normX = (pt.x - minX) / rangeX;
    const normY = (pt.y - minY) / rangeY;
    const cx = pad + normX * (width - 2 * pad);
    const cy = pad + (1 - normY) * (height - 2 * pad);
    return {
      x: (cx - width / 2) * canvasScale + width / 2 + canvasOffset.x,
      y: (cy - height / 2) * canvasScale + height / 2 + canvasOffset.y,
    };
  }

  // Draw background points (domain filter applies)
  for (const pt of points) {
    if (domainFilter !== "all" && pt.domain !== domainFilter) continue;

    const isHit = currentHighlightedIds.has(pt.record_id);
    if (isHit) continue; // draw hits on top

    const pos = toCanvasCoords(pt);
    ctx.beginPath();
    ctx.arc(pos.x, pos.y, 2.5 * canvasScale, 0, Math.PI * 2);
    ctx.fillStyle = pt.domain === "aviation" ? "rgba(56, 189, 248, 0.45)" : "rgba(245, 158, 11, 0.55)";
    ctx.fill();
  }

  // Draw query hits on top (domain filter also applies)
  for (const pt of points) {
    if (domainFilter !== "all" && pt.domain !== domainFilter) continue;
    if (!currentHighlightedIds.has(pt.record_id)) continue;
    const pos = toCanvasCoords(pt);

    // Glowing outer ring
    ctx.beginPath();
    ctx.arc(pos.x, pos.y, 8 * canvasScale, 0, Math.PI * 2);
    ctx.fillStyle = "rgba(244, 63, 94, 0.35)";
    ctx.fill();
    ctx.lineWidth = 1.5;
    ctx.strokeStyle = "#f43f5e";
    ctx.stroke();

    // Inner bright dot
    ctx.beginPath();
    ctx.arc(pos.x, pos.y, 4 * canvasScale, 0, Math.PI * 2);
    ctx.fillStyle = "#ffffff";
    ctx.fill();
  }
}

function findNearestPoint(clickX, clickY) {
  if (!projectionData || !projectionData.points) return null;
  const canvas = document.getElementById("projectionCanvas");
  const width = canvas.clientWidth;
  const height = canvas.clientHeight;

  const points = projectionData.points;
  let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;
  for (const pt of points) {
    if (pt.x < minX) minX = pt.x;
    if (pt.x > maxX) maxX = pt.x;
    if (pt.y < minY) minY = pt.y;
    if (pt.y > maxY) maxY = pt.y;
  }
  const rangeX = (maxX - minX) || 1;
  const rangeY = (maxY - minY) || 1;
  const pad = 40;

  const domainFilter = document.getElementById("projectionDomainFilter").value;
  let closest = null;
  let minDist = 15; // 15px radius threshold

  for (const pt of points) {
    if (domainFilter !== "all" && pt.domain !== domainFilter) continue;

    const normX = (pt.x - minX) / rangeX;
    const normY = (pt.y - minY) / rangeY;
    const cx = pad + normX * (width - 2 * pad);
    const cy = pad + (1 - normY) * (height - 2 * pad);
    const px = (cx - width / 2) * canvasScale + width / 2 + canvasOffset.x;
    const py = (cy - height / 2) * canvasScale + height / 2 + canvasOffset.y;

    const dist = Math.hypot(clickX - px, clickY - py);
    if (dist < minDist) {
      minDist = dist;
      closest = pt;
    }
  }
  return closest;
}

// 3. Corpus Record Browser
let currentRecordPage = 1;

function initRecordBrowser() {
  const domainFilter = document.getElementById("browserDomainSelect");
  const searchFilter = document.getElementById("browserSearchInput");
  const pageSizeSelect = document.getElementById("browserPageSizeSelect");
  const prevBtn = document.getElementById("browserPrevBtn");
  const nextBtn = document.getElementById("browserNextBtn");

  domainFilter.addEventListener("change", () => loadRecords(1));
  searchFilter.addEventListener("input", debounce(() => loadRecords(1), 300));
  pageSizeSelect.addEventListener("change", () => loadRecords(1));

  prevBtn.addEventListener("click", () => {
    if (currentRecordPage > 1) loadRecords(currentRecordPage - 1);
  });
  nextBtn.addEventListener("click", () => {
    loadRecords(currentRecordPage + 1);
  });
}

async function loadRecords(page = 1) {
  currentRecordPage = page;
  const domain = document.getElementById("browserDomainSelect").value;
  const search = document.getElementById("browserSearchInput").value.trim();
  const pageSize = document.getElementById("browserPageSizeSelect").value;

  const url = new URL("/api/maintenance/v1/lab/records", window.location.origin);
  if (domain && domain !== "all") url.searchParams.set("domain", domain);
  if (search) url.searchParams.set("search", search);
  url.searchParams.set("page", page);
  url.searchParams.set("page_size", pageSize);

  try {
    const res = await fetch(url.toString(), {
      headers: { "Origin": window.location.origin }
    });
    if (!res.ok) return;

    const data = await res.json();
    renderRecordsTable(data);
  } catch (err) {
    console.error("Records load error:", err);
  }
}

function renderRecordsTable(data) {
  const tbody = document.getElementById("recordsTableBody");
  tbody.innerHTML = "";

  document.getElementById("recordsMetaChip").textContent = `${data.total} records total`;
  document.getElementById("browserPageMeta").textContent = `Page ${data.page} of ${data.total_pages}`;
  document.getElementById("browserPrevBtn").disabled = data.page <= 1;
  document.getElementById("browserNextBtn").disabled = data.page >= data.total_pages;

  (data.items || []).forEach((r) => {
    const tr = document.createElement("tr");
    tr.onclick = () => openRecordModal(r.domain, r.source_id, r.corpus_id, r);

    const domainBadge = r.domain === "aviation"
      ? '<span class="badge badge-aviation">aviation</span>'
      : '<span class="badge badge-facility">facility</span>';

    const actionVal = r.action_raw
      ? escapeHtml(r.action_raw)
      : '<span style="color:var(--text-dim);">null</span>';

    tr.innerHTML = `
      <td style="font-family:var(--font-mono);font-weight:600;">${escapeHtml(r.record_id)}</td>
      <td>${domainBadge}</td>
      <td style="font-family:var(--font-mono);">${escapeHtml(r.source_id)}</td>
      <td>${escapeHtml(r.problem_raw)}</td>
      <td>${actionVal}</td>
      <td style="font-family:var(--font-mono);">${r.csv_row}</td>
      <td style="font-family:var(--font-mono);font-size:11px;color:var(--text-dim);">${(r.duplicate_key || "").slice(0, 10)}...</td>
    `;
    tbody.appendChild(tr);
  });
}

// 4. System & Storage View
function initStorageView() {
  // Storage view initialization
  const refreshBtn = document.getElementById("refreshStorageBtn");
  if (refreshBtn) {
    refreshBtn.addEventListener("click", () => loadStorage());
  }
}

async function loadStorage() {
  try {
    const res = await fetch("/api/maintenance/v1/lab/storage", {
      headers: { "Origin": window.location.origin }
    });
    if (!res.ok) return;

    const data = await res.json();

    document.getElementById("storageTimestampVal").textContent = data.timestamp;

    const dbBadge = document.getElementById("dbStatusVal");
    if (data.database_status === "connected") {
      dbBadge.className = "badge badge-tier-direct";
      dbBadge.textContent = "connected";
    } else {
      dbBadge.className = "badge badge-degraded";
      dbBadge.textContent = data.database_status || "unavailable";
    }

    // Database size & Quota
    const quotaBytes = data.quota_bytes || 500000000;
    const dbBytes = data.database_bytes;

    if (dbBytes === null || dbBytes === undefined) {
      document.getElementById("quotaProgressBar").style.width = "0%";
      document.getElementById("quotaProgressBar").style.background = "var(--border-color)";
      document.getElementById("quotaTextVal").textContent = `Database size unavailable (Postgres not connected) — [${data.quota_label}]`;
    } else {
      const pct = Math.min(100, Math.max(0, (dbBytes / quotaBytes) * 100));
      document.getElementById("quotaProgressBar").style.width = `${pct}%`;
      document.getElementById("quotaProgressBar").style.background = "linear-gradient(90deg, var(--accent-cyan), var(--accent-blue))";
      document.getElementById("quotaTextVal").textContent = `${formatBytes(dbBytes)} of ${formatBytes(quotaBytes)} (${pct.toFixed(2)}% used) — [${data.quota_label}]`;
    }

    // Records & Vectors
    document.getElementById("totalRecordsVal").textContent = (data.index_record_count ?? data.db_records ?? 0).toLocaleString();
    document.getElementById("totalVectorsVal").textContent = (data.index_vector_count ?? data.db_vectors ?? 0).toLocaleString();
    document.getElementById("indexMemoryVal").textContent = formatBytes(data.dense_vector_memory_bytes || 0);

    // Domains
    const dom = data.domains || {};
    document.getElementById("domainBreakdownVal").textContent = `Aviation: ${dom.aviation ?? 0} | Facility: ${dom.facility ?? 0}`;

    // Tables
    const tablesTbody = document.getElementById("storageTablesBody");
    tablesTbody.innerHTML = "";
    const tbls = data.tables || {};
    if (Object.keys(tbls).length === 0) {
      tablesTbody.innerHTML = '<tr><td colspan="3" style="color:var(--text-dim);text-align:center;">Database tables metrics unavailable (in-memory mode)</td></tr>';
    } else {
      for (const [tname, tinfo] of Object.entries(tbls)) {
        const tr = document.createElement("tr");
        tr.innerHTML = `
          <td style="font-family:var(--font-mono);font-weight:600;">${escapeHtml(tname)}</td>
          <td style="font-family:var(--font-mono);">${formatBytes(tinfo.bytes || 0)}</td>
          <td style="font-family:var(--font-mono);">${(tinfo.row_count || 0).toLocaleString()}</td>
        `;
        tablesTbody.appendChild(tr);
      }
    }
  } catch (err) {
    console.error("Storage load error:", err);
  }
}

// 5. Shared Async Source Fetch & Record Modal (Guarded against race conditions)
let currentModalRequestId = 0;

function initModal() {
  const overlay = document.getElementById("recordModalOverlay");
  const closeBtn = document.getElementById("modalCloseBtn");
  closeBtn.addEventListener("click", () => {
    currentModalRequestId++; // Invalidate any pending async fetch
    overlay.classList.remove("open");
  });
  overlay.addEventListener("click", (e) => {
    if (e.target === overlay) {
      currentModalRequestId++; // Invalidate any pending async fetch
      overlay.classList.remove("open");
    }
  });
}

async function openRecordModal(domain, sourceId, corpusId, fallbackSnapshot = null) {
  const overlay = document.getElementById("recordModalOverlay");
  overlay.classList.add("open");

  currentModalRequestId++;
  const thisRequestId = currentModalRequestId;

  const modalRecordId = document.getElementById("modalRecordId");
  const modalDomain = document.getElementById("modalDomain");
  const modalSourceId = document.getElementById("modalSourceId");
  const modalCsvRow = document.getElementById("modalCsvRow");
  const modalSourceFileSha = document.getElementById("modalSourceFileSha");
  const modalProblemRaw = document.getElementById("modalProblemRaw");
  const modalActionRaw = document.getElementById("modalActionRaw");
  const modalFieldsTableBody = document.getElementById("modalFieldsTableBody");
  const modalFetchStatus = document.getElementById("modalFetchStatus");

  modalRecordId.textContent = `${domain}:${sourceId}`;
  modalDomain.textContent = domain;
  modalDomain.className = domain === "aviation" ? "badge badge-aviation" : "badge badge-facility";
  modalSourceId.textContent = sourceId;
  modalCsvRow.textContent = "...";
  modalSourceFileSha.textContent = "...";
  modalProblemRaw.textContent = "Loading exact record from server...";
  modalActionRaw.textContent = "...";
  modalFieldsTableBody.innerHTML = '<tr><td colspan="3" style="text-align:center;color:var(--text-dim);padding:20px;">Fetching exact source record...</td></tr>';
  modalFetchStatus.textContent = "Fetching via GET /api/maintenance/v1/records...";

  const t0 = performance.now();
  let record = null;

  try {
    const url = `/api/maintenance/v1/records/${encodeURIComponent(domain)}/${encodeURIComponent(sourceId)}?corpus_id=${encodeURIComponent(corpusId)}`;
    const res = await fetch(url, {
      headers: { "Origin": window.location.origin }
    });

    // Guard: ignore response if modal was closed or a newer record was clicked
    if (thisRequestId !== currentModalRequestId) return;

    const elapsedMs = (performance.now() - t0).toFixed(1);

    if (res.ok) {
      record = await res.json();
      modalFetchStatus.textContent = `Client HTTP Fetch: ${elapsedMs} ms (GET /records/${domain}/${sourceId})`;
    } else {
      modalFetchStatus.textContent = `Fetch returned ${res.status}. Falling back to cached snapshot.`;
      record = fallbackSnapshot;
    }
  } catch (err) {
    if (thisRequestId !== currentModalRequestId) return;
    modalFetchStatus.textContent = `Network fetch failed. Using available snapshot.`;
    record = fallbackSnapshot;
  }

  if (thisRequestId !== currentModalRequestId) return;

  if (!record) {
    modalProblemRaw.textContent = "Failed to load record details.";
    modalFieldsTableBody.innerHTML = '<tr><td colspan="3" style="color:var(--accent-rose);text-align:center;">Record not found.</td></tr>';
    return;
  }

  modalRecordId.textContent = record.record_id || `${domain}:${sourceId}`;
  modalDomain.textContent = record.domain || domain;
  modalSourceId.textContent = record.source_id || sourceId;
  modalCsvRow.textContent = record.csv_row || "-";
  modalSourceFileSha.textContent = record.source_file_sha256 || "-";

  modalProblemRaw.textContent = record.problem_raw || "-";
  modalActionRaw.textContent = record.action_raw ?? "null (facility domain has no action field)";

  // Populate Original Fields Table
  const origFields = record.original_fields || {};
  const fieldHashes = record.field_sha256 || {};
  modalFieldsTableBody.innerHTML = "";

  if (Object.keys(origFields).length === 0) {
    modalFieldsTableBody.innerHTML = '<tr><td colspan="3" style="color:var(--text-dim);text-align:center;">No original fields recorded.</td></tr>';
    return;
  }

  for (const [key, val] of Object.entries(origFields)) {
    const tr = document.createElement("tr");
    const sha = fieldHashes[key] || "-";
    tr.innerHTML = `
      <td style="font-family:var(--font-mono);font-weight:600;">${escapeHtml(key)}</td>
      <td>${escapeHtml(val)}</td>
      <td class="sha-text">${escapeHtml(sha)}</td>
    `;
    modalFieldsTableBody.appendChild(tr);
  }
}

// Helpers
function escapeHtml(str) {
  if (str === null || str === undefined) return "";
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

function formatBytes(bytes) {
  if (bytes === 0) return "0 B";
  const k = 1024;
  const sizes = ["B", "KiB", "MiB", "GiB", "TiB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + " " + sizes[i];
}

function debounce(func, wait) {
  let timeout;
  return function executedFunction(...args) {
    const later = () => {
      clearTimeout(timeout);
      func(...args);
    };
    clearTimeout(timeout);
    timeout = setTimeout(later, wait);
  };
}
