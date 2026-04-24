const GROUP_STORAGE_KEY = "oj-problem-tracker.local-groups.v1";
const SELECTED_GROUP_STORAGE_KEY = "oj-problem-tracker.selected-group.v1";

const state = {
  currentRunId: null,
  pollTimer: null,
  isSubmitting: false,
  isContestTypeExpanded: false,
  groups: [],
  selectedGroupName: null,
  storageError: null,
  modalMode: null,
  viewGroupName: null,
  draftGroup: null,
  draftOriginalName: null,
  draftUserInputs: {
    atcoder: "",
    cf: "",
  },
};

const elements = {
  form: document.querySelector("#check-form"),
  groupSelect: document.querySelector("#group-select"),
  groupViewButton: document.querySelector("#group-view-button"),
  groupEditButton: document.querySelector("#group-edit-button"),
  groupNewButton: document.querySelector("#group-new-button"),
  groupImportButton: document.querySelector("#group-import-button"),
  groupDeleteButton: document.querySelector("#group-delete-button"),
  groupImportInput: document.querySelector("#group-import-input"),
  ojInputs: document.querySelectorAll('input[name="oj"]'),
  contestInput: document.querySelector("#contest-input"),
  contestTypeFieldset: document.querySelector("#cf-contest-type-fieldset"),
  contestTypeToggle: document.querySelector("#contest-type-toggle"),
  contestTypeToggleLabel: document.querySelector("#contest-type-toggle-label"),
  contestTypePanel: document.querySelector("#contest-type-panel"),
  contestTypeInputs: document.querySelectorAll('input[name="contest_types"]'),
  contestTypeSelectAll: document.querySelector("#contest-type-select-all"),
  contestTypeClearAll: document.querySelector("#contest-type-clear-all"),
  refreshCache: document.querySelector("#refresh-cache"),
  submitButton: document.querySelector("#submit-button"),
  runStatus: document.querySelector("#run-status"),
  eventFeed: document.querySelector("#event-feed"),
  contestResults: document.querySelector("#contest-results"),
  groupNotice: document.querySelector("#group-notice"),
  formError: document.querySelector("#form-error"),
  groupModal: document.querySelector("#group-modal"),
  groupModalBackdrop: document.querySelector("#group-modal-backdrop"),
  groupModalClose: document.querySelector("#group-modal-close"),
  groupModalKicker: document.querySelector("#group-modal-kicker"),
  groupModalTitle: document.querySelector("#group-modal-title"),
  groupModalContent: document.querySelector("#group-modal-content"),
  groupModalActions: document.querySelector("#group-modal-actions"),
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

function renderNotice(element, message, level = "warning") {
  if (!message) {
    element.hidden = true;
    element.textContent = "";
    element.className = "notice";
    return;
  }

  element.hidden = false;
  element.className = `notice ${level}`;
  element.textContent = message;
}

function renderFormError(message) {
  renderNotice(elements.formError, message, "error");
}

function renderGroupNotice(message, level = "warning") {
  renderNotice(elements.groupNotice, message, level);
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

function getSelectedContestTypes() {
  return Array.from(elements.contestTypeInputs)
    .filter((input) => input.checked)
    .map((input) => input.value);
}

function setSelectedContestTypes(contestTypes) {
  const selectedTypes = new Set(contestTypes);
  elements.contestTypeInputs.forEach((input) => {
    input.checked = selectedTypes.has(input.value);
  });
}

function getContestTypeToggleLabel() {
  const selectedCount = getSelectedContestTypes().length;
  return `Choose contest type (${selectedCount} selected)`;
}

function updateContestTypeFieldsetState() {
  const isCf = getSelectedOj() === "cf";
  const isExpanded = isCf && state.isContestTypeExpanded;
  elements.contestTypeFieldset.hidden = !isCf;
  elements.contestTypeFieldset.classList.toggle("expanded", isExpanded);
  elements.contestTypeToggle.disabled = !isCf;
  elements.contestTypeToggleLabel.textContent = getContestTypeToggleLabel();
  elements.contestTypeToggle.setAttribute("aria-expanded", String(isExpanded));
  elements.contestTypePanel.hidden = !isExpanded;
  elements.contestTypeInputs.forEach((input) => {
    input.disabled = !isCf;
  });
  elements.contestTypeSelectAll.disabled = !isCf;
  elements.contestTypeClearAll.disabled = !isCf;
}

function cloneGroupUsers(users) {
  return {
    atcoder: [...(users.atcoder ?? [])],
    cf: [...(users.cf ?? [])],
  };
}

function cloneGroup(group) {
  return {
    name: group.name,
    users: cloneGroupUsers(group.users),
  };
}

function normalizeUserList(users, sourceLabel) {
  if (!Array.isArray(users)) {
    throw new Error(`${sourceLabel} must be a list of users.`);
  }

  const normalizedUsers = [];
  const seenUsers = new Set();
  for (const user of users) {
    if (typeof user !== "string" || !user.trim()) {
      throw new Error(`${sourceLabel} must contain only non-empty strings.`);
    }
    const normalizedUser = user.trim();
    if (seenUsers.has(normalizedUser)) {
      continue;
    }
    seenUsers.add(normalizedUser);
    normalizedUsers.push(normalizedUser);
  }

  return normalizedUsers;
}

function normalizeGroupUsersPayload(payload, sourceLabel = "Group JSON") {
  if (!payload || typeof payload !== "object" || Array.isArray(payload)) {
    throw new Error(`${sourceLabel} must be an object with atcoder and cf lists.`);
  }

  return {
    atcoder: normalizeUserList(payload.atcoder, `${sourceLabel}.atcoder`),
    cf: normalizeUserList(payload.cf, `${sourceLabel}.cf`),
  };
}

function normalizeStoredGroup(record, index) {
  if (!record || typeof record !== "object" || Array.isArray(record)) {
    throw new Error(`Stored group #${index + 1} must be an object.`);
  }
  if (typeof record.name !== "string" || !record.name.trim()) {
    throw new Error(`Stored group #${index + 1} must have a non-empty name.`);
  }

  return {
    name: record.name.trim(),
    users: normalizeGroupUsersPayload(record.users, `Stored group "${record.name.trim()}"`),
  };
}

function readSelectedGroupName() {
  try {
    const selectedGroupName = localStorage.getItem(SELECTED_GROUP_STORAGE_KEY);
    return selectedGroupName && selectedGroupName.trim() ? selectedGroupName.trim() : null;
  } catch (error) {
    state.storageError = `Could not access browser storage: ${error.message}`;
    return null;
  }
}

function loadStoredGroups() {
  try {
    const rawValue = localStorage.getItem(GROUP_STORAGE_KEY);
    if (!rawValue) {
      state.storageError = null;
      return [];
    }

    const parsedValue = JSON.parse(rawValue);
    if (!Array.isArray(parsedValue)) {
      throw new Error("root must be an array of groups");
    }

    const groups = parsedValue.map(normalizeStoredGroup);
    const seenGroupNames = new Set();
    for (const group of groups) {
      if (seenGroupNames.has(group.name)) {
        throw new Error(`duplicate group name "${group.name}" in browser storage`);
      }
      seenGroupNames.add(group.name);
    }

    state.storageError = null;
    return groups;
  } catch (error) {
    state.storageError = `Stored groups could not be loaded: ${error.message}`;
    return [];
  }
}

function persistSelectedGroupName() {
  try {
    if (state.selectedGroupName) {
      localStorage.setItem(SELECTED_GROUP_STORAGE_KEY, state.selectedGroupName);
      return;
    }
    localStorage.removeItem(SELECTED_GROUP_STORAGE_KEY);
  } catch (error) {
    throw new Error(`Could not save the selected group in this browser: ${error.message}`);
  }
}

function persistGroups() {
  try {
    localStorage.setItem(GROUP_STORAGE_KEY, JSON.stringify(state.groups));
    state.storageError = null;
  } catch (error) {
    throw new Error(`Could not save groups in this browser: ${error.message}`);
  }
  persistSelectedGroupName();
}

function syncSelectedGroup(preferredName = null) {
  const groupNames = new Set(state.groups.map((group) => group.name));
  if (preferredName && groupNames.has(preferredName)) {
    state.selectedGroupName = preferredName;
    return;
  }
  if (state.selectedGroupName && groupNames.has(state.selectedGroupName)) {
    return;
  }
  if (!state.groups.length) {
    state.selectedGroupName = null;
    return;
  }
  state.selectedGroupName = state.groups[0].name;
}

function getSelectedGroup() {
  return state.groups.find((group) => group.name === state.selectedGroupName) ?? null;
}

function updateGroupActionState() {
  const hasSelectedGroup = Boolean(getSelectedGroup());
  elements.groupViewButton.disabled = !hasSelectedGroup;
  elements.groupEditButton.disabled = !hasSelectedGroup;
  elements.groupDeleteButton.disabled = !hasSelectedGroup;
}

function updateSubmitButtonState() {
  elements.submitButton.disabled = state.isSubmitting || !getSelectedGroup();
  elements.submitButton.textContent = state.isSubmitting ? "Checking..." : "Start Check";
}

function renderGroups() {
  if (!state.groups.length) {
    elements.groupSelect.disabled = true;
    elements.groupSelect.innerHTML = '<option value="">No local groups yet</option>';
    updateGroupActionState();
    updateSubmitButtonState();
    return;
  }

  elements.groupSelect.disabled = false;
  elements.groupSelect.innerHTML = state.groups
    .map((group) => {
      const label = `${group.name}  A:${group.users.atcoder.length}  C:${group.users.cf.length}`;
      return `<option value="${escapeHtml(group.name)}">${escapeHtml(label)}</option>`;
    })
    .join("");
  elements.groupSelect.value = state.selectedGroupName;
  updateGroupActionState();
  updateSubmitButtonState();
}

function refreshGroupUi() {
  renderGroups();
  if (state.storageError) {
    renderGroupNotice(state.storageError, "error");
    return;
  }
  if (!state.groups.length) {
    renderGroupNotice(
      "Create or import a local group. It will stay in this browser and never be written to the server disk.",
      "warning"
    );
    return;
  }
  renderGroupNotice("");
}

function setSubmitting(isSubmitting) {
  state.isSubmitting = isSubmitting;
  updateSubmitButtonState();
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
      const matchedUsers = summary.matched_users ?? [];
      const warnings = summary.warnings ?? [];
      if (summary.status === "skipped") {
        const contestTypeLabel = summary.contest_type ? `Type: ${summary.contest_type}` : "Type: unknown";
        return `
          <article class="result-card skipped">
            <header>
              <strong>${escapeHtml(summary.contest_id)}</strong>
              <span class="badge skipped">Skipped</span>
            </header>
            <section class="skip-section">
              <p class="skip-meta">${escapeHtml(contestTypeLabel)}</p>
              <p>${escapeHtml(summary.skip_reason ?? "contest was skipped")}</p>
            </section>
          </article>
        `;
      }

      const hasMatches = matchedUsers.length > 0;
      const badgeClass = hasMatches ? "hit" : "miss";
      const badgeLabel = hasMatches ? `${matchedUsers.length} hit` : "No hits";
      const detailMarkup = hasMatches
        ? `<div class="user-list">${matchedUsers
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

function renderGroupViewSection(oj, users) {
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
}

function renderGroupEditorSection(oj, users) {
  const title = oj === "atcoder" ? "AtCoder" : "Codeforces";
  const inputValue = state.draftUserInputs[oj] ?? "";
  const userMarkup = users.length
    ? `<div class="user-list editable-user-list">${users
        .map(
          (user, index) => `
            <span class="user-chip removable-chip">
              <span>${escapeHtml(user)}</span>
              <button
                class="chip-remove"
                type="button"
                aria-label="Remove user"
                title="Remove user"
                data-action="remove-user"
                data-oj="${escapeHtml(oj)}"
                data-index="${index}"
              >
                x
              </button>
            </span>
          `
        )
        .join("")}</div>`
    : '<p class="editor-empty">No users configured.</p>';
  return `
    <section class="modal-group">
      <header>
        <h3>${escapeHtml(title)}</h3>
        <span class="modal-count">${escapeHtml(String(users.length))} users</span>
      </header>
      <div class="editor-user-entry">
        <input
          class="editor-user-input"
          type="text"
          data-oj="${escapeHtml(oj)}"
          value="${escapeHtml(inputValue)}"
          placeholder="Add ${escapeHtml(title)} user"
        />
        <button class="secondary-button" type="button" data-action="add-user" data-oj="${escapeHtml(oj)}">
          Add
        </button>
      </div>
      ${userMarkup}
    </section>
  `;
}

function renderGroupModal() {
  elements.groupModalContent.classList.toggle("editor-mode", state.modalMode === "edit");
  if (state.modalMode === "edit" && state.draftGroup) {
    elements.groupModalKicker.textContent = state.draftOriginalName ? "Edit Local Group" : "New Local Group";
    elements.groupModalTitle.textContent = state.draftGroup.name.trim() || "Untitled Group";
    elements.groupModalContent.innerHTML = `
      <div class="editor-shell">
        <label class="field-block">
          <span class="field-label">Group Name</span>
          <input
            id="group-name-input"
            class="editor-name-input"
            type="text"
            value="${escapeHtml(state.draftGroup.name)}"
            placeholder="Team Spring 2026"
          />
        </label>
        <div class="editor-grid">
          ${renderGroupEditorSection("atcoder", state.draftGroup.users.atcoder)}
          ${renderGroupEditorSection("cf", state.draftGroup.users.cf)}
        </div>
      </div>
    `;
    elements.groupModalActions.innerHTML =
      '<button id="group-save-button" class="submit-button" type="button">Save Group</button>';
    return;
  }

  const group = state.groups.find((item) => item.name === state.viewGroupName);
  if (!group) {
    closeGroupModal();
    return;
  }

  elements.groupModalKicker.textContent = "Local Group";
  elements.groupModalTitle.textContent = group.name;
  elements.groupModalContent.innerHTML = `
    ${renderGroupViewSection("atcoder", group.users.atcoder)}
    ${renderGroupViewSection("cf", group.users.cf)}
  `;
  elements.groupModalActions.innerHTML =
    '<button id="group-modal-edit" class="secondary-button" type="button">Edit</button>';
}

function openGroupModal() {
  elements.groupModal.hidden = false;
  document.body.style.overflow = "hidden";
}

function closeGroupModal() {
  elements.groupModal.hidden = true;
  elements.groupModalContent.innerHTML = "";
  elements.groupModalActions.innerHTML = "";
  elements.groupModalContent.classList.remove("editor-mode");
  document.body.style.overflow = "";
  state.modalMode = null;
  state.viewGroupName = null;
  state.draftGroup = null;
  state.draftOriginalName = null;
  state.draftUserInputs = {
    atcoder: "",
    cf: "",
  };
}

function openGroupViewModal(group) {
  state.modalMode = "view";
  state.viewGroupName = group.name;
  renderGroupModal();
  openGroupModal();
}

function openGroupEditor(group, originalName = null) {
  state.modalMode = "edit";
  state.viewGroupName = null;
  state.draftGroup = cloneGroup(group);
  state.draftOriginalName = originalName;
  state.draftUserInputs = {
    atcoder: "",
    cf: "",
  };
  renderGroupModal();
  openGroupModal();
}

function addDraftUser(oj) {
  const rawUser = state.draftUserInputs[oj] ?? "";
  const normalizedUser = rawUser.trim();
  if (!normalizedUser) {
    renderFormError("Enter a user before adding it to the group.");
    return;
  }
  if (state.draftGroup.users[oj].includes(normalizedUser)) {
    renderFormError(`${normalizedUser} is already in this group.`);
    return;
  }

  state.draftGroup.users[oj].push(normalizedUser);
  state.draftUserInputs[oj] = "";
  renderFormError("");
  renderGroupModal();
}

function removeDraftUser(oj, index) {
  state.draftGroup.users[oj].splice(index, 1);
  renderFormError("");
  renderGroupModal();
}

function saveDraftGroup() {
  try {
    const nextGroupName = state.draftGroup.name.trim();
    if (!nextGroupName) {
      throw new Error("Group name is required before saving.");
    }

    const nextGroup = {
      name: nextGroupName,
      users: normalizeGroupUsersPayload(state.draftGroup.users, `Group "${nextGroupName}"`),
    };

    const conflictingGroup = state.groups.find(
      (group) => group.name === nextGroupName && group.name !== state.draftOriginalName
    );
    if (conflictingGroup) {
      throw new Error(`A group named "${nextGroupName}" already exists in this browser.`);
    }

    const existingIndex = state.groups.findIndex((group) => group.name === state.draftOriginalName);
    const nextGroups = [...state.groups];
    if (existingIndex >= 0) {
      nextGroups[existingIndex] = nextGroup;
    } else {
      nextGroups.push(nextGroup);
    }

    state.groups = nextGroups.sort((left, right) => left.name.localeCompare(right.name));
    syncSelectedGroup(nextGroup.name);
    persistGroups();
    refreshGroupUi();
    renderFormError("");
    closeGroupModal();
  } catch (error) {
    renderFormError(error.message);
  }
}

function handleGroupSelectionChange() {
  state.selectedGroupName = elements.groupSelect.value || null;
  try {
    persistSelectedGroupName();
  } catch (error) {
    renderFormError(error.message);
  }
  updateGroupActionState();
  updateSubmitButtonState();
}

function handleGroupView() {
  const group = getSelectedGroup();
  if (!group) {
    return;
  }
  renderFormError("");
  openGroupViewModal(group);
}

function handleGroupEdit() {
  const group = getSelectedGroup();
  if (!group) {
    return;
  }
  renderFormError("");
  openGroupEditor(group, group.name);
}

function handleGroupNew() {
  renderFormError("");
  openGroupEditor(
    {
      name: "",
      users: {
        atcoder: [],
        cf: [],
      },
    },
    null
  );
}

function handleGroupDelete() {
  const group = getSelectedGroup();
  if (!group) {
    return;
  }
  if (!window.confirm(`Delete local group "${group.name}" from this browser?`)) {
    return;
  }

  try {
    state.groups = state.groups.filter((item) => item.name !== group.name);
    syncSelectedGroup();
    persistGroups();
    refreshGroupUi();
    renderFormError("");
  } catch (error) {
    renderFormError(error.message);
  }
}

async function handleGroupImport(event) {
  const file = event.target.files?.[0];
  if (!file) {
    return;
  }

  try {
    const rawText = await file.text();
    let payload;
    try {
      payload = JSON.parse(rawText);
    } catch (error) {
      throw new Error(`Imported JSON ${file.name} is invalid: ${error.message}`);
    }
    const groupName = file.name.replace(/\.json$/i, "") || "inline";
    const groupUsers = normalizeGroupUsersPayload(payload, `Imported JSON ${file.name}`);
    renderFormError("");
    openGroupEditor(
      {
        name: groupName,
        users: groupUsers,
      },
      null
    );
  } catch (error) {
    renderFormError(error.message);
  } finally {
    elements.groupImportInput.value = "";
  }
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

  const selectedGroup = getSelectedGroup();
  if (!selectedGroup) {
    renderFormError("Create or import a local group before starting a check.");
    return;
  }

  const contestTokens = parseContestTokens(elements.contestInput.value);
  if (!contestTokens.length) {
    renderFormError("Enter at least one contest token before starting a check.");
    return;
  }

  const selectedOj = getSelectedOj();
  if (!(selectedGroup.users[selectedOj] ?? []).length) {
    const ojLabel = selectedOj === "cf" ? "Codeforces" : "AtCoder";
    renderFormError(`${selectedGroup.name} has no ${ojLabel} users.`);
    return;
  }

  const isCf = selectedOj === "cf";
  const contestTypes = isCf ? getSelectedContestTypes() : null;
  if (isCf && !contestTypes.length) {
    renderFormError("Select at least one Codeforces contest type before starting a check.");
    return;
  }

  setSubmitting(true);
  setStatusPill("running", "Running");
  renderEventFeed([]);
  renderContestResults([]);

  try {
    const payload = await fetchJson("/api/check", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        oj: selectedOj,
        group: selectedGroup.name,
        group_users: cloneGroupUsers(selectedGroup.users),
        contest_tokens: contestTokens,
        contest_types: contestTypes ?? undefined,
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

function restoreGroupsFromStorage() {
  const preferredGroupName = readSelectedGroupName();
  state.groups = loadStoredGroups();
  syncSelectedGroup(preferredGroupName);
  refreshGroupUi();
}

function handleGroupModalContentClick(event) {
  const actionTarget = event.target.closest("[data-action]");
  if (!actionTarget || state.modalMode !== "edit" || !state.draftGroup) {
    return;
  }

  const action = actionTarget.dataset.action;
  const oj = actionTarget.dataset.oj;
  if (action === "add-user" && oj) {
    addDraftUser(oj);
    return;
  }
  if (action === "remove-user" && oj) {
    removeDraftUser(oj, Number(actionTarget.dataset.index));
  }
}

function handleGroupModalContentInput(event) {
  if (state.modalMode !== "edit" || !state.draftGroup) {
    return;
  }

  if (event.target.id === "group-name-input") {
    state.draftGroup.name = event.target.value;
    elements.groupModalTitle.textContent = event.target.value.trim() || "Untitled Group";
    return;
  }

  if (event.target.classList.contains("editor-user-input")) {
    const oj = event.target.dataset.oj;
    state.draftUserInputs[oj] = event.target.value;
  }
}

function handleGroupModalKeydown(event) {
  if (event.key !== "Enter" || state.modalMode !== "edit" || !event.target.classList.contains("editor-user-input")) {
    return;
  }
  event.preventDefault();
  addDraftUser(event.target.dataset.oj);
}

function handleGroupModalActionsClick(event) {
  if (event.target.id === "group-save-button") {
    saveDraftGroup();
    return;
  }
  if (event.target.id === "group-modal-edit") {
    const group = state.groups.find((item) => item.name === state.viewGroupName);
    if (group) {
      openGroupEditor(group, group.name);
    }
  }
}

function bootstrap() {
  elements.form.addEventListener("submit", handleSubmit);
  elements.groupSelect.addEventListener("change", handleGroupSelectionChange);
  elements.groupViewButton.addEventListener("click", handleGroupView);
  elements.groupEditButton.addEventListener("click", handleGroupEdit);
  elements.groupNewButton.addEventListener("click", handleGroupNew);
  elements.groupImportButton.addEventListener("click", () => {
    elements.groupImportInput.click();
  });
  elements.groupImportInput.addEventListener("change", handleGroupImport);
  elements.groupDeleteButton.addEventListener("click", handleGroupDelete);
  elements.contestTypeToggle.addEventListener("click", () => {
    state.isContestTypeExpanded = !state.isContestTypeExpanded;
    updateContestTypeFieldsetState();
  });
  elements.ojInputs.forEach((input) => {
    input.addEventListener("change", updateContestTypeFieldsetState);
  });
  elements.contestTypeInputs.forEach((input) => {
    input.addEventListener("change", updateContestTypeFieldsetState);
  });
  elements.contestTypeSelectAll.addEventListener("click", () => {
    setSelectedContestTypes(Array.from(elements.contestTypeInputs).map((input) => input.value));
    updateContestTypeFieldsetState();
  });
  elements.contestTypeClearAll.addEventListener("click", () => {
    setSelectedContestTypes([]);
    updateContestTypeFieldsetState();
  });
  elements.groupModalClose.addEventListener("click", closeGroupModal);
  elements.groupModalBackdrop.addEventListener("click", closeGroupModal);
  elements.groupModalContent.addEventListener("click", handleGroupModalContentClick);
  elements.groupModalContent.addEventListener("input", handleGroupModalContentInput);
  elements.groupModalContent.addEventListener("keydown", handleGroupModalKeydown);
  elements.groupModalActions.addEventListener("click", handleGroupModalActionsClick);
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && !elements.groupModal.hidden) {
      closeGroupModal();
    }
  });

  setStatusPill("idle", "Idle");
  setSubmitting(false);
  renderEventFeed([]);
  renderContestResults([]);
  updateContestTypeFieldsetState();
  restoreGroupsFromStorage();
}

bootstrap();
