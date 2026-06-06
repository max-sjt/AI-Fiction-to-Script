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
    refreshButton: "刷新",
    noProjectsCard: "还没有项目。先生成一版剧本即可开始。",
    generateHeading: "生成剧本",
    qwenPill: "Qwen 生成",
    apiKeyLabel: "Qwen API Key",
    apiKeyPlaceholder: "请输入 sk-...",
    uploadLabel: "上传小说文件（txt / doc / docx）",
    titleLabel: "剧本标题",
    titlePlaceholder: "老街回声",
    authorLabel: "原著作者",
    authorPlaceholder: "测试作者",
    originalTitleLabel: "原著标题",
    originalTitlePlaceholder: "老街回声",
    scriptTypeLabel: "生成剧本类型",
    genreLabel: "题材",
    genrePlaceholder: "悬疑,成长",
    toneLabel: "语气风格",
    pasteTextLabel: "直接粘贴小说文本",
    novelTextPlaceholder: "如果不上传文件，可以在这里粘贴一章或多章小说正文；多章生成会更稳定。",
    generateButton: "生成剧本",
    workspaceHeading: "工作区",
    workspaceEmpty: "尚未选择项目",
    currentProjectLabel: "当前项目",
    currentVersionLabel: "当前版本",
    reloadButton: "重新加载",
    downloadYamlButton: "下载 YAML",
    finalScriptHeading: "最终生成剧本",
    scriptPreviewPlaceholder: "请选择一个版本查看生成结果。",
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
    loadingVersionsStatus: "正在加载 {projectId} 的版本...",
    noVersionsStatus: "项目 {projectId} 还没有保存版本。",
    loadingVersionStatus: "正在加载 {projectId}/{versionId}...",
    loadedVersionStatus: "已加载 {projectId}/{versionId}",
    generatingDraftStatus: "正在调用 Qwen 生成剧本...",
    generatedDraftStatus: "已生成 {projectId}/{versionId}",
    qwenGenerationPending: "Qwen 正在以极速草稿模式生成，单章通常会快很多；只有在整条流程完成后，工作区才会切换到新版本。",
    qwenRegenerationPending: "Qwen 正在以极速模式重生成场景；完成前工作区不会更新。",
    apiKeyRequired: "请输入 Qwen API Key。",
    inputRequired: "请上传小说文件，或直接粘贴小说文本。",
    selectVersionBeforeRegenerate: "请先选择一个项目版本再重生成场景。",
    regeneratingSceneStatus: "正在重生成 {sceneId}...",
    regeneratedSceneStatus: "已生成新版本 {versionId}",
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
    refreshButton: "Refresh",
    noProjectsCard: "No projects yet. Generate a screenplay to begin.",
    generateHeading: "Generate Screenplay",
    qwenPill: "Qwen Generation",
    apiKeyLabel: "Qwen API Key",
    apiKeyPlaceholder: "Enter sk-...",
    uploadLabel: "Upload novel file (txt / doc / docx)",
    titleLabel: "Screenplay title",
    titlePlaceholder: "Old Street Echo",
    authorLabel: "Original author",
    authorPlaceholder: "Demo Author",
    originalTitleLabel: "Original title",
    originalTitlePlaceholder: "Old Street Echo",
    scriptTypeLabel: "Screenplay type",
    genreLabel: "Genre",
    genrePlaceholder: "mystery,growth",
    toneLabel: "Tone style",
    pasteTextLabel: "Paste novel text directly",
    novelTextPlaceholder: "If you do not upload a file, paste one or more chapters of source text here. More chapters usually produce better results.",
    generateButton: "Generate Screenplay",
    workspaceHeading: "Workspace",
    workspaceEmpty: "No project selected",
    currentProjectLabel: "Current project",
    currentVersionLabel: "Current version",
    reloadButton: "Reload",
    downloadYamlButton: "Download YAML",
    finalScriptHeading: "Final screenplay",
    scriptPreviewPlaceholder: "Select a version to view the generated screenplay.",
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
    loadingVersionsStatus: "Loading versions for {projectId}...",
    noVersionsStatus: "Project {projectId} has no saved versions.",
    loadingVersionStatus: "Loading {projectId}/{versionId}...",
    loadedVersionStatus: "Loaded {projectId}/{versionId}",
    generatingDraftStatus: "Generating screenplay with Qwen...",
    generatedDraftStatus: "Generated {projectId}/{versionId}",
    qwenGenerationPending: "Qwen is generating in fast-draft mode. Single-chapter drafts should complete much faster, but the workspace updates only after the full pipeline finishes.",
    qwenRegenerationPending: "Qwen is regenerating the scene in fast mode. The workspace will not update until it finishes.",
    apiKeyRequired: "Enter a Qwen API key first.",
    inputRequired: "Upload a novel file or paste novel text first.",
    selectVersionBeforeRegenerate: "Select a project version before regenerating a scene.",
    regeneratingSceneStatus: "Regenerating {sceneId}...",
    regeneratedSceneStatus: "Generated new version {versionId}",
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
  health: null,
};

const els = {
  languageSelect: document.getElementById("languageSelect"),
  statusText: document.getElementById("statusText"),
  buildBadge: document.getElementById("buildBadge"),
  messageBanner: document.getElementById("messageBanner"),
  workspacePill: document.getElementById("workspacePill"),
  projectsList: document.getElementById("projectsList"),
  refreshProjectsButton: document.getElementById("refreshProjectsButton"),
  apiKey: document.getElementById("apiKey"),
  uploadFile: document.getElementById("uploadFile"),
  title: document.getElementById("title"),
  author: document.getElementById("author"),
  originalTitle: document.getElementById("originalTitle"),
  scriptType: document.getElementById("scriptType"),
  genre: document.getElementById("genre"),
  tone: document.getElementById("tone"),
  novelText: document.getElementById("novelText"),
  generateButton: document.getElementById("generateButton"),
  projectSelect: document.getElementById("projectSelect"),
  versionSelect: document.getElementById("versionSelect"),
  reloadVersionButton: document.getElementById("reloadVersionButton"),
  downloadYamlButton: document.getElementById("downloadYamlButton"),
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
  }
  if (!state.selectedVersionPayload) {
    els.workspacePill.textContent = t("workspaceEmpty");
    els.scriptPreview.textContent = t("scriptPreviewPlaceholder");
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

function renderBuildBadge() {
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
    const card = document.createElement("button");
    card.type = "button";
    card.className = `project-card ${project.project_id === state.selectedProjectId ? "active" : ""}`;
    card.innerHTML = `
      <strong>${escapeHtml(project.project_id)}</strong>
      <small>${escapeHtml(t("projectLatestLabel", { versionId: project.latest_version || "-" }))}</small>
      <small>${escapeHtml(t("projectVersionCountLabel", { count: project.versions.length }))}</small>
    `;
    card.addEventListener("click", () => {
      selectProject(project.project_id).catch(handleError);
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

async function loadProjects(preferredProjectId = "") {
  setStatus(t("refreshingProjectsStatus"));
  setBanner("");
  const data = await api("/api/projects");
  state.projects = data.projects;
  renderProjects();

  const projectIds = state.projects.map((project) => project.project_id);
  const nextProjectId =
    preferredProjectId ||
    (projectIds.includes(state.selectedProjectId) ? state.selectedProjectId : projectIds[0] || "");

  fillSelect(
    els.projectSelect,
    state.projects,
    (project) => project.project_id,
    (project) => project.project_id,
    nextProjectId,
  );

  if (nextProjectId) {
    await selectProject(nextProjectId);
  } else {
    els.versionSelect.innerHTML = "";
    els.sceneSelect.innerHTML = "";
    els.scriptPreview.textContent = t("scriptPreviewPlaceholder");
    state.lastSceneComparison = null;
    renderSceneComparison(null);
    els.workspacePill.textContent = t("workspaceEmpty");
    setStatus(t("noProjectsFoundStatus"));
  }
}

async function selectProject(projectId, preferredVersionId = "") {
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
  els.scriptPreview.textContent = data.rendered_script || t("scriptPreviewPlaceholder");
  renderSceneOptions(data.scene_options);
  setStatus(t("loadedVersionStatus", { projectId, versionId }));
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

function renderSceneComparison(comparison) {
  if (!comparison) {
    const placeholder = t("comparisonPlaceholder");
    els.sceneComparisonInstruction.textContent = placeholder;
    els.sceneBeforePreview.textContent = placeholder;
    els.sceneAfterPreview.textContent = placeholder;
    return;
  }

  els.sceneComparisonInstruction.textContent = comparison.instruction || comparison.scene_id || "";
  els.sceneBeforePreview.textContent = comparison.before?.rendered || "";
  els.sceneAfterPreview.textContent = comparison.after?.rendered || "";
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
  const data = await api("/api/adapt", {
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
  await loadProjects(data.project_id);
  await loadVersion(data.project_id, data.version.version_id);
  setBanner(t("generatedDraftStatus", { projectId: data.project_id, versionId: data.version.version_id }), "info");
  setStatus(t("generatedDraftStatus", { projectId: data.project_id, versionId: data.version.version_id }));
}

async function regenerateScene() {
  if (!state.selectedProjectId || !state.selectedVersionId) {
    throw new Error(t("selectVersionBeforeRegenerate"));
  }
  if (!els.apiKey.value.trim()) {
    throw new Error(t("apiKeyRequired"));
  }
  const sceneId = els.sceneSelect.value;
  setStatus(t("regeneratingSceneStatus", { sceneId }));
  setBanner(t("qwenRegenerationPending"), "info");
  const data = await api(
    `/api/projects/${encodeURIComponent(state.selectedProjectId)}/versions/${encodeURIComponent(state.selectedVersionId)}/regenerate-scene`,
    {
      method: "POST",
      body: JSON.stringify({
        scene_id: sceneId,
        instruction: els.regenInstruction.value,
        provider: "qwen",
        api_key: els.apiKey.value.trim(),
        tone: els.tone.value,
      }),
    },
  );
  els.regenInstruction.value = "";
  await loadProjects(state.selectedProjectId);
  await loadVersion(state.selectedProjectId, data.version.version_id);
  state.lastSceneComparison = data.scene_comparison || null;
  renderSceneComparison(state.lastSceneComparison);
  setBanner(t("regeneratedSceneStatus", { versionId: data.version.version_id }), "info");
  setStatus(t("regeneratedSceneStatus", { versionId: data.version.version_id }));
}

async function loadHealth() {
  state.health = await api("/api/health");
  renderBuildBadge();
}

function downloadYaml() {
  if (!state.selectedVersionPayload) {
    return;
  }
  const yamlText = state.selectedVersionPayload.yaml_text || "";
  const blob = new Blob([yamlText], { type: "text/yaml;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = t("downloadYamlFilename", {
    projectId: state.selectedVersionPayload.project_id,
    versionId: state.selectedVersionPayload.version.version_id,
  });
  anchor.click();
  URL.revokeObjectURL(url);
}

async function handleFileUpload(file) {
  if (!file) {
    state.upload = { name: "", base64: "" };
    return;
  }
  state.upload.name = file.name;
  state.upload.base64 = await readFileAsBase64(file);
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
  els.generateButton.addEventListener("click", () => {
    generateDraft().catch(handleError);
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
  els.downloadYamlButton.addEventListener("click", downloadYaml);
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
registerEvents();
Promise.all([loadHealth(), loadProjects()]).catch(handleError);
