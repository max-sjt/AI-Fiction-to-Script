const scriptTypes = [
  { value: "film", zh: "电影剧本", en: "Film Screenplay" },
  { value: "tv_drama", zh: "电视剧剧本", en: "TV Drama Screenplay" },
  { value: "short_drama", zh: "短剧剧本", en: "Short Drama Screenplay" },
  { value: "stage_play", zh: "舞台剧剧本", en: "Stage Play Script" },
  { value: "animation", zh: "动画剧本", en: "Animation Script" },
  { value: "audio_drama", zh: "广播剧剧本", en: "Audio Drama Script" },
];

const toneOptions = [
  { value: "balanced", zh: "平衡", en: "Balanced" },
  { value: "serious", zh: "严肃", en: "Serious" },
  { value: "angry", zh: "愤怒", en: "Angry" },
  { value: "gentle", zh: "温柔", en: "Gentle" },
  { value: "suspenseful", zh: "悬疑", en: "Suspenseful" },
  { value: "humorous", zh: "幽默", en: "Humorous" },
  { value: "dark", zh: "暗黑", en: "Dark" },
  { value: "lyrical", zh: "抒情", en: "Lyrical" },
  { value: "cold", zh: "冷峻", en: "Cold" },
  { value: "uplifting", zh: "振奋", en: "Uplifting" },
];

const translations = {
  zh: {
    htmlLang: "zh-CN",
    heroTitle: "Qwen 剧本生成工作台",
    heroCopy: "上传小说文件或直接粘贴正文，调用通义千问生成不同类型、不同语气的结构化剧本，并支持场景级重生成。",
    languageLabel: "界面语言",
    loadingWorkspace: "正在加载工作区...",
    projectsHeading: "项目",
    resetButton: "重置",
    refreshButton: "刷新",
    deleteButton: "删除",
    noProjectsCard: "还没有项目。先生成一版剧本即可开始。",
    generateHeading: "生成剧本",
    qwenPill: "Qwen 生成",
    apiKeyLabel: "Qwen API Key",
    apiKeyPlaceholder: "请输入 sk-...",
    uploadLabel: "上传小说文件（txt / doc / docx）",
    yamlBundleLabel: "上传剧本 YAML（.yaml / .yml）",
    titleLabel: "剧本标题",
    authorLabel: "原著作者",
    originalTitleLabel: "原著标题",
    scriptTypeLabel: "生成剧本类型",
    genreLabel: "题材",
    toneLabel: "语气风格",
    pasteTextLabel: "直接粘贴小说文本",
    novelTextPlaceholder: "如果不上传文件，可以在这里粘贴一章或多章小说正文；多章生成会更稳定。",
    generateButton: "生成剧本",
    regenerateFromYamlButton: "根据 YAML 重生成",
    workspaceHeading: "工作区",
    workspaceEmpty: "尚未选择项目",
    currentProjectLabel: "当前项目",
    currentVersionLabel: "当前版本",
    reloadButton: "重新加载",
    downloadYamlButton: "下载 YAML",
    downloadRegeneratedYamlButton: "下载修改后 YAML",
    finalScriptHeading: "最终生成剧本",
    scriptPreviewPlaceholder: "请上传小说后等待Qwen生成剧本",
    sceneRegenerationHeading: "场景重生成",
    targetedRewritePill: "定向重写",
    sceneLabel: "场景",
    instructionLabel: "修改要求",
    regenInstructionPlaceholder: "描述这个场景需要如何调整。",
    regenerateButton: "重生成场景",
    sceneComparisonHeading: "修改前后对比",
    comparisonResultPill: "结果对比",
    comparisonInstructionLabel: "修改要求",
    comparisonBeforeLabel: "修改前",
    comparisonAfterLabel: "修改后",
    comparisonPlaceholder: "重生成场景后，这里会显示修改前后对比。",
    refreshingProjectsStatus: "正在刷新项目列表...",
    noProjectsFoundStatus: "没有发现任何项目。",
    selectProjectPlaceholder: "请选择项目",
    selectProjectStatus: "请选择项目。",
    selectionResetStatus: "已清空输入表单和工作区状态。",
    deletingVersionStatus: "正在删除 {projectId}/{versionId}...",
    deletedVersionStatus: "已删除 {projectId}/{versionId}",
    loadingVersionsStatus: "正在加载 {projectId} 的版本...",
    noVersionsStatus: "项目 {projectId} 还没有保存版本。",
    loadingVersionStatus: "正在加载 {projectId}/{versionId}...",
    loadedVersionStatus: "已加载 {projectId}/{versionId}",
    generatingDraftStatus: "正在调用 Qwen 生成剧本...",
    generatedDraftStatus: "已生成 {projectId}/{versionId}",
    qwenGenerationPending: "Qwen 正在以极速草稿模式生成，单章通常会快很多；只有在整条流程完成后，工作区才会切换到新版本。",
    qwenRegenerationPending: "Qwen 正在以极速模式重生成场景；完成前工作区不会更新。",
    localPreviewReady: "已先生成本地草稿 {projectId}/{versionId}，后台正在继续生成 Qwen 正式版。",
    qwenFinalReady: "Qwen 正式版已完成：{projectId}/{versionId}",
    backgroundTaskFailed: "后台 Qwen 任务失败：{error}",
    apiKeyRequired: "请输入 Qwen API Key。",
    inputRequired: "请上传小说文件，或直接粘贴小说文本。",
    yamlFileRequired: "请先上传一个 YAML 文件。",
    selectVersionBeforeRegenerate: "请先选择一个项目版本再重生成场景。",
    regeneratingSceneStatus: "正在重生成 {sceneId}...",
    regeneratingFromYamlStatus: "正在根据 YAML 重生成剧本...",
    regeneratedSceneStatus: "已生成新版本 {versionId}",
    yamlRegenerationPending: "Qwen 正在根据 YAML 重生成整篇剧本；完成前工作区不会切换到新版本。",
    downloadYamlFilename: "{projectId}_{versionId}.yaml",
    projectLatestLabel: "最新版本：{versionId}",
    projectVersionCountLabel: "版本数：{count}",
    versionOptionLabel: "{versionId}",
    buildBadgeLabel: "服务版本 {version} · 启动于 {startedAt}",
    genericNetworkError: "请求失败，可能是服务未重启、页面缓存未刷新，或 Qwen 请求本身报错。",
    unknownError: "发生了未预期的错误。",
  },
  en: {
    htmlLang: "en",
    heroTitle: "Qwen Screenplay Generation Workbench",
    heroCopy: "Upload a novel file or paste source text, use Qwen to generate structured screenplay drafts in different formats and tones, and regenerate individual scenes when needed.",
    languageLabel: "Interface language",
    loadingWorkspace: "Loading workspace...",
    projectsHeading: "Projects",
    resetButton: "Reset",
    refreshButton: "Refresh",
    deleteButton: "Delete",
    noProjectsCard: "No projects yet. Generate a screenplay to begin.",
    generateHeading: "Generate Screenplay",
    qwenPill: "Qwen Generation",
    apiKeyLabel: "Qwen API Key",
    apiKeyPlaceholder: "Enter sk-...",
    uploadLabel: "Upload novel file (txt / doc / docx)",
    yamlBundleLabel: "Upload screenplay YAML (.yaml / .yml)",
    titleLabel: "Screenplay title",
    authorLabel: "Original author",
    originalTitleLabel: "Original title",
    scriptTypeLabel: "Screenplay type",
    genreLabel: "Genre",
    toneLabel: "Tone style",
    pasteTextLabel: "Paste novel text directly",
    novelTextPlaceholder: "If you do not upload a file, paste one or more chapters of source text here. More chapters usually produce better results.",
    generateButton: "Generate Screenplay",
    regenerateFromYamlButton: "Regenerate From YAML",
    workspaceHeading: "Workspace",
    workspaceEmpty: "No project selected",
    currentProjectLabel: "Current project",
    currentVersionLabel: "Current version",
    reloadButton: "Reload",
    downloadYamlButton: "Download YAML",
    downloadRegeneratedYamlButton: "Download Regenerated YAML",
    finalScriptHeading: "Final screenplay",
    scriptPreviewPlaceholder: "Upload a novel and wait for Qwen to generate the screenplay.",
    sceneRegenerationHeading: "Scene Regeneration",
    targetedRewritePill: "Targeted rewrite",
    sceneLabel: "Scene",
    instructionLabel: "Instruction",
    regenInstructionPlaceholder: "Describe how this scene should be adjusted.",
    regenerateButton: "Regenerate Scene",
    sceneComparisonHeading: "Before / After Comparison",
    comparisonResultPill: "Result comparison",
    comparisonInstructionLabel: "Instruction",
    comparisonBeforeLabel: "Before",
    comparisonAfterLabel: "After",
    comparisonPlaceholder: "The before-and-after comparison will appear here after scene regeneration.",
    refreshingProjectsStatus: "Refreshing projects...",
    noProjectsFoundStatus: "No projects found.",
    selectProjectPlaceholder: "Select project",
    selectProjectStatus: "Select a project.",
    selectionResetStatus: "Form inputs and workspace state cleared.",
    deletingVersionStatus: "Deleting {projectId}/{versionId}...",
    deletedVersionStatus: "Deleted {projectId}/{versionId}",
    loadingVersionsStatus: "Loading versions for {projectId}...",
    noVersionsStatus: "Project {projectId} has no saved versions.",
    loadingVersionStatus: "Loading {projectId}/{versionId}...",
    loadedVersionStatus: "Loaded {projectId}/{versionId}",
    generatingDraftStatus: "Generating screenplay with Qwen...",
    generatedDraftStatus: "Generated {projectId}/{versionId}",
    qwenGenerationPending: "Qwen is generating in fast-draft mode. Single-chapter drafts should complete much faster, but the workspace updates only after the full pipeline finishes.",
    qwenRegenerationPending: "Qwen is regenerating the scene in fast mode. The workspace will not update until it finishes.",
    localPreviewReady: "Local preview draft is ready: {projectId}/{versionId}. Qwen is still generating the final version in the background.",
    qwenFinalReady: "Qwen final version is ready: {projectId}/{versionId}",
    backgroundTaskFailed: "Background Qwen task failed: {error}",
    apiKeyRequired: "Enter a Qwen API key first.",
    inputRequired: "Upload a novel file or paste novel text first.",
    yamlFileRequired: "Upload a YAML file first.",
    selectVersionBeforeRegenerate: "Select a project version before regenerating a scene.",
    regeneratingSceneStatus: "Regenerating {sceneId}...",
    regeneratingFromYamlStatus: "Regenerating screenplay from YAML...",
    regeneratedSceneStatus: "Generated new version {versionId}",
    yamlRegenerationPending: "Qwen is regenerating the full screenplay from the YAML bundle. The workspace will switch after it finishes.",
    downloadYamlFilename: "{projectId}_{versionId}.yaml",
    projectLatestLabel: "Latest: {versionId}",
    projectVersionCountLabel: "Versions: {count}",
    versionOptionLabel: "{versionId}",
    buildBadgeLabel: "Server {version} · started {startedAt}",
    genericNetworkError: "The request failed. The usual causes are an old server process, a stale page cache, or a Qwen request error.",
    unknownError: "An unexpected error occurred.",
  },
};
const state = {
  projects: [],
  selectedProjectId: "",
  selectedVersionId: "",
  selectedVersionPayload: null,
  lastSceneComparison: null,
  language: localStorage.getItem("workbench.language") || "zh",
  upload: {
    name: "",
    base64: "",
  },
  yamlUpload: {
    name: "",
    base64: "",
  },
  lastRegeneratedVersionId: "",
  lastRegeneratedProjectId: "",
  health: null,
  activeTaskId: "",
  activeTaskKind: "",
  activeTaskStream: null,
};

const STREAM_FRAME_MS = 24;
const STREAM_MIN_CHUNK = 2;
const STREAM_MAX_CHUNK = 8;
const streamRenderers = new WeakMap();

const els = {
  languageSelect: document.getElementById("languageSelect"),
  statusText: document.getElementById("statusText"),
  buildBadge: document.getElementById("buildBadge"),
  messageBanner: document.getElementById("messageBanner"),
  workspacePill: document.getElementById("workspacePill"),
  projectsList: document.getElementById("projectsList"),
  resetProjectsButton: document.getElementById("resetProjectsButton"),
  refreshProjectsButton: document.getElementById("refreshProjectsButton"),
  apiKey: document.getElementById("apiKey"),
  uploadFile: document.getElementById("uploadFile"),
  uploadYamlFile: document.getElementById("uploadYamlFile"),
  title: document.getElementById("title"),
  author: document.getElementById("author"),
  originalTitle: document.getElementById("originalTitle"),
  scriptType: document.getElementById("scriptType"),
  genre: document.getElementById("genre"),
  tone: document.getElementById("tone"),
  novelText: document.getElementById("novelText"),
  generateButton: document.getElementById("generateButton"),
  regenerateFromYamlButton: document.getElementById("regenerateFromYamlButton"),
  projectSelect: document.getElementById("projectSelect"),
  versionSelect: document.getElementById("versionSelect"),
  reloadVersionButton: document.getElementById("reloadVersionButton"),
  downloadYamlButton: document.getElementById("downloadYamlButton"),
  downloadRegeneratedYamlButton: document.getElementById("downloadRegeneratedYamlButton"),
  scriptPreview: document.getElementById("scriptPreview"),
  sceneSelect: document.getElementById("sceneSelect"),
  regenInstruction: document.getElementById("regenInstruction"),
  regenerateButton: document.getElementById("regenerateButton"),
  sceneComparisonInstruction: document.getElementById("sceneComparisonInstruction"),
  sceneBeforePreview: document.getElementById("sceneBeforePreview"),
  sceneAfterPreview: document.getElementById("sceneAfterPreview"),
};

function t(key, params = {}) {
  const dictionary = translations[state.language] || translations.en;
  const template = dictionary[key] || translations.en[key] || key;
  return template.replace(/\{(\w+)\}/g, (_, token) => String(params[token] ?? ""));
}

function applyTranslations() {
  document.documentElement.lang = t("htmlLang");
  els.languageSelect.value = state.language;

  document.querySelectorAll("[data-i18n]").forEach((element) => {
    const key = element.dataset.i18n;
    element.textContent = t(key);
  });
  document.querySelectorAll("[data-i18n-placeholder]").forEach((element) => {
    const key = element.dataset.i18nPlaceholder;
    element.setAttribute("placeholder", t(key));
  });

  renderStaticSelects();
  if (state.projects.length) {
    renderProjects();
    renderProjectSelectOptions(state.selectedProjectId);
  }
  if (!state.selectedVersionPayload) {
    els.workspacePill.textContent = t("workspaceEmpty");
    setElementText(els.scriptPreview, t("scriptPreviewPlaceholder"));
  }
  renderBuildBadge();
  renderSceneComparison(state.lastSceneComparison);
}

function renderStaticSelects() {
  fillSelect(
    els.scriptType,
    scriptTypes,
    (item) => item.value,
    (item) => (state.language === "zh" ? item.zh : item.en),
    els.scriptType.value || "tv_drama",
  );
  fillSelect(
    els.tone,
    toneOptions,
    (item) => item.value,
    (item) => (state.language === "zh" ? item.zh : item.en),
    els.tone.value || "balanced",
  );
}

async function api(path, options = {}) {
  let response;
  try {
    response = await fetch(path, {
      cache: "no-store",
      headers: {
        "Content-Type": "application/json",
        ...(options.headers || {}),
      },
      ...options,
    });
  } catch (error) {
    throw new Error(`${t("genericNetworkError")} ${error.message || ""}`.trim());
  }

  let payload;
  try {
    payload = await response.json();
  } catch (error) {
    throw new Error(`${t("genericNetworkError")} ${error.message || ""}`.trim());
  }

  if (!response.ok || !payload.ok) {
    throw new Error(payload.error || `Request failed: ${response.status}`);
  }
  return payload.data;
}

function setStatus(message) {
  els.statusText.textContent = message;
}

function setBanner(message, kind = "info") {
  if (!message) {
    els.messageBanner.textContent = "";
    els.messageBanner.className = "message-banner hidden";
    return;
  }
  els.messageBanner.textContent = message;
  els.messageBanner.className = `message-banner ${kind}`;
}

function stopElementStream(element) {
  const renderer = streamRenderers.get(element);
  if (renderer?.timer) {
    window.clearInterval(renderer.timer);
  }
  if (renderer) {
    renderer.timer = null;
  }
}

function setElementText(element, text) {
  stopElementStream(element);
  element.textContent = text;
}

function commonPrefixLength(left, right) {
  const limit = Math.min(left.length, right.length);
  let index = 0;
  while (index < limit && left[index] === right[index]) {
    index += 1;
  }
  return index;
}

function streamTextToElement(element, targetText) {
  const currentText = element.textContent || "";
  const prefixLength = commonPrefixLength(currentText, targetText);
  if (prefixLength < currentText.length) {
    setElementText(element, currentText.slice(0, prefixLength));
  }

  const renderer = streamRenderers.get(element) || { timer: null, revision: 0 };
  renderer.revision += 1;
  const revision = renderer.revision;
  stopElementStream(element);

  let cursor = prefixLength;
  if (cursor >= targetText.length) {
    streamRenderers.set(element, renderer);
    return;
  }

  renderer.timer = window.setInterval(() => {
    const active = streamRenderers.get(element);
    if (!active || active.revision !== revision) {
      window.clearInterval(renderer.timer);
      return;
    }

    const nextChar = targetText[cursor] || "";
    const chunkSize = nextChar === "\n"
      ? 1
      : Math.max(
          STREAM_MIN_CHUNK,
          Math.min(STREAM_MAX_CHUNK, Math.ceil((targetText.length - cursor) / 120)),
        );
    cursor = Math.min(targetText.length, cursor + chunkSize);
    element.textContent = targetText.slice(0, cursor);

    if (cursor >= targetText.length) {
      window.clearInterval(renderer.timer);
      renderer.timer = null;
    }
  }, STREAM_FRAME_MS);

  streamRenderers.set(element, renderer);
}

function stopTaskMonitor() {
  if (state.activeTaskStream) {
    state.activeTaskStream.close();
    state.activeTaskStream = null;
  }
}

function renderBuildBadge() {
  if (!els.buildBadge) {
    return;
  }
  if (!state.health) {
    els.buildBadge.textContent = "server unknown";
    return;
  }
  const startedAt = String(state.health.server_started_at || "").replace("T", " ").replace("+00:00", " UTC");
  els.buildBadge.textContent = t("buildBadgeLabel", {
    version: state.health.version || "?",
    startedAt: startedAt || "?",
  });
}

function renderProjects() {
  els.projectsList.innerHTML = "";
  if (!state.projects.length) {
    els.projectsList.innerHTML = `<div class="project-card">${escapeHtml(t("noProjectsCard"))}</div>`;
    return;
  }
  state.projects.forEach((project) => {
    const card = document.createElement("section");
    card.className = `project-card ${project.project_id === state.selectedProjectId ? "active" : ""}`;
    const versionsHtml = (project.versions || []).map((version) => `
      <div class="project-version-row">
        <button type="button" class="project-version-button" data-project-id="${escapeHtml(project.project_id)}" data-version-id="${escapeHtml(version.version_id)}">
          ${escapeHtml(version.version_id)}
        </button>
        <button type="button" class="project-version-delete" data-project-id="${escapeHtml(project.project_id)}" data-version-id="${escapeHtml(version.version_id)}">
          ${escapeHtml(t("deleteButton"))}
        </button>
      </div>
    `).join("");
    card.innerHTML = `
      <button type="button" class="project-card-main" data-project-id="${escapeHtml(project.project_id)}">
        <strong>${escapeHtml(project.project_id)}</strong>
        <small>${escapeHtml(t("projectLatestLabel", { versionId: project.latest_version || "-" }))}</small>
        <small>${escapeHtml(t("projectVersionCountLabel", { count: project.versions.length }))}</small>
      </button>
      <div class="project-versions">
        ${versionsHtml}
      </div>
    `;
    card.querySelector(".project-card-main")?.addEventListener("click", () => {
      selectProject(project.project_id).catch(handleError);
    });
    card.querySelectorAll(".project-version-button").forEach((button) => {
      button.addEventListener("click", (event) => {
        const target = event.currentTarget;
        const versionId = target?.dataset?.versionId || "";
        if (!versionId) {
          return;
        }
        loadVersion(project.project_id, versionId).catch(handleError);
      });
    });
    card.querySelectorAll(".project-version-delete").forEach((button) => {
      button.addEventListener("click", (event) => {
        const target = event.currentTarget;
        const versionId = target?.dataset?.versionId || "";
        if (!versionId) {
          return;
        }
        deleteVersion(project.project_id, versionId).catch(handleError);
      });
    });
    els.projectsList.appendChild(card);
  });
}

function fillSelect(select, items, getValue, getLabel, selectedValue = "") {
  select.innerHTML = "";
  items.forEach((item) => {
    const option = document.createElement("option");
    option.value = getValue(item);
    option.textContent = getLabel(item);
    if (option.value === selectedValue) {
      option.selected = true;
    }
    select.appendChild(option);
  });
}

function renderProjectSelectOptions(selectedValue = "") {
  els.projectSelect.innerHTML = "";

  const placeholder = document.createElement("option");
  placeholder.value = "";
  placeholder.textContent = t("selectProjectPlaceholder");
  placeholder.selected = !selectedValue;
  els.projectSelect.appendChild(placeholder);

  state.projects.forEach((project) => {
    const option = document.createElement("option");
    option.value = project.project_id;
    option.textContent = project.project_id;
    if (option.value === selectedValue) {
      option.selected = true;
    }
    els.projectSelect.appendChild(option);
  });
}

function resetProjectSelection() {
  state.selectedProjectId = "";
  state.selectedVersionId = "";
  state.selectedVersionPayload = null;
  state.lastSceneComparison = null;
  state.lastRegeneratedProjectId = "";
  state.lastRegeneratedVersionId = "";
  els.projectSelect.value = "";
  els.versionSelect.innerHTML = "";
  els.sceneSelect.innerHTML = "";
  els.workspacePill.textContent = t("workspaceEmpty");
  setElementText(els.scriptPreview, t("scriptPreviewPlaceholder"));
  renderSceneComparison(null);
  syncRegeneratedYamlButton();
  renderProjects();
  setBanner("");
  setStatus(t("selectionResetStatus"));
}

function resetFormAndWorkspace() {
  stopTaskMonitor();
  state.activeTaskId = "";
  state.activeTaskKind = "";
  state.upload = { name: "", base64: "" };
  state.yamlUpload = { name: "", base64: "" };
  state.projects = [];

  els.apiKey.value = "";
  els.uploadFile.value = "";
  els.uploadYamlFile.value = "";
  els.title.value = "";
  els.author.value = "";
  els.originalTitle.value = "";
  els.genre.value = "";
  els.novelText.value = "";

  renderStaticSelects();
  els.scriptType.value = "tv_drama";
  els.tone.value = "balanced";
  els.projectsList.innerHTML = "";
  renderProjectSelectOptions("");

  resetProjectSelection();
}

async function loadProjects(preferredProjectId = "") {
  setStatus(t("refreshingProjectsStatus"));
  setBanner("");
  const data = await api("/api/projects");
  state.projects = data.projects;
  renderProjects();

  const projectIds = state.projects.map((project) => project.project_id);
  const nextProjectId =
    preferredProjectId ||
    (projectIds.includes(state.selectedProjectId) ? state.selectedProjectId : "");

  renderProjectSelectOptions(nextProjectId);

  if (nextProjectId) {
    await selectProject(nextProjectId);
  } else {
    resetProjectSelection();
    setStatus(state.projects.length ? t("selectProjectStatus") : t("noProjectsFoundStatus"));
  }
}

async function selectProject(projectId, preferredVersionId = "") {
  if (!projectId) {
    resetProjectSelection();
    return;
  }
  state.selectedProjectId = projectId;
  renderProjects();
  els.projectSelect.value = projectId;
  setStatus(t("loadingVersionsStatus", { projectId }));
  const data = await api(`/api/projects/${encodeURIComponent(projectId)}/versions`);
  const versions = data.versions;

  fillSelect(
    els.versionSelect,
    versions,
    (version) => version.version_id,
    (version) => t("versionOptionLabel", { versionId: version.version_id }),
    preferredVersionId || versions.at(-1)?.version_id || "",
  );

  const nextVersionId = preferredVersionId || versions.at(-1)?.version_id;
  if (nextVersionId) {
    await loadVersion(projectId, nextVersionId);
  } else {
    setStatus(t("noVersionsStatus", { projectId }));
  }
}

async function loadVersion(projectId, versionId) {
  if (!projectId || !versionId) {
    return;
  }
  state.lastSceneComparison = null;
  renderSceneComparison(null);
  setStatus(t("loadingVersionStatus", { projectId, versionId }));
  setBanner("");
  state.selectedProjectId = projectId;
  state.selectedVersionId = versionId;
  els.projectSelect.value = projectId;
  els.versionSelect.value = versionId;

  const data = await api(`/api/projects/${encodeURIComponent(projectId)}/versions/${encodeURIComponent(versionId)}`);
  state.selectedVersionPayload = data;

  els.workspacePill.textContent = `${projectId} · ${versionId}`;
  setElementText(els.scriptPreview, data.rendered_script || t("scriptPreviewPlaceholder"));
  renderSceneOptions(data.scene_options);
  setStatus(t("loadedVersionStatus", { projectId, versionId }));
}

async function deleteVersion(projectId, versionId) {
  setStatus(t("deletingVersionStatus", { projectId, versionId }));
  setBanner("");
  const deleted = await api(
    `/api/projects/${encodeURIComponent(projectId)}/versions/${encodeURIComponent(versionId)}/delete`,
    { method: "DELETE" },
  );

  const deletedSelectedVersion = state.selectedProjectId === projectId && state.selectedVersionId === versionId;
  const deletingSelectedProject = state.selectedProjectId === projectId;
  const nextProjectId = deleted.project_exists && deletingSelectedProject ? projectId : state.selectedProjectId;

  await loadProjects(nextProjectId);

  if (!deleted.project_exists && deletingSelectedProject) {
    resetProjectSelection();
  } else if (deletedSelectedVersion && projectId === state.selectedProjectId && !state.selectedVersionId) {
    await selectProject(projectId);
  }

  setBanner(t("deletedVersionStatus", { projectId, versionId }), "info");
  setStatus(t("deletedVersionStatus", { projectId, versionId }));
}

function renderSceneOptions(sceneOptions) {
  els.sceneSelect.innerHTML = "";
  sceneOptions.forEach((scene) => {
    const option = document.createElement("option");
    option.value = scene.scene_id;
    option.textContent = scene.label;
    els.sceneSelect.appendChild(option);
  });
}

function resolveSceneComparisonInstruction(comparison = null) {
  const draftInstruction = els.regenInstruction.value.trim();
  if (draftInstruction) {
    return draftInstruction;
  }
  if (comparison?.instruction) {
    return comparison.instruction;
  }
  if (comparison?.scene_id) {
    return comparison.scene_id;
  }
  return t("comparisonPlaceholder");
}

function syncSceneComparisonInstruction(comparison = state.lastSceneComparison) {
  setElementText(els.sceneComparisonInstruction, resolveSceneComparisonInstruction(comparison));
}

function renderSceneComparison(comparison, options = {}) {
  if (!comparison) {
    const placeholder = t("comparisonPlaceholder");
    syncSceneComparisonInstruction(null);
    setElementText(els.sceneBeforePreview, placeholder);
    setElementText(els.sceneAfterPreview, placeholder);
    return;
  }

  syncSceneComparisonInstruction(comparison);
  setElementText(els.sceneBeforePreview, comparison.before?.rendered || "");
  if (options.streamAfter) {
    if (options.directStream) {
      setElementText(els.sceneAfterPreview, comparison.after?.rendered || "");
      return;
    }
    streamTextToElement(els.sceneAfterPreview, comparison.after?.rendered || "");
    return;
  }
  setElementText(els.sceneAfterPreview, comparison.after?.rendered || "");
}

function syncRegeneratedYamlButton() {
  if (!els.downloadRegeneratedYamlButton) {
    return;
  }
  els.downloadRegeneratedYamlButton.disabled = !state.lastRegeneratedProjectId || !state.lastRegeneratedVersionId;
}

async function generateDraft() {
  if (!els.apiKey.value.trim()) {
    throw new Error(t("apiKeyRequired"));
  }
  if (!state.upload.base64 && !els.novelText.value.trim()) {
    throw new Error(t("inputRequired"));
  }
  setStatus(t("generatingDraftStatus"));
  setBanner(t("qwenGenerationPending"), "info");
  const data = await api("/api/adapt-async", {
    method: "POST",
    body: JSON.stringify({
      api_key: els.apiKey.value.trim(),
      provider: "qwen",
      title: els.title.value,
      original_author: els.author.value,
      original_title: els.originalTitle.value,
      script_type: els.scriptType.value,
      genre: els.genre.value,
      tone: els.tone.value,
      novel_text: els.novelText.value,
      upload_name: state.upload.name,
      upload_base64: state.upload.base64,
    }),
  });
  const preview = data.preview;
  state.activeTaskId = data.task.task_id;
  state.activeTaskKind = data.task.kind;
  setElementText(els.scriptPreview, "");
  state.lastSceneComparison = null;
  state.lastRegeneratedProjectId = "";
  state.lastRegeneratedVersionId = "";
  renderSceneComparison(null);
  syncRegeneratedYamlButton();
  els.workspacePill.textContent = t("workspaceEmpty");
  monitorTask(data.task.task_id, preview.project_id);
}

async function regenerateDraftFromYaml() {
  if (!els.apiKey.value.trim()) {
    throw new Error(t("apiKeyRequired"));
  }
  if (!state.yamlUpload.base64) {
    throw new Error(t("yamlFileRequired"));
  }
  setStatus(t("regeneratingFromYamlStatus"));
  setBanner(t("yamlRegenerationPending"), "info");
  const data = await api("/api/regenerate-from-yaml-async", {
    method: "POST",
    body: JSON.stringify({
      api_key: els.apiKey.value.trim(),
      provider: "qwen",
      title: els.title.value,
      original_author: els.author.value,
      original_title: els.originalTitle.value,
      script_type: els.scriptType.value,
      genre: els.genre.value,
      tone: els.tone.value,
      upload_base64: state.yamlUpload.base64,
    }),
  });
  const preview = data.preview;
  state.activeTaskId = data.task.task_id;
  state.activeTaskKind = data.task.kind;
  setElementText(els.scriptPreview, "");
  state.lastSceneComparison = null;
  state.lastRegeneratedProjectId = "";
  state.lastRegeneratedVersionId = "";
  renderSceneComparison(null);
  syncRegeneratedYamlButton();
  els.workspacePill.textContent = t("workspaceEmpty");
  monitorTask(data.task.task_id, preview.project_id);
}

async function regenerateScene() {
  if (!state.selectedProjectId || !state.selectedVersionId) {
    throw new Error(t("selectVersionBeforeRegenerate"));
  }
  if (!els.apiKey.value.trim()) {
    throw new Error(t("apiKeyRequired"));
  }
  const sceneId = els.sceneSelect.value;
  const instruction = els.regenInstruction.value.trim();
  setStatus(t("regeneratingSceneStatus", { sceneId }));
  setBanner(t("qwenRegenerationPending"), "info");
  const data = await api(
    `/api/projects/${encodeURIComponent(state.selectedProjectId)}/versions/${encodeURIComponent(state.selectedVersionId)}/regenerate-scene-async`,
    {
      method: "POST",
      body: JSON.stringify({
        scene_id: sceneId,
        instruction,
        provider: "qwen",
        api_key: els.apiKey.value.trim(),
        tone: els.tone.value,
      }),
    },
  );
  const preview = data.preview;
  state.activeTaskId = data.task.task_id;
  state.activeTaskKind = data.task.kind;
  state.lastSceneComparison = preview?.scene_comparison || null;
  state.lastRegeneratedProjectId = "";
  state.lastRegeneratedVersionId = "";
  syncRegeneratedYamlButton();
  renderSceneComparison(state.lastSceneComparison);
  monitorTask(data.task.task_id, state.selectedProjectId);
}

async function loadHealth() {
  state.health = await api("/api/health");
  renderBuildBadge();
}

function renderStreamingTask(task) {
  const result = task.result;
  if (!result) {
    return;
  }
  const isModelChunkStream = result.stream_source === "model_chunk";
  if (result.rendered_script) {
    if (isModelChunkStream) {
      setElementText(els.scriptPreview, result.rendered_script);
    } else {
      streamTextToElement(els.scriptPreview, result.rendered_script);
    }
    if (result.project_id && result.version?.version_id) {
      els.workspacePill.textContent = `${result.project_id} · ${result.version.version_id}`;
    }
  }
  if (typeof result.completed_scenes === "number" && typeof result.total_scenes === "number" && result.total_scenes > 0) {
    const sceneLabel = result.active_scene_id ? ` ${result.active_scene_id}` : "";
    setStatus(`Qwen streaming${sceneLabel} ${result.completed_scenes}/${result.total_scenes}`);
  }
  if (result.scene_comparison) {
    state.lastSceneComparison = result.scene_comparison;
    renderSceneComparison(result.scene_comparison, {
      streamAfter: task.kind === "regenerate_scene",
      directStream: isModelChunkStream,
    });
  }
}

async function finalizeTask(task, projectId) {
  const result = task.result;
  if (!result) {
    return;
  }
  state.activeTaskId = "";
  stopTaskMonitor();
  await loadProjects(projectId || result.project_id);
  await loadVersion(result.project_id, result.version.version_id);
  if (result.scene_comparison) {
    state.lastSceneComparison = result.scene_comparison;
    renderSceneComparison(state.lastSceneComparison);
  }
  setBanner(t("qwenFinalReady", { projectId: result.project_id, versionId: result.version.version_id }), "info");
  if (task.kind === "regenerate_scene") {
    state.lastRegeneratedProjectId = result.project_id;
    state.lastRegeneratedVersionId = result.version.version_id;
    syncRegeneratedYamlButton();
    setStatus(t("regeneratedSceneStatus", { versionId: result.version.version_id }));
    return;
  }
  setStatus(t("generatedDraftStatus", { projectId: result.project_id, versionId: result.version.version_id }));
}

function handleTaskFailure(task) {
  state.activeTaskId = "";
  stopTaskMonitor();
  setBanner(t("backgroundTaskFailed", { error: task.error || t("unknownError") }), "error");
  setStatus(task.error || t("unknownError"));
}

async function consumeTaskUpdate(task, projectId) {
  if (task.result?.mode === "streaming") {
    renderStreamingTask(task);
  }
  if (task.status === "completed") {
    await finalizeTask(task, projectId);
    return;
  }
  if (task.status === "failed") {
    handleTaskFailure(task);
  }
}

async function monitorTaskByPolling(taskId, projectId) {
  for (;;) {
    if (state.activeTaskId !== taskId) {
      return;
    }
    const task = await api(`/api/tasks/${encodeURIComponent(taskId)}`);
    if (state.activeTaskId !== taskId) {
      return;
    }
    await consumeTaskUpdate(task, projectId);
    if (task.status === "completed" || task.status === "failed") {
      return;
    }
    await new Promise((resolve) => setTimeout(resolve, 1500));
  }
}

function monitorTask(taskId, projectId) {
  state.activeTaskId = taskId;
  stopTaskMonitor();
  if (typeof window.EventSource !== "function") {
    monitorTaskByPolling(taskId, projectId).catch(handleError);
    return;
  }

  const stream = new EventSource(`/api/tasks/${encodeURIComponent(taskId)}/stream`);
  state.activeTaskStream = stream;
  stream.addEventListener("task", (event) => {
    if (state.activeTaskId !== taskId) {
      return;
    }
    const task = JSON.parse(event.data);
    consumeTaskUpdate(task, projectId).catch(handleError);
  });
  stream.onerror = () => {
    if (state.activeTaskId !== taskId) {
      return;
    }
    stopTaskMonitor();
    monitorTaskByPolling(taskId, projectId).catch(handleError);
  };
}

async function downloadVersionYaml(projectId, versionId) {
  if (!projectId || !versionId) {
    return;
  }
  const latest = await api(
    `/api/projects/${encodeURIComponent(projectId)}/versions/${encodeURIComponent(versionId)}/export-yaml`,
  );
  const yamlText = latest.yaml_text || "";
  const blob = new Blob([yamlText], { type: "text/yaml;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = t("downloadYamlFilename", {
    projectId: latest.project_id,
    versionId: latest.version_id,
  });
  anchor.click();
  URL.revokeObjectURL(url);
}

async function downloadYaml() {
  if (!state.selectedVersionPayload) {
    return;
  }
  await downloadVersionYaml(state.selectedProjectId, state.selectedVersionId);
}

async function downloadRegeneratedYaml() {
  if (!state.lastRegeneratedProjectId || !state.lastRegeneratedVersionId) {
    return;
  }
  await downloadVersionYaml(state.lastRegeneratedProjectId, state.lastRegeneratedVersionId);
}

async function handleFileUpload(file) {
  if (!file) {
    state.upload = { name: "", base64: "" };
    return;
  }
  state.upload.name = file.name;
  state.upload.base64 = await readFileAsBase64(file);
}

async function handleYamlUpload(file) {
  if (!file) {
    state.yamlUpload = { name: "", base64: "" };
    return;
  }
  state.yamlUpload.name = file.name;
  state.yamlUpload.base64 = await readFileAsBase64(file);
}

function readFileAsBase64(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => {
      const result = String(reader.result || "");
      const base64 = result.includes(",") ? result.split(",")[1] : result;
      resolve(base64);
    };
    reader.onerror = () => reject(new Error("Failed to read the selected file."));
    reader.readAsDataURL(file);
  });
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;");
}

function registerEvents() {
  els.languageSelect.addEventListener("change", () => {
    state.language = els.languageSelect.value;
    localStorage.setItem("workbench.language", state.language);
    applyTranslations();
  });
  els.resetProjectsButton.addEventListener("click", () => {
    resetFormAndWorkspace();
  });
  els.refreshProjectsButton.addEventListener("click", () => {
    loadProjects().catch(handleError);
  });
  els.uploadFile.addEventListener("change", async () => {
    try {
      const [file] = els.uploadFile.files;
      await handleFileUpload(file);
    } catch (error) {
      handleError(error);
    }
  });
  els.uploadYamlFile.addEventListener("change", async () => {
    try {
      const [file] = els.uploadYamlFile.files;
      await handleYamlUpload(file);
    } catch (error) {
      handleError(error);
    }
  });
  els.generateButton.addEventListener("click", () => {
    generateDraft().catch(handleError);
  });
  els.regenerateFromYamlButton.addEventListener("click", () => {
    regenerateDraftFromYaml().catch(handleError);
  });
  els.projectSelect.addEventListener("change", () => {
    selectProject(els.projectSelect.value).catch(handleError);
  });
  els.versionSelect.addEventListener("change", () => {
    loadVersion(state.selectedProjectId, els.versionSelect.value).catch(handleError);
  });
  els.reloadVersionButton.addEventListener("click", () => {
    loadVersion(state.selectedProjectId, state.selectedVersionId).catch(handleError);
  });
  els.downloadYamlButton.addEventListener("click", () => {
    downloadYaml().catch(handleError);
  });
  if (els.downloadRegeneratedYamlButton) {
    els.downloadRegeneratedYamlButton.addEventListener("click", () => {
      downloadRegeneratedYaml().catch(handleError);
    });
  }
  els.regenInstruction.addEventListener("input", () => {
    syncSceneComparisonInstruction();
  });
  els.regenerateButton.addEventListener("click", () => {
    regenerateScene().catch(handleError);
  });
}

function handleError(error) {
  console.error(error);
  const message = error.message || t("unknownError");
  setStatus(message);
  setBanner(message, "error");
}

applyTranslations();
syncRegeneratedYamlButton();
registerEvents();
Promise.all([loadHealth(), loadProjects()]).catch(handleError);
