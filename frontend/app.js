const MAX_SELECT = 4;
const TOKEN_KEY = "toptalk_token";

let masters = [];
let selected = new Set();
let currentUser = null;
let appConfig = { authRequired: true };

const $ = (sel) => document.querySelector(sel);

function getToken() {
  return localStorage.getItem(TOKEN_KEY);
}

function setToken(token) {
  if (token) localStorage.setItem(TOKEN_KEY, token);
  else localStorage.removeItem(TOKEN_KEY);
}

async function api(path, options = {}) {
  const headers = { "Content-Type": "application/json", ...options.headers };
  const token = getToken();
  if (token) headers.Authorization = `Bearer ${token}`;
  const res = await fetch(path, { ...options, headers });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.detail || data.message || "请求失败");
  return data;
}

function showApp() {
  $("#authGate").classList.add("hidden");
  $("#appHeader").classList.remove("hidden");
  $("#appMain").classList.remove("hidden");
  $("#appFooter").classList.remove("hidden");
  updateCreditsUI();
}

function showAuthGate() {
  $("#authGate").classList.remove("hidden");
  $("#appHeader").classList.add("hidden");
  $("#appMain").classList.add("hidden");
  $("#appFooter").classList.add("hidden");
}

function updateCreditsUI() {
  const badge = $("#creditsBadge");
  const modelBadge = $("#modelBadge");
  if (!appConfig.authRequired) {
    badge?.classList.add("hidden");
    if (modelBadge) {
      modelBadge.textContent = appConfig.defaultModel || "";
      modelBadge.classList.remove("hidden");
    }
    return;
  }
  badge?.classList.remove("hidden");
  modelBadge?.classList.add("hidden");
  const n = currentUser?.credits ?? 0;
  badge.textContent = `${n} 次`;
  badge.classList.toggle("credits-zero", n < 1);
}

function applyAuthModeUI() {
  const authOnly = document.querySelectorAll(".auth-only");
  authOnly.forEach((el) => el.classList.toggle("hidden", !appConfig.authRequired));
  const footer = $("#footerText");
  if (footer) {
    footer.textContent = appConfig.authRequired
      ? "TopTalk领晤 · 人物设定内置 · 每次领晤消耗 1 次机会"
      : `TopTalk领晤 · 试用模式 · ${appConfig.defaultModel || "Claude"}`;
  }
  if (!appConfig.authRequired) {
    $("#authGate")?.classList.add("hidden");
  }
}

function showAuthError(msg) {
  const el = $("#authError");
  el.textContent = msg;
  el.classList.remove("hidden");
}

async function loadMastersData() {
  try {
    const res = await fetch("/api/masters");
    if (res.ok) {
      const data = await res.json();
      if (Array.isArray(data) && data.length > 0) return data;
    }
  } catch (_) {}
  const fallback = await fetch("/static/masters.json");
  if (!fallback.ok) throw new Error("无法加载大师数据");
  return fallback.json();
}

async function initApp() {
  try {
    masters = await loadMastersData();
    renderMasters();
    bindAppEvents();
    $("#loadError").classList.add("hidden");
  } catch (err) {
    $("#loadError").textContent = `加载失败：${err.message}`;
    $("#loadError").classList.remove("hidden");
  }
}

async function bootstrap() {
  bindAuthEvents();
  try {
    appConfig = await fetch("/api/config").then((r) => r.json());
  } catch {
    appConfig = { authRequired: true };
  }
  applyAuthModeUI();

  if (!appConfig.authRequired) {
    currentUser = { username: "guest", credits: 999 };
    showApp();
    await initApp();
    return;
  }

  const token = getToken();
  if (!token) {
    showAuthGate();
    return;
  }
  try {
    currentUser = await api("/api/auth/me");
    showApp();
    await initApp();
  } catch {
    setToken(null);
    showAuthGate();
  }
}

function bindAuthEvents() {
  document.querySelectorAll(".auth-tab").forEach((tab) => {
    tab.addEventListener("click", () => {
      document.querySelectorAll(".auth-tab").forEach((t) => t.classList.remove("active"));
      tab.classList.add("active");
      const isLogin = tab.dataset.tab === "login";
      $("#loginForm").classList.toggle("hidden", !isLogin);
      $("#registerForm").classList.toggle("hidden", isLogin);
      $("#authError").classList.add("hidden");
    });
  });

  $("#loginForm").addEventListener("submit", async (e) => {
    e.preventDefault();
    $("#authError").classList.add("hidden");
    try {
      const data = await api("/api/auth/login", {
        method: "POST",
        body: JSON.stringify({
          username: $("#loginUser").value.trim(),
          password: $("#loginPass").value,
        }),
      });
      setToken(data.token);
      currentUser = data.user;
      showApp();
      await initApp();
    } catch (err) {
      showAuthError(err.message);
    }
  });

  $("#registerForm").addEventListener("submit", async (e) => {
    e.preventDefault();
    $("#authError").classList.add("hidden");
    try {
      const data = await api("/api/auth/register", {
        method: "POST",
        body: JSON.stringify({
          username: $("#regUser").value.trim(),
          password: $("#regPass").value,
        }),
      });
      setToken(data.token);
      currentUser = data.user;
      showApp();
      await initApp();
      alert("注册成功！请兑换口令获取领晤次数。");
      $("#redeemModal").showModal();
    } catch (err) {
      showAuthError(err.message);
    }
  });
}

function bindAppEvents() {
  $("#questionInput").addEventListener("input", updateSelectionUI);
  $("#btnStart").addEventListener("click", startDiscussion);
  $("#btnReset").addEventListener("click", resetUI);
  $("#btnLogout").addEventListener("click", () => {
    setToken(null);
    currentUser = null;
    selected.clear();
    location.reload();
  });

  $("#btnRedeem").addEventListener("click", () => {
    $("#redeemCodeInput").value = "";
    $("#redeemError").classList.add("hidden");
    $("#redeemModal").showModal();
  });

  $("#btnRedeemCancel").addEventListener("click", () => $("#redeemModal").close());

  $("#redeemForm").addEventListener("submit", async (e) => {
    e.preventDefault();
    $("#redeemError").classList.add("hidden");
    try {
      const data = await api("/api/auth/redeem", {
        method: "POST",
        body: JSON.stringify({ code: $("#redeemCodeInput").value.trim() }),
      });
      currentUser.credits = data.credits;
      updateCreditsUI();
      $("#redeemModal").close();
      alert(data.message);
    } catch (err) {
      const el = $("#redeemError");
      el.textContent = err.message;
      el.classList.remove("hidden");
    }
  });
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
      </div>
    </button>`
    )
    .join("");

  grid.querySelectorAll(".master-card").forEach((card) => {
    card.addEventListener("click", () => toggleMaster(card.dataset.id));
  });
}

function toggleMaster(id) {
  if (selected.has(id)) selected.delete(id);
  else if (selected.size < MAX_SELECT) selected.add(id);
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
  const hasCredits = !appConfig.authRequired || (currentUser?.credits ?? 0) >= 1;
  $("#btnStart").disabled = selected.size < 2 || q.length < 4 || !hasCredits;
  if (appConfig.authRequired && !hasCredits && selected.size >= 2 && q.length >= 4) {
    $("#btnStart").title = "领晤次数不足，请先兑换口令";
  } else {
    $("#btnStart").title = "";
  }
}

async function startDiscussion() {
  if (appConfig.authRequired && (currentUser?.credits ?? 0) < 1) {
    alert("领晤次数不足，请先兑换口令");
    $("#redeemModal").showModal();
    return;
  }

  const question = $("#questionInput").value.trim();
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
    const data = await api("/api/discuss", {
      method: "POST",
      body: JSON.stringify({
        question,
        participants: [...selected],
      }),
    });
    if (data.creditsRemaining !== undefined) {
      currentUser.credits = data.creditsRemaining;
      updateCreditsUI();
    }
    renderResults(data);
    $("#stepResults").classList.remove("hidden");
    $("#stepResults").scrollIntoView({ behavior: "smooth" });
  } catch (err) {
    alert("领晤失败：" + err.message);
    if (err.message.includes("次数不足")) $("#redeemModal").showModal();
  } finally {
    clearInterval(stepTimer);
    overlay.classList.add("hidden");
  }
}

function renderResults(data) {
  const names = data.participants.map((p) => `${p.avatar} ${p.name}`).join("、");
  let html = `
    <div class="result-header">
      <h3>TopTalk 领晤实录</h3>
      <p class="result-question">${escapeHtml(data.question)}</p>
      <p class="result-participants">参与者：${names}</p>
    </div>`;

  html += `<div class="round-section"><div class="round-title">第一轮 · 初始观点</div>`;
  for (const u of data.round1) {
    const p = data.participants.find((x) => x.id === u.speakerId);
    html += utteranceHtml(p?.avatar || "◉", u.speaker, null, u.content);
  }
  html += `</div><div class="round-section"><div class="round-title">第二轮 · 反驳与共识</div>`;
  for (const u of data.round2) {
    const p = data.participants.find((x) => x.id === u.speakerId);
    html += utteranceHtml(p?.avatar || "◉", u.speaker, u.target, u.content);
  }
  html += `</div><div class="consensus-block"><h4>◈ 共识收敛</h4><div class="consensus-body">${formatConsensus(data.consensus)}</div></div>`;

  $("#resultsContent").innerHTML = html;
  $("#charCount").textContent = data.totalChars;
}

function utteranceHtml(avatar, speaker, target, content) {
  const targetLine = target ? `<span class="utterance-target">→ 回应 ${escapeHtml(target)}</span>` : "";
  return `<div class="utterance"><div class="utterance-head"><span>${avatar}</span><span>${escapeHtml(speaker)}</span>${targetLine}</div><div class="utterance-body">${escapeHtml(content)}</div></div>`;
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

bootstrap();
