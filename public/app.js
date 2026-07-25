/* Didikids Parc — application de gestion des abonnements */
"use strict";

const $ = (sel, el = document) => el.querySelector(sel);
const app = $("#app");

const state = {
  user: null,
  page: "accueil",
  scanTarget: null,   // fonction qui reçoit les UID scannés (SSE ou clavier)
  sse: null,
};

/* ---------------------------------------------------------- utilitaires */

const GNF = (n) => (n == null ? "—" : new Intl.NumberFormat("fr-FR").format(n) + " GNF");
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) =>
  ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const fmtDate = (d) => (d ? d.split("-").reverse().join("/") : "—");
const fmtDateTime = (dt) => (dt ? fmtDate(dt.slice(0, 10)) + " à " + dt.slice(11, 16) : "—");
const todayISO = () => {
  const d = new Date();
  return d.getFullYear() + "-" + String(d.getMonth() + 1).padStart(2, "0") + "-" +
         String(d.getDate()).padStart(2, "0");
};

async function api(path, opts = {}) {
  const res = await fetch("/api" + path, {
    headers: { "Content-Type": "application/json" },
    ...opts,
    body: opts.body ? JSON.stringify(opts.body) : undefined,
  });
  const data = await res.json().catch(() => ({}));
  if (res.status === 401 && state.user) { state.user = null; renderLogin(); throw new Error("Session expirée"); }
  if (!res.ok) throw new Error(data.error || "Erreur " + res.status);
  return data;
}

function toast(msg, kind = "") {
  const el = document.createElement("div");
  el.className = "toast " + kind;
  el.textContent = msg;
  $("#toast-zone").appendChild(el);
  setTimeout(() => el.remove(), 3800);
}

function beep(ok) {
  try {
    const ctx = new (window.AudioContext || window.webkitAudioContext)();
    const play = (freq, start, dur) => {
      const o = ctx.createOscillator(), g = ctx.createGain();
      o.connect(g); g.connect(ctx.destination);
      o.frequency.value = freq; g.gain.value = 0.12;
      o.start(ctx.currentTime + start); o.stop(ctx.currentTime + start + dur);
    };
    if (ok) { play(880, 0, 0.12); play(1320, 0.13, 0.18); }
    else { play(220, 0, 0.4); }
  } catch (e) { /* audio non disponible */ }
}

function modal(html, wide = false) {
  const bg = document.createElement("div");
  bg.className = "modal-bg";
  bg.innerHTML = `<div class="modal ${wide ? "modal-wide" : ""}">${html}</div>`;
  bg.addEventListener("mousedown", (e) => { if (e.target === bg) close(); });
  document.body.appendChild(bg);
  const close = () => bg.remove();
  return { el: bg, close };
}

/* ---------------------------------------------------------- flux scan RFID */

function connectSSE() {
  if (state.sse) state.sse.close();
  state.sse = new EventSource("/api/events");
  state.sse.onmessage = (e) => {
    try {
      const msg = JSON.parse(e.data);
      if (msg.type === "scan" && state.scanTarget) state.scanTarget(msg.uid);
    } catch (err) { /* ignorer */ }
  };
}

/* ---------------------------------------------------------- connexion */

function renderLogin() {
  state.scanTarget = null;
  app.innerHTML = `
    <div class="login-wrap">
      <div class="login-card">
        <div class="login-logo">🐻</div>
        <h1>Didikids <span class="accent">Parc</span></h1>
        <div class="login-sub">Gestion des abonnements</div>
        <form id="login-form">
          <div class="field"><label>Nom d'utilisateur</label>
            <input id="lg-user" autocomplete="username" required autofocus></div>
          <div class="field"><label>Mot de passe</label>
            <input id="lg-pass" type="password" autocomplete="current-password" required></div>
          <button class="btn btn-green" style="width:100%; justify-content:center" type="submit">Se connecter</button>
        </form>
      </div>
    </div>`;
  $("#login-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    try {
      const data = await api("/login", { method: "POST", body: { username: $("#lg-user").value, password: $("#lg-pass").value } });
      state.user = data.user;
      connectSSE();
      go("accueil");
    } catch (err) { toast(err.message, "err"); }
  });
}

/* ---------------------------------------------------------- structure */

const PAGES = [
  { id: "accueil", icon: "🎟️", label: "Accueil / Entrées", roles: ["admin", "agent"] },
  { id: "membres", icon: "🧒", label: "Membres", roles: ["admin", "agent"] },
  { id: "abonnements", icon: "💳", label: "Abonnements", roles: ["admin"] },
  { id: "paiements", icon: "💰", label: "Paiements", roles: ["admin"] },
  { id: "visites", icon: "🕐", label: "Historique visites", roles: ["admin", "agent"] },
  { id: "dashboard", icon: "📊", label: "Tableau de bord", roles: ["admin"] },
  { id: "employes", icon: "👥", label: "Employés", roles: ["admin"] },
  { id: "parametres", icon: "⚙️", label: "Paramètres", roles: ["admin"] },
];

function go(page) {
  state.page = page;
  state.scanTarget = null;
  renderLayout();
}

function renderLayout() {
  const navItems = PAGES.filter((p) => p.roles.includes(state.user.role));
  app.innerHTML = `
    <div class="layout">
      <aside class="sidebar">
        <div class="brand">🐻 Didikids <span class="accent">Parc</span></div>
        <nav class="nav">
          ${navItems.map((p) => `
            <button data-page="${p.id}" class="${state.page === p.id ? "active" : ""}">
              <span class="icon">${p.icon}</span> ${p.label}
            </button>`).join("")}
        </nav>
        <div class="user-box">
          <div class="name">${esc(state.user.full_name)}</div>
          <div class="role">${state.user.role === "admin" ? "Administrateur" : "Agent accueil"}</div>
          <button class="btn btn-ghost btn-sm" id="logout-btn">Déconnexion</button>
        </div>
      </aside>
      <main class="main" id="page-content"></main>
    </div>`;
  app.querySelectorAll("[data-page]").forEach((b) =>
    b.addEventListener("click", () => go(b.dataset.page)));
  $("#logout-btn").addEventListener("click", async () => {
    await api("/logout", { method: "POST", body: {} }).catch(() => {});
    state.user = null;
    if (state.sse) state.sse.close();
    renderLogin();
  });
  const renderers = {
    accueil: renderAccueil, membres: renderMembres, abonnements: renderAbonnements,
    paiements: renderPaiements, visites: renderVisites, dashboard: renderDashboard,
    employes: renderEmployes, parametres: renderParametres,
  };
  renderers[state.page]();
}

/* ---------------------------------------------------------- page accueil */

async function renderAccueil() {
  const c = $("#page-content");
  c.innerHTML = `
    <div class="page-head"><h2>🎟️ Contrôle des entrées</h2>
      <span class="badge badge-green" id="sse-badge">Lecteur en attente…</span></div>
    <div class="checkin-grid">
      <div>
        <div class="card scan-box">
          <div class="wave pulse">📶</div>
          <h3>Présentez la carte</h3>
          <div class="hint">Le passage est validé automatiquement dès la lecture de la carte</div>
          <input class="scan-input" id="scan-input" placeholder="ou saisir l'UID ici"
                 autocomplete="off" spellcheck="false">
        </div>
        <div id="checkin-result"></div>
      </div>
      <div class="card">
        <h3 class="section-title">Passages du jour</h3>
        <div id="today-visits"><div class="empty">Chargement…</div></div>
      </div>
    </div>`;

  const input = $("#scan-input");
  input.focus();
  // Garder le focus pour les lecteurs qui émulent un clavier
  const refocus = setInterval(() => {
    if (state.page === "accueil" && !document.querySelector(".modal-bg") &&
        document.activeElement !== input) input.focus();
  }, 1500);

  input.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && input.value.trim()) {
      doCheckin(input.value.trim());
      input.value = "";
    }
  });

  state.scanTarget = (uid) => {
    if (document.querySelector(".modal-bg")) return; // une fenêtre est ouverte
    $("#sse-badge").textContent = "Lecteur connecté ✓";
    doCheckin(uid);
  };

  async function doCheckin(uid) {
    try {
      const r = await api("/checkin", { method: "POST", body: { uid } });
      showResult(r);
      beep(r.allowed);
      loadTodayVisits();
    } catch (err) { toast(err.message, "err"); }
  }

  function showResult(r) {
    const zone = $("#checkin-result");
    if (!zone) { clearInterval(refocus); return; }
    if (r.allowed) {
      const m = r.member, s = m.current_subscription;
      const entries = s ? (s.entries_left == null ? "∞" : s.entries_left) : "0";
      const expiry = s ? fmtDate(s.end_date) : (m.subscriptions[0] ? fmtDate(m.subscriptions[0].end_date) : "—");
      const subName = s ? s.type_name : (m.subscriptions[0] ? m.subscriptions[0].type_name : "");
      zone.innerHTML = `
        <div class="result-card result-ok">
          <div class="verdict">✅ ENTRÉE AUTORISÉE</div>
          <div class="member-name">${esc(m.child_name)}</div>
          <div class="sub-line">${esc(m.code)} · ${esc(subName)}</div>
          <div class="result-stats">
            <div class="stat"><div class="v">${entries}</div><div class="l">Entrées restantes</div></div>
            <div class="stat"><div class="v" style="font-size:17px; padding-top:6px">${expiry}</div><div class="l">Expire le</div></div>
          </div>
          ${r.already_today ? `<div class="warn-line">⚠️ Déjà passé ${r.already_today} fois aujourd'hui</div>` : ""}
        </div>`;
    } else {
      zone.innerHTML = `
        <div class="result-card result-no">
          <div class="verdict">⛔ ENTRÉE REFUSÉE</div>
          ${r.member ? `<div class="member-name">${esc(r.member.child_name)}</div>
                        <div class="sub-line">${esc(r.member.code)}</div>` : ""}
          <div class="warn-line" style="background:#fff; color:var(--red)">${esc(r.reason)}</div>
          <div class="sub-line mt">UID : ${esc(r.uid)}</div>
        </div>`;
    }
  }

  async function loadTodayVisits() {
    const visits = await api("/visits").catch(() => []);
    const zone = $("#today-visits");
    if (!zone) return;
    const todays = visits.filter((v) => v.visited_at.startsWith(todayISO()));
    const okCount = todays.filter((v) => v.result === "ok").length;
    zone.innerHTML = todays.length === 0
      ? `<div class="empty">Aucun passage aujourd'hui</div>`
      : `<div class="muted" style="margin-bottom:8px">${okCount} entrée(s) validée(s)</div>
         <table class="data"><tbody>
          ${todays.slice(0, 15).map((v) => `
            <tr><td>${v.visited_at.slice(11, 16)}</td>
                <td>${esc(v.child_name || "Carte inconnue")}</td>
                <td>${v.result === "ok" ? '<span class="badge badge-green">OK</span>'
                    : `<span class="badge badge-red" title="${esc(v.refusal_reason)}">Refus</span>`}</td></tr>`).join("")}
         </tbody></table>`;
  }
  loadTodayVisits();
}

/* ---------------------------------------------------------- page membres */

async function renderMembres() {
  const c = $("#page-content");
  const isAdmin = state.user.role === "admin";
  c.innerHTML = `
    <div class="page-head"><h2>🧒 Membres</h2>
      <div style="display:flex; gap:10px">
        <input class="search-input" id="mb-search" placeholder="🔍 Rechercher nom, téléphone, code…">
        ${isAdmin ? '<button class="btn btn-yellow" id="mb-new">+ Nouveau membre</button>' : ""}
      </div></div>
    <div class="card"><div id="mb-list"><div class="empty">Chargement…</div></div></div>`;

  let searchTimer;
  $("#mb-search").addEventListener("input", () => {
    clearTimeout(searchTimer);
    searchTimer = setTimeout(load, 250);
  });
  if (isAdmin) $("#mb-new").addEventListener("click", () => memberForm());

  async function load() {
    const q = encodeURIComponent($("#mb-search").value.trim());
    const members = await api("/members?q=" + q).catch((e) => { toast(e.message, "err"); return []; });
    const zone = $("#mb-list");
    if (!zone) return;
    zone.innerHTML = members.length === 0
      ? `<div class="empty">Aucun membre trouvé</div>`
      : `<table class="data">
          <thead><tr><th>Code</th><th>Enfant</th><th>Parent</th><th>Téléphone</th>
          <th>Carte</th><th>Abonnement</th><th></th></tr></thead><tbody>
          ${members.map((m) => {
            const s = m.current_subscription;
            return `<tr>
              <td>${esc(m.code)}</td>
              <td><b>${esc(m.child_name)}</b></td>
              <td>${esc(m.parent_name || "—")}</td>
              <td>${esc(m.phone || "—")}</td>
              <td>${m.card_uid ? '<span class="badge badge-green">✓ Carte</span>' : '<span class="badge badge-gray">Aucune</span>'}</td>
              <td>${s ? `<span class="badge badge-green">${esc(s.type_name)}</span>
                         <span class="muted">${s.entries_left == null ? "∞" : s.entries_left} restantes · exp. ${fmtDate(s.end_date)}</span>`
                      : '<span class="badge badge-red">Inactif</span>'}</td>
              <td><button class="btn btn-ghost btn-sm" data-open="${m.id}">Ouvrir</button></td></tr>`;
          }).join("")}
         </tbody></table>`;
    zone.querySelectorAll("[data-open]").forEach((b) =>
      b.addEventListener("click", () => openMember(+b.dataset.open, load)));
  }
  load();
}

function memberForm(member, onSaved) {
  const m = member || {};
  const { el, close } = modal(`
    <h3>${m.id ? "Modifier le membre" : "Nouveau membre"}</h3>
    <form id="mb-form">
      <div class="grid-2">
        <div class="field"><label>Nom de l'enfant *</label><input id="f-child" value="${esc(m.child_name || "")}" required></div>
        <div class="field"><label>Date de naissance</label><input id="f-birth" type="date" value="${esc(m.birth_date || "")}"></div>
        <div class="field"><label>Nom du parent</label><input id="f-parent" value="${esc(m.parent_name || "")}"></div>
        <div class="field"><label>Téléphone</label><input id="f-phone" value="${esc(m.phone || "")}"></div>
      </div>
      <div class="field"><label>Email</label><input id="f-email" type="email" value="${esc(m.email || "")}"></div>
      <div class="field"><label>Notes</label><textarea id="f-notes" rows="2">${esc(m.notes || "")}</textarea></div>
      <div class="modal-actions">
        <button type="button" class="btn btn-ghost" id="f-cancel">Annuler</button>
        <button type="submit" class="btn btn-green">Enregistrer</button>
      </div>
    </form>`);
  $("#f-cancel", el).addEventListener("click", close);
  $("#mb-form", el).addEventListener("submit", async (e) => {
    e.preventDefault();
    const body = {
      child_name: $("#f-child", el).value, birth_date: $("#f-birth", el).value,
      parent_name: $("#f-parent", el).value, phone: $("#f-phone", el).value,
      email: $("#f-email", el).value, notes: $("#f-notes", el).value,
    };
    try {
      const saved = m.id
        ? await api("/members/" + m.id, { method: "PUT", body })
        : await api("/members", { method: "POST", body });
      toast("Membre enregistré ✓", "ok");
      close();
      if (onSaved) onSaved(saved);
    } catch (err) { toast(err.message, "err"); }
  });
}

async function openMember(id, onChange) {
  const isAdmin = state.user.role === "admin";
  let m = await api("/members/" + id).catch((e) => { toast(e.message, "err"); });
  if (!m) return;

  const { el, close } = modal("", true);
  el.addEventListener("remove", () => { state.scanTarget = null; });

  function render() {
    const s = m.current_subscription;
    const activeCard = m.cards.find((c) => c.status === "active");
    $(".modal", el).innerHTML = `
      <div class="flex-between">
        <h3>🧒 ${esc(m.child_name)} <span class="muted" style="font-size:14px">${esc(m.code)}</span></h3>
        <div>
          ${isAdmin ? `<button class="btn btn-ghost btn-sm" id="d-edit">✏️ Modifier</button>
                       <button class="btn btn-yellow btn-sm" id="d-sell">💳 Vendre un abonnement</button>` : ""}
        </div>
      </div>
      <div class="grid-2 mt">
        <div>
          <div class="muted">Parent : <b>${esc(m.parent_name || "—")}</b></div>
          <div class="muted">Téléphone : <b>${esc(m.phone || "—")}</b></div>
          <div class="muted">Total visites : <b>${m.visit_count}</b></div>
        </div>
        <div>
          ${s ? `<span class="badge badge-green">${esc(s.type_name)}</span>
                 <div class="muted mt">Entrées restantes : <b>${s.entries_left == null ? "Illimité" : s.entries_left}</b><br>
                 Valide du ${fmtDate(s.start_date)} au <b>${fmtDate(s.end_date)}</b></div>`
              : '<span class="badge badge-red">Aucun abonnement actif</span>'}
        </div>
      </div>
      <hr style="border:none; border-top:2px solid var(--green-pale); margin:16px 0">
      <div class="flex-between">
        <h3 class="section-title" style="margin:0">💳 Cartes RFID</h3>
        ${isAdmin ? '<button class="btn btn-green btn-sm" id="d-addcard">+ Attribuer une carte</button>' : ""}
      </div>
      <div id="d-cards" class="mt">
        ${m.cards.length === 0 ? '<div class="muted">Aucune carte attribuée</div>' : `
        <table class="data"><thead><tr><th>UID</th><th>N° carte</th><th>Statut</th><th>Attribuée le</th><th></th></tr></thead>
        <tbody>${m.cards.map((card) => `
          <tr><td><code>${esc(card.uid)}</code></td>
              <td>${esc(card.card_number || "—")}</td>
              <td>${card.status === "active" ? '<span class="badge badge-green">Active</span>'
                   : `<span class="badge badge-red" title="${esc(card.block_reason || "")}">Bloquée</span>`}</td>
              <td>${fmtDate(card.assigned_at.slice(0, 10))}</td>
              <td>${card.status === "active" && isAdmin
                    ? `<button class="btn btn-red btn-sm" data-block="${card.id}">Bloquer</button>` : ""}</td></tr>`).join("")}
        </tbody></table>`}
      </div>
      <h3 class="section-title mt">📋 Abonnements</h3>
      ${m.subscriptions.length === 0 ? '<div class="muted">Aucun abonnement</div>' : `
      <table class="data"><thead><tr><th>Type</th><th>Période</th><th>Entrées</th><th>Statut</th></tr></thead>
      <tbody>${m.subscriptions.map((sub) => {
        const expired = sub.end_date < todayISO();
        const stateBadge = sub.status === "cancelled" ? '<span class="badge badge-gray">Annulé</span>'
          : expired ? '<span class="badge badge-red">Expiré</span>'
          : sub.entries_left === 0 ? '<span class="badge badge-yellow">Épuisé</span>'
          : '<span class="badge badge-green">Actif</span>';
        return `<tr><td>${esc(sub.type_name)}</td>
          <td>${fmtDate(sub.start_date)} → ${fmtDate(sub.end_date)}</td>
          <td>${sub.entries_left == null ? "Illimité" : sub.entries_left + " / " + sub.entries_total}</td>
          <td>${stateBadge}</td></tr>`;
      }).join("")}</tbody></table>`}
      <div class="modal-actions"><button class="btn btn-ghost" id="d-close">Fermer</button></div>`;

    $("#d-close", el).addEventListener("click", () => { state.scanTarget = null; close(); if (onChange) onChange(); });
    if (isAdmin) {
      $("#d-edit", el).addEventListener("click", () => memberForm(m, (updated) => { m = updated; render(); }));
      $("#d-sell", el).addEventListener("click", () => sellSubscription(m, (updated) => { m = updated; render(); }));
      $("#d-addcard", el).addEventListener("click", assignCardFlow);
      el.querySelectorAll("[data-block]").forEach((b) =>
        b.addEventListener("click", async () => {
          if (!confirm("Bloquer cette carte (perdue/volée) ? Elle sera refusée à l'accueil.")) return;
          try {
            m = await api("/cards/" + b.dataset.block + "/block", { method: "POST", body: { reason: "Carte perdue" } });
            toast("Carte bloquée", "ok"); render();
          } catch (err) { toast(err.message, "err"); }
        }));
    }
  }

  function assignCardFlow() {
    const inner = modal(`
      <h3>Attribuer une carte RFID</h3>
      <div class="muted">Passez la carte sur le lecteur — l'UID se remplit automatiquement.</div>
      <div class="field mt"><label>UID de la carte *</label>
        <input id="ac-uid" class="scan-input" style="max-width:100%" placeholder="En attente de la carte…" autofocus></div>
      <div class="field"><label>Numéro imprimé sur la carte (optionnel)</label><input id="ac-num"></div>
      <div class="modal-actions">
        <button class="btn btn-ghost" id="ac-cancel">Annuler</button>
        <button class="btn btn-green" id="ac-save">Attribuer</button>
      </div>`);
    state.scanTarget = (uid) => { const f = $("#ac-uid", inner.el); if (f) f.value = uid; };
    $("#ac-cancel", inner.el).addEventListener("click", () => { state.scanTarget = null; inner.close(); });
    $("#ac-save", inner.el).addEventListener("click", async () => {
      try {
        m = await api("/cards", { method: "POST", body: {
          member_id: m.id, uid: $("#ac-uid", inner.el).value, card_number: $("#ac-num", inner.el).value } });
        toast("Carte attribuée ✓", "ok");
        state.scanTarget = null; inner.close(); render();
      } catch (err) { toast(err.message, "err"); }
    });
  }

  render();
}

/* ---------------------------------------------------------- vente d'abonnement */

async function sellSubscription(member, onSold) {
  const types = await api("/types").catch(() => []);
  const activeTypes = types.filter((t) => t.active);
  let selected = null;
  const { el, close } = modal(`
    <h3>💳 Vendre un abonnement — ${esc(member.child_name)}</h3>
    <div class="type-cards" id="s-types">
      ${activeTypes.map((t) => `
        <div class="type-card" data-type="${t.id}">
          <div class="tc-name">${esc(t.name)}</div>
          <div class="tc-price">${GNF(t.price)}</div>
          <div class="tc-info">${t.entries == null ? "Entrées illimitées" : t.entries + " entrée(s)"} · ${t.validity_days} jours</div>
        </div>`).join("")}
    </div>
    <div class="grid-2 mt">
      <div class="field"><label>Date de début</label><input id="s-start" type="date" value="${todayISO()}"></div>
      <div class="field"><label>Mode de paiement</label>
        <select id="s-method">
          <option value="especes">Espèces</option>
          <option value="orange_money">Orange Money</option>
          <option value="mtn_momo">MTN MoMo</option>
          <option value="carte">Carte bancaire</option>
        </select></div>
    </div>
    <div class="field"><label>Montant payé (GNF)</label><input id="s-amount" type="number" min="0"></div>
    <div class="modal-actions">
      <button class="btn btn-ghost" id="s-cancel">Annuler</button>
      <button class="btn btn-green" id="s-save" disabled>Encaisser et imprimer le reçu</button>
    </div>`, true);

  el.querySelectorAll("[data-type]").forEach((card) =>
    card.addEventListener("click", () => {
      el.querySelectorAll(".type-card").forEach((c) => c.classList.remove("selected"));
      card.classList.add("selected");
      selected = activeTypes.find((t) => t.id === +card.dataset.type);
      $("#s-amount", el).value = selected.price;
      $("#s-save", el).disabled = false;
    }));
  $("#s-cancel", el).addEventListener("click", close);
  $("#s-save", el).addEventListener("click", async () => {
    try {
      const r = await api("/subscriptions", { method: "POST", body: {
        member_id: member.id, type_id: selected.id,
        start_date: $("#s-start", el).value, method: $("#s-method", el).value,
        amount: +$("#s-amount", el).value || selected.price,
      } });
      toast("Abonnement enregistré ✓", "ok");
      close();
      if (onSold) onSold(r.member);
      printReceipt(r.receipt);
    } catch (err) { toast(err.message, "err"); }
  });
}

function printReceipt(r) {
  const METHODS = { especes: "Espèces", orange_money: "Orange Money", mtn_momo: "MTN MoMo", carte: "Carte bancaire" };
  $("#print-zone").innerHTML = `
    <div class="receipt">
      <div class="r-head">
        <div style="font-size:24px">🐻</div>
        <div class="r-title">${esc(r.park_name)}</div>
        <div>${esc(r.park_address || "")}</div>
        <div>${esc(r.park_phone || "")}</div>
      </div>
      <hr>
      <div class="r-row"><span>Reçu N°</span><b>${esc(r.receipt_number)}</b></div>
      <div class="r-row"><span>Date</span><span>${fmtDateTime(r.paid_at)}</span></div>
      <div class="r-row"><span>Caissier</span><span>${esc(r.cashier || "")}</span></div>
      <hr>
      <div class="r-row"><span>Membre</span><b>${esc(r.child_name)}</b></div>
      <div class="r-row"><span>Code</span><span>${esc(r.member_code)}</span></div>
      ${r.type_name ? `
        <div class="r-row"><span>Abonnement</span><b>${esc(r.type_name)}</b></div>
        <div class="r-row"><span>Validité</span><span>${fmtDate(r.start_date)} → ${fmtDate(r.end_date)}</span></div>
        <div class="r-row"><span>Entrées</span><span>${r.entries_total == null ? "Illimitées" : r.entries_total}</span></div>` : ""}
      <hr>
      <div class="r-row r-total"><span>TOTAL</span><span>${GNF(r.amount)}</span></div>
      <div class="r-row"><span>Paiement</span><span>${METHODS[r.method] || esc(r.method)}</span></div>
      <hr>
      <div class="r-foot">${esc(r.footer || "Merci de votre visite !")}</div>
    </div>`;
  setTimeout(() => window.print(), 150);
}

/* ---------------------------------------------------------- page abonnements (types) */

async function renderAbonnements() {
  const c = $("#page-content");
  c.innerHTML = `
    <div class="page-head"><h2>💳 Types d'abonnements</h2>
      <button class="btn btn-yellow" id="t-new">+ Nouveau type</button></div>
    <div class="muted" style="margin-bottom:14px">Pour vendre un abonnement : ouvrez la fiche du membre
      (page <b>Membres</b>) puis « Vendre un abonnement ».</div>
    <div class="type-cards" id="t-list"></div>`;

  async function load() {
    const types = await api("/types").catch(() => []);
    $("#t-list").innerHTML = types.map((t) => `
      <div class="type-card" style="${t.active ? "" : "opacity:.5"}">
        <div class="tc-name">${esc(t.name)}</div>
        <div class="tc-price">${GNF(t.price)}</div>
        <div class="tc-info">${t.entries == null ? "Entrées illimitées" : t.entries + " entrée(s)"} · ${t.validity_days} jours</div>
        ${t.active ? "" : '<div class="badge badge-gray mt">Désactivé</div>'}
        <button class="btn btn-ghost btn-sm mt" data-edit="${t.id}">Modifier</button>
      </div>`).join("");
    $("#t-list").querySelectorAll("[data-edit]").forEach((b) =>
      b.addEventListener("click", () => typeForm(types.find((t) => t.id === +b.dataset.edit), load)));
  }
  $("#t-new").addEventListener("click", () => typeForm(null, load));
  load();
}

function typeForm(t, onSaved) {
  const v = t || {};
  const { el, close } = modal(`
    <h3>${v.id ? "Modifier le type" : "Nouveau type d'abonnement"}</h3>
    <div class="field"><label>Nom *</label><input id="t-name" value="${esc(v.name || "")}" placeholder="ex : Mensuel 4 entrées"></div>
    <div class="grid-2">
      <div class="field"><label>Prix (GNF) *</label><input id="t-price" type="number" min="0" value="${v.price ?? ""}"></div>
      <div class="field"><label>Validité (jours) *</label><input id="t-days" type="number" min="1" value="${v.validity_days ?? 30}"></div>
    </div>
    <div class="field"><label>Nombre d'entrées (vide = illimité)</label>
      <input id="t-entries" type="number" min="1" value="${v.entries ?? ""}" placeholder="Illimité"></div>
    ${v.id ? `<div class="field"><label><input type="checkbox" id="t-active" ${v.active ? "checked" : ""}>
      Type actif (proposé à la vente)</label></div>` : ""}
    <div class="modal-actions">
      <button class="btn btn-ghost" id="t-cancel">Annuler</button>
      <button class="btn btn-green" id="t-save">Enregistrer</button>
    </div>`);
  $("#t-cancel", el).addEventListener("click", close);
  $("#t-save", el).addEventListener("click", async () => {
    try {
      await api("/types" + (v.id ? "/" + v.id : ""), { method: "POST", body: {
        name: $("#t-name", el).value, price: $("#t-price", el).value,
        validity_days: $("#t-days", el).value,
        entries: $("#t-entries", el).value || null,
        active: v.id ? $("#t-active", el).checked : true,
      } });
      toast("Type enregistré ✓", "ok"); close(); onSaved();
    } catch (err) { toast(err.message, "err"); }
  });
}

/* ---------------------------------------------------------- page paiements */

async function renderPaiements() {
  const c = $("#page-content");
  c.innerHTML = `
    <div class="page-head"><h2>💰 Paiements</h2></div>
    <div class="card">
      <div class="filters">
        <div class="field"><label>Du</label><input type="date" id="p-from"></div>
        <div class="field"><label>Au</label><input type="date" id="p-to"></div>
        <button class="btn btn-green" id="p-filter">Filtrer</button>
      </div>
      <div id="p-list"><div class="empty">Chargement…</div></div>
    </div>`;
  $("#p-filter").addEventListener("click", load);

  async function load() {
    const params = new URLSearchParams();
    if ($("#p-from").value) params.set("from", $("#p-from").value);
    if ($("#p-to").value) params.set("to", $("#p-to").value);
    const data = await api("/payments?" + params).catch((e) => { toast(e.message, "err"); return { payments: [], total: 0 }; });
    const zone = $("#p-list");
    if (!zone) return;
    zone.innerHTML = `
      <div class="flex-between" style="margin-bottom:10px">
        <span class="muted">${data.payments.length} paiement(s)</span>
        <span class="badge badge-yellow" style="font-size:15px">Total : ${GNF(data.total)}</span></div>
      ${data.payments.length === 0 ? '<div class="empty">Aucun paiement</div>' : `
      <table class="data"><thead><tr><th>Reçu</th><th>Date</th><th>Membre</th><th>Abonnement</th>
        <th>Mode</th><th>Caissier</th><th class="num">Montant</th><th></th></tr></thead>
      <tbody>${data.payments.map((p) => `
        <tr><td>${esc(p.receipt_number)}</td>
            <td>${fmtDateTime(p.paid_at)}</td>
            <td><b>${esc(p.child_name)}</b></td>
            <td>${esc(p.type_name || "—")}</td>
            <td>${esc(p.method)}</td>
            <td>${esc(p.cashier || "—")}</td>
            <td class="num"><b>${GNF(p.amount)}</b></td>
            <td><button class="btn btn-ghost btn-sm" data-print="${esc(p.receipt_number)}">🖨️ Reçu</button></td></tr>`).join("")}
      </tbody></table>`}`;
    zone.querySelectorAll("[data-print]").forEach((b) =>
      b.addEventListener("click", async () => {
        try { printReceipt(await api("/receipts/" + b.dataset.print)); }
        catch (err) { toast(err.message, "err"); }
      }));
  }
  load();
}

/* ---------------------------------------------------------- page visites */

async function renderVisites() {
  const c = $("#page-content");
  const isAdmin = state.user.role === "admin";
  c.innerHTML = `
    <div class="page-head"><h2>🕐 Historique des visites</h2></div>
    <div class="card">
      ${isAdmin ? `<div class="filters">
        <div class="field"><label>Du</label><input type="date" id="v-from"></div>
        <div class="field"><label>Au</label><input type="date" id="v-to"></div>
        <button class="btn btn-green" id="v-filter">Filtrer</button>
      </div>` : '<div class="muted" style="margin-bottom:12px">Visites du jour</div>'}
      <div id="v-list"><div class="empty">Chargement…</div></div>
    </div>`;
  if (isAdmin) $("#v-filter").addEventListener("click", load);

  async function load() {
    const params = new URLSearchParams();
    if (isAdmin && $("#v-from").value) params.set("from", $("#v-from").value);
    if (isAdmin && $("#v-to").value) params.set("to", $("#v-to").value);
    const visits = await api("/visits?" + params).catch((e) => { toast(e.message, "err"); return []; });
    const zone = $("#v-list");
    if (!zone) return;
    zone.innerHTML = visits.length === 0 ? '<div class="empty">Aucune visite</div>' : `
      <table class="data"><thead><tr><th>Date</th><th>Heure</th><th>Membre</th>
        <th>Résultat</th><th>Validé par</th></tr></thead>
      <tbody>${visits.map((v) => `
        <tr><td>${fmtDate(v.visited_at.slice(0, 10))}</td>
            <td>${v.visited_at.slice(11, 16)}</td>
            <td><b>${esc(v.child_name || "Carte inconnue")}</b> <span class="muted">${esc(v.member_code || "")}</span></td>
            <td>${v.result === "ok" ? '<span class="badge badge-green">Entrée OK</span>'
                 : `<span class="badge badge-red">${esc(v.refusal_reason || "Refusé")}</span>`}</td>
            <td>${esc(v.agent || "—")}</td></tr>`).join("")}
      </tbody></table>`;
  }
  load();
}

/* ---------------------------------------------------------- tableau de bord */

async function renderDashboard() {
  const c = $("#page-content");
  c.innerHTML = `<div class="page-head"><h2>📊 Tableau de bord</h2></div><div id="dash"><div class="empty">Chargement…</div></div>`;
  const d = await api("/dashboard").catch((e) => { toast(e.message, "err"); });
  if (!d || !$("#dash")) return;

  $("#dash").innerHTML = `
    <div class="tiles">
      <div class="tile accent-green"><div class="t-label">Membres actifs</div>
        <div class="t-value">${d.active_members}</div>
        <div class="t-sub">${d.total_members} membres au total</div></div>
      <div class="tile accent-yellow"><div class="t-label">Revenus du mois</div>
        <div class="t-value" style="font-size:24px">${GNF(d.revenue.month)}</div>
        <div class="t-sub">Aujourd'hui : ${GNF(d.revenue.today)}</div></div>
      <div class="tile accent-purple"><div class="t-label">Visites aujourd'hui</div>
        <div class="t-value">${d.visits.today}</div>
        <div class="t-sub">${d.visits.week} cette semaine · ${d.visits.month} ce mois</div></div>
      <div class="tile accent-orange"><div class="t-label">Nouveaux membres (mois)</div>
        <div class="t-value">${d.new_members_month}</div>
        <div class="t-sub">Revenu total : ${GNF(d.revenue.total)}</div></div>
    </div>
    <div class="card">
      <h3 class="section-title">Visites — 14 derniers jours</h3>
      <div class="chart-wrap" id="chart-days"></div>
    </div>
    <div class="grid-2" style="gap:18px">
      <div class="card">
        <h3 class="section-title">Heures de pointe (30 derniers jours)</h3>
        <div class="chart-wrap" id="chart-hours"></div>
      </div>
      <div class="card">
        <h3 class="section-title">⏳ Abonnements expirant sous 7 jours</h3>
        ${d.expiring_soon.length === 0 ? '<div class="empty">Aucune expiration proche</div>' : `
        <table class="data"><thead><tr><th>Membre</th><th>Type</th><th>Expire le</th><th>Téléphone</th></tr></thead>
        <tbody>${d.expiring_soon.map((s) => `
          <tr><td><b>${esc(s.child_name)}</b></td><td>${esc(s.type_name)}</td>
              <td><span class="badge badge-yellow">${fmtDate(s.end_date)}</span></td>
              <td>${esc(s.phone || "—")}</td></tr>`).join("")}
        </tbody></table>`}
      </div>
    </div>`;

  barChart($("#chart-days"), d.visits_by_day.map((x) => ({
    label: x.date.slice(8, 10) + "/" + x.date.slice(5, 7), value: x.count,
    tip: fmtDate(x.date) + " : " + x.count + " visite(s)",
  })));
  barChart($("#chart-hours"), d.peak_hours.map((x) => ({
    label: x.hour + "h", value: x.count,
    tip: x.hour + "h – " + (x.hour + 1) + "h : " + x.count + " visite(s)",
  })));
}

/* Graphique à barres SVG — une seule série, teinte verte Didikids,
   extrémités arrondies, grille discrète, info-bulle au survol. */
function barChart(container, data) {
  const W = Math.max(460, data.length * 34), H = 210;
  const padL = 34, padB = 26, padT = 14;
  const max = Math.max(1, ...data.map((d) => d.value));
  const bw = (W - padL - 8) / data.length;
  const y = (v) => padT + (H - padT - padB) * (1 - v / max);
  const ticks = [0, Math.ceil(max / 2), max];

  let svg = `<svg class="chart-svg" width="${W}" height="${H}" viewBox="0 0 ${W} ${H}" role="img">`;
  ticks.forEach((t) => {
    svg += `<line x1="${padL}" x2="${W - 4}" y1="${y(t)}" y2="${y(t)}" stroke="#e3efe4" stroke-width="1"/>
            <text x="${padL - 6}" y="${y(t) + 4}" text-anchor="end" font-size="11" fill="#7c8f7e">${t}</text>`;
  });
  data.forEach((d, i) => {
    const x = padL + i * bw + bw * 0.18;
    const w = bw * 0.64;
    const h = Math.max(d.value > 0 ? 3 : 0, y(0) - y(d.value));
    svg += `<rect class="bar-rect" x="${x.toFixed(1)}" y="${(y(0) - h).toFixed(1)}" width="${w.toFixed(1)}"
             height="${h.toFixed(1)}" rx="4" data-tip="${esc(d.tip)}"/>`;
    if (i % Math.ceil(data.length / 16) === 0 || data.length <= 16)
      svg += `<text x="${(x + w / 2).toFixed(1)}" y="${H - 8}" text-anchor="middle" font-size="11" fill="#7c8f7e">${esc(d.label)}</text>`;
  });
  svg += `<line x1="${padL}" x2="${W - 4}" y1="${y(0)}" y2="${y(0)}" stroke="#c9dfca" stroke-width="1.5"/></svg>`;
  container.innerHTML = svg;

  let tipEl = null;
  container.querySelectorAll(".bar-rect").forEach((r) => {
    r.addEventListener("mouseenter", (e) => {
      tipEl = document.createElement("div");
      tipEl.className = "chart-tooltip";
      tipEl.textContent = r.dataset.tip;
      document.body.appendChild(tipEl);
    });
    r.addEventListener("mousemove", (e) => {
      if (tipEl) { tipEl.style.left = e.clientX + "px"; tipEl.style.top = e.clientY + "px"; }
    });
    r.addEventListener("mouseleave", () => { if (tipEl) { tipEl.remove(); tipEl = null; } });
  });
}

/* ---------------------------------------------------------- page employés */

async function renderEmployes() {
  const c = $("#page-content");
  c.innerHTML = `
    <div class="page-head"><h2>👥 Employés & comptes</h2>
      <button class="btn btn-yellow" id="u-new">+ Nouvel employé</button></div>
    <div class="card"><div id="u-list"><div class="empty">Chargement…</div></div></div>`;
  $("#u-new").addEventListener("click", () => userForm(null, load));

  async function load() {
    const users = await api("/users").catch((e) => { toast(e.message, "err"); return []; });
    const zone = $("#u-list");
    if (!zone) return;
    zone.innerHTML = `
      <table class="data"><thead><tr><th>Employé</th><th>Poste</th><th>Téléphone</th>
        <th>Identifiant</th><th>Rôle</th><th>Statut</th><th></th></tr></thead>
      <tbody>${users.map((u) => `
        <tr><td><b>${esc(u.full_name || "—")}</b></td>
            <td>${esc(u.position || "—")}</td>
            <td>${esc(u.phone || "—")}</td>
            <td><code>${esc(u.username)}</code></td>
            <td>${u.role === "admin" ? '<span class="badge badge-purple">Administrateur</span>'
                 : '<span class="badge badge-green">Agent accueil</span>'}</td>
            <td>${u.active ? '<span class="badge badge-green">Actif</span>' : '<span class="badge badge-red">Désactivé</span>'}</td>
            <td><button class="btn btn-ghost btn-sm" data-edit="${u.id}">Modifier</button></td></tr>`).join("")}
      </tbody></table>`;
    zone.querySelectorAll("[data-edit]").forEach((b) =>
      b.addEventListener("click", () => userForm(users.find((u) => u.id === +b.dataset.edit), load)));
  }
  load();
}

function userForm(u, onSaved) {
  const isNew = !u;
  const v = u || {};
  const { el, close } = modal(`
    <h3>${isNew ? "Nouvel employé" : "Modifier — " + esc(v.full_name || v.username)}</h3>
    <div class="grid-2">
      <div class="field"><label>Nom complet *</label><input id="u-name" value="${esc(v.full_name || "")}"></div>
      <div class="field"><label>Téléphone</label><input id="u-phone" value="${esc(v.phone || "")}"></div>
      <div class="field"><label>Poste</label><input id="u-pos" value="${esc(v.position || "")}" placeholder="Agent accueil"></div>
      <div class="field"><label>Rôle *</label>
        <select id="u-role">
          <option value="agent" ${v.role === "agent" ? "selected" : ""}>Agent accueil</option>
          <option value="admin" ${v.role === "admin" ? "selected" : ""}>Administrateur</option>
        </select></div>
      ${isNew ? `<div class="field"><label>Identifiant *</label><input id="u-user" autocomplete="off"></div>` : ""}
      <div class="field"><label>${isNew ? "Mot de passe *" : "Nouveau mot de passe (laisser vide pour garder)"}</label>
        <input id="u-pass" type="password" autocomplete="new-password"></div>
    </div>
    ${!isNew ? `<div class="field"><label><input type="checkbox" id="u-active" ${v.active ? "checked" : ""}> Compte actif</label></div>` : ""}
    <div class="modal-actions">
      <button class="btn btn-ghost" id="u-cancel">Annuler</button>
      <button class="btn btn-green" id="u-save">Enregistrer</button>
    </div>`);
  $("#u-cancel", el).addEventListener("click", close);
  $("#u-save", el).addEventListener("click", async () => {
    try {
      const body = {
        full_name: $("#u-name", el).value, phone: $("#u-phone", el).value,
        position: $("#u-pos", el).value, role: $("#u-role", el).value,
      };
      if ($("#u-pass", el).value) body.password = $("#u-pass", el).value;
      if (isNew) {
        body.username = $("#u-user", el).value;
        await api("/users", { method: "POST", body });
      } else {
        body.active = $("#u-active", el).checked;
        await api("/users/" + v.id, { method: "POST", body });
      }
      toast("Employé enregistré ✓", "ok"); close(); onSaved();
    } catch (err) { toast(err.message, "err"); }
  });
}

/* ---------------------------------------------------------- page paramètres */

async function renderParametres() {
  const c = $("#page-content");
  const s = await api("/settings").catch(() => ({}));
  c.innerHTML = `
    <div class="page-head"><h2>⚙️ Paramètres</h2></div>
    <div class="card" style="max-width:560px">
      <div class="field"><label>Nom du parc</label><input id="set-name" value="${esc(s.park_name || "")}"></div>
      <div class="field"><label>Adresse</label><input id="set-addr" value="${esc(s.park_address || "")}"></div>
      <div class="field"><label>Téléphone</label><input id="set-phone" value="${esc(s.park_phone || "")}"></div>
      <div class="field"><label>Message en bas du reçu</label>
        <textarea id="set-footer" rows="2">${esc(s.receipt_footer || "")}</textarea></div>
      <button class="btn btn-green" id="set-save">Enregistrer</button>
    </div>
    <div class="card" style="max-width:560px">
      <h3 class="section-title">🔌 Lecteur RFID (ACR122U)</h3>
      <div class="muted">Lancez le pont sur ce poste :<br>
        <code>python3 bridge/acr122u_bridge.py</code><br><br>
        Le jeton de connexion s'affiche au démarrage du serveur.
        Les lecteurs « émulation clavier » fonctionnent aussi : cliquez simplement
        dans le champ de saisie de la page Accueil.</div>
    </div>`;
  $("#set-save").addEventListener("click", async () => {
    try {
      await api("/settings", { method: "POST", body: {
        park_name: $("#set-name").value, park_address: $("#set-addr").value,
        park_phone: $("#set-phone").value, receipt_footer: $("#set-footer").value,
      } });
      toast("Paramètres enregistrés ✓", "ok");
    } catch (err) { toast(err.message, "err"); }
  });
}

/* ---------------------------------------------------------- démarrage */

(async function init() {
  try {
    const me = await api("/me");
    state.user = me;
    connectSSE();
    go("accueil");
  } catch (e) {
    renderLogin();
  }
})();
