const MAX_SELECT = 4;
const STORAGE_KEY = "roundtable_api_key";
const MODEL_KEY = "roundtable_model";

let masters = [];
let selected = new Set();
let serverConfig = { serverProvidesKey: false, needsUserKey: true };

const $ = (sel) => document.querySelector(sel);

async function init() {
  const [mastersRes, configRes] = await Promise.all([
    fetch("/api/masters"),
    fetch("/api/config"),
  ]);
  masters = await mastersRes.json();
  serverConfig = await configRes.json();
  renderMasters();
  bindEvents();
  restoreSettings();
  updateApiUI();
}

function updateApiUI() {
  const btn = $("#btnSettings");
  const desc = $("#settingsDesc");
  if (serverConfig.serverProvidesKey) {
    btn.textContent = "✓ 已就绪";
    btn.title = "本站已配置 AI，直接使用即可";
    if (desc) {
      desc.textContent =
        "本站已由站长配置 AI 能力，你无需安装 nuwa 或填写 API Key，直接使用即可。" +
        (serverConfig.rateLimitPerHour
          ? `（每小时限 ${serverConfig.rateLimitPerHour} 次）`
          : "");
    }
  } else {
    btn.textContent = "⚙ API";
    btn.title = "请设置 OpenAI API Key";
    if (desc) {
      desc.textContent =
        "本站未配置服务端 Key，请填写你的 OpenAI API Key。Key 仅存本机浏览器。";
    }
  }
}

function renderMasters() {
  const grid = $("#mastersGrid");
  grid.innerHTML = masters
    .map(
      (m) => `
    <button type="button" class="master-card" data-id="${m.id}" aria-pressed="false">
      <span class="check"></span>
      <div class="master-avatar">${m.avatar}</div>
      <div class="master-name">${m.name}</div>
      <div class="master-name-en">${m.nameEn}</div>
      <div class="master-tagline">${m.tagline}</div>
      <div class="master-detail">
        <p>${m.bio}</p>
        <p style="margin-top:0.4rem"><strong>擅长：</strong>${m.expertise.join("、")}</p>
        <p style="margin-top:0.25rem"><strong>适合讨论：</strong>${m.topics}</p>
      </div>
    </button>`
    )
    .join("");

  grid.querySelectorAll(".master-card").forEach((card) => {
    card.addEventListener("click", () => toggleMaster(card.dataset.id));
  });
}

function toggleMaster(id) {
  if (selected.has(id)) {
    selected.delete(id);
  } else {
    if (selected.size >= MAX_SELECT) return;
    selected.add(id);
  }
  updateSelectionUI();
}

function updateSelectionUI() {
  $("#selectedCount").textContent = selected.size;

  document.querySelectorAll(".master-card").forEach((card) => {
    const id = card.dataset.id;
    const isSelected = selected.has(id);
    const isDisabled = !isSelected && selected.size >= MAX_SELECT;

    card.classList.toggle("selected", isSelected);
    card.classList.toggle("disabled", isDisabled);
    card.setAttribute("aria-pressed", isSelected);
    card.querySelector(".check").textContent = isSelected ? "✓" : "";
  });

  const q = $("#questionInput").value.trim();
  $("#btnStart").disabled = selected.size < 2 || q.length < 4;
}

function bindEvents() {
  $("#questionInput").addEventListener("input", updateSelectionUI);

  $("#btnStart").addEventListener("click", startDiscussion);
  $("#btnReset").addEventListener("click", resetUI);

  $("#btnSettings").addEventListener("click", () => {
    $("#apiKeyInput").value = localStorage.getItem(STORAGE_KEY) || "";
    $("#modelSelect").value = localStorage.getItem(MODEL_KEY) || "gpt-4o-mini";
    $("#settingsModal").showModal();
  });

  $("#settingsModal").addEventListener("close", () => {
    const key = $("#apiKeyInput").value.trim();
    const model = $("#modelSelect").value;
    if (key) localStorage.setItem(STORAGE_KEY, key);
    localStorage.setItem(MODEL_KEY, model);
  });

  $("#btnClearKey").addEventListener("click", () => {
    localStorage.removeItem(STORAGE_KEY);
    $("#apiKeyInput").value = "";
  });
}

function restoreSettings() {
  const model = localStorage.getItem(MODEL_KEY);
  if (model) $("#modelSelect").value = model;
}

async function startDiscussion() {
  const question = $("#questionInput").value.trim();
  const apiKey = serverConfig.serverProvidesKey
    ? null
    : localStorage.getItem(STORAGE_KEY);
  const model =
    localStorage.getItem(MODEL_KEY) ||
    serverConfig.defaultModel ||
    "gpt-4o-mini";

  if (serverConfig.needsUserKey && !apiKey) {
    alert("请先在右上角 ⚙ API 中设置 OpenAI API Key");
    $("#settingsModal").showModal();
    return;
  }

  if (selected.size < 2) {
    alert("请至少选择 2 位大师");
    return;
  }

  const overlay = $("#loadingOverlay");
  overlay.classList.remove("hidden");
  const steps = [
    "第一轮：大师们发表独立观点…",
    "第二轮：交叉辩论与反驳…",
    "正在提炼共识收敛…",
  ];
  let stepIdx = 0;
  $("#loaderStep").textContent = steps[0];
  const stepTimer = setInterval(() => {
    stepIdx = Math.min(stepIdx + 1, steps.length - 1);
    $("#loaderStep").textContent = steps[stepIdx];
  }, 25000);

  try {
    const res = await fetch("/api/discuss", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        question,
        participants: [...selected],
        ...(apiKey ? { api_key: apiKey } : {}),
        model,
      }),
    });

    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "请求失败");

    renderResults(data);
    $("#stepResults").classList.remove("hidden");
    $("#stepResults").scrollIntoView({ behavior: "smooth" });
  } catch (err) {
    alert("圆桌失败：" + err.message);
  } finally {
    clearInterval(stepTimer);
    overlay.classList.add("hidden");
  }
}

function renderResults(data) {
  const names = data.participants.map((p) => `${p.avatar} ${p.name}`).join("、");

  let html = `
    <div class="result-header">
      <h3>思维圆桌对谈</h3>
      <p class="result-question">${escapeHtml(data.question)}</p>
      <p class="result-participants">参与者：${names}</p>
    </div>
  `;

  html += `<div class="round-section">
    <div class="round-title">第一轮 · 初始观点</div>`;
  for (const u of data.round1) {
    const p = data.participants.find((x) => x.id === u.speakerId);
    html += utteranceHtml(p?.avatar || "◉", u.speaker, null, u.content);
  }
  html += `</div>`;

  html += `<div class="round-section">
    <div class="round-title">第二轮 · 反驳与共识</div>`;
  for (const u of data.round2) {
    const p = data.participants.find((x) => x.id === u.speakerId);
    html += utteranceHtml(p?.avatar || "◉", u.speaker, u.target, u.content);
  }
  html += `</div>`;

  html += `
    <div class="consensus-block">
      <h4>◉ 共识收敛</h4>
      <div class="consensus-body">${formatConsensus(data.consensus)}</div>
    </div>
  `;

  $("#resultsContent").innerHTML = html;

  const countEl = $("#charCount");
  countEl.textContent = data.totalChars;
  countEl.parentElement.classList.toggle("over", data.totalChars > 3500);
}

function utteranceHtml(avatar, speaker, target, content) {
  const targetLine = target
    ? `<span class="utterance-target">→ 回应 ${escapeHtml(target)}</span>`
    : "";
  return `
    <div class="utterance">
      <div class="utterance-head">
        <span>${avatar}</span>
        <span>${escapeHtml(speaker)}</span>
        ${targetLine}
      </div>
      <div class="utterance-body">${escapeHtml(content)}</div>
    </div>`;
}

function formatConsensus(md) {
  return md
    .replace(/^## (.+)$/gm, "<h2>$1</h2>")
    .replace(/^- (.+)$/gm, "<li>$1</li>")
    .replace(/(<li>.*<\/li>\n?)+/g, (m) => `<ul>${m}</ul>`)
    .replace(/\n\n/g, "<br><br>")
    .replace(/\n/g, "<br>");
}

function escapeHtml(s) {
  const d = document.createElement("div");
  d.textContent = s;
  return d.innerHTML;
}

function resetUI() {
  $("#stepResults").classList.add("hidden");
  $("#resultsContent").innerHTML = "";
  $("#questionInput").value = "";
  selected.clear();
  updateSelectionUI();
  window.scrollTo({ top: 0, behavior: "smooth" });
}

init();
