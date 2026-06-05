const state = {
  projects: [],
  selectedProjectId: "",
  selectedVersionId: "",
  selectedVersionPayload: null,
};

const els = {
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
    els.projectsList.innerHTML = `<div class="summary-card">No projects yet. Generate a draft to begin.</div>`;
    return;
  }

  state.projects.forEach((project) => {
    const card = document.createElement("button");
    card.type = "button";
    card.className = `project-card ${project.project_id === state.selectedProjectId ? "active" : ""}`;
    card.innerHTML = `
      <strong>${project.project_id}</strong>
      <small>Latest: ${project.latest_version || "-"}</small>
      <small>Versions: ${project.versions.length}</small>
    `;
    card.addEventListener("click", () => {
      selectProject(project.project_id);
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
  setStatus("Refreshing projects...");
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
    (project) => `${project.project_id} (${project.versions.length})`,
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
    els.diffOutput.textContent = "Select two versions to compare.";
    els.workspacePill.textContent = "No project selected";
    setStatus("No projects found.");
  }
}

async function selectProject(projectId, preferredVersionId = "") {
  state.selectedProjectId = projectId;
  renderProjects();
  els.projectSelect.value = projectId;
  setStatus(`Loading versions for ${projectId}...`);
  const data = await api(`/api/projects/${encodeURIComponent(projectId)}/versions`);
  const versions = data.versions;

  fillSelect(
    els.versionSelect,
    versions,
    (version) => version.version_id,
    (version) => `${version.version_id} · ${version.note || "no note"}`,
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
    setStatus(`Project ${projectId} has no saved versions.`);
  }
}

async function loadVersion(projectId, versionId) {
  if (!projectId || !versionId) {
    return;
  }
  setStatus(`Loading ${projectId}/${versionId}...`);
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
  setStatus(`Loaded ${projectId}/${versionId}`);
}

function renderSummary(data) {
  const document = data.document;
  const quality = document.quality || {};
  const sceneCount = (document.script?.acts || []).reduce((sum, act) => sum + (act.scenes || []).length, 0);

  const cards = [
    { label: "Title", value: document.meta?.title || "-" },
    { label: "Target format", value: document.meta?.target_format || "-" },
    { label: "Confidence", value: `${quality.confidence ?? "-"} ` },
    { label: "Scenes", value: String(sceneCount) },
    { label: "Warnings", value: String((quality.warnings || []).length) },
    { label: "Version note", value: data.version.note || "no note" },
  ];

  els.summaryCards.innerHTML = cards
    .map(
      (card) => `
      <div class="summary-card">
        <small>${card.label}</small>
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
  setStatus(`Comparing ${versionA} -> ${versionB}...`);
  const data = await api(
    `/api/projects/${encodeURIComponent(projectId)}/diff?from=${encodeURIComponent(versionA)}&to=${encodeURIComponent(versionB)}`,
  );
  renderDiff(data.diff || "No diff.");
  setStatus(`Compared ${versionA} and ${versionB}`);
}

function renderDiff(diffText) {
  const lines = diffText.split("\n");
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
    throw new Error("Select a project version before saving.");
  }
  setStatus(`Saving edited YAML as a new version for ${state.selectedProjectId}...`);
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
  setStatus(`Saved new version ${data.version.version_id}`);
}

async function regenerateScene() {
  if (!state.selectedProjectId || !state.selectedVersionId) {
    throw new Error("Select a project version before regenerating a scene.");
  }
  setStatus(`Regenerating ${els.sceneSelect.value}...`);
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
  setStatus(`Regenerated scene into ${data.version.version_id}`);
}

async function generateDraft() {
  setStatus("Generating screenplay draft...");
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
  setStatus(`Generated ${data.project_id}/${data.version.version_id}`);
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;");
}

function registerEvents() {
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
  setStatus(error.message || "An unexpected error occurred.");
}

registerEvents();
loadProjects().catch(handleError);
