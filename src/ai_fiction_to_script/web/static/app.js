const translations = {
  zh: {
    htmlLang: "zh-CN",
    heroTitle: "剧本工作台",
    heroCopy: "在一个页面里完成结构化剧本生成、版本浏览、YAML 编辑、差异对比和单场景重生成。",
    languageLabel: "界面语言",
    loadingWorkspace: "正在加载工作区...",
    projectsHeading: "项目",
    refreshButton: "刷新",
    noProjectsCard: "还没有项目。先生成一版剧本即可开始。",
    generateHeading: "生成初稿",
    newVersionPill: "新版本",
    novelFilePathLabel: "小说文件路径",
    inputPathPlaceholder: "examples/sample_novel.txt",
    projectIdLabel: "项目 ID",
    projectIdPlaceholder: "demo-project",
    titleLabel: "剧本标题",
    titlePlaceholder: "老街回声",
    authorLabel: "原著作者",
    authorPlaceholder: "测试作者",
    originalTitleLabel: "原著标题",
    originalTitlePlaceholder: "老街回声",
    providerLabel: "模型供应商",
    targetFormatLabel: "目标格式",
    genreLabel: "题材",
    genrePlaceholder: "悬疑,成长",
    toneLabel: "语气",
    tonePlaceholder: "balanced",
    versionNoteLabel: "版本备注",
    adaptNotePlaceholder: "网页初稿",
    pasteTextLabel: "或直接粘贴小说文本",
    novelTextPlaceholder: "如果不想传文件路径，可以在这里粘贴不少于三章的小说正文。",
    generateButton: "生成剧本初稿",
    workspaceHeading: "工作区",
    workspaceEmpty: "尚未选择项目",
    selectedProjectLabel: "当前项目",
    selectedVersionLabel: "当前版本",
    diffBaseLabel: "对比基线",
    diffTargetLabel: "对比目标",
    yamlEditorHeading: "YAML 编辑器",
    saveNotePlaceholder: "手工编辑备注",
    saveYamlButton: "另存为新版本",
    versionSummaryHeading: "版本摘要",
    reloadButton: "重新加载",
    scenesHeading: "场景",
    diffHeading: "版本差异",
    compareButton: "比较版本",
    diffPlaceholder: "请选择两个版本进行对比。",
    sceneRegenerationHeading: "场景重生成",
    targetedRewritePill: "定向重写",
    sceneLabel: "场景",
    providerOverrideLabel: "覆盖模型供应商",
    keepCurrentOption: "沿用当前版本",
    instructionLabel: "修改要求",
    regenInstructionPlaceholder: "描述这个场景应该怎么改。",
    regenNoteLabel: "版本备注",
    regenNotePlaceholder: "场景重写备注",
    regenerateButton: "重生成场景",
    noProjectSelected: "尚未选择项目",
    noProjectsFoundStatus: "没有发现任何项目。",
    refreshingProjectsStatus: "正在刷新项目列表...",
    loadingVersionsStatus: "正在加载 {projectId} 的版本...",
    noVersionsStatus: "项目 {projectId} 还没有保存版本。",
    loadingVersionStatus: "正在加载 {projectId}/{versionId}...",
    loadedVersionStatus: "已加载 {projectId}/{versionId}",
    comparingVersionsStatus: "正在比较 {versionA} -> {versionB}...",
    comparedVersionsStatus: "已完成 {versionA} 和 {versionB} 的比较",
    noDiff: "没有差异。",
    selectVersionBeforeSave: "请先选择一个项目版本再保存。",
    savingYamlStatus: "正在把编辑后的 YAML 保存为 {projectId} 的新版本...",
    savedVersionStatus: "已保存新版本 {versionId}",
    selectVersionBeforeRegenerate: "请先选择一个项目版本再重生成场景。",
    regeneratingSceneStatus: "正在重生成 {sceneId}...",
    regeneratedSceneStatus: "已生成新版本 {versionId}",
    generatingDraftStatus: "正在生成剧本初稿...",
    generatedDraftStatus: "已生成 {projectId}/{versionId}",
    summaryTitle: "标题",
    summaryTargetFormat: "目标格式",
    summaryConfidence: "置信度",
    summaryScenes: "场景数",
    summaryWarnings: "警告数",
    summaryVersionNote: "版本备注",
    noNote: "无备注",
    versionListCount: "{projectId}（{count} 个版本）",
    projectLatestLabel: "最新版本：{versionId}",
    projectVersionCountLabel: "版本数：{count}",
    versionOptionLabel: "{versionId} · {note}",
    unknownError: "发生了未预期的错误。",
  },
  en: {
    htmlLang: "en",
    heroTitle: "Screenplay Workbench",
    heroCopy:
      "Generate structured screenplay drafts, inspect version history, edit YAML directly, compare revisions, and regenerate individual scenes without leaving one page.",
    languageLabel: "Interface language",
    loadingWorkspace: "Loading workspace...",
    projectsHeading: "Projects",
    refreshButton: "Refresh",
    noProjectsCard: "No projects yet. Generate a draft to begin.",
    generateHeading: "Generate Draft",
    newVersionPill: "New version",
    novelFilePathLabel: "Novel file path",
    inputPathPlaceholder: "examples/sample_novel.txt",
    projectIdLabel: "Project ID",
    projectIdPlaceholder: "demo-project",
    titleLabel: "Title",
    titlePlaceholder: "Old Street Echo",
    authorLabel: "Author",
    authorPlaceholder: "Demo Author",
    originalTitleLabel: "Original title",
    originalTitlePlaceholder: "Old Street Echo",
    providerLabel: "Provider",
    targetFormatLabel: "Target format",
    genreLabel: "Genre",
    genrePlaceholder: "mystery,growth",
    toneLabel: "Tone",
    tonePlaceholder: "balanced",
    versionNoteLabel: "Version note",
    adaptNotePlaceholder: "initial web draft",
    pasteTextLabel: "Or paste novel text",
    novelTextPlaceholder: "Paste 3 or more chapters here if you do not want to use a file path.",
    generateButton: "Generate Draft",
    workspaceHeading: "Workspace",
    workspaceEmpty: "No project selected",
    selectedProjectLabel: "Selected project",
    selectedVersionLabel: "Selected version",
    diffBaseLabel: "Diff base",
    diffTargetLabel: "Diff target",
    yamlEditorHeading: "YAML Editor",
    saveNotePlaceholder: "manual edit note",
    saveYamlButton: "Save As New Version",
    versionSummaryHeading: "Version Summary",
    reloadButton: "Reload",
    scenesHeading: "Scenes",
    diffHeading: "Version Diff",
    compareButton: "Compare Versions",
    diffPlaceholder: "Select two versions to compare.",
    sceneRegenerationHeading: "Scene Regeneration",
    targetedRewritePill: "Targeted rewrite",
    sceneLabel: "Scene",
    providerOverrideLabel: "Provider override",
    keepCurrentOption: "keep current",
    instructionLabel: "Instruction",
    regenInstructionPlaceholder: "Describe what should change in this scene.",
    regenNoteLabel: "Version note",
    regenNotePlaceholder: "scene rewrite note",
    regenerateButton: "Regenerate Scene",
    noProjectSelected: "No project selected",
    noProjectsFoundStatus: "No projects found.",
    refreshingProjectsStatus: "Refreshing projects...",
    loadingVersionsStatus: "Loading versions for {projectId}...",
    noVersionsStatus: "Project {projectId} has no saved versions.",
    loadingVersionStatus: "Loading {projectId}/{versionId}...",
    loadedVersionStatus: "Loaded {projectId}/{versionId}",
    comparingVersionsStatus: "Comparing {versionA} -> {versionB}...",
    comparedVersionsStatus: "Compared {versionA} and {versionB}",
    noDiff: "No diff.",
    selectVersionBeforeSave: "Select a project version before saving.",
    savingYamlStatus: "Saving edited YAML as a new version for {projectId}...",
    savedVersionStatus: "Saved new version {versionId}",
    selectVersionBeforeRegenerate: "Select a project version before regenerating a scene.",
    regeneratingSceneStatus: "Regenerating {sceneId}...",
    regeneratedSceneStatus: "Regenerated scene into {versionId}",
    generatingDraftStatus: "Generating screenplay draft...",
    generatedDraftStatus: "Generated {projectId}/{versionId}",
    summaryTitle: "Title",
    summaryTargetFormat: "Target format",
    summaryConfidence: "Confidence",
    summaryScenes: "Scenes",
    summaryWarnings: "Warnings",
    summaryVersionNote: "Version note",
    noNote: "no note",
    versionListCount: "{projectId} ({count} versions)",
    projectLatestLabel: "Latest: {versionId}",
    projectVersionCountLabel: "Versions: {count}",
    versionOptionLabel: "{versionId} · {note}",
    unknownError: "An unexpected error occurred.",
  },
};

const state = {
  projects: [],
  selectedProjectId: "",
  selectedVersionId: "",
  selectedVersionPayload: null,
  language: localStorage.getItem("workbench.language") || "zh",
};

const els = {
  languageSelect: document.getElementById("languageSelect"),
  statusText: document.getElementById("statusText"),
  workspacePill: document.getElementById("workspacePill"),
  projectsList: document.getElementById("projectsList"),
  refreshProjectsButton: document.getElementById("refreshProjectsButton"),
  projectSelect: document.getElementById("projectSelect"),
  versionSelect: document.getElementById("versionSelect"),
  diffFromSelect: document.getElementById("diffFromSelect"),
  diffToSelect: document.getElementById("diffToSelect"),
  compareButton: document.getElementById("compareButton"),
  diffOutput: document.getElementById("diffOutput"),
  yamlEditor: document.getElementById("yamlEditor"),
  summaryCards: document.getElementById("summaryCards"),
  sceneChipList: document.getElementById("sceneChipList"),
  sceneSelect: document.getElementById("sceneSelect"),
  regenInstruction: document.getElementById("regenInstruction"),
  regenProvider: document.getElementById("regenProvider"),
  regenNote: document.getElementById("regenNote"),
  regenerateButton: document.getElementById("regenerateButton"),
  saveYamlButton: document.getElementById("saveYamlButton"),
  saveNote: document.getElementById("saveNote"),
  reloadVersionButton: document.getElementById("reloadVersionButton"),
  generateButton: document.getElementById("generateButton"),
  inputPath: document.getElementById("inputPath"),
  projectId: document.getElementById("projectId"),
  title: document.getElementById("title"),
  author: document.getElementById("author"),
  originalTitle: document.getElementById("originalTitle"),
  provider: document.getElementById("provider"),
  targetFormat: document.getElementById("targetFormat"),
  genre: document.getElementById("genre"),
  tone: document.getElementById("tone"),
  adaptNote: document.getElementById("adaptNote"),
  novelText: document.getElementById("novelText"),
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

  const keepCurrentOption = els.regenProvider.querySelector('option[value=""]');
  if (keepCurrentOption) {
    keepCurrentOption.textContent = t("keepCurrentOption");
  }

  if (state.projects.length) {
    renderProjects();
  }
  if (state.selectedVersionPayload) {
    renderSummary(state.selectedVersionPayload);
    renderSceneOptions(state.selectedVersionPayload.scene_options || []);
    if (!els.diffOutput.dataset.dynamic) {
      els.diffOutput.textContent = t("diffPlaceholder");
    }
  } else {
    els.workspacePill.textContent = t("workspaceEmpty");
  }
}

async function api(path, options = {}) {
  const response = await fetch(path, {
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
    ...options,
  });
  const payload = await response.json();
  if (!response.ok || !payload.ok) {
    throw new Error(payload.error || `Request failed: ${response.status}`);
  }
  return payload.data;
}

function setStatus(message) {
  els.statusText.textContent = message;
}

function renderProjects() {
  els.projectsList.innerHTML = "";
  if (!state.projects.length) {
    els.projectsList.innerHTML = `<div class="summary-card">${escapeHtml(t("noProjectsCard"))}</div>`;
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
    (project) => t("versionListCount", { projectId: project.project_id, count: project.versions.length }),
    nextProjectId,
  );

  if (nextProjectId) {
    await selectProject(nextProjectId);
  } else {
    els.versionSelect.innerHTML = "";
    els.diffFromSelect.innerHTML = "";
    els.diffToSelect.innerHTML = "";
    els.yamlEditor.value = "";
    els.summaryCards.innerHTML = "";
    els.sceneChipList.innerHTML = "";
    els.sceneSelect.innerHTML = "";
    els.diffOutput.textContent = t("diffPlaceholder");
    els.diffOutput.dataset.dynamic = "";
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
    (version) => t("versionOptionLabel", { versionId: version.version_id, note: version.note || t("noNote") }),
    preferredVersionId || versions.at(-1)?.version_id || "",
  );
  fillSelect(
    els.diffFromSelect,
    versions,
    (version) => version.version_id,
    (version) => version.version_id,
    versions.at(Math.max(0, versions.length - 2))?.version_id || versions.at(-1)?.version_id || "",
  );
  fillSelect(
    els.diffToSelect,
    versions,
    (version) => version.version_id,
    (version) => version.version_id,
    versions.at(-1)?.version_id || "",
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
  setStatus(t("loadingVersionStatus", { projectId, versionId }));
  state.selectedProjectId = projectId;
  state.selectedVersionId = versionId;
  els.projectSelect.value = projectId;
  els.versionSelect.value = versionId;

  const data = await api(`/api/projects/${encodeURIComponent(projectId)}/versions/${encodeURIComponent(versionId)}`);
  state.selectedVersionPayload = data;

  els.yamlEditor.value = data.yaml_text;
  els.workspacePill.textContent = `${projectId} · ${versionId}`;
  renderSummary(data);
  renderSceneOptions(data.scene_options);
  setStatus(t("loadedVersionStatus", { projectId, versionId }));
}

function renderSummary(data) {
  const document = data.document;
  const quality = document.quality || {};
  const sceneCount = (document.script?.acts || []).reduce((sum, act) => sum + (act.scenes || []).length, 0);

  const cards = [
    { label: t("summaryTitle"), value: document.meta?.title || "-" },
    { label: t("summaryTargetFormat"), value: document.meta?.target_format || "-" },
    { label: t("summaryConfidence"), value: `${quality.confidence ?? "-"}` },
    { label: t("summaryScenes"), value: String(sceneCount) },
    { label: t("summaryWarnings"), value: String((quality.warnings || []).length) },
    { label: t("summaryVersionNote"), value: data.version.note || t("noNote") },
  ];

  els.summaryCards.innerHTML = cards
    .map(
      (card) => `
      <div class="summary-card">
        <small>${escapeHtml(card.label)}</small>
        <strong>${escapeHtml(card.value)}</strong>
      </div>
    `,
    )
    .join("");
}

function renderSceneOptions(sceneOptions) {
  els.sceneChipList.innerHTML = "";
  els.sceneSelect.innerHTML = "";
  sceneOptions.forEach((scene) => {
    const chip = document.createElement("span");
    chip.className = "scene-chip";
    chip.textContent = scene.label;
    els.sceneChipList.appendChild(chip);

    const option = document.createElement("option");
    option.value = scene.scene_id;
    option.textContent = scene.label;
    els.sceneSelect.appendChild(option);
  });
}

async function compareVersions() {
  const projectId = state.selectedProjectId;
  const versionA = els.diffFromSelect.value;
  const versionB = els.diffToSelect.value;
  if (!projectId || !versionA || !versionB) {
    return;
  }
  setStatus(t("comparingVersionsStatus", { versionA, versionB }));
  const data = await api(
    `/api/projects/${encodeURIComponent(projectId)}/diff?from=${encodeURIComponent(versionA)}&to=${encodeURIComponent(versionB)}`,
  );
  renderDiff(data.diff || t("noDiff"));
  setStatus(t("comparedVersionsStatus", { versionA, versionB }));
}

function renderDiff(diffText) {
  const lines = diffText.split("\n");
  els.diffOutput.dataset.dynamic = "true";
  els.diffOutput.innerHTML = lines
    .map((line) => {
      let className = "";
      if (line.startsWith("@@")) {
        className = "diff-line-header";
      } else if (line.startsWith("---") || line.startsWith("+++")) {
        className = "diff-line-meta";
      } else if (line.startsWith("+")) {
        className = "diff-line-add";
      } else if (line.startsWith("-")) {
        className = "diff-line-remove";
      }
      return `<span class="${className}">${escapeHtml(line)}</span>`;
    })
    .join("\n");
}

async function saveYaml() {
  if (!state.selectedProjectId || !state.selectedVersionId) {
    throw new Error(t("selectVersionBeforeSave"));
  }
  setStatus(t("savingYamlStatus", { projectId: state.selectedProjectId }));
  const data = await api(
    `/api/projects/${encodeURIComponent(state.selectedProjectId)}/versions/${encodeURIComponent(state.selectedVersionId)}/save`,
    {
      method: "POST",
      body: JSON.stringify({
        yaml_text: els.yamlEditor.value,
        note: els.saveNote.value,
      }),
    },
  );
  els.saveNote.value = "";
  await loadProjects(state.selectedProjectId);
  await loadVersion(state.selectedProjectId, data.version.version_id);
  setStatus(t("savedVersionStatus", { versionId: data.version.version_id }));
}

async function regenerateScene() {
  if (!state.selectedProjectId || !state.selectedVersionId) {
    throw new Error(t("selectVersionBeforeRegenerate"));
  }
  setStatus(t("regeneratingSceneStatus", { sceneId: els.sceneSelect.value }));
  const data = await api(
    `/api/projects/${encodeURIComponent(state.selectedProjectId)}/versions/${encodeURIComponent(state.selectedVersionId)}/regenerate-scene`,
    {
      method: "POST",
      body: JSON.stringify({
        scene_id: els.sceneSelect.value,
        instruction: els.regenInstruction.value,
        provider: els.regenProvider.value,
        note: els.regenNote.value,
      }),
    },
  );
  els.regenInstruction.value = "";
  els.regenNote.value = "";
  els.regenProvider.value = "";
  await loadProjects(state.selectedProjectId);
  await loadVersion(state.selectedProjectId, data.version.version_id);
  setStatus(t("regeneratedSceneStatus", { versionId: data.version.version_id }));
}

async function generateDraft() {
  setStatus(t("generatingDraftStatus"));
  const data = await api("/api/adapt", {
    method: "POST",
    body: JSON.stringify({
      input_path: els.inputPath.value,
      project_id: els.projectId.value,
      title: els.title.value,
      original_author: els.author.value,
      original_title: els.originalTitle.value,
      provider: els.provider.value,
      target_format: els.targetFormat.value,
      genre: els.genre.value,
      tone: els.tone.value,
      note: els.adaptNote.value,
      novel_text: els.novelText.value,
    }),
  });
  await loadProjects(data.project_id);
  await loadVersion(data.project_id, data.version.version_id);
  setStatus(t("generatedDraftStatus", { projectId: data.project_id, versionId: data.version.version_id }));
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
  els.projectSelect.addEventListener("change", () => {
    selectProject(els.projectSelect.value).catch(handleError);
  });
  els.versionSelect.addEventListener("change", () => {
    loadVersion(state.selectedProjectId, els.versionSelect.value).catch(handleError);
  });
  els.compareButton.addEventListener("click", () => {
    compareVersions().catch(handleError);
  });
  els.saveYamlButton.addEventListener("click", () => {
    saveYaml().catch(handleError);
  });
  els.regenerateButton.addEventListener("click", () => {
    regenerateScene().catch(handleError);
  });
  els.generateButton.addEventListener("click", () => {
    generateDraft().catch(handleError);
  });
  els.reloadVersionButton.addEventListener("click", () => {
    loadVersion(state.selectedProjectId, state.selectedVersionId).catch(handleError);
  });
}

function handleError(error) {
  console.error(error);
  setStatus(error.message || t("unknownError"));
}

applyTranslations();
registerEvents();
loadProjects().catch(handleError);
