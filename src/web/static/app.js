const state = {
  currentRunId: null,
  pollTimer: null,
  groupDetailCache: new Map(),
};

const elements = {
  form: document.querySelector("#check-form"),
  groupSelect: document.querySelector("#group-select"),
  groupViewButton: document.querySelector("#group-view-button"),
  contestInput: document.querySelector("#contest-input"),
  refreshCache: document.querySelector("#refresh-cache"),
  submitButton: document.querySelector("#submit-button"),
  runStatus: document.querySelector("#run-status"),
  eventFeed: document.querySelector("#event-feed"),
  contestResults: document.querySelector("#contest-results"),
  formError: document.querySelector("#form-error"),
  groupErrors: document.querySelector("#group-errors"),
  groupModal: document.querySelector("#group-modal"),
  groupModalBackdrop: document.querySelector("#group-modal-backdrop"),
  groupModalClose: document.querySelector("#group-modal-close"),
  groupModalTitle: document.querySelector("#group-modal-title"),
  groupModalContent: document.querySelector("#group-modal-content"),
};

function setStatusPill(status, label) {
  elements.runStatus.className = `status-pill ${status}`;
  elements.runStatus.textContent = label;
}

function escapeHtml(text) {
  return text
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function renderFormError(message) {
  if (!message) {
    elements.formError.hidden = true;
    elements.formError.textContent = "";
    return;
  }

  elements.formError.hidden = false;
  elements.formError.textContent = message;
}

function renderGroupErrors(errors) {
  if (!errors.length) {
    elements.groupErrors.hidden = true;
    elements.groupErrors.innerHTML = "";
    return;
  }

  elements.groupErrors.hidden = false;
  elements.groupErrors.innerHTML = errors
    .map((message) => `<div class="notice warning">${escapeHtml(message)}</div>`)
    .join("");
}

function updateGroupViewButtonState() {
  elements.groupViewButton.disabled = !elements.groupSelect.value;
}

function populateGroups(groups) {
  elements.groupSelect.innerHTML = groups
    .map((group) => {
      const counts = group.counts || {};
      const label = `${group.name}  A:${counts.atcoder ?? 0}  C:${counts.cf ?? 0}`;
      return `<option value="${escapeHtml(group.name)}">${escapeHtml(label)}</option>`;
    })
    .join("");
  updateGroupViewButtonState();
}

function parseContestTokens(raw) {
  return raw
    .split(/\s+/)
    .map((token) => token.trim())
    .filter(Boolean);
}

function getSelectedOj() {
  return new FormData(elements.form).get("oj");
}

function setSubmitting(isSubmitting) {
  elements.submitButton.disabled = isSubmitting;
  elements.submitButton.textContent = isSubmitting ? "Checking..." : "Start Check";
}

function renderEventFeed(events) {
  const visibleEvents = events.slice(-3).reverse();
  if (!visibleEvents.length) {
    elements.eventFeed.innerHTML =
      '<li data-kind="idle"><span class="log-meta">Idle</span><strong>No recent activity.</strong></li>';
    return;
  }

  elements.eventFeed.innerHTML = visibleEvents
    .map((event) => {
      const metaParts = [event.kind.replaceAll("_", " ")];
      if (event.user_id) {
        metaParts.push(event.user_id);
      }
      if (event.contest_id) {
        metaParts.push(event.contest_id);
      }
      return `
        <li data-kind="${escapeHtml(event.kind)}">
          <span class="log-meta">${escapeHtml(metaParts.join(" / "))}</span>
          <strong>${escapeHtml(event.message)}</strong>
        </li>
      `;
    })
    .join("");
}

function renderContestResults(contestSummaries) {
  if (!contestSummaries.length) {
    elements.contestResults.className = "result-list empty-state";
    elements.contestResults.textContent = "Expanded contest results will show up here.";
    return;
  }

  elements.contestResults.className = "result-list";
  elements.contestResults.innerHTML = contestSummaries
    .map((summary) => {
      const hasMatches = summary.matched_users.length > 0;
      const warnings = summary.warnings ?? [];
      const badgeClass = hasMatches ? "hit" : "miss";
      const badgeLabel = hasMatches ? `${summary.matched_users.length} hit` : "No hits";
      const detailMarkup = hasMatches
        ? `<div class="user-list">${summary.matched_users
            .map((user) => `<span class="user-chip">${escapeHtml(user)}</span>`)
            .join("")}</div>`
        : `<p>${escapeHtml(`no users have done ${summary.contest_id}`)}</p>`;
      const warningMarkup = warnings.length
        ? `
          <section class="warning-section">
            <p class="warning-heading">Possible same-round matches</p>
            <div class="warning-list">
              ${warnings
                .map(
                  (warning) => `
                    <article class="warning-item">
                      <strong>${escapeHtml(warning.user_id)}</strong>
                      <p>via ${escapeHtml(warning.warning_contests.join(", "))}</p>
                    </article>
                  `
                )
                .join("")}
            </div>
          </section>
        `
        : "";

      return `
        <article class="result-card">
          <header>
            <strong>${escapeHtml(summary.contest_id)}</strong>
            <span class="badge ${badgeClass}">${escapeHtml(badgeLabel)}</span>
          </header>
          ${detailMarkup}
          ${warningMarkup}
        </article>
      `;
    })
    .join("");
}

function renderSnapshot(snapshot) {
  const events = snapshot.events ?? snapshot.result?.events ?? [];
  const contestSummaries = snapshot.result?.contest_summaries ?? [];

  state.currentRunId = snapshot.run_id;
  renderEventFeed(events);
  renderContestResults(contestSummaries);

  if (snapshot.status === "running") {
    setStatusPill("running", "Running");
  } else if (snapshot.status === "completed") {
    setStatusPill("completed", "Completed");
  } else if (snapshot.status === "failed") {
    setStatusPill("failed", "Failed");
    renderFormError(snapshot.error?.message || "Run failed");
  } else {
    setStatusPill("idle", "Idle");
  }
}

function renderGroupModal(group) {
  const ojOrder = ["atcoder", "cf"];
  elements.groupModalTitle.textContent = group.name;
  elements.groupModalContent.innerHTML = ojOrder
    .map((oj) => {
      const users = group.users?.[oj] ?? [];
      const title = oj === "atcoder" ? "AtCoder" : "Codeforces";
      const userMarkup = users.length
        ? `<div class="user-list">${users
            .map((user) => `<span class="user-chip">${escapeHtml(user)}</span>`)
            .join("")}</div>`
        : "<p>No users configured.</p>";
      return `
        <section class="modal-group">
          <header>
            <h3>${escapeHtml(title)}</h3>
            <span class="modal-count">${escapeHtml(String(users.length))} users</span>
          </header>
          ${userMarkup}
        </section>
      `;
    })
    .join("");
}

function openGroupModal() {
  elements.groupModal.hidden = false;
  document.body.style.overflow = "hidden";
}

function closeGroupModal() {
  elements.groupModal.hidden = true;
  document.body.style.overflow = "";
}

async function fetchJson(url, options = {}) {
  const response = await fetch(url, options);
  const payload = await response.json();
  if (!response.ok) {
    const message = payload.error?.message || `Request failed with ${response.status}`;
    const error = new Error(message);
    error.payload = payload;
    error.status = response.status;
    throw error;
  }
  return payload;
}

async function pollRun() {
  if (!state.currentRunId) {
    return;
  }

  try {
    const snapshot = await fetchJson(`/api/runs/${state.currentRunId}`);
    renderSnapshot(snapshot);
    if (snapshot.status === "running") {
      state.pollTimer = window.setTimeout(pollRun, 800);
      return;
    }
    setSubmitting(false);
  } catch (error) {
    setSubmitting(false);
    renderFormError(error.message);
    setStatusPill("failed", "Failed");
  }
}

async function handleSubmit(event) {
  event.preventDefault();
  window.clearTimeout(state.pollTimer);
  renderFormError("");

  const contestTokens = parseContestTokens(elements.contestInput.value);
  if (!contestTokens.length) {
    renderFormError("Enter at least one contest token before starting a check.");
    return;
  }

  setSubmitting(true);
  setStatusPill("running", "Starting");
  renderEventFeed([]);
  renderContestResults([]);

  try {
    const payload = await fetchJson("/api/check", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        oj: getSelectedOj(),
        group: elements.groupSelect.value,
        contest_tokens: contestTokens,
        refresh_cache: elements.refreshCache.checked,
      }),
    });

    state.currentRunId = payload.run_id;
    pollRun();
  } catch (error) {
    if (error.status === 409 && error.payload?.error?.run_id) {
      state.currentRunId = error.payload.error.run_id;
      renderFormError("A check is already running. Following the active run.");
      pollRun();
      return;
    }
    setSubmitting(false);
    setStatusPill("failed", "Failed");
    renderFormError(error.message);
  }
}

async function handleGroupView() {
  const groupName = elements.groupSelect.value;
  if (!groupName) {
    return;
  }

  renderFormError("");

  try {
    let group = state.groupDetailCache.get(groupName);
    if (!group) {
      const payload = await fetchJson(`/api/groups/${encodeURIComponent(groupName)}`);
      group = payload.group;
      state.groupDetailCache.set(groupName, group);
    }
    renderGroupModal(group);
    openGroupModal();
  } catch (error) {
    renderFormError(error.message);
  }
}

async function bootstrap() {
  elements.form.addEventListener("submit", handleSubmit);
  elements.groupViewButton.addEventListener("click", handleGroupView);
  elements.groupSelect.addEventListener("change", updateGroupViewButtonState);
  elements.groupModalClose.addEventListener("click", closeGroupModal);
  elements.groupModalBackdrop.addEventListener("click", closeGroupModal);
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && !elements.groupModal.hidden) {
      closeGroupModal();
    }
  });

  setStatusPill("idle", "Idle");
  renderEventFeed([]);
  renderContestResults([]);

  try {
    const groupsPayload = await fetchJson("/api/groups");
    populateGroups(groupsPayload.groups);
    renderGroupErrors(groupsPayload.errors);

    if (!groupsPayload.groups.length) {
      elements.submitButton.disabled = true;
      renderFormError("No valid group files were found in usergroup/.");
    }
  } catch (error) {
    setStatusPill("failed", "Failed");
    renderFormError(error.message);
  }
}

bootstrap();
