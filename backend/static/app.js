/**
 * AI Strategy Arena v3.0 — 3 Krallık Savaş Arenası
 * OpenAI vs DeepSeek vs Anthropic Claude (Tri-Polar Geopolitics)
 * Canlı Canvas Hex Render, 3'lü Radar Grafiği, 6 Yönlü Elçi Ağı
 */

// ── Varlıklar (Assets) Önyükleme ─────────────────────────────────
const ASSETS = {
  envoy: new Image(),
  leader_openai: new Image(),
  leader_deepseek: new Image(),
  leader_claude: new Image(),
  worker: new Image(),
  ship: new Image(),
  barbarian: new Image(),
  dragon: new Image(),
  archer: new Image(),
  forest: new Image(),
  water: new Image(),
};

ASSETS.envoy.src = "assets/units/envoy.png";
ASSETS.leader_openai.src = "assets/units/leader_openai.png";
ASSETS.leader_deepseek.src = "assets/units/leader_deepseek.png";
ASSETS.leader_claude.src = "assets/units/leader_claude.png";
ASSETS.worker.src = "assets/units/worker.png";
ASSETS.ship.src = "assets/units/ship.png";
ASSETS.barbarian.src = "assets/units/barbarian.png";
ASSETS.dragon.src = "assets/units/dragon.png";
ASSETS.archer.src = "assets/units/archer.png";
ASSETS.forest.src = "assets/terrain/forest.png";
ASSETS.water.src = "assets/terrain/water.png";

// ── Global State ─────────────────────────────────────────────────
let socket = null;
let mapTiles = [];
let gameState = null;
let radarChart = null;

const canvas = document.getElementById("hex-canvas");
const ctx = canvas.getContext("2d");
const tooltip = document.getElementById("hex-tooltip");

// ── Odd-R Hex Geometrisi ──────────────────────────────────────────
const HEX_RADIUS = 20.8;
const HEX_WIDTH  = Math.sqrt(3) * HEX_RADIUS;
const HEX_HEIGHT = 2 * HEX_RADIUS;

// Kamera (Zoom & Pan)
let camera = {
  x: 28,
  y: 22,
  zoom: 1.0,
  isDragging: false,
  dragStartX: 0,
  dragStartY: 0
};

let animTimer = 0;

// ── Hex Koordinat Dönüştürücüler ──────────────────────────────────
function hexToPixel(col, row) {
  const isOdd = (row % 2 === 1);
  const x = (col + (isOdd ? 0.5 : 0)) * HEX_WIDTH;
  const y = row * (HEX_HEIGHT * 0.75);
  return {
    x: camera.x + x * camera.zoom,
    y: camera.y + y * camera.zoom
  };
}

function pixelToHex(screenX, screenY) {
  const worldX = (screenX - camera.x) / camera.zoom;
  const worldY = (screenY - camera.y) / camera.zoom;

  let bestDist = Infinity;
  let bestHex = { col: 0, row: 0 };

  for (const t of mapTiles) {
    const isOdd = (t.row % 2 === 1);
    const hx = (t.col + (isOdd ? 0.5 : 0)) * HEX_WIDTH;
    const hy = t.row * (HEX_HEIGHT * 0.75);
    const d = Math.hypot(worldX - hx, worldY - hy);
    if (d < bestDist && d < HEX_RADIUS * 1.1) {
      bestDist = d;
      bestHex = { col: t.col, row: t.row };
    }
  }
  return bestHex;
}

function drawHexPath(cx, cy, radius) {
  ctx.beginPath();
  for (let i = 0; i < 6; i++) {
    const angle = (Math.PI / 180) * (60 * i - 30);
    const x = cx + radius * Math.cos(angle);
    const y = cy + radius * Math.sin(angle);
    if (i === 0) ctx.moveTo(x, y);
    else ctx.lineTo(x, y);
  }
  ctx.closePath();
}

// ── 3 Krallık Keep Koordinatları ─────────────────────────────────
const KEEP_COORDS = {
  1: { col: 13, row: 2 },   // OpenAI (Kuzey)
  2: { col: 21, row: 15 },  // DeepSeek (Güneydoğu)
  3: { col: 5,  row: 15 },  // Claude (Güneybatı)
};

// ── Ana Render Fonksiyonu ─────────────────────────────────────────
function renderScene() {
  animTimer += 0.04;
  ctx.clearRect(0, 0, canvas.width, canvas.height);

  // Arka Plan
  const bgGrad = ctx.createLinearGradient(0, 0, canvas.width, canvas.height);
  bgGrad.addColorStop(0, "#030712");
  bgGrad.addColorStop(1, "#081026");
  ctx.fillStyle = bgGrad;
  ctx.fillRect(0, 0, canvas.width, canvas.height);

  const r = HEX_RADIUS * camera.zoom;

  // 1. AŞAMA: ARAZİ ÇİZİMİ
  mapTiles.forEach((tile) => {
    const { x, y } = hexToPixel(tile.col, tile.row);
    if (x < -r || x > canvas.width + r || y < -r || y > canvas.height + r) return;

    drawHexPath(x, y, r);

    switch (tile.terrain) {
      case "plains": {
        const grad = ctx.createLinearGradient(x - r, y - r, x + r, y + r);
        grad.addColorStop(0, "#24522e");
        grad.addColorStop(1, "#1c4024");
        ctx.fillStyle = grad;
        ctx.fill();
        ctx.strokeStyle = "#2b6639";
        ctx.lineWidth = 1;
        ctx.stroke();
        break;
      }

      case "forest": {
        const grad = ctx.createLinearGradient(x - r, y - r, x + r, y + r);
        grad.addColorStop(0, "#11361c");
        grad.addColorStop(1, "#081f10");
        ctx.fillStyle = grad;
        ctx.fill();
        ctx.strokeStyle = "#164724";
        ctx.lineWidth = 1;
        ctx.stroke();

        ctx.fillStyle = "#064e3b";
        ctx.beginPath();
        ctx.arc(x - 4 * camera.zoom, y - 2 * camera.zoom, 5 * camera.zoom, 0, Math.PI * 2);
        ctx.arc(x + 4 * camera.zoom, y - 2 * camera.zoom, 5 * camera.zoom, 0, Math.PI * 2);
        ctx.arc(x, y + 3 * camera.zoom, 6 * camera.zoom, 0, Math.PI * 2);
        ctx.fill();
        break;
      }

      case "mountain": {
        ctx.fillStyle = "#334155";
        ctx.fill();
        ctx.strokeStyle = "#475569";
        ctx.lineWidth = 1;
        ctx.stroke();

        ctx.beginPath();
        ctx.moveTo(x - 7 * camera.zoom, y + 6 * camera.zoom);
        ctx.lineTo(x, y - 9 * camera.zoom);
        ctx.lineTo(x + 7 * camera.zoom, y + 6 * camera.zoom);
        ctx.closePath();
        ctx.fillStyle = "#1e293b";
        ctx.fill();

        ctx.beginPath();
        ctx.moveTo(x - 2.5 * camera.zoom, y - 2 * camera.zoom);
        ctx.lineTo(x, y - 9 * camera.zoom);
        ctx.lineTo(x + 2.5 * camera.zoom, y - 2 * camera.zoom);
        ctx.closePath();
        ctx.fillStyle = "#f8fafc";
        ctx.fill();
        break;
      }

      case "water": {
        const wave = Math.sin(animTimer + tile.col * 0.4 + tile.row * 0.3) * 0.1;
        const grad = ctx.createLinearGradient(x - r, y - r, x + r, y + r);
        grad.addColorStop(0, "#0c3554");
        grad.addColorStop(1, "#072036");
        ctx.fillStyle = grad;
        ctx.fill();
        ctx.strokeStyle = "#134972";
        ctx.lineWidth = 1;
        ctx.stroke();
        break;
      }

      case "bridge": {
        ctx.fillStyle = "#0b2a44";
        ctx.fill();

        ctx.fillStyle = "#78350f";
        ctx.fillRect(x - 6 * camera.zoom, y - r * 0.85, 12 * camera.zoom, r * 1.7);
        ctx.strokeStyle = "#b45309";
        ctx.lineWidth = 1.5;
        ctx.strokeRect(x - 6 * camera.zoom, y - r * 0.85, 12 * camera.zoom, r * 1.7);
        break;
      }

      case "relic_island": {
        const pulse = (Math.sin(animTimer * 2) + 1) * 0.5;
        const grad = ctx.createRadialGradient(x, y, 2, x, y, r);
        grad.addColorStop(0, "#7e22ce");
        grad.addColorStop(1, "#3b0764");
        ctx.fillStyle = grad;
        ctx.fill();

        ctx.strokeStyle = `rgba(216, 180, 254, ${0.4 + pulse * 0.5})`;
        ctx.lineWidth = 2 + pulse;
        ctx.stroke();

        ctx.fillStyle = "#f59e0b";
        ctx.beginPath();
        ctx.arc(x, y, (5 + pulse * 2) * camera.zoom, 0, Math.PI * 2);
        ctx.fill();

        ctx.font = `${Math.round(11 * camera.zoom)}px Inter`;
        ctx.textAlign = "center";
        ctx.textBaseline = "middle";
        ctx.fillText("💎", x, y);
        break;
      }

      case "keep_1": {
        // OpenAI Keep
        ctx.fillStyle = "#1e3a8a";
        ctx.fill();
        ctx.strokeStyle = "#38bdf8";
        ctx.lineWidth = 2.5;
        ctx.stroke();

        ctx.fillStyle = "#0f172a";
        ctx.fillRect(x - 12 * camera.zoom, y - 12 * camera.zoom, 24 * camera.zoom, 24 * camera.zoom);
        ctx.strokeStyle = "#38bdf8";
        ctx.strokeRect(x - 12 * camera.zoom, y - 12 * camera.zoom, 24 * camera.zoom, 24 * camera.zoom);

        if (ASSETS.leader_openai.complete) {
          const sz = 26 * camera.zoom;
          ctx.drawImage(ASSETS.leader_openai, x - sz / 2, y - sz / 2, sz, sz);
        }
        break;
      }

      case "keep_2": {
        // DeepSeek Keep
        ctx.fillStyle = "#881337";
        ctx.fill();
        ctx.strokeStyle = "#f43f5e";
        ctx.lineWidth = 2.5;
        ctx.stroke();

        ctx.fillStyle = "#0f172a";
        ctx.fillRect(x - 12 * camera.zoom, y - 12 * camera.zoom, 24 * camera.zoom, 24 * camera.zoom);
        ctx.strokeStyle = "#f43f5e";
        ctx.strokeRect(x - 12 * camera.zoom, y - 12 * camera.zoom, 24 * camera.zoom, 24 * camera.zoom);

        if (ASSETS.leader_deepseek.complete) {
          const sz = 26 * camera.zoom;
          ctx.drawImage(ASSETS.leader_deepseek, x - sz / 2, y - sz / 2, sz, sz);
        }
        break;
      }

      case "keep_3": {
        // Anthropic Claude Keep
        ctx.fillStyle = "#78350f";
        ctx.fill();
        ctx.strokeStyle = "#f59e0b";
        ctx.lineWidth = 2.5;
        ctx.stroke();

        ctx.fillStyle = "#0f172a";
        ctx.fillRect(x - 12 * camera.zoom, y - 12 * camera.zoom, 24 * camera.zoom, 24 * camera.zoom);
        ctx.strokeStyle = "#f59e0b";
        ctx.strokeRect(x - 12 * camera.zoom, y - 12 * camera.zoom, 24 * camera.zoom, 24 * camera.zoom);

        if (ASSETS.leader_claude.complete) {
          const sz = 26 * camera.zoom;
          ctx.drawImage(ASSETS.leader_claude, x - sz / 2, y - sz / 2, sz, sz);
        }
        break;
      }

      case "barbarian": {
        ctx.fillStyle = "#450a0a";
        ctx.fill();
        ctx.strokeStyle = "#ef4444";
        ctx.lineWidth = 1.5;
        ctx.stroke();

        if (ASSETS.barbarian.complete) {
          const sz = 20 * camera.zoom;
          ctx.drawImage(ASSETS.barbarian, x - sz / 2, y - sz / 2, sz, sz);
        }
        break;
      }
    }

    // Hakimiyet Sınır Renkleri
    if (tile.owner === 1) {
      ctx.strokeStyle = "rgba(56, 189, 248, 0.4)";
      ctx.lineWidth = 2;
      drawHexPath(x, y, r * 0.88);
      ctx.stroke();
    } else if (tile.owner === 2) {
      ctx.strokeStyle = "rgba(244, 63, 94, 0.4)";
      ctx.lineWidth = 2;
      drawHexPath(x, y, r * 0.88);
      ctx.stroke();
    } else if (tile.owner === 3) {
      ctx.strokeStyle = "rgba(245, 158, 11, 0.45)";
      ctx.lineWidth = 2;
      drawHexPath(x, y, r * 0.88);
      ctx.stroke();
    }
  });

  // 2. AŞAMA: YAŞAYAN BİRLİKLER & KALYONLAR
  if (ASSETS.ship.complete) {
    const bob = Math.sin(animTimer * 1.5) * 2;
    const p1 = hexToPixel(25, 4);
    const sz = 26 * camera.zoom;
    ctx.drawImage(ASSETS.ship, p1.x - sz / 2, p1.y - sz / 2 + bob, sz, sz);
  }

  // 3 Krallık Köylüleri / İşçileri
  if (ASSETS.worker.complete) {
    const pw1 = hexToPixel(12, 3);
    const pw2 = hexToPixel(20, 14);
    const pw3 = hexToPixel(6, 14);
    const sz = 18 * camera.zoom;
    ctx.drawImage(ASSETS.worker, pw1.x - sz / 2, pw1.y - sz / 2, sz, sz);
    ctx.drawImage(ASSETS.worker, pw2.x - sz / 2, pw2.y - sz / 2, sz, sz);
    ctx.drawImage(ASSETS.worker, pw3.x - sz / 2, pw3.y - sz / 2, sz, sz);
  }

  // 3. AŞAMA: 6 YÖNLÜ DÖRT NALA KOŞAN ELÇİLER
  if (gameState && gameState.envoys) {
    let hasActiveMoving = false;

    for (const [key, envoy] of Object.entries(gameState.envoys)) {
      if (envoy.phase === "departure" || envoy.phase === "arrival" || envoy.phase === "return") {
        hasActiveMoving = true;

        const fromPos = KEEP_COORDS[envoy.from_side] || { col: 13, row: 9 };
        const toPos   = KEEP_COORDS[envoy.to_side]   || { col: 13, row: 9 };
        const centerPos = { col: 13, row: 9 };

        let curCol = centerPos.col;
        let curRow = centerPos.row;

        if (envoy.phase === "departure") {
          curCol = Math.round((fromPos.col * 2 + centerPos.col) / 3);
          curRow = Math.round((fromPos.row * 2 + centerPos.row) / 3);
        } else if (envoy.phase === "arrival") {
          curCol = toPos.col;
          curRow = toPos.row;
        } else if (envoy.phase === "return") {
          curCol = Math.round((toPos.col + fromPos.col * 2) / 3);
          curRow = Math.round((toPos.row + fromPos.row * 2) / 3);
        }

        const ep = hexToPixel(curCol, curRow);

        // Halka parıltısı
        const pulseRing = (Math.sin(animTimer * 4) + 1) * 3;
        ctx.beginPath();
        ctx.arc(ep.x, ep.y, (14 + pulseRing) * camera.zoom, 0, Math.PI * 2);
        ctx.fillStyle = "rgba(245, 158, 11, 0.25)";
        ctx.fill();
        ctx.strokeStyle = "#f59e0b";
        ctx.lineWidth = 2;
        ctx.stroke();

        if (ASSETS.envoy.complete) {
          const sz = 28 * camera.zoom;
          ctx.drawImage(ASSETS.envoy, ep.x - sz / 2, ep.y - sz / 2, sz, sz);
        }

        ctx.fillStyle = "#0f172a";
        ctx.fillRect(ep.x - 45 * camera.zoom, ep.y - 25 * camera.zoom, 90 * camera.zoom, 14 * camera.zoom);
        ctx.strokeStyle = "#f59e0b";
        ctx.lineWidth = 1;
        ctx.strokeRect(ep.x - 45 * camera.zoom, ep.y - 25 * camera.zoom, 90 * camera.zoom, 14 * camera.zoom);
        ctx.fillStyle = "#fef08a";
        ctx.font = `bold ${Math.round(9 * camera.zoom)}px Inter`;
        ctx.textAlign = "center";
        ctx.textBaseline = "middle";
        ctx.fillText(`📜 ELÇİ (${envoy.from_side} ➔ ${envoy.to_side})`, ep.x, ep.y - 18 * camera.zoom);
      }
    }

    const floatingInd = document.getElementById("envoy-floating-indicator");
    if (floatingInd) {
      if (hasActiveMoving) floatingInd.classList.remove("hidden");
      else floatingInd.classList.add("hidden");
    }
  }

  requestAnimationFrame(renderScene);
}

// ── WebSocket İletişimi ───────────────────────────────────────────
function initWebSocket() {
  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  const wsUrl = `${protocol}//${window.location.host}/ws`;

  socket = new WebSocket(wsUrl);

  socket.onopen = () => {
    console.log("[WS] 3 Krallık Arena Motoruna bağlandı.");
  };

  socket.onmessage = (event) => {
    const data = JSON.parse(event.data);
    handleServerMessage(data);
  };

  socket.onclose = () => {
    console.warn("[WS] Bağlantı koptu. Yeniden bağlanılıyor...");
    setTimeout(initWebSocket, 2000);
  };
}

function handleServerMessage(data) {
  if (data.type === "INIT_STATE") {
    mapTiles = data.map;
    gameState = data.state;
    updateUI();
    initRadarChart();
  } else if (data.type === "TURN_STARTED") {
    gameState.turn = data.turn;
    document.getElementById("turn-badge").innerText = data.turn;
    if (data.world_event) {
      appendDiplomacyEvent("🌍 DÜNYA", `${data.world_event.title}: ${data.world_event.description}`, "amber");
    }
  } else if (data.type === "DECISION_APPLIED") {
    gameState = data.state;
    appendThoughtCard(data.log);
    updateUI();
    updateRadarChart();
  } else if (data.type === "TURN_COMPLETED") {
    gameState = data.state;
    updateUI();
    updateRadarChart();
  } else if (data.type === "RESET_COMPLETED") {
    gameState = data.state;
    document.getElementById("thought-feed").innerHTML = '<div class="text-center py-8 text-slate-500 text-xs">Yeni 3 Krallık simülasyonu başlatıldı.</div>';
    document.getElementById("diplomacy-feed").innerHTML = '<div class="text-center py-4 text-slate-500 text-xs">Henüz diplomatik temas gerçekleşmedi.</div>';
    updateUI();
    updateRadarChart();
  }
}

// ── Mouse Zoom & Pan ─────────────────────────────────────────────
canvas.addEventListener("mousedown", (e) => {
  camera.isDragging = true;
  camera.dragStartX = e.clientX - camera.x;
  camera.dragStartY = e.clientY - camera.y;
});

window.addEventListener("mouseup", () => {
  camera.isDragging = false;
});

canvas.addEventListener("mousemove", (e) => {
  const rect = canvas.getBoundingClientRect();
  const mouseX = e.clientX - rect.left;
  const mouseY = e.clientY - rect.top;

  if (camera.isDragging) {
    camera.x = e.clientX - camera.dragStartX;
    camera.y = e.clientY - camera.dragStartY;
    return;
  }

  const hex = pixelToHex(mouseX, mouseY);
  const found = mapTiles.find(t => t.col === hex.col && t.row === hex.row);

  if (found) {
    tooltip.classList.remove("hidden");
    tooltip.style.left = `${e.pageX + 16}px`;
    tooltip.style.top = `${e.pageY + 16}px`;

    let ownerName = "Tarafsız";
    if (found.owner === 1) ownerName = "OpenAI İmparatorluğu";
    if (found.owner === 2) ownerName = "DeepSeek Orman Krallığı";
    if (found.owner === 3) ownerName = "Anthropic Claude Bilgeliği";
    if (found.owner === 4) ownerName = "Vahşi Barbar Klanı";

    let tName = found.terrain.toUpperCase();
    if (found.terrain === "relic_island") tName = "💎 KADİM BÜYÜ ADASI (+15g/tur)";
    else if (found.terrain === "keep_1") tName = "🏰 OPENAI BAŞKENTİ (Kuzey)";
    else if (found.terrain === "keep_2") tName = "🏰 DEEPSEEK BAŞKENTİ (Güneydoğu)";
    else if (found.terrain === "keep_3") tName = "🏰 CLAUDE BİLGE KALESİ (Güneybatı)";
    else if (found.terrain === "bridge") tName = "🌉 TAŞ KÖPRÜ";

    tooltip.innerHTML = `
      <div class="font-mono font-bold text-slate-100 pb-1 border-b border-slate-700">Hex [${found.col}, ${found.row}]</div>
      <div class="pt-1 text-slate-300">Arazi: <span class="text-amber-400 font-semibold">${tName}</span></div>
      <div class="text-slate-300">Hakimiyet: <span class="text-sky-300 font-semibold">${ownerName}</span></div>
    `;
  } else {
    tooltip.classList.add("hidden");
  }
});

canvas.addEventListener("mouseleave", () => {
  tooltip.classList.add("hidden");
});

canvas.addEventListener("wheel", (e) => {
  e.preventDefault();
  const zoomFactor = e.deltaY < 0 ? 1.08 : 0.92;
  const newZoom = Math.min(Math.max(camera.zoom * zoomFactor, 0.7), 2.2);

  const rect = canvas.getBoundingClientRect();
  const mouseX = e.clientX - rect.left;
  const mouseY = e.clientY - rect.top;

  camera.x = mouseX - (mouseX - camera.x) * (newZoom / camera.zoom);
  camera.y = mouseY - (mouseY - camera.y) * (newZoom / camera.zoom);
  camera.zoom = newZoom;
}, { passive: false });

// ── UI Dashboard Updater (3 Krallık) ─────────────────────────────
function updateUI() {
  if (!gameState) return;

  document.getElementById("turn-badge").innerText = gameState.turn;

  // İkili İlişkiler Özeti
  const dipBadge = document.getElementById("diplomacy-badge");
  let warCount = 0;
  let pactCount = 0;

  if (gameState.relations) {
    for (const rel of Object.values(gameState.relations)) {
      if (rel.war_turns > 0) warCount++;
      if (rel.pact_turns > 0) pactCount++;
    }
  }

  if (warCount > 0) {
    dipBadge.className = "bg-rose-950 text-rose-400 border border-rose-600 px-3 py-1.5 rounded-lg font-bold flex items-center gap-1.5 animate-bounce shadow-lg";
    dipBadge.innerHTML = `<span class="w-2 h-2 rounded-full bg-rose-500 animate-ping"></span> 🚨 SICAK SAVAŞ (${warCount} Cephe)`;
  } else if (pactCount > 0) {
    dipBadge.className = "bg-sky-950 text-sky-300 border border-sky-600/50 px-3 py-1.5 rounded-lg font-semibold flex items-center gap-1.5";
    dipBadge.innerHTML = `📜 Aktif İttifak/Paktlar (${pactCount} Anlaşma)`;
  } else if (gameState.first_contact) {
    dipBadge.className = "bg-emerald-950 text-emerald-400 border border-emerald-500/30 px-3 py-1.5 rounded-lg font-semibold flex items-center gap-1.5";
    dipBadge.innerHTML = `🌍 3 Krallık Teması Sağlandı`;
  }

  document.getElementById("island-owner").innerText = gameState.island_controller || "Tarafsız";

  // 1. OpenAI
  const s1 = gameState.sides["1"];
  if (s1) {
    document.getElementById("s1-gold").innerText = s1.gold;
    document.getElementById("s1-wood").innerText = s1.wood;
    document.getElementById("s1-stone").innerText = s1.stone;
    document.getElementById("s1-units").innerText = s1.units;
    document.getElementById("s1-ships").innerText = s1.ships;
    document.getElementById("s1-workers").innerText = `${s1.workers} / 4`;
  }

  // 2. DeepSeek
  const s2 = gameState.sides["2"];
  if (s2) {
    document.getElementById("s2-gold").innerText = s2.gold;
    document.getElementById("s2-wood").innerText = s2.wood;
    document.getElementById("s2-stone").innerText = s2.stone;
    document.getElementById("s2-units").innerText = s2.units;
    document.getElementById("s2-ships").innerText = s2.ships;
    document.getElementById("s2-workers").innerText = `${s2.workers} / 4`;
  }

  // 3. Anthropic Claude
  const s3 = gameState.sides["3"];
  if (s3) {
    document.getElementById("s3-gold").innerText = s3.gold;
    document.getElementById("s3-wood").innerText = s3.wood;
    document.getElementById("s3-stone").innerText = s3.stone;
    document.getElementById("s3-units").innerText = s3.units;
    document.getElementById("s3-ships").innerText = s3.ships;
    document.getElementById("s3-workers").innerText = `${s3.workers} / 4`;
  }
}

// ── Thought Stream Kartları ───────────────────────────────────────
function appendThoughtCard(log) {
  const feed = document.getElementById("thought-feed");
  if (feed.querySelector(".text-center")) {
    feed.innerHTML = "";
  }

  let borderColor = "border-openaiblue/50 shadow-openaiblue/10";
  let nameColor = "text-openaiblue";
  let avatar = "assets/units/leader_openai.png";

  if (log.side_id === 2) {
    borderColor = "border-deepseekred/50 shadow-deepseekred/10";
    nameColor = "text-deepseekred";
    avatar = "assets/units/leader_deepseek.png";
  } else if (log.side_id === 3) {
    borderColor = "border-amber-500/50 shadow-amber-500/10";
    nameColor = "text-amber-400";
    avatar = "assets/units/leader_claude.png";
  }

  const actionsBadges = log.actions.map(act => {
    const val = act.unit || act.building || act.tree || act.stance || act.target || "";
    return `<span class="bg-slate-900 border border-slate-700 px-1.5 py-0.5 rounded text-[10px] text-slate-300 font-mono">${act.type}: ${val}</span>`;
  }).join(" ");

  const card = document.createElement("div");
  card.className = `bg-cardbg border ${borderColor} rounded-xl p-3 shadow-lg space-y-2 text-xs transition-all duration-300 hover:border-slate-400`;
  card.innerHTML = `
    <div class="flex items-center justify-between">
      <div class="flex items-center gap-2">
        <img src="${avatar}" class="w-5 h-5 rounded object-contain bg-slate-900 p-0.5 border border-slate-700">
        <span class="font-mono font-bold ${nameColor}">${log.name} (T${log.turn})</span>
      </div>
      <span class="text-[10px] text-slate-400 font-mono bg-slate-900 px-1.5 py-0.5 rounded">${log.latency_ms} ms</span>
    </div>
    <p class="text-slate-300 leading-relaxed italic">"${log.thought}"</p>
    <div class="flex flex-wrap gap-1 pt-1 border-t border-slate-700/60">
      ${actionsBadges}
    </div>
  `;

  feed.prepend(card);

  if (log.proposal && log.proposal !== "null") {
    const targetTag = log.target ? ` ➔ ${log.target}` : "";
    const colTag = log.side_id === 1 ? "blue" : (log.side_id === 2 ? "rose" : "amber");
    appendDiplomacyEvent(log.name + targetTag, `[${log.proposal}] ${log.message || ""}`, colTag);
  }
}

function appendDiplomacyEvent(from, message, color) {
  const feed = document.getElementById("diplomacy-feed");
  if (feed.querySelector(".text-center")) {
    feed.innerHTML = "";
  }

  const colorClass = color === "blue" ? "text-openaiblue" : color === "rose" ? "text-deepseekred" : "text-amber-400";
  const borderClass = color === "blue" ? "border-openaiblue/30" : color === "rose" ? "border-deepseekred/30" : "border-amber-500/30";

  const item = document.createElement("div");
  item.className = `bg-cardbg border ${borderClass} rounded-lg p-2 flex items-start gap-2 shadow`;
  item.innerHTML = `
    <span class="text-base">📜</span>
    <div class="flex-1">
      <strong class="${colorClass}">${from}:</strong>
      <span class="text-slate-300">${message}</span>
    </div>
  `;
  feed.prepend(item);
}

// ── 6D Radar Benchmark Grafiği (3 Model Kıyaslaması) ──────────────
function initRadarChart() {
  const ctxRadar = document.getElementById("radar-chart").getContext("2d");

  radarChart = new Chart(ctxRadar, {
    type: "radar",
    data: {
      labels: ["AGG (Saldırganlık)", "ECO (Ekonomi)", "TRU (Güvenilirlik)", "ADP (Adaptasyon)", "DEC (Aldatma)", "LTP (Planlama)"],
      datasets: [
        {
          label: "OpenAI",
          data: [0, 0, 5, 0, 0, 0],
          borderColor: "#38bdf8",
          backgroundColor: "rgba(56, 189, 248, 0.20)",
          borderWidth: 2,
          pointBackgroundColor: "#38bdf8",
        },
        {
          label: "DeepSeek",
          data: [0, 0, 5, 0, 0, 0],
          borderColor: "#f43f5e",
          backgroundColor: "rgba(244, 63, 94, 0.20)",
          borderWidth: 2,
          pointBackgroundColor: "#f43f5e",
        },
        {
          label: "Claude",
          data: [0, 0, 5, 0, 0, 0],
          borderColor: "#f59e0b",
          backgroundColor: "rgba(245, 158, 11, 0.20)",
          borderWidth: 2,
          pointBackgroundColor: "#f59e0b",
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: {
        r: {
          min: 0,
          max: 10,
          ticks: { stepSize: 2, color: "#64748b", backdropColor: "transparent", font: { size: 9 } },
          grid: { color: "rgba(51, 65, 85, 0.8)" },
          angleLines: { color: "rgba(51, 65, 85, 0.8)" },
          pointLabels: { color: "#cbd5e1", font: { size: 10, family: "Inter", weight: "bold" } }
        }
      },
      plugins: {
        legend: {
          position: "top",
          labels: { color: "#e2e8f0", font: { family: "Orbitron", size: 10 } }
        }
      }
    }
  });
}

function updateRadarChart() {
  if (!radarChart || !gameState) return;

  const s1 = gameState.sides["1"];
  const s2 = gameState.sides["2"];
  const s3 = gameState.sides["3"];

  if (s1 && s1.benchmark) {
    radarChart.data.datasets[0].data = [
      s1.benchmark.AGG || 0, s1.benchmark.ECO || 0, s1.benchmark.TRU || 5,
      s1.benchmark.ADP || 0, s1.benchmark.DEC || 0, s1.benchmark.LTP || 0
    ];
  }

  if (s2 && s2.benchmark) {
    radarChart.data.datasets[1].data = [
      s2.benchmark.AGG || 0, s2.benchmark.ECO || 0, s2.benchmark.TRU || 5,
      s2.benchmark.ADP || 0, s2.benchmark.DEC || 0, s2.benchmark.LTP || 0
    ];
  }

  if (s3 && s3.benchmark) {
    radarChart.data.datasets[2].data = [
      s3.benchmark.AGG || 0, s3.benchmark.ECO || 0, s3.benchmark.TRU || 5,
      s3.benchmark.ADP || 0, s3.benchmark.DEC || 0, s3.benchmark.LTP || 0
    ];
  }

  radarChart.update();
}

// ── Buton Olay Dinleyicileri ──────────────────────────────────────
document.getElementById("btn-start").addEventListener("click", () => {
  if (socket && socket.readyState === WebSocket.OPEN) {
    socket.send(JSON.stringify({ action: "START" }));
  }
});

document.getElementById("btn-pause").addEventListener("click", () => {
  if (socket && socket.readyState === WebSocket.OPEN) {
    socket.send(JSON.stringify({ action: "PAUSE" }));
  }
});

document.getElementById("btn-step").addEventListener("click", () => {
  if (socket && socket.readyState === WebSocket.OPEN) {
    socket.send(JSON.stringify({ action: "STEP" }));
  }
});

document.getElementById("btn-reset").addEventListener("click", () => {
  if (socket && socket.readyState === WebSocket.OPEN) {
    socket.send(JSON.stringify({ action: "RESET" }));
  }
});

document.getElementById("btn-report").addEventListener("click", () => {
  window.open("/api/report", "_blank");
});

window.addEventListener("DOMContentLoaded", () => {
  initWebSocket();
  requestAnimationFrame(renderScene);
});
