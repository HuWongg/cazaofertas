const NOMBRES = { falabella: "Falabella", ripley: "Ripley", paris: "Paris" };
const CONF = { alta: "Error probable", media: "Por confirmar", baja: "Solo según tienda", falso: "Descuento falso" };
const $ = (s) => document.querySelector(s);
const clp = (n) => "$" + Math.round(n).toLocaleString("es-CL");
const pct = (x) => Math.round(x * 100) + "%";

// Los datos se actualizan cada ~3 min en la rama "web-datos" del repo.
const [OWNER] = location.hostname.split(".");
const REPO = location.pathname.split("/").filter(Boolean)[0] || "cazaofertas";

const st = {
  ofertas: [],
  tiendas: new Set(["falabella", "ripley", "paris"]),
  tipos: new Set(["externo", "entre_tiendas", "caida", "historial"]),
  verFalsos: false,
  minDesc: 0.5,
  q: "",
  cat: "",
  orden: "desc",
  soloNuevas: false,
};

function guardarPrefs() {
  try {
    localStorage.setItem("caza:prefs2", JSON.stringify({
      tiendas: [...st.tiendas], tipos: [...st.tipos], minDesc: st.minDesc, orden: st.orden,
    }));
  } catch (e) { /* sin almacenamiento */ }
}
function cargarPrefs() {
  try {
    const p = JSON.parse(localStorage.getItem("caza:prefs2") || "null");
    if (!p) return;
    if (p.tiendas) st.tiendas = new Set(p.tiendas);
    if (p.tipos) st.tipos = new Set(p.tipos);
    if (p.minDesc) st.minDesc = p.minDesc;
    if (p.orden) st.orden = p.orden;
  } catch (e) { /* nada */ }
}

function hace(ts) {
  const s = Date.now() / 1000 - ts;
  if (s < 90) return "hace un momento";
  if (s < 3600) return `hace ${Math.round(s / 60)} min`;
  if (s < 86400) return `hace ${Math.round(s / 3600)} h`;
  return `hace ${Math.round(s / 86400)} d`;
}

function descPorTipo(o, t) {
  const e = o.externo || {};
  return {
    externo: Math.max(e.desc_tiendas || 0, e.desc_historial || 0),
    entre_tiendas: o.desc_cruzado || 0,
    caida: o.desc_caida || 0,
    historial: o.desc_historial || 0,
    declarado: o.desc_declarado || 0,
  }[t] || 0;
}

function descuentoVisible(o) {
  let d = 0;
  for (const t of o.tipos) if (st.tipos.has(t)) d = Math.max(d, descPorTipo(o, t));
  if (o.confianza === "falso") d = o.desc_declarado || 0;
  return d;
}

function referencias(o) {
  const out = [];
  const e = o.externo || {};
  if (o.tipos.includes("externo") && e.ref_tiendas && (e.desc_tiendas || 0) >= 0.5)
    out.push([e.ref_tiendas, `en otras tiendas (SoloTodo)`]);
  if (o.tipos.includes("entre_tiendas") && o.ref_cruzada) out.push([o.ref_cruzada, "en otra tienda"]);
  if (o.tipos.includes("caida") && o.precio_anterior) out.push([o.precio_anterior, "costaba hace poco"]);
  if (o.tipos.includes("externo") && e.ref_historial && (e.desc_historial || 0) >= 0.5)
    out.push([e.ref_historial, "precio habitual (SoloTodo)"]);
  if (o.tipos.includes("historial") && o.ref_historial) out.push([o.ref_historial, "su precio habitual"]);
  if (!out.length && o.precio_lista) out.push([o.precio_lista, "precio normal según la tienda"]);
  return out;
}

function sparkline(svg, h) {
  if (!h || h.length < 2) { svg.remove(); return; }
  const vals = h.map((x) => x[1]);
  const min = Math.min(...vals), max = Math.max(...vals);
  const rango = max - min || 1;
  const pts = vals.map((v, i) => [(i / (vals.length - 1)) * 116 + 2, 26 - ((v - min) / rango) * 22]);
  const ns = "http://www.w3.org/2000/svg";
  const pl = document.createElementNS(ns, "polyline");
  pl.setAttribute("points", pts.map((p) => p.join(",")).join(" "));
  const c = document.createElementNS(ns, "circle");
  const last = pts[pts.length - 1];
  c.setAttribute("cx", last[0]); c.setAttribute("cy", last[1]); c.setAttribute("r", 2.6);
  svg.append(pl, c);
}

function esc(s) {
  return String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}
function norm(s) {
  return String(s || "").normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();
}

function filaComparar(nombreTienda, clase, precio, url, titulo) {
  const li = document.createElement("li");
  li.innerHTML = `<a href="${esc(url)}" target="_blank" rel="noopener" title="${esc(titulo || "")}">`
    + `<span>${clase ? `<i class="dot ${clase}"></i> ` : "• "}${esc(nombreTienda)}</span>`
    + `<span><b>${clp(precio)}</b></span></a>`;
  return li;
}

function tarjeta(o) {
  const t = $("#tplCard").content.firstElementChild.cloneNode(true);
  const d = descuentoVisible(o);
  t.classList.add("c-" + o.confianza);
  t.querySelector(".img").href = o.url;
  const img = t.querySelector("img");
  if (o.img) { img.src = o.img; img.alt = o.nombre; } else img.remove();
  t.querySelector(".tienda").innerHTML = `<i class="dot ${o.tienda}"></i>${NOMBRES[o.tienda] || o.tienda}`
    + (o.vendedor && !["Falabella", "Ripley"].includes(o.vendedor) ? ` · <span style="font-weight:400">${esc(o.vendedor)}</span>` : "");
  const conf = t.querySelector(".conf");
  conf.textContent = CONF[o.confianza]; conf.classList.add(o.confianza);
  if (Date.now() / 1000 - o.desde < 3 * 3600 && o.confianza !== "falso") t.querySelector(".nuevo").hidden = false;
  t.querySelector(".nombre").textContent = o.nombre;
  t.querySelector(".nombre").title = o.nombre;
  t.querySelector(".badge").textContent = "-" + pct(d);
  t.querySelector(".ahora").textContent = clp(o.precio);
  const refs = referencias(o);
  t.querySelector(".antes").innerHTML = refs.map(([p, txt]) => `<div><s>${clp(p)}</s> ${txt}</div>`).join("");
  if (o.confianza === "falso" && o.externo) {
    const e = o.externo;
    t.querySelector(".antes").innerHTML = `<div><s>${clp(o.precio_lista)}</s> dice la tienda</div>`
      + (e.ref_tiendas ? `<div>pero otras tiendas: ${clp(e.ref_tiendas)}</div>` : "")
      + (e.ref_historial ? `<div>precio habitual: ${clp(e.ref_historial)}</div>` : "");
  }
  if (o.precio_tarjeta) t.querySelector(".tarjeta").textContent = `Con tarjeta de la tienda: ${clp(o.precio_tarjeta)}`;
  sparkline(t.querySelector(".spark"), o.historial);

  const det = t.querySelector(".comparar");
  const ul = det.querySelector("ul");
  let n = 0;
  for (const c of o.comparados || []) { ul.append(filaComparar(NOMBRES[c.tienda] || c.tienda, c.tienda, c.precio, c.url, c.nombre)); n++; }
  const e = o.externo;
  if (e) {
    for (const c of e.otras || []) { ul.append(filaComparar(c.tienda, "", c.precio, c.url, "")); n++; }
    const li = document.createElement("li");
    li.innerHTML = `<a class="st" href="${esc(e.url)}" target="_blank" rel="noopener"><span>Ver historial en SoloTodo</span><span>→</span></a>`;
    ul.append(li);
  }
  if (n || e) {
    det.hidden = false;
    det.querySelector("summary").textContent = n ? `Comparar con ${n} tienda${n > 1 ? "s" : ""}` : "Historial externo";
  }
  t.querySelector(".ir").href = o.url;
  t.querySelector(".visto").textContent = `Detectado ${hace(o.desde)}`;
  return t;
}

function visible(o, ahora, q) {
  if (!st.tiendas.has(o.tienda)) return false;
  if (o.confianza === "falso") { if (!st.verFalsos) return false; }
  else if (!o.tipos.some((t) => st.tipos.has(t))) return false;
  if (o.confianza !== "falso" && descuentoVisible(o) < st.minDesc) return false;
  if (st.cat && o.categoria !== st.cat) return false;
  if (st.soloNuevas && ahora - o.desde > 86400) return false;
  if (q.length) {
    const txt = norm(o.nombre + " " + o.marca + " " + o.categoria);
    if (!q.every((p) => txt.includes(p))) return false;
  }
  return true;
}

function render() {
  const q = norm(st.q).split(/\s+/).filter(Boolean);
  const ahora = Date.now() / 1000;
  const lista = st.ofertas.filter((o) => visible(o, ahora, q));
  const rango = { alta: 0, media: 1, baja: 2, falso: 3 };
  const orden = {
    desc: (a, b) => rango[a.confianza] - rango[b.confianza] || descuentoVisible(b) - descuentoVisible(a),
    nuevo: (a, b) => b.desde - a.desde,
    precio: (a, b) => a.precio - b.precio,
    ahorro: (a, b) => (((referencias(b)[0] || [0])[0]) - b.precio) - (((referencias(a)[0] || [0])[0]) - a.precio),
  }[st.orden];
  lista.sort(orden);
  $("#grilla").replaceChildren(...lista.slice(0, 300).map(tarjeta));
  $("#vacio").hidden = lista.length > 0;
  const altas = st.ofertas.filter((o) => o.confianza === "alta").length;
  $("#resumen").textContent = lista.length
    ? `${lista.length} resultado${lista.length > 1 ? "s" : ""}${lista.length > 300 ? " (mostrando 300)" : ""} · ${altas} errores probables en total`
    : "";
}

function pintarEstado(e) {
  const cont = $("#tiendasEstado");
  cont.replaceChildren();
  const filas = [];
  for (const t of ["falabella", "ripley", "paris"]) {
    const s = (e.tiendas || {})[t];
    const span = document.createElement("span");
    span.className = "est";
    let txt = "sin datos";
    if (s) {
      const atraso = Date.now() / 1000 - (s.ultimo_ok || 0);
      if (atraso > 30 * 60) span.classList.add("bad");
      else if (!s.ok || s.errores > 0) span.classList.add("warn");
      txt = s.ultimo_ok ? hace(s.ultimo_ok) : "con problemas";
      filas.push(`<tr><td><i class="dot ${t}"></i> ${NOMBRES[t]}</td><td>${(e.por_tienda || {})[t] || 0}</td>`
        + `<td>${s.productos}</td><td>${s.ultimo_ok ? hace(s.ultimo_ok) : "nunca"}</td>`
        + `<td>${s.barrido ? hace(s.barrido) : "—"}</td><td>${s.errores}</td></tr>`);
    }
    span.innerHTML = `<i></i>${NOMBRES[t]} · ${txt}`;
    span.title = s && s.detalle_errores && s.detalle_errores.length ? s.detalle_errores.join("\n") : "";
    cont.append(span);
  }
  $("#pie").innerHTML = `<p>Ciclo #${e.ciclo || e.corrida} · ${(e.catalogo || 0).toLocaleString("es-CL")} productos vigilados · `
    + `${e.verificados_solotodo || 0} verificados en SoloTodo · alertas: ${e.canal_alertas ? `activadas (${e.alertas_enviadas} enviadas)` : "no configuradas"}</p>`
    + `<table><tr><th>Tienda</th><th>En catálogo</th><th>Leídos último ciclo</th><th>Último OK</th><th>Inicio barrido actual</th><th>Errores</th></tr>${filas.join("")}</table>`;
}

function enlazar() {
  document.querySelectorAll("[data-tienda]").forEach((b) => {
    b.classList.toggle("on", st.tiendas.has(b.dataset.tienda));
    b.onclick = () => { const v = b.dataset.tienda; st.tiendas.has(v) ? st.tiendas.delete(v) : st.tiendas.add(v); b.classList.toggle("on"); guardarPrefs(); render(); };
  });
  document.querySelectorAll("[data-tipo]").forEach((b) => {
    b.classList.toggle("on", st.tipos.has(b.dataset.tipo));
    b.onclick = () => { const v = b.dataset.tipo; st.tipos.has(v) ? st.tipos.delete(v) : st.tipos.add(v); b.classList.toggle("on"); guardarPrefs(); render(); };
  });
  const r = $("#minDesc");
  r.value = Math.round(st.minDesc * 100);
  $("#minDescTxt").textContent = r.value + "%";
  r.oninput = () => { st.minDesc = r.value / 100; $("#minDescTxt").textContent = r.value + "%"; guardarPrefs(); render(); };
  $("#orden").value = st.orden;
  $("#orden").onchange = (e) => { st.orden = e.target.value; guardarPrefs(); render(); };
  let tmr;
  $("#buscar").oninput = (e) => { clearTimeout(tmr); tmr = setTimeout(() => { st.q = e.target.value; render(); }, 150); };
  $("#categoria").onchange = (e) => { st.cat = e.target.value; render(); };
  $("#soloNuevas").onchange = (e) => { st.soloNuevas = e.target.checked; render(); };
  $("#verFalsos").onchange = (e) => { st.verFalsos = e.target.checked; render(); };
}

async function obtenerDatos() {
  // 1) Lo más fresco: rama web-datos (se actualiza cada ciclo).
  try {
    const rama = await fetch(`https://api.github.com/repos/${OWNER}/${REPO}/branches/web-datos`).then((r) => r.ok ? r.json() : null);
    const sha = rama && rama.commit && rama.commit.sha;
    if (sha) {
      const base = `https://raw.githubusercontent.com/${OWNER}/${REPO}/${sha}`;
      const [of, es] = await Promise.all([fetch(`${base}/ofertas.json`).then((r) => r.json()), fetch(`${base}/estado.json`).then((r) => r.json())]);
      return [of, es];
    }
  } catch (e) { /* sigue con la copia publicada */ }
  // 2) Respaldo: copia publicada junto a la página.
  const v = Date.now();
  return Promise.all([fetch(`data/ofertas.json?v=${v}`).then((r) => r.json()), fetch(`data/estado.json?v=${v}`).then((r) => r.json())]);
}

let ultimoGenerado = 0;
async function cargar() {
  try {
    const [of, es] = await obtenerDatos();
    if (of.generado !== ultimoGenerado) {
      ultimoGenerado = of.generado;
      st.ofertas = of.ofertas || [];
      const cats = [...new Set(st.ofertas.map((o) => o.categoria).filter(Boolean))].sort();
      const sel = $("#categoria");
      const actual = sel.value;
      sel.replaceChildren(new Option("Todas las categorías", ""), ...cats.map((c) => new Option(c[0].toUpperCase() + c.slice(1), c)));
      sel.value = cats.includes(actual) ? actual : "";
      pintarEstado(es);
      render();
    }
    $("#actualizado").textContent = `Actualizado ${hace(of.generado)} · monitoreo continuo`;
  } catch (e) {
    $("#actualizado").textContent = "Aún no hay datos. La primera revisión puede tardar unos minutos.";
    $("#vacio").hidden = false;
  }
}

cargarPrefs();
enlazar();
cargar();
setInterval(cargar, 90 * 1000);
