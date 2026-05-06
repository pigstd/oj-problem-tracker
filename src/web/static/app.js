const GROUP_STORAGE_KEY = "oj-problem-tracker.local-groups.v1";
const SELECTED_GROUP_STORAGE_KEY = "oj-problem-tracker.selected-group.v1";
const LANGUAGE_STORAGE_KEY = "oj-problem-tracker.language.v1";
const THEME_STORAGE_KEY = "oj-problem-tracker.theme.v1";
const DEFAULT_LANGUAGE = "en";
const DEFAULT_THEME = "classic";
const SUPPORTED_THEMES = ["classic", "ocean", "light", "rainbow"];

const translations = {
  en: {
    "app.title": "OJ Problem Tracker",
    "title.githubLink": "View source on GitHub",
    "title.githubRepository": "GitHub repository",
    "language.switchLabel": "Language",
    "theme.label": "Theme",
    "theme.classic": "Classic",
    "theme.ocean": "Ocean",
    "theme.light": "Light",
    "theme.rainbow": "Rainbow",
    "panel.input": "Input",
    "panel.log": "Log",
    "panel.result": "Result",
    "field.oj": "OJ",
    "field.group": "Group",
    "field.contestToken": "Contest Token",
    "field.contestPlaceholder": "abc403 abc404-abc406\nor\n2065 2067-2070",
    "field.contestType": "Contest Type",
    "field.forceRefreshCache": "Force refresh cache",
    "field.groupName": "Group Name",
    "field.groupNamePlaceholder": "Team Spring 2026",
    "field.addUserPlaceholder": ({ title }) => `Add ${title} user`,
    "action.startCheck": "Start Check",
    "action.checking": "Checking...",
    "action.view": "View",
    "action.edit": "Edit",
    "action.new": "New",
    "action.importJson": "Import JSON",
    "action.delete": "Delete",
    "action.selectAll": "Select all",
    "action.clearAll": "Clear all",
    "action.add": "Add",
    "action.saveGroup": "Save Group",
    "action.close": "Close",
    "action.removeUser": "Remove user",
    "status.idle": "Idle",
    "status.running": "Running",
    "status.completed": "Completed",
    "status.failed": "Failed",
    "contestType.toggle": ({ count }) => `Choose contest type (${count} selected)`,
    "group.noLocalGroups": "No local groups yet",
    "group.optionLabel": ({ name, atcoderCount, cfCount }) =>
      `${name}  A:${atcoderCount}  C:${cfCount}`,
    "group.createOrImportNotice":
      "Create or import a local group. It will stay in this browser and never be written to the server disk.",
    "group.localGroup": "Local Group",
    "group.editLocalGroup": "Edit Local Group",
    "group.newLocalGroup": "New Local Group",
    "group.untitled": "Untitled Group",
    "group.usersCount": ({ count }) => `${count} ${count === 1 ? "user" : "users"}`,
    "group.noUsersConfigured": "No users configured.",
    "result.empty": "Expanded contest results will show up here.",
    "result.skipped": "Skipped",
    "result.type": ({ type }) => `Type: ${type}`,
    "result.unknownType": "unknown",
    "result.skipFallback": "contest was skipped",
    "result.hitBadge": ({ count }) => `${count} ${count === 1 ? "hit" : "hits"}`,
    "result.noHitsBadge": "No hits",
    "result.noUsersDone": ({ contestId }) => `no users have done ${contestId}`,
    "result.warningHeading": "Possible same-round matches",
    "result.warningVia": ({ contests }) => `via ${contests}`,
    "log.noRecentActivity": "No recent activity.",
    "modal.groupDetail": "Group Detail",
    "modal.closeGroupDetail": "Close group detail",
    "error.browserStorageAccess": ({ message }) => `Could not access browser storage: ${message}`,
    "error.storedGroupsCouldNotBeLoaded": ({ message }) =>
      `Stored groups could not be loaded: ${message}`,
    "error.saveSelectedGroup": ({ message }) =>
      `Could not save the selected group in this browser: ${message}`,
    "error.saveGroups": ({ message }) => `Could not save groups in this browser: ${message}`,
    "error.saveLanguage": ({ message }) => `Could not save language in this browser: ${message}`,
    "error.saveTheme": ({ message }) => `Could not save theme in this browser: ${message}`,
    "error.userListType": ({ sourceLabel }) => `${sourceLabel} must be a list of users.`,
    "error.userListItemType": ({ sourceLabel }) =>
      `${sourceLabel} must contain only non-empty strings.`,
    "error.groupPayloadType": ({ sourceLabel }) =>
      `${sourceLabel} must be an object with atcoder and cf lists.`,
    "error.storedGroupType": ({ index }) => `Stored group #${index} must be an object.`,
    "error.storedGroupName": ({ index }) => `Stored group #${index} must have a non-empty name.`,
    "error.duplicateStoredGroup": ({ name }) => `duplicate group name "${name}" in browser storage`,
    "error.enterUser": "Enter a user before adding it to the group.",
    "error.duplicateUser": ({ user }) => `${user} is already in this group.`,
    "error.groupNameRequired": "Group name is required before saving.",
    "error.duplicateGroup": ({ name }) => `A group named "${name}" already exists in this browser.`,
    "error.importedJsonInvalid": ({ fileName, message }) =>
      `Imported JSON ${fileName} is invalid: ${message}`,
    "error.requestFailed": ({ status }) => `Request failed with ${status}`,
    "error.runFailed": "Run failed",
    "error.noGroup": "Create or import a local group before starting a check.",
    "error.noContestToken": "Enter at least one contest token before starting a check.",
    "error.groupHasNoUsers": ({ groupName, ojLabel }) => `${groupName} has no ${ojLabel} users.`,
    "error.noContestTypes": "Select at least one Codeforces contest type before starting a check.",
    "error.activeRun": "A check is already running. Following the active run.",
    "confirm.deleteGroup": ({ name }) => `Delete local group "${name}" from this browser?`,
  },
  "zh-CN": {
    "app.title": "OJ Problem Tracker",
    "title.githubLink": "在 GitHub 查看源码",
    "title.githubRepository": "GitHub 仓库",
    "language.switchLabel": "语言",
    "theme.label": "主题",
    "theme.classic": "经典",
    "theme.ocean": "海风",
    "theme.light": "清爽",
    "theme.rainbow": "彩虹",
    "panel.input": "输入",
    "panel.log": "日志",
    "panel.result": "结果",
    "field.oj": "OJ",
    "field.group": "用户组",
    "field.contestToken": "比赛 Token",
    "field.contestPlaceholder": "abc403 abc404-abc406\n或\n2065 2067-2070",
    "field.contestType": "比赛类型",
    "field.forceRefreshCache": "强制刷新缓存",
    "field.groupName": "用户组名称",
    "field.groupNamePlaceholder": "Team Spring 2026",
    "field.addUserPlaceholder": ({ title }) => `添加 ${title} 用户`,
    "action.startCheck": "开始检查",
    "action.checking": "检查中...",
    "action.view": "查看",
    "action.edit": "编辑",
    "action.new": "新建",
    "action.importJson": "导入 JSON",
    "action.delete": "删除",
    "action.selectAll": "全选",
    "action.clearAll": "清空",
    "action.add": "添加",
    "action.saveGroup": "保存用户组",
    "action.close": "关闭",
    "action.removeUser": "移除用户",
    "status.idle": "空闲",
    "status.running": "运行中",
    "status.completed": "已完成",
    "status.failed": "失败",
    "contestType.toggle": ({ count }) => `选择比赛类型（已选 ${count} 个）`,
    "group.noLocalGroups": "还没有本地用户组",
    "group.optionLabel": ({ name, atcoderCount, cfCount }) =>
      `${name}  AtCoder:${atcoderCount}  Codeforces:${cfCount}`,
    "group.createOrImportNotice":
      "请新建或导入一个本地用户组。它只会保存在当前浏览器，不会写入服务器磁盘。",
    "group.localGroup": "本地用户组",
    "group.editLocalGroup": "编辑本地用户组",
    "group.newLocalGroup": "新建本地用户组",
    "group.untitled": "未命名用户组",
    "group.usersCount": ({ count }) => `${count} 个用户`,
    "group.noUsersConfigured": "未配置用户。",
    "result.empty": "展开后的比赛结果会显示在这里。",
    "result.skipped": "已跳过",
    "result.type": ({ type }) => `类型：${type}`,
    "result.unknownType": "未知",
    "result.skipFallback": "比赛已跳过",
    "result.hitBadge": ({ count }) => `命中 ${count} 人`,
    "result.noHitsBadge": "无命中",
    "result.noUsersDone": ({ contestId }) => `没有用户完成 ${contestId}`,
    "result.warningHeading": "可能的同场比赛命中",
    "result.warningVia": ({ contests }) => `通过 ${contests}`,
    "log.noRecentActivity": "暂无最近活动。",
    "modal.groupDetail": "用户组详情",
    "modal.closeGroupDetail": "关闭用户组详情",
    "error.browserStorageAccess": ({ message }) => `无法访问浏览器存储：${message}`,
    "error.storedGroupsCouldNotBeLoaded": ({ message }) =>
      `无法加载已保存的用户组：${message}`,
    "error.saveSelectedGroup": ({ message }) => `无法在当前浏览器保存所选用户组：${message}`,
    "error.saveGroups": ({ message }) => `无法在当前浏览器保存用户组：${message}`,
    "error.saveLanguage": ({ message }) => `无法在当前浏览器保存语言：${message}`,
    "error.saveTheme": ({ message }) => `无法在当前浏览器保存主题：${message}`,
    "error.userListType": ({ sourceLabel }) => `${sourceLabel} 必须是用户列表。`,
    "error.userListItemType": ({ sourceLabel }) => `${sourceLabel} 只能包含非空字符串。`,
    "error.groupPayloadType": ({ sourceLabel }) =>
      `${sourceLabel} 必须是包含 atcoder 和 cf 列表的对象。`,
    "error.storedGroupType": ({ index }) => `已保存的第 ${index} 个用户组必须是对象。`,
    "error.storedGroupName": ({ index }) => `已保存的第 ${index} 个用户组必须有非空名称。`,
    "error.duplicateStoredGroup": ({ name }) => `浏览器存储中存在重复用户组 "${name}"`,
    "error.enterUser": "请先输入用户再添加到用户组。",
    "error.duplicateUser": ({ user }) => `${user} 已在这个用户组中。`,
    "error.groupNameRequired": "保存前需要填写用户组名称。",
    "error.duplicateGroup": ({ name }) => `当前浏览器中已经有名为 "${name}" 的用户组。`,
    "error.importedJsonInvalid": ({ fileName, message }) =>
      `导入的 JSON ${fileName} 无效：${message}`,
    "error.requestFailed": ({ status }) => `请求失败，状态码 ${status}`,
    "error.runFailed": "运行失败",
    "error.noGroup": "请先新建或导入一个本地用户组再开始检查。",
    "error.noContestToken": "请至少输入一个比赛 token 再开始检查。",
    "error.groupHasNoUsers": ({ groupName, ojLabel }) => `${groupName} 没有 ${ojLabel} 用户。`,
    "error.noContestTypes": "请至少选择一种 Codeforces 比赛类型再开始检查。",
    "error.activeRun": "已有检查正在运行，将跟随当前运行任务。",
    "confirm.deleteGroup": ({ name }) => `从当前浏览器删除本地用户组 "${name}"？`,
  },
};

const state = {
  language: DEFAULT_LANGUAGE,
  theme: DEFAULT_THEME,
  runStatus: "idle",
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
  lastEvents: [],
  lastContestSummaries: [],
  formError: null,
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
  languageButtons: document.querySelectorAll("[data-language]"),
  themeSelect: document.querySelector("#theme-select"),
};

function t(key, params = {}, fallback = key) {
  const languageMessages = translations[state.language] ?? translations[DEFAULT_LANGUAGE];
  const defaultMessages = translations[DEFAULT_LANGUAGE];
  const message = languageMessages[key] ?? defaultMessages[key] ?? fallback;
  if (typeof message === "function") {
    return message(params);
  }
  return message.replace(/\{(\w+)\}/g, (match, paramName) => {
    if (Object.prototype.hasOwnProperty.call(params, paramName)) {
      return String(params[paramName]);
    }
    return match;
  });
}

function normalizeLanguage(language) {
  return Object.prototype.hasOwnProperty.call(translations, language) ? language : DEFAULT_LANGUAGE;
}

function normalizeTheme(theme) {
  return SUPPORTED_THEMES.includes(theme) ? theme : DEFAULT_THEME;
}

function readStoredLanguage() {
  try {
    return normalizeLanguage(localStorage.getItem(LANGUAGE_STORAGE_KEY));
  } catch (error) {
    return DEFAULT_LANGUAGE;
  }
}

function readStoredTheme() {
  try {
    return normalizeTheme(localStorage.getItem(THEME_STORAGE_KEY));
  } catch (error) {
    return DEFAULT_THEME;
  }
}

function persistLanguage() {
  try {
    localStorage.setItem(LANGUAGE_STORAGE_KEY, state.language);
  } catch (error) {
    throw localizedError("error.saveLanguage", { message: error.message });
  }
}

function persistTheme() {
  try {
    localStorage.setItem(THEME_STORAGE_KEY, state.theme);
  } catch (error) {
    throw localizedError("error.saveTheme", { message: error.message });
  }
}

function applyTheme() {
  document.documentElement.dataset.theme = state.theme;
  elements.themeSelect.value = state.theme;
}

function applyLanguage() {
  document.documentElement.lang = state.language === "zh-CN" ? "zh-CN" : "en";
  document.title = t("app.title");

  document.querySelectorAll("[data-i18n]").forEach((element) => {
    element.textContent = t(element.dataset.i18n);
  });
  document.querySelectorAll("[data-i18n-placeholder]").forEach((element) => {
    element.placeholder = t(element.dataset.i18nPlaceholder);
  });
  document.querySelectorAll("[data-i18n-title]").forEach((element) => {
    element.title = t(element.dataset.i18nTitle);
  });
  document.querySelectorAll("[data-i18n-aria-label]").forEach((element) => {
    element.setAttribute("aria-label", t(element.dataset.i18nAriaLabel));
  });
  elements.languageButtons.forEach((button) => {
    const isActive = button.dataset.language === state.language;
    button.classList.toggle("active", isActive);
    button.setAttribute("aria-pressed", String(isActive));
  });
}

function refreshLocalizedUi() {
  applyLanguage();
  setStatusPill(state.runStatus);
  updateSubmitButtonState();
  updateContestTypeFieldsetState();
  refreshGroupUi();
  renderStoredFormError();
  renderEventFeed(state.lastEvents);
  renderContestResults(state.lastContestSummaries);
  if (!elements.groupModal.hidden) {
    renderGroupModal();
  }
}

function setLanguage(language, { persist = false } = {}) {
  state.language = normalizeLanguage(language);
  if (persist) {
    try {
      persistLanguage();
    } catch (error) {
      renderFormErrorFromError(error);
    }
  }
  refreshLocalizedUi();
}

function setTheme(theme, { persist = false } = {}) {
  state.theme = normalizeTheme(theme);
  if (persist) {
    try {
      persistTheme();
    } catch (error) {
      renderFormErrorFromError(error);
    }
  }
  applyTheme();
}

function setStatusPill(status) {
  state.runStatus = status;
  elements.runStatus.className = `status-pill ${status}`;
  elements.runStatus.textContent = t(`status.${status}`);
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
  state.formError = message
    ? {
        type: "literal",
        message,
      }
    : null;
  renderNotice(elements.formError, message, "error");
}

function renderFormErrorKey(key, params = {}) {
  state.formError = {
    type: "translation",
    key,
    params,
  };
  renderNotice(elements.formError, t(key, params), "error");
}

function renderStoredFormError() {
  if (!state.formError) {
    renderNotice(elements.formError, "", "error");
    return;
  }
  if (state.formError.type === "translation") {
    renderNotice(elements.formError, t(state.formError.key, state.formError.params), "error");
    return;
  }
  renderNotice(elements.formError, state.formError.message, "error");
}

function localizedError(key, params = {}) {
  const error = new Error(t(key, params));
  error.translationKey = key;
  error.translationParams = params;
  return error;
}

function renderFormErrorFromError(error) {
  if (error.translationKey) {
    renderFormErrorKey(error.translationKey, error.translationParams ?? {});
    return;
  }
  renderFormError(error.message);
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
  return t("contestType.toggle", { count: selectedCount });
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
    throw localizedError("error.userListType", { sourceLabel });
  }

  const normalizedUsers = [];
  const seenUsers = new Set();
  for (const user of users) {
    if (typeof user !== "string" || !user.trim()) {
      throw localizedError("error.userListItemType", { sourceLabel });
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
    throw localizedError("error.groupPayloadType", { sourceLabel });
  }

  return {
    atcoder: normalizeUserList(payload.atcoder, `${sourceLabel}.atcoder`),
    cf: normalizeUserList(payload.cf, `${sourceLabel}.cf`),
  };
}

function normalizeStoredGroup(record, index) {
  if (!record || typeof record !== "object" || Array.isArray(record)) {
    throw localizedError("error.storedGroupType", { index: index + 1 });
  }
  if (typeof record.name !== "string" || !record.name.trim()) {
    throw localizedError("error.storedGroupName", { index: index + 1 });
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
    state.storageError = {
      key: "error.browserStorageAccess",
      params: { message: error.message },
    };
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
        throw localizedError("error.duplicateStoredGroup", { name: group.name });
      }
      seenGroupNames.add(group.name);
    }

    state.storageError = null;
    return groups;
  } catch (error) {
    state.storageError = {
      key: "error.storedGroupsCouldNotBeLoaded",
      params: { message: error.message },
    };
    return [];
  }
}

function getStorageErrorMessage() {
  if (!state.storageError) {
    return "";
  }
  if (typeof state.storageError === "string") {
    return state.storageError;
  }
  return t(state.storageError.key, state.storageError.params);
}

function persistSelectedGroupName() {
  try {
    if (state.selectedGroupName) {
      localStorage.setItem(SELECTED_GROUP_STORAGE_KEY, state.selectedGroupName);
      return;
    }
    localStorage.removeItem(SELECTED_GROUP_STORAGE_KEY);
  } catch (error) {
    throw localizedError("error.saveSelectedGroup", { message: error.message });
  }
}

function persistGroups() {
  try {
    localStorage.setItem(GROUP_STORAGE_KEY, JSON.stringify(state.groups));
    state.storageError = null;
  } catch (error) {
    throw localizedError("error.saveGroups", { message: error.message });
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
  elements.submitButton.textContent = state.isSubmitting ? t("action.checking") : t("action.startCheck");
}

function renderGroups() {
  if (!state.groups.length) {
    elements.groupSelect.disabled = true;
    elements.groupSelect.innerHTML = `<option value="">${escapeHtml(t("group.noLocalGroups"))}</option>`;
    updateGroupActionState();
    updateSubmitButtonState();
    return;
  }

  elements.groupSelect.disabled = false;
  elements.groupSelect.innerHTML = state.groups
    .map((group) => {
      const label = t("group.optionLabel", {
        name: group.name,
        atcoderCount: group.users.atcoder.length,
        cfCount: group.users.cf.length,
      });
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
    renderGroupNotice(getStorageErrorMessage(), "error");
    return;
  }
  if (!state.groups.length) {
    renderGroupNotice(t("group.createOrImportNotice"), "warning");
    return;
  }
  renderGroupNotice("");
}

function setSubmitting(isSubmitting) {
  state.isSubmitting = isSubmitting;
  updateSubmitButtonState();
}

function renderEventFeed(events) {
  state.lastEvents = events;
  const visibleEvents = events.slice(-3).reverse();
  if (!visibleEvents.length) {
    elements.eventFeed.innerHTML =
      `<li data-kind="idle"><span class="log-meta">${escapeHtml(t("status.idle"))}</span><strong>${escapeHtml(
        t("log.noRecentActivity")
      )}</strong></li>`;
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
  state.lastContestSummaries = contestSummaries;
  if (!contestSummaries.length) {
    elements.contestResults.className = "result-list empty-state";
    elements.contestResults.textContent = t("result.empty");
    return;
  }

  elements.contestResults.className = "result-list";
  elements.contestResults.innerHTML = contestSummaries
    .map((summary) => {
      const matchedUsers = summary.matched_users ?? [];
      const warnings = summary.warnings ?? [];
      if (summary.status === "skipped") {
        const contestTypeLabel = t("result.type", {
          type: summary.contest_type || t("result.unknownType"),
        });
        return `
          <article class="result-card skipped">
            <header>
              <strong>${escapeHtml(summary.contest_id)}</strong>
              <span class="badge skipped">${escapeHtml(t("result.skipped"))}</span>
            </header>
            <section class="skip-section">
              <p class="skip-meta">${escapeHtml(contestTypeLabel)}</p>
              <p>${escapeHtml(summary.skip_reason ?? t("result.skipFallback"))}</p>
            </section>
          </article>
        `;
      }

      const hasMatches = matchedUsers.length > 0;
      const badgeClass = hasMatches ? "hit" : "miss";
      const badgeLabel = hasMatches ? t("result.hitBadge", { count: matchedUsers.length }) : t("result.noHitsBadge");
      const detailMarkup = hasMatches
        ? `<div class="user-list">${matchedUsers
            .map((user) => `<span class="user-chip">${escapeHtml(user)}</span>`)
            .join("")}</div>`
        : `<p>${escapeHtml(t("result.noUsersDone", { contestId: summary.contest_id }))}</p>`;
      const warningMarkup = warnings.length
        ? `
          <section class="warning-section">
            <p class="warning-heading">${escapeHtml(t("result.warningHeading"))}</p>
            <div class="warning-list">
              ${warnings
                .map(
                  (warning) => `
                    <article class="warning-item">
                      <strong>${escapeHtml(warning.user_id)}</strong>
                      <p>${escapeHtml(t("result.warningVia", { contests: warning.warning_contests.join(", ") }))}</p>
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
    setStatusPill("running");
  } else if (snapshot.status === "completed") {
    setStatusPill("completed");
  } else if (snapshot.status === "failed") {
    setStatusPill("failed");
    if (snapshot.error?.message) {
      renderFormError(snapshot.error.message);
    } else {
      renderFormErrorKey("error.runFailed");
    }
  } else {
    setStatusPill("idle");
  }
}

function renderGroupViewSection(oj, users) {
  const title = oj === "atcoder" ? "AtCoder" : "Codeforces";
  const userMarkup = users.length
    ? `<div class="user-list">${users
        .map((user) => `<span class="user-chip">${escapeHtml(user)}</span>`)
        .join("")}</div>`
    : `<p>${escapeHtml(t("group.noUsersConfigured"))}</p>`;
  return `
    <section class="modal-group">
      <header>
        <h3>${escapeHtml(title)}</h3>
        <span class="modal-count">${escapeHtml(t("group.usersCount", { count: users.length }))}</span>
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
                aria-label="${escapeHtml(t("action.removeUser"))}"
                title="${escapeHtml(t("action.removeUser"))}"
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
    : `<p class="editor-empty">${escapeHtml(t("group.noUsersConfigured"))}</p>`;
  return `
    <section class="modal-group">
      <header>
        <h3>${escapeHtml(title)}</h3>
        <span class="modal-count">${escapeHtml(t("group.usersCount", { count: users.length }))}</span>
      </header>
      <div class="editor-user-entry">
        <input
          class="editor-user-input"
          type="text"
          data-oj="${escapeHtml(oj)}"
          value="${escapeHtml(inputValue)}"
          placeholder="${escapeHtml(t("field.addUserPlaceholder", { title }))}"
        />
        <button class="secondary-button" type="button" data-action="add-user" data-oj="${escapeHtml(oj)}">
          ${escapeHtml(t("action.add"))}
        </button>
      </div>
      ${userMarkup}
    </section>
  `;
}

function renderGroupModal() {
  elements.groupModalContent.classList.toggle("editor-mode", state.modalMode === "edit");
  if (state.modalMode === "edit" && state.draftGroup) {
    elements.groupModalKicker.textContent = state.draftOriginalName
      ? t("group.editLocalGroup")
      : t("group.newLocalGroup");
    elements.groupModalTitle.textContent = state.draftGroup.name.trim() || t("group.untitled");
    elements.groupModalContent.innerHTML = `
      <div class="editor-shell">
        <label class="field-block">
          <span class="field-label">${escapeHtml(t("field.groupName"))}</span>
          <input
            id="group-name-input"
            class="editor-name-input"
            type="text"
            value="${escapeHtml(state.draftGroup.name)}"
            placeholder="${escapeHtml(t("field.groupNamePlaceholder"))}"
          />
        </label>
        <div class="editor-grid">
          ${renderGroupEditorSection("atcoder", state.draftGroup.users.atcoder)}
          ${renderGroupEditorSection("cf", state.draftGroup.users.cf)}
        </div>
      </div>
    `;
    elements.groupModalActions.innerHTML =
      `<button id="group-save-button" class="submit-button" type="button">${escapeHtml(t("action.saveGroup"))}</button>`;
    return;
  }

  const group = state.groups.find((item) => item.name === state.viewGroupName);
  if (!group) {
    closeGroupModal();
    return;
  }

  elements.groupModalKicker.textContent = t("group.localGroup");
  elements.groupModalTitle.textContent = group.name;
  elements.groupModalContent.innerHTML = `
    ${renderGroupViewSection("atcoder", group.users.atcoder)}
    ${renderGroupViewSection("cf", group.users.cf)}
  `;
  elements.groupModalActions.innerHTML =
    `<button id="group-modal-edit" class="secondary-button" type="button">${escapeHtml(t("action.edit"))}</button>`;
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
    renderFormErrorKey("error.enterUser");
    return;
  }
  if (state.draftGroup.users[oj].includes(normalizedUser)) {
    renderFormErrorKey("error.duplicateUser", { user: normalizedUser });
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
      throw localizedError("error.groupNameRequired");
    }

    const nextGroup = {
      name: nextGroupName,
      users: normalizeGroupUsersPayload(state.draftGroup.users, `Group "${nextGroupName}"`),
    };

    const conflictingGroup = state.groups.find(
      (group) => group.name === nextGroupName && group.name !== state.draftOriginalName
    );
    if (conflictingGroup) {
      throw localizedError("error.duplicateGroup", { name: nextGroupName });
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
    renderFormErrorFromError(error);
  }
}

function handleGroupSelectionChange() {
  state.selectedGroupName = elements.groupSelect.value || null;
  try {
    persistSelectedGroupName();
  } catch (error) {
    renderFormErrorFromError(error);
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
  if (!window.confirm(t("confirm.deleteGroup", { name: group.name }))) {
    return;
  }

  try {
    state.groups = state.groups.filter((item) => item.name !== group.name);
    syncSelectedGroup();
    persistGroups();
    refreshGroupUi();
    renderFormError("");
  } catch (error) {
    renderFormErrorFromError(error);
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
      throw localizedError("error.importedJsonInvalid", { fileName: file.name, message: error.message });
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
    renderFormErrorFromError(error);
  } finally {
    elements.groupImportInput.value = "";
  }
}

async function fetchJson(url, options = {}) {
  const response = await fetch(url, options);
  const payload = await response.json();
  if (!response.ok) {
    const error = payload.error?.message
      ? new Error(payload.error.message)
      : localizedError("error.requestFailed", { status: response.status });
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
    renderFormErrorFromError(error);
    setStatusPill("failed");
  }
}

async function handleSubmit(event) {
  event.preventDefault();
  window.clearTimeout(state.pollTimer);
  renderFormError("");

  const selectedGroup = getSelectedGroup();
  if (!selectedGroup) {
    renderFormErrorKey("error.noGroup");
    return;
  }

  const contestTokens = parseContestTokens(elements.contestInput.value);
  if (!contestTokens.length) {
    renderFormErrorKey("error.noContestToken");
    return;
  }

  const selectedOj = getSelectedOj();
  if (!(selectedGroup.users[selectedOj] ?? []).length) {
    const ojLabel = selectedOj === "cf" ? "Codeforces" : "AtCoder";
    renderFormErrorKey("error.groupHasNoUsers", { groupName: selectedGroup.name, ojLabel });
    return;
  }

  const isCf = selectedOj === "cf";
  const contestTypes = isCf ? getSelectedContestTypes() : null;
  if (isCf && !contestTypes.length) {
    renderFormErrorKey("error.noContestTypes");
    return;
  }

  setSubmitting(true);
  setStatusPill("running");
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
      renderFormErrorKey("error.activeRun");
      pollRun();
      return;
    }
    setSubmitting(false);
    setStatusPill("failed");
    renderFormErrorFromError(error);
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
    elements.groupModalTitle.textContent = event.target.value.trim() || t("group.untitled");
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

function handleLanguageSelection(event) {
  const languageButton = event.target.closest("[data-language]");
  if (!languageButton) {
    return;
  }
  setLanguage(languageButton.dataset.language, { persist: true });
}

function handleThemeSelection(event) {
  setTheme(event.target.value, { persist: true });
}

function bootstrap() {
  state.language = readStoredLanguage();
  state.theme = readStoredTheme();
  applyTheme();
  applyLanguage();

  elements.form.addEventListener("submit", handleSubmit);
  elements.languageButtons.forEach((button) => {
    button.addEventListener("click", handleLanguageSelection);
  });
  elements.themeSelect.addEventListener("change", handleThemeSelection);
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

  setStatusPill("idle");
  setSubmitting(false);
  renderEventFeed([]);
  renderContestResults([]);
  updateContestTypeFieldsetState();
  restoreGroupsFromStorage();
}

bootstrap();
