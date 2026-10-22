/**
 * Maintenance Atlas — Frontend Client Controller
 */

(() => {
  const API_PREFIX = "/api/maintenance/v1";

  // Application state
  let currentSessionId = null;
  let currentStateRevision = 0;
  let currentDomain = "aviation";
  let activeEventSource = null;
  let loadedEvidence = {}; // evidence_id -> snapshot
  let pinnedRecords = new Set();

  // DOM Elements
  const heroSection = document.getElementById("heroSection");
  const workspaceContainer = document.getElementById("workspaceContainer");
  const faultForm = document.getElementById("faultForm");
  const faultInput = document.getElementById("faultInput");
  const followUpForm = document.getElementById("followUpForm");
  const followUpInput = document.getElementById("followUpInput");
  const domainSelect = document.getElementById("domainSelect");
  const aircraftSelect = document.getElementById("aircraftSelect");
  const answersContainer = document.getElementById("answersContainer");
  const evidenceList = document.getElementById("evidenceList");
  const evidenceCount = document.getElementById("evidenceCount");
  const activityList = document.getElementById("activityList");
  const pinCountEl = document.getElementById("pinCount");
  const visualContainer = document.getElementById("visualContainer");
  const newSessionBtn = document.getElementById("newSessionBtn");

  // Tab switching
  const tabBtns = document.querySelectorAll(".tab-btn");
  tabBtns.forEach(btn => {
    btn.addEventListener("click", () => {
      tabBtns.forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      const tab = btn.dataset.tab;
      document.querySelectorAll(".tab-pane").forEach(p => p.style.display = "none");
      const targetPane = document.getElementById(`pane-${tab}`);
      if (targetPane) targetPane.style.display = "block";
    });
  });

  // Example chips
  document.querySelectorAll(".example-chip").forEach(chip => {
    chip.addEventListener("click", () => {
      faultInput.value = chip.dataset.query;
      faultForm.dispatchEvent(new Event("submit"));
    });
  });

  // Domain change -> creates a new session per specifications
  domainSelect.addEventListener("change", async (e) => {
    currentDomain = e.target.value;
    await initNewSession();
  });

  newSessionBtn.addEventListener("click", async () => {
    await initNewSession();
  });

  // Helper: UUID generator
  function uuidv4() {
    return "10000000-1000-4000-8000-100000000000".replace(/[018]/g, c =>
      (+c ^ crypto.getRandomValues(new Uint8Array(1))[0] & 15 >> +c / 4).toString(16)
    );
  }

  // Helper: Safe Unicode code point slicing
  function sliceCodePoints(text, start, end) {
    if (!text) return "";
    const chars = Array.from(text);
    return chars.slice(start, end).join("");
  }

  // Initialize a fresh session
  async function initNewSession() {
    try {
      if (activeEventSource) {
        activeEventSource.close();
        activeEventSource = null;
      }
      const resp = await fetch(`${API_PREFIX}/sessions`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          domain: currentDomain,
          title: "Investigation " + new Date().toLocaleTimeString(),
          aircraft_profile: aircraftSelect.value ? { model: aircraftSelect.value } : {}
        })
      });
      if (!resp.ok) throw new Error("Failed to create session");
      const snap = await resp.json();
      currentSessionId = snap.session_id;
      currentStateRevision = snap.state_revision;
      answersContainer.innerHTML = "";
      evidenceList.innerHTML = `<p style="font-size:12.5px; color:var(--muted);">Click any citation pill in an answer to inspect exact raw records with highlighted source spans.</p>`;
      evidenceCount.textContent = "0";
      activityList.innerHTML = "";
      loadedEvidence = {};
      renderBoard(snap.board || []);
    } catch (err) {
      console.error("Session init failed:", err);
    }
  }

  // Load SVG Visual Schematic
  async function loadVisualSchematic() {
    try {
      const resp = await fetch(`${API_PREFIX}/visuals/engine_concept_piston_2d`);
      if (resp.ok) {
        const svgText = await resp.text();
        visualContainer.innerHTML = svgText;

        // Wire SVG hotspots
        const hotspots = visualContainer.querySelectorAll(".hotspot");
        hotspots.forEach(hs => {
          hs.addEventListener("click", () => {
            const compId = hs.dataset.componentId;
            if (compId) {
              loadComponentContext(compId);
            }
          });
        });
      }
    } catch (err) {
      console.error("Failed to load visual SVG:", err);
    }
  }

  // Load Component Explanation
  async function loadComponentContext(compId) {
    try {
      const resp = await fetch(`${API_PREFIX}/components/${compId}/context`);
      if (!resp.ok) return;
      const data = await resp.json();
      const box = document.getElementById("componentInfoBox");
      document.getElementById("compInfoName").textContent = data.name;
      document.getElementById("compInfoText").textContent = data.explanation;
      const cite = data.citations && data.citations[0] ? `${data.citations[0].source} (${data.citations[0].section || ''})` : "";
      document.getElementById("compInfoCite").textContent = cite ? `Source: ${cite}` : "";
      box.style.display = "block";

      // Highlight corresponding SVG hotspot
      visualContainer.querySelectorAll(".hotspot").forEach(hs => hs.classList.remove("active"));
      if (data.asset_mapping_ids) {
        data.asset_mapping_ids.forEach(id => {
          const el = visualContainer.querySelector(`#${id}`);
          if (el) el.classList.add("active");
        });
      }

      // Switch to visual tab
      document.querySelector('[data-tab="visual"]').click();
    } catch (err) {
      console.error("Failed to load component context:", err);
    }
  }

  // Send message
  async function sendMessage(text) {
    if (!text.trim()) return;
    if (!currentSessionId) {
      await initNewSession();
    }

    // Show workspace
    workspaceContainer.style.display = "grid";

    // Add user query banner in stream
    const userDiv = document.createElement("div");
    userDiv.style.cssText = "font-size:14px; font-weight:700; color:var(--navy-950); margin:8px 0;";
    userDiv.textContent = `Q: ${text}`;
    answersContainer.appendChild(userDiv);

    try {
      const resp = await fetch(`${API_PREFIX}/sessions/${currentSessionId}/messages`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          text: text,
          idempotency_key: uuidv4(),
          expected_revision: currentStateRevision
        })
      });

      if (resp.status === 409) {
        alert("Session state revision conflict or live run in progress. Please refresh.");
        return;
      }
      if (!resp.ok) {
        const err = await resp.json();
        alert(`Error: ${err.message || 'Request failed'}`);
        return;
      }

      const res = await resp.json();
      subscribeToRunEvents(res.run_id);
    } catch (err) {
      console.error("Message send failed:", err);
    }
  }

  // Subscribe to SSE Run Events
  function subscribeToRunEvents(runId) {
    if (activeEventSource) {
      activeEventSource.close();
    }

    const sse = new EventSource(`${API_PREFIX}/runs/${runId}/events`);
    activeEventSource = sse;

    sse.addEventListener("message", (e) => {
      // standard message or ping
    });

    const eventTypes = [
      "run_started", "query_interpreted", "search_started", "search_completed",
      "tool_started", "tool_completed", "evidence_ready", "validation_started",
      "board_updated", "answer_validated", "run_cancelled", "run_failed", "done"
    ];

    eventTypes.forEach(type => {
      sse.addEventListener(type, (e) => {
        const event = JSON.parse(e.data);
        appendActivityItem(event);

        if (type === "answer_validated") {
          const payload = event.data;
          currentStateRevision = payload.new_state_revision;
          renderAnswerEnvelope(payload.envelope);
          // Refresh session snapshot to update board and evidence
          refreshSessionSnapshot();
        }

        if (type === "done" || type === "run_cancelled" || type === "run_failed") {
          sse.close();
          activeEventSource = null;
        }
      });
    });

    sse.onerror = () => {
      sse.close();
      activeEventSource = null;
    };
  }

  // Append Activity Event
  function appendActivityItem(ev) {
    const item = document.createElement("div");
    item.className = "activity-item";
    const summary = ev.data.summary || ev.data.tool_name || ev.data.headline || ev.type;
    item.innerHTML = `
      <span class="act-seq">#${ev.sequence}</span>
      <div>
        <div class="act-op">${ev.type.replace(/_/g, " ").toUpperCase()}</div>
        <div style="color:#718096; font-size:11px;">${escapeHtml(String(summary))}</div>
      </div>
    `;
    activityList.prepend(item);
  }

  // Refresh Session Snapshot
  async function refreshSessionSnapshot() {
    if (!currentSessionId) return;
    try {
      const resp = await fetch(`${API_PREFIX}/sessions/${currentSessionId}`);
      if (resp.ok) {
        const snap = await resp.json();
        currentStateRevision = snap.state_revision;
        renderBoard(snap.board || []);
      }
    } catch (err) {
      console.error("Failed to refresh session snapshot:", err);
    }
  }

  // Render Answer Envelope
  function renderAnswerEnvelope(ans) {
    const card = document.createElement("article");
    card.className = "answer-card";

    const isHypo = ans.mode === "HYPOTHESIS";
    const statusClass = isHypo ? "badge-hypo" : (ans.status === "supported_historical" ? "badge-supported" : "badge-insufficient");
    const statusLabel = isHypo ? "Possible Solutions — Unverified" : ans.status.replace(/_/g, " ");

    let claimsHtml = "";
    if (isHypo) {
      claimsHtml += `<div class="claim-group"><div class="claim-title">Conceptual Explanations</div>`;
      (ans.possible_explanations || []).forEach(exp => {
        claimsHtml += `<div class="claim-item hypo-item">${escapeHtml(exp)}</div>`;
      });
      claimsHtml += `</div>`;

      claimsHtml += `<div class="claim-group"><div class="claim-title">Information Needed to Distinguish</div>`;
      (ans.information_needed || []).forEach(inf => {
        claimsHtml += `<div class="claim-item">${escapeHtml(inf)}</div>`;
      });
      claimsHtml += `</div>`;
    } else {
      if (ans.claims && ans.claims.length > 0) {
        claimsHtml += `<div class="claim-group"><div class="claim-title">Grounded Historical Findings</div>`;
        ans.claims.forEach(c => {
          let pills = "";
          (c.supports || []).forEach(s => {
            if (s.kind === "log_span") {
              loadedEvidence[s.evidence_id] = s;
              pills += `<button class="citation-pill" data-evidence-id="${s.evidence_id}" title="Inspect raw source text">cite:${s.record_id} [${s.field}]</button>`;
            }
          });
          claimsHtml += `<div class="claim-item">${escapeHtml(c.text)} ${pills}</div>`;
        });
        claimsHtml += `</div>`;
      }
    }

    let limitsHtml = "";
    if (ans.limitations && ans.limitations.length > 0) {
      limitsHtml += `<div class="limits-box"><strong>Applicability &amp; Safety Limits:</strong><ul>`;
      ans.limitations.forEach(lim => {
        limitsHtml += `<li>${escapeHtml(lim)}</li>`;
      });
      limitsHtml += `</ul></div>`;
    }

    // Action buttons
    let actButtonsHtml = `<div class="action-buttons-row">`;
    (ans.allowed_actions || []).forEach(act => {
      if (act.action === "hypothesis") {
        actButtonsHtml += `<button class="act-btn hypo-btn" data-act="hypothesis" data-parent="${ans.answer_id}">⚡ Possible solutions — unverified</button>`;
      } else if (act.action === "distinguish") {
        actButtonsHtml += `<button class="act-btn" data-act="distinguish" data-parent="${ans.answer_id}">⇄ Distinguish cases</button>`;
      } else if (act.action === "challenge") {
        actButtonsHtml += `<button class="act-btn" data-act="challenge" data-parent="${ans.answer_id}">⚔ Challenge answer</button>`;
      } else if (act.action === "sensitivity") {
        actButtonsHtml += `<button class="act-btn" data-act="sensitivity" data-parent="${ans.answer_id}">𝚫 Search sensitivity</button>`;
      } else if (act.action === "handover") {
        actButtonsHtml += `<button class="act-btn" data-act="handover">📋 Export handover</button>`;
      }
    });

    if (ans.visual_refs && ans.visual_refs.length > 0) {
      ans.visual_refs.forEach(vRef => {
        actButtonsHtml += `<button class="act-btn" data-comp="${vRef}">🔍 Explain ${vRef.replace(/_/g, ' ')}</button>`;
      });
    }
    actButtonsHtml += `</div>`;

    card.innerHTML = `
      <div class="answer-head">
        <span class="answer-badge ${statusClass}">${statusLabel}</span>
        <span style="font-family:var(--mono); font-size:11px; color:var(--muted);">${new Date().toLocaleTimeString()}</span>
      </div>
      <div class="answer-headline">${escapeHtml(ans.headline || '')}</div>
      ${claimsHtml}
      ${limitsHtml}
      ${actButtonsHtml}
    `;

    answersContainer.appendChild(card);
    card.scrollIntoView({ behavior: "smooth" });

    // Wire citation pills
    card.querySelectorAll(".citation-pill").forEach(pill => {
      pill.addEventListener("click", () => {
        const evId = pill.dataset.evidenceId;
        showEvidenceDetail(evId);
      });
    });

    // Wire action buttons
    card.querySelectorAll(".act-btn").forEach(btn => {
      btn.addEventListener("click", () => {
        const act = btn.dataset.act;
        const parentId = btn.dataset.parent;
        const compId = btn.dataset.comp;
        if (compId) {
          loadComponentContext(compId);
        } else if (act) {
          triggerAction(act, parentId);
        }
      });
    });
  }

  // Show Evidence in right drawer
  async function showEvidenceDetail(evidenceId) {
    const spanInfo = loadedEvidence[evidenceId];
    if (!spanInfo) return;

    // Switch to evidence tab
    document.querySelector('[data-tab="evidence"]').click();

    // Fetch original raw record
    const domain = currentDomain;
    const sourceId = spanInfo.record_id.includes(":") ? spanInfo.record_id.split(":")[1] : spanInfo.record_id;

    try {
      const resp = await fetch(`${API_PREFIX}/records/${domain}/${sourceId}`);
      if (!resp.ok) return;
      const rec = await resp.json();

      const rawField = rec[spanInfo.field.toLowerCase() + "_raw"] || rec.problem_raw;
      const safeQuote = escapeHtml(spanInfo.quote);

      // Highlight code-point slice
      const start = spanInfo.start;
      const end = spanInfo.end;
      const before = escapeHtml(sliceCodePoints(rawField, 0, start));
      const highlighted = `<mark class="evidence-highlight">${escapeHtml(sliceCodePoints(rawField, start, end))}</mark>`;
      const after = escapeHtml(sliceCodePoints(rawField, end, rawField.length));

      const card = document.createElement("div");
      card.className = "evidence-card";
      card.innerHTML = `
        <div class="evidence-card-head">
          <span class="rec-id-tag">Record: ${rec.record_id}</span>
          <span class="field-tag">${spanInfo.field}</span>
        </div>
        <div style="font-size:11px; font-family:var(--mono); color:var(--muted); margin-bottom:6px;">
          Offsets: [${start}:${end}] · SHA256: ${spanInfo.source_sha256 ? spanInfo.source_sha256.substring(0, 16) + '...' : ''}
        </div>
        <div class="raw-text-view">${before}${highlighted}${after}</div>
        <div style="margin-top:8px; display:flex; justify-content:space-between; align-items:center;">
          <button class="act-btn" id="pinBtn-${rec.record_id}" style="padding:3px 10px; font-size:11px;">
            ${pinnedRecords.has(rec.record_id) ? '★ Pinned' : '☆ Pin Record'}
          </button>
        </div>
      `;

      evidenceList.innerHTML = "";
      evidenceList.appendChild(card);
      evidenceCount.textContent = "1";

      document.getElementById(`pinBtn-${rec.record_id}`).addEventListener("click", () => {
        togglePinRecord(rec.record_id, sourceId);
      });
    } catch (err) {
      console.error("Failed to load record:", err);
    }
  }

  // Pin/Unpin Record
  async function togglePinRecord(recordId, sourceId) {
    const isPinned = pinnedRecords.has(recordId);
    const method = isPinned ? "DELETE" : "PUT";
    try {
      const resp = await fetch(`${API_PREFIX}/sessions/${currentSessionId}/pins/${currentDomain}/${sourceId}`, {
        method: method,
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ expected_revision: currentStateRevision })
      });
      if (resp.ok) {
        if (isPinned) pinnedRecords.delete(recordId);
        else pinnedRecords.add(recordId);
        pinCountEl.textContent = String(pinnedRecords.size);
        const btn = document.getElementById(`pinBtn-${recordId}`);
        if (btn) btn.textContent = isPinned ? '☆ Pin Record' : '★ Pinned';
      }
    } catch (err) {
      console.error("Pin failed:", err);
    }
  }

  // Trigger Action
  async function triggerAction(actionName, parentAnswerId) {
    if (!currentSessionId) return;

    if (actionName === "handover") {
      try {
        const resp = await fetch(`${API_PREFIX}/sessions/${currentSessionId}/handover`);
        if (resp.ok) {
          const md = await resp.text();
          document.getElementById("handoverContent").textContent = md;
          document.getElementById("handoverDialog").showModal();
        }
      } catch (err) {
        console.error("Handover error:", err);
      }
      return;
    }

    try {
      const resp = await fetch(`${API_PREFIX}/sessions/${currentSessionId}/actions`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          action: actionName,
          parent_answer_id: parentAnswerId,
          expected_revision: currentStateRevision,
          idempotency_key: uuidv4()
        })
      });

      if (!resp.ok) {
        const err = await resp.json();
        alert(`Action failed: ${err.message || 'Request error'}`);
        return;
      }

      const res = await resp.json();
      currentStateRevision = res.state_revision || currentStateRevision;
      if (res.envelope) {
        renderAnswerEnvelope(res.envelope);
      } else if (res.comparison) {
        alert("Case Comparison:\n" + JSON.stringify(res.comparison, null, 2));
      } else if (res.result) {
        alert("Sensitivity Result:\n" + JSON.stringify(res.result, null, 2));
      }
      refreshSessionSnapshot();
    } catch (err) {
      console.error("Action error:", err);
    }
  }

  // Render Board
  function renderBoard(items) {
    const knownList = document.getElementById("boardKnownList");
    const repList = document.getElementById("boardReportedList");
    const missList = document.getElementById("boardMissingList");

    knownList.innerHTML = "";
    repList.innerHTML = "";
    missList.innerHTML = "";

    let kc = 0, rc = 0, mc = 0;
    (items || []).forEach(it => {
      const div = document.createElement("div");
      div.className = "board-item-card";
      div.innerHTML = `
        <div>${escapeHtml(it.text)}</div>
        <div class="board-origin-tag">${it.origin} · ${it.verification_status}</div>
      `;

      if (it.column === "known") { knownList.appendChild(div); kc++; }
      else if (it.column === "reported") { repList.appendChild(div); rc++; }
      else if (it.column === "missing") { missList.appendChild(div); mc++; }
    });

    document.getElementById("boardKnownCount").textContent = String(kc);
    document.getElementById("boardReportedCount").textContent = String(rc);
    document.getElementById("boardMissingCount").textContent = String(mc);
  }

  // Handover Dialog controls
  document.getElementById("closeHandoverBtn").addEventListener("click", () => {
    document.getElementById("handoverDialog").close();
  });
  document.getElementById("copyHandoverBtn").addEventListener("click", () => {
    const text = document.getElementById("handoverContent").textContent;
    navigator.clipboard.writeText(text);
    alert("Copied markdown handover to clipboard.");
  });
  document.getElementById("downloadHandoverBtn").addEventListener("click", () => {
    const text = document.getElementById("handoverContent").textContent;
    const blob = new Blob([text], { type: "text/markdown" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `maintenance_handover_${new Date().toISOString().slice(0,10)}.md`;
    a.click();
    URL.revokeObjectURL(url);
  });

  // Form Submissions
  faultForm.addEventListener("submit", (e) => {
    e.preventDefault();
    const q = faultInput.value;
    faultInput.value = "";
    sendMessage(q);
  });

  followUpForm.addEventListener("submit", (e) => {
    e.preventDefault();
    const q = followUpInput.value;
    followUpInput.value = "";
    sendMessage(q);
  });

  function escapeHtml(str) {
    if (!str) return "";
    return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
  }

  // Initial load
  initNewSession();
  loadVisualSchematic();
})();
