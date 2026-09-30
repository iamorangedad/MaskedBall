const state = {
  me: null,
  users: [],
  edges: [],
  catalog: null,
  query: "",
  selectedId: null,
  messages: [],
  sending: false,
  notice: "",
  nodes: new Map(),
  camera: { x: 0, y: 0, k: 1 },
  drag: null,
  running: false,
};

const canvas = document.querySelector("#space");
const ctx = canvas.getContext("2d");
const dockEmpty = document.querySelector("#dock-empty");
const dockChat = document.querySelector("#dock-chat");
const gate = document.querySelector("#gate");
const settings = document.querySelector("#settings");

const COLORS = {
  friendly: "#e0a36a",
  humorous: "#d4c06a",
  mysterious: "#b7a4de",
  academic: "#8fb4c9",
  creative: "#d39aaa",
  supportive: "#8fbfa4",
};

function $(id) { return document.querySelector(id); }

async function api(path, options = {}) {
  const response = await fetch(path, {
    credentials: "same-origin",
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options,
    body: options.body ? JSON.stringify(options.body) : undefined,
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data.error || "请求没有完成");
  return data;
}

function place(id) {
  let hash = 2166136261;
  for (const char of id) hash = Math.imul(hash ^ char.charCodeAt(0), 16777619);
  const angle = ((hash >>> 0) / 2 ** 32) * Math.PI * 2;
  const radius = 160 + ((hash >>> 8) % 120);
  return { x: Math.cos(angle) * radius, y: Math.sin(angle) * radius * 0.72 };
}

function syncNodes() {
  const seen = new Set();
  for (const user of state.users) {
    seen.add(user.id);
    if (!state.nodes.has(user.id)) {
      const spot = place(user.id);
      state.nodes.set(user.id, { ...spot, vx: 0, vy: 0 });
    }
  }
  for (const id of [...state.nodes.keys()]) {
    if (!seen.has(id)) state.nodes.delete(id);
  }
}

let cameraReady = false;
let viewSize = { w: 0, h: 0 };

function visualCenter() {
  const rect = canvas.getBoundingClientRect();
  const dock = document.querySelector("#dock").getBoundingClientRect();
  const dockOnRight = dock.width > 200 && dock.left > rect.width * 0.45 && dock.top < rect.height * 0.4;
  return {
    x: dockOnRight ? dock.left / 2 : rect.width / 2,
    y: dockOnRight ? rect.height / 2 : Math.min(rect.height / 2, dock.top / 2 || rect.height / 2),
  };
}

function resize() {
  const rect = canvas.getBoundingClientRect();
  const ratio = window.devicePixelRatio || 1;
  canvas.width = Math.max(1, Math.floor(rect.width * ratio));
  canvas.height = Math.max(1, Math.floor(rect.height * ratio));
  ctx.setTransform(ratio, 0, 0, ratio, 0, 0);
  const center = visualCenter();
  if (!cameraReady && rect.width > 0) {
    state.camera.x = center.x;
    state.camera.y = center.y;
    cameraReady = true;
  } else if (viewSize.w > 0 && rect.width > 0) {
    const previous = {
      x: viewSize.dockRight ? viewSize.focusX : viewSize.w / 2,
      y: viewSize.h / 2,
    };
    state.camera.x += center.x - previous.x;
    state.camera.y += center.y - previous.y;
  }
  viewSize = { w: rect.width, h: rect.height, dockRight: center.x !== rect.width / 2, focusX: center.x };
  draw();
}

function worldFromEvent(event) {
  const rect = canvas.getBoundingClientRect();
  return {
    x: (event.clientX - rect.left - state.camera.x) / state.camera.k,
    y: (event.clientY - rect.top - state.camera.y) / state.camera.k,
  };
}

function hitNode(point) {
  let found = null;
  let best = 28;
  for (const user of visibleUsers()) {
    const node = state.nodes.get(user.id);
    const distance = Math.hypot(node.x - point.x, node.y - point.y);
    if (distance < best) {
      best = distance;
      found = user;
    }
  }
  return found;
}

function visibleUsers() {
  const query = state.query.trim().toLowerCase();
  if (!query) return state.users;
  return state.users.filter((user) => {
    const blob = [user.name, user.bio, ...(user.keywords || [])].join(" ").toLowerCase();
    return blob.includes(query);
  });
}

function step() {
  const users = state.users;
  let energy = 0;
  for (let i = 0; i < users.length; i += 1) {
    const a = state.nodes.get(users[i].id);
    for (let j = i + 1; j < users.length; j += 1) {
      const b = state.nodes.get(users[j].id);
      let dx = a.x - b.x;
      let dy = a.y - b.y;
      let dist = Math.hypot(dx, dy) || 0.01;
      const force = 2800 / (dist * dist);
      dx = (dx / dist) * force;
      dy = (dy / dist) * force;
      a.vx += dx;
      a.vy += dy;
      b.vx -= dx;
      b.vy -= dy;
    }
  }
  for (const edge of state.edges) {
    const a = state.nodes.get(edge.a);
    const b = state.nodes.get(edge.b);
    if (!a || !b) continue;
    const dx = b.x - a.x;
    const dy = b.y - a.y;
    const dist = Math.hypot(dx, dy) || 0.01;
    const pull = (dist - 168) * 0.012;
    a.vx += (dx / dist) * pull;
    a.vy += (dy / dist) * pull;
    b.vx -= (dx / dist) * pull;
    b.vy -= (dy / dist) * pull;
  }
  for (const user of users) {
    const node = state.nodes.get(user.id);
    if (state.drag && state.drag.id === user.id) {
      node.vx = 0;
      node.vy = 0;
      continue;
    }
    node.vx += -node.x * 0.01;
    node.vy += -node.y * 0.01;
    node.vx *= 0.78;
    node.vy *= 0.78;
    node.x += node.vx;
    node.y += node.vy;
    energy += Math.abs(node.vx) + Math.abs(node.vy);
  }
  return energy;
}

function draw() {
  const rect = canvas.getBoundingClientRect();
  ctx.clearRect(0, 0, rect.width, rect.height);
  const { x: cx, y: cy, k } = state.camera;
  ctx.save();
  ctx.translate(cx, cy);
  ctx.scale(k, k);

  ctx.beginPath();
  ctx.arc(0, 0, 250, 0, Math.PI * 2);
  ctx.strokeStyle = "rgba(224,193,122,0.08)";
  ctx.lineWidth = 1;
  ctx.stroke();

  const visible = new Set(visibleUsers().map((user) => user.id));
  for (const edge of state.edges) {
    const a = state.nodes.get(edge.a);
    const b = state.nodes.get(edge.b);
    if (!a || !b) continue;
    const mine = state.me && (edge.a === state.me.id || edge.b === state.me.id);
    const faded = state.query && (!visible.has(edge.a) || !visible.has(edge.b));
    ctx.beginPath();
    ctx.moveTo(a.x, a.y);
    ctx.lineTo(b.x, b.y);
    ctx.strokeStyle = mine ? "rgba(224,193,122,0.85)" : "rgba(243,232,214,0.28)";
    ctx.globalAlpha = faded ? 0.15 : 1;
    ctx.lineWidth = mine ? 1.6 : 1;
    ctx.stroke();
    ctx.globalAlpha = 1;
  }

  for (const user of state.users) {
    const node = state.nodes.get(user.id);
    const faded = state.query && !visible.has(user.id);
    const selected = user.id === state.selectedId;
    const mine = state.me && user.id === state.me.id;
    const color = COLORS[user.personality] || "#e0c17a";
    ctx.globalAlpha = faded ? 0.18 : 1;
    ctx.beginPath();
    ctx.arc(node.x, node.y, mine ? 24 : 20, 0, Math.PI * 2);
    ctx.fillStyle = "#1a1613";
    ctx.fill();
    ctx.lineWidth = selected || mine ? 2.4 : 1.2;
    ctx.strokeStyle = selected ? "#f3e6c4" : color;
    ctx.stroke();
    if (user.assistMode === "llm") {
      ctx.beginPath();
      ctx.arc(node.x + 14, node.y - 14, 4, 0, Math.PI * 2);
      ctx.fillStyle = color;
      ctx.fill();
    }
    ctx.fillStyle = "#f6efe4";
    ctx.font = "16px 'Noto Serif CJK SC', serif";
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    ctx.fillText(user.name.slice(0, 1), node.x, node.y + 1);
    ctx.font = "13px 'Noto Sans CJK SC', sans-serif";
    ctx.fillStyle = mine ? "#e0c17a" : "#f6efe4";
    ctx.fillText(mine ? `${user.name} · 你` : user.name, node.x, node.y + 36);
    ctx.globalAlpha = 1;
  }
  ctx.restore();
}

function wake() {
  if (state.running) return;
  state.running = true;
  const frame = () => {
    const energy = step();
    draw();
    if (energy < 0.08 && !state.drag) {
      state.running = false;
      return;
    }
    requestAnimationFrame(frame);
  };
  requestAnimationFrame(frame);
}

function linkCountForMe() {
  if (!state.me) return 0;
  return state.edges.filter((edge) => edge.a === state.me.id || edge.b === state.me.id).length;
}

function renderChrome() {
  const count = linkCountForMe();
  $("#link-count").textContent = count ? `你已和 ${count} 个人连线` : "你还没有连线";
}

function renderDock() {
  const user = state.users.find((item) => item.id === state.selectedId);
  if (!user || (state.me && user.id === state.me.id)) {
    dockEmpty.hidden = false;
    dockChat.hidden = true;
    if (state.me && user && user.id === state.me.id) {
      dockEmpty.querySelector("h2").textContent = "这是你自己";
      dockEmpty.querySelector("p:last-child").textContent = "在画像设置里写下你是谁。和别人交谈之后，你们之间会出现连线。";
    } else {
      dockEmpty.querySelector("h2").textContent = "先选一个节点";
      dockEmpty.querySelector("p:last-child").textContent = "所有人都在这里。你和谁说过话，两个人之间就会留下一条线。";
    }
    return;
  }
  dockEmpty.hidden = true;
  dockChat.hidden = false;
  dockChat.replaceChildren();

  const profile = document.createElement("div");
  profile.className = "profile";
  const top = document.createElement("div");
  top.className = "profile-top";
  const avatar = document.createElement("div");
  avatar.className = "avatar";
  avatar.textContent = user.name.slice(0, 1);
  const title = document.createElement("div");
  const name = document.createElement("h2");
  name.textContent = user.name;
  const meta = document.createElement("p");
  meta.className = "meta";
  meta.textContent = `${user.personalityLabel} · ${user.styleLabel.split("，")[0]} · ${user.assistMode === "llm" ? "画像会代为回复" : "等待亲手回复"}`;
  title.append(name, meta);
  top.append(avatar, title);
  const keywords = document.createElement("div");
  keywords.className = "keywords";
  for (const keyword of user.keywords) {
    const chip = document.createElement("span");
    chip.textContent = keyword;
    keywords.append(chip);
  }
  const bio = document.createElement("p");
  bio.className = "meta";
  bio.textContent = user.bio || "这个人还没有写背景。";
  const greeting = document.createElement("p");
  greeting.className = "greeting";
  greeting.textContent = user.greeting ? `“${user.greeting}”` : "";
  profile.append(top, keywords, bio, greeting);

  const thread = document.createElement("div");
  thread.className = "thread";
  if (!state.messages.length) {
    const empty = document.createElement("p");
    empty.className = "empty-thread";
    empty.textContent = "还没有交谈。说一句，这条线就会出现。";
    thread.append(empty);
  }
  for (const message of state.messages) {
    const mine = state.me && message.senderId === state.me.id;
    const bubble = document.createElement("div");
    bubble.className = mine ? "bubble mine" : "bubble";
    const text = document.createElement("p");
    text.textContent = message.content;
    const note = document.createElement("small");
    const speaker = state.users.find((item) => item.id === message.senderId);
    const how = message.via === "llm" ? "画像代发" : "亲手";
    note.textContent = `${speaker ? speaker.name : ""} · ${how}`;
    bubble.append(text, note);
    thread.append(bubble);
  }
  if (state.sending) {
    const waiting = document.createElement("p");
    waiting.className = "empty-thread";
    waiting.textContent = "本地模型正在按画像组织语言，通常要十几秒。";
    thread.append(waiting);
  }

  const composer = document.createElement("form");
  composer.className = "composer";
  const modes = document.createElement("div");
  modes.className = "modes";
  const humanBtn = document.createElement("button");
  humanBtn.type = "button";
  humanBtn.textContent = "亲手回复";
  const llmBtn = document.createElement("button");
  llmBtn.type = "button";
  llmBtn.textContent = "画像代聊";
  const mode = state.me.assistMode;
  humanBtn.classList.toggle("active", mode === "human");
  llmBtn.classList.toggle("active", mode === "llm");
  humanBtn.addEventListener("click", () => setMode("human"));
  llmBtn.addEventListener("click", () => setMode("llm"));
  modes.append(humanBtn, llmBtn);

  const row = document.createElement("div");
  row.className = "composer-row";
  const input = document.createElement("input");
  input.maxLength = 800;
  input.placeholder = mode === "llm" ? "可选：给画像一个意图，留空就让它自己接话" : "亲手写一句";
  input.required = mode === "human";
  const send = document.createElement("button");
  send.type = "submit";
  send.textContent = mode === "llm" ? "代为发送" : "发送";
  send.disabled = state.sending;
  row.append(input, send);
  const error = document.createElement("p");
  error.className = "form-error";
  error.hidden = !state.notice;
  error.textContent = state.notice;
  composer.append(modes, row, error);
  composer.addEventListener("submit", async (event) => {
    event.preventDefault();
    const draft = input.value;
    const pending = {
      id: "pending",
      senderId: state.me.id,
      content: state.me.assistMode === "llm" && !draft ? "正在按画像组织这句话。" : draft,
      via: state.me.assistMode,
    };
    state.notice = "";
    state.sending = true;
    state.messages = state.messages.concat(pending);
    renderDock();
    try {
      const data = await api(`/api/chat/${user.id}`, {
        method: "POST",
        body: { via: state.me.assistMode, content: draft },
      });
      state.messages = data.messages;
      upsertEdge(data.edge);
      state.notice = data.replyError || "";
    } catch (err) {
      state.messages = state.messages.filter((item) => item.id !== "pending");
      state.notice = err.message;
    } finally {
      state.sending = false;
      renderDock();
      const scroller = dockChat.querySelector(".thread");
      if (scroller) scroller.scrollTop = scroller.scrollHeight;
      wake();
    }
  });

  dockChat.append(profile, thread, composer);
  thread.scrollTop = thread.scrollHeight;
}

function upsertEdge(edge) {
  if (!edge) return;
  const index = state.edges.findIndex((item) =>
    (item.a === edge.a && item.b === edge.b) || (item.a === edge.b && item.b === edge.a));
  if (index >= 0) state.edges[index] = edge;
  else state.edges.push(edge);
  renderChrome();
}

async function setMode(assistMode) {
  if (!state.me || state.me.assistMode === assistMode) return;
  const me = await api("/api/me", { method: "PUT", body: { ...state.me, assistMode } });
  state.me = me.me;
  const index = state.users.findIndex((user) => user.id === state.me.id);
  if (index >= 0) state.users[index] = state.me;
  renderDock();
  draw();
}

async function openChat(user) {
  state.selectedId = user.id;
  state.notice = "";
  state.sending = false;
  state.messages = [];
  draw();
  renderDock();
  if (!state.me || user.id === state.me.id) return;
  try {
    const data = await api(`/api/chat/${user.id}`);
    if (state.selectedId !== user.id) return;
    state.messages = data.messages;
    renderDock();
  } catch (err) {
    state.notice = err.message;
    renderDock();
  }
}

function fillSelect(select, options, selected) {
  select.replaceChildren();
  for (const option of options) {
    const node = document.createElement("option");
    node.value = option.id;
    node.textContent = option.hint ? `${option.label} · ${option.hint}` : option.label;
    select.append(node);
  }
  select.value = selected;
}

function openSettings() {
  if (!state.me || !state.catalog) return;
  $("#profile-name").value = state.me.name;
  fillSelect($("#profile-personality"), state.catalog.personalities, state.me.personality);
  fillSelect($("#profile-style"), state.catalog.styles, state.me.languageStyle);
  $("#profile-bio").value = state.me.bio;
  $("#profile-keywords").value = (state.me.keywords || []).join("，");
  $("#profile-greeting").value = state.me.greeting;
  settings.querySelector(`input[name="assistMode"][value="${state.me.assistMode}"]`).checked = true;
  $("#settings-error").hidden = true;
  $("#settings-note").textContent = `代聊使用本地模型 ${state.catalog.model}`;
  settings.hidden = false;
}

async function refresh() {
  const data = await api("/api/space");
  state.me = data.me;
  state.users = data.users;
  state.edges = data.edges;
  state.catalog = data.catalog;
  syncNodes();
  renderChrome();
  renderDock();
  wake();
  return data;
}

canvas.addEventListener("pointerdown", (event) => {
  const point = worldFromEvent(event);
  const user = hitNode(point);
  state.drag = {
    id: user ? user.id : null,
    px: event.clientX,
    py: event.clientY,
    cx: state.camera.x,
    cy: state.camera.y,
    moved: false,
    user,
  };
  canvas.classList.add("dragging");
  try { canvas.setPointerCapture(event.pointerId); } catch (err) { /* untrusted pointer */ }
});

canvas.addEventListener("pointermove", (event) => {
  if (!state.drag) return;
  const dx = event.clientX - state.drag.px;
  const dy = event.clientY - state.drag.py;
  if (Math.hypot(dx, dy) > 4) state.drag.moved = true;
  if (state.drag.id) {
    const node = state.nodes.get(state.drag.id);
    const point = worldFromEvent(event);
    node.x = point.x;
    node.y = point.y;
    wake();
  } else {
    state.camera.x = state.drag.cx + dx;
    state.camera.y = state.drag.cy + dy;
    draw();
  }
});

canvas.addEventListener("pointerup", (event) => {
  if (state.drag && !state.drag.moved && state.drag.user) openChat(state.drag.user);
  state.drag = null;
  canvas.classList.remove("dragging");
});

canvas.addEventListener("wheel", (event) => {
  event.preventDefault();
  const rect = canvas.getBoundingClientRect();
  const mouseX = event.clientX - rect.left;
  const mouseY = event.clientY - rect.top;
  const next = Math.min(2.4, Math.max(0.45, state.camera.k * (event.deltaY > 0 ? 0.92 : 1.08)));
  const worldX = (mouseX - state.camera.x) / state.camera.k;
  const worldY = (mouseY - state.camera.y) / state.camera.k;
  state.camera.k = next;
  state.camera.x = mouseX - worldX * next;
  state.camera.y = mouseY - worldY * next;
  draw();
}, { passive: false });

$("#search").addEventListener("input", (event) => {
  state.query = event.target.value;
  draw();
});

$("#open-settings").addEventListener("click", openSettings);
$("#close-settings").addEventListener("click", () => { settings.hidden = true; });
$("#gate-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const data = await api("/api/join", { method: "POST", body: { name: $("#gate-name").value } });
  state.me = data.me;
  gate.hidden = true;
  await refresh();
});
$("#settings-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = new FormData(event.target);
  const error = $("#settings-error");
  error.hidden = true;
  try {
    const data = await api("/api/me", {
      method: "PUT",
      body: {
        name: form.get("name"),
        personality: form.get("personality"),
        languageStyle: form.get("languageStyle"),
        bio: form.get("bio"),
        keywords: String(form.get("keywords") || "").split(/[,，]/).map((item) => item.trim()).filter(Boolean),
        greeting: form.get("greeting"),
        assistMode: form.get("assistMode"),
      },
    });
    state.me = data.me;
    const index = state.users.findIndex((user) => user.id === state.me.id);
    if (index >= 0) state.users[index] = state.me;
    $("#settings-note").textContent = "已保存。下一次代聊会使用这份画像。";
    renderChrome();
    renderDock();
    draw();
  } catch (err) {
    error.hidden = false;
    error.textContent = err.message;
  }
});

window.addEventListener("resize", resize);
window.addEventListener("keydown", (event) => {
  if (event.key === "Escape") settings.hidden = true;
});

resize();
refresh().then((data) => {
  gate.hidden = Boolean(data.me);
  if (!data.me) $("#gate-name").focus();
}).catch((error) => {
  gate.hidden = false;
  $("#gate-form").querySelector("p:last-of-type").textContent = error.message;
});
