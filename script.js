// ── Estado da aplicacao ──────────────────────────────────────
const state = {
  servicos: [],
  abaAtiva: "todos",
  logs: {}, // id -> [{ id, nome, cor, msg, ts, classe }]
  contadores: {}, // id -> number
  totalMsgs: 0,
  sse: null,
};

// ── Boot ─────────────────────────────────────────────────────
async function boot() {
  const res = await fetch("/servicos");
  state.servicos = await res.json();

  state.logs["todos"] = [];
  state.servicos.forEach((s) => {
    state.logs[s.id] = [];
    state.contadores[s.id] = 0;
  });

  renderCards();
  renderTabs();
  conectarSSE();
}

// ── Renderizacao dos cards ────────────────────────────────────
function renderCards() {
  const grid = document.getElementById("cards-grid");
  grid.innerHTML = state.servicos
    .map(
      (s) => `
    <div class="card" id="card-${s.id}" style="--card-color: ${s.cor}">
      <div class="card-header">
        <span class="card-icone">${s.icone}</span>
        <span class="card-nome">${s.nome}</span>
      </div>
      <div class="card-badge">
        <div class="badge-dot" id="dot-${s.id}"></div>
        <span id="status-${s.id}">parado</span>
      </div>
      <div class="card-count" id="count-${s.id}">0</div>
      <div class="card-count-label">mensagens</div>
    </div>
  `,
    )
    .join("");
}

function atualizarCard(id, estado) {
  const card   = document.getElementById(`card-${id}`);
  const status = document.getElementById(`status-${id}`);
  if (!card) return;
  card.classList.toggle("ativo", estado === "rodando");
  status.textContent = estado;
}

function incrementarCard(id) {
  state.contadores[id] = (state.contadores[id] || 0) + 1;
  const el = document.getElementById(`count-${id}`);
  if (el) el.textContent = state.contadores[id];
}

// ── Renderizacao das abas ─────────────────────────────────────
function renderTabs() {
  const container = document.getElementById("tabs");
  const todas     = [{ id: "todos", nome: "Todos", icone: "&#128203;" }];
  const lista     = todas.concat(state.servicos);

  container.innerHTML = lista
    .map(
      (s) => `
    <div class="tab ${s.id === state.abaAtiva ? "ativa" : ""}"
         id="tab-${s.id}"
         onclick="trocarAba('${s.id}')">
      <span>${s.icone || ""}</span>
      ${s.nome}
      <span class="tab-count" id="badge-${s.id}">0</span>
    </div>
  `,
    )
    .join("");
}

function trocarAba(id) {
  state.abaAtiva = id;
  document.querySelectorAll(".tab").forEach((t) => t.classList.remove("ativa"));
  document.getElementById(`tab-${id}`)?.classList.add("ativa");
  renderLogsCompleto();
}

function atualizarBadges(id) {
  const b1 = document.getElementById(`badge-${id}`);
  const b2 = document.getElementById("badge-todos");
  if (b1) b1.textContent = state.logs[id]?.length || 0;
  if (b2) b2.textContent = state.logs["todos"]?.length || 0;
  document.getElementById("log-info").textContent = `${state.totalMsgs} mensagens`;
}

// ── Logs ──────────────────────────────────────────────────────
function classificar(msg) {
  if (msg.includes("[OK]"))                         return "ok";
  if (msg.includes("[FALHA]") || msg.includes("[ERRO]")) return "erro";
  if (msg.includes("[RETRY]") || msg.includes("[DLQ]"))  return "retry";
  if (msg.includes("[SISTEMA]"))                    return "sys";
  return "";
}

function adicionarLog(evento) {
  const { id, nome, cor, msg, ts } = evento;
  const classe  = classificar(msg);
  const entrada = { id, nome, cor, msg, ts, classe };

  state.logs["todos"].push(entrada);
  if (!state.logs[id]) state.logs[id] = [];
  state.logs[id].push(entrada);

  incrementarCard(id);
  state.totalMsgs++;
  atualizarBadges(id);

  const vazio = document.getElementById("log-empty");
  if (vazio) vazio.remove();

  if (state.abaAtiva === id || state.abaAtiva === "todos") {
    const body = document.getElementById("log-body");
    body.appendChild(criarLinhaLog(entrada, state.abaAtiva === "todos"));
    body.scrollTop = body.scrollHeight;
  }
}

function criarLinhaLog(entrada, mostrarTag) {
  const srv   = state.servicos.find((s) => s.id === entrada.id);
  const cor   = srv ? srv.cor : "#888";
  const tagBg = cor + "22";

  const row = document.createElement("div");
  row.className = "log-row";
  row.innerHTML = `
    <span class="log-ts">${entrada.ts}</span>
    ${mostrarTag ? `<span class="log-tag" style="color:${cor};background:${tagBg}">${entrada.nome}</span>` : ""}
    <span class="log-msg ${entrada.classe}">${esc(entrada.msg)}</span>
  `;
  return row;
}

function renderLogsCompleto() {
  const body  = document.getElementById("log-body");
  const lista = state.logs[state.abaAtiva] || [];
  body.innerHTML = "";

  if (lista.length === 0) {
    body.innerHTML = `
      <div class="log-empty" id="log-empty">
        <div class="log-empty-icon">&#128236;</div>
        <div class="log-empty-text">Nenhuma mensagem nesta aba.</div>
      </div>`;
    return;
  }

  const mostrarTag = state.abaAtiva === "todos";
  const frag       = document.createDocumentFragment();
  lista.forEach((e) => frag.appendChild(criarLinhaLog(e, mostrarTag)));
  body.appendChild(frag);
  body.scrollTop = body.scrollHeight;
}

function limparLogs() {
  Object.keys(state.logs).forEach((k) => (state.logs[k] = []));
  Object.keys(state.contadores).forEach((k) => {
    state.contadores[k] = 0;
    const el = document.getElementById(`count-${k}`);
    if (el) el.textContent = "0";
  });
  state.totalMsgs = 0;
  document.getElementById("log-info").textContent = "0 mensagens";
  document.querySelectorAll(".tab-count").forEach((b) => (b.textContent = "0"));
  renderLogsCompleto();
}

// ── SSE ───────────────────────────────────────────────────────
function conectarSSE() {
  if (state.sse) state.sse.close();
  state.sse = new EventSource("/eventos");

  state.sse.onopen = () => {
    document.getElementById("conn-dot").classList.add("ok");
    document.getElementById("conn-label").textContent = "conectado";
  };

  state.sse.onmessage = (e) => {
    const ev = JSON.parse(e.data);
    if (ev.tipo === "log")    adicionarLog(ev);
    if (ev.tipo === "status") {
      atualizarCard(ev.id, ev.estado);
      setFooter(`${ev.id}: ${ev.estado}`);
    }
  };

  state.sse.onerror = () => {
    document.getElementById("conn-dot").classList.remove("ok");
    document.getElementById("conn-label").textContent = "reconectando...";
    setTimeout(conectarSSE, 3000);
  };
}

// ── Acoes dos botoes ──────────────────────────────────────────
async function iniciarConsumidores() {
  await fetch("/iniciar-consumidores", { method: "POST" });
  setFooter("Consumidores iniciados. Aguardando mensagens...");
  toast("Consumidores iniciados!");
}

async function iniciarProdutorTeste() {
  const r = await fetch("/iniciar-produtor-teste", { method: "POST" });
  const d = await r.json();
  if (d.ok) {
    setFooter("Produtor de teste publicando 5 pedidos aleatórios...");
    toast("Pedidos de teste sendo enviados!");
  } else {
    toast(d.erro, true);
  }
}

async function pararTudo() {
  await fetch("/parar", { method: "POST" });
  setFooter("Todos os processos encerrados.");
  toast("Processos encerrados.");
}

// ── Modal de pedido manual ────────────────────────────────────
function abrirModalPedido() {
  document.getElementById("modal-overlay").classList.add("visivel");
  document.getElementById("modal-nome").focus();
}

function fecharModalPedido() {
  document.getElementById("modal-overlay").classList.remove("visivel");
  document.getElementById("form-pedido").reset();
  document.getElementById("modal-erro").textContent = "";
}

async function enviarPedidoManual() {
  const get = (id) => document.getElementById(id).value.trim();

  const campos = {
    cliente_nome:     get("modal-nome"),
    cliente_email:    get("modal-email"),
    produto_nome:     get("modal-produto"),
    produto_preco:    get("modal-preco"),
    quantidade:       get("modal-qtd"),
    forma_pagamento:  get("modal-pagamento"),
    endereco_rua:     get("modal-rua"),
    endereco_cidade:  get("modal-cidade"),
    endereco_estado:  get("modal-estado"),
    endereco_cep:     get("modal-cep"),
  };

  // Validação básica
  const obrigatorios = ["cliente_nome", "cliente_email", "produto_nome",
                        "produto_preco", "quantidade", "forma_pagamento"];
  const faltando = obrigatorios.filter((k) => !campos[k]);
  if (faltando.length) {
    document.getElementById("modal-erro").textContent =
      "Preencha todos os campos obrigatórios (*)";
    return;
  }

  const btn = document.getElementById("btn-enviar-pedido");
  btn.disabled    = true;
  btn.textContent = "Enviando...";

  const r = await fetch("/iniciar-produtor-manual", {
    method:  "POST",
    headers: { "Content-Type": "application/json" },
    body:    JSON.stringify(campos),
  });
  const d = await r.json();

  btn.disabled    = false;
  btn.textContent = "Enviar Pedido";

  if (d.ok) {
    fecharModalPedido();
    setFooter("Pedido manual publicado com sucesso.");
    toast("Pedido enviado!");
  } else {
    document.getElementById("modal-erro").textContent = d.erro;
  }
}

// Fecha modal ao clicar fora
document.addEventListener("DOMContentLoaded", () => {
  document.getElementById("modal-overlay").addEventListener("click", (e) => {
    if (e.target.id === "modal-overlay") fecharModalPedido();
  });
});

// ── Helpers ───────────────────────────────────────────────────
function setFooter(msg) {
  document.getElementById("footer-msg").textContent = msg;
}

function esc(str) {
  return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

let _toastTimer;
function toast(msg, erro = false) {
  const el = document.getElementById("toast");
  el.textContent = msg;
  el.className   = "toast show" + (erro ? " erro" : "");
  clearTimeout(_toastTimer);
  _toastTimer = setTimeout(() => el.classList.remove("show"), 3000);
}

// ── Inicia ────────────────────────────────────────────────────
boot();
