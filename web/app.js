const NOMBRES = { falabella: "Falabella", ripley: "Ripley", paris: "Paris" };
const CONF = { alta: "Confianza alta", media: "Confianza media", baja: "Solo según tienda" };
const $ = (s) => document.querySelector(s);
const clp = (n) => "$" + Math.round(n).toLocaleString("es-CL");
const pct = (x) => Math.round(x * 100) + "%";

const st = {
  ofertas: [],
  tiendas: new Set(["falabella", "ripley", "paris"]),
  tipos: new Set(["entre_tiendas", "historial"]),
  minDesc: 0.5,
  q: "",
  cat: "",
  orden: "desc",
  soloNuevas: false,
};

function guardarPrefs() {
  try {
    localStorage.setItem("caza:prefs", JSON.stringify({
      tiendas: [...st.tiendas], tipos: [...st.tipos], minDesc: st.minDesc, orden: st.orden,
    }));
  } catch (e) { /* sin almacenamiento */ }
}
function cargarPrefs() {
  try {
    const p = JSON.parse(localStorage.getItem("caza:prefs") || "null");
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

function descuentoVisible(o) {
  // Descuento según los métodos activos en el filtro.
  let d = 0;
  if (st.tipos.has("entre_tiendas") && o.tipos.includes("entre_tiendas")) d = Math.max(d, o.desc_cruzado || 0);
  if (st.tipos.has("historial") && o.tipos.includes("historial")) d = Math.max(d, o.desc_historial || 0);
  if (st.tipos.has("declarado") && o.tipos.includes("declarado")) d = Math.max(d, o.desc_declarado || 0);
  return d;
}

function referencia(o) {
  if (st.tipos.has("entre_tiendas") && o.tipos.includes("entre_tiendas") && o.ref_cruzada)
    return [o.ref_cruzada, "en otras publicaciones"];
  if (st.tipos.has("historial") && o.tipos.includes("historial") && o.ref_historial)
    return [o.ref_historial, "su precio habitual"];
  if (o.precio_lista) return [o.precio_lista, "precio normal según la tienda"];
  return [null, ""];
}

function sparkline(svg, h, precioActual) {
  if (!h || h.length < 2) { svg.remove(); return; }
  const vals = h.map((x) => x[1]);
  const min = Math.min(...vals), max = Math.max(...vals);
  const rango = max - min || 1;
  const pts = vals.map((v, i) => {
    const x = (i / (vals.length - 1)) * 116 + 2;
    const y = 26 - ((v - min) / rango) * 22;
    return [x, y];
  });
  const ns = "http://www.w3.org/2000/svg";
  const pl = document.createElementNS(ns, "polyline");
  pl.setAttribute("points", pts.map((p) => p.join(",")).join(" "));
  const c = document.createElementNS(ns, "circle");
  const last = pts[pts.length - 1];
  c.setAttribute("cx", last[0]); c.setAttribute("cy", last[1]); c.setAttribute("r", 2.6);
  svg.append(pl, c);
  svg.setAttribute("aria-label", `Historial: entre ${clp(min)} y ${clp(max)}`);
}

function tarjeta(o) {
  const t = $("#tplCard").content.firstElementChild.cloneNode(true);
  const d = descuentoVisible(o);
  const [ref, refTxt] = referencia(o);
  t.querySelector(".img").href = o.url;
  const img = t.querySelector("img");
  if (o.img) { img.src = o.img; img.alt = o.nombre; } else img.remove();
  t.querySelector(".tienda").innerHTML = `<i class="dot ${o.tienda}"></i>${NOMBRES[o.tienda] || o.tienda}`
    + (o.vendedor && !["Falabella", "Ripley"].includes(o.vendedor) ? ` · <span style="font-weight:400">${esc(o.vendedor)}</span>` : "");
  const conf = t.querySelector(".conf");
  conf.textContent = CONF[o.confianza]; conf.classList.add(o.confianza);
  if (Date.now() / 1000 - o.desde < 86400) t.querySelector(".nuevo").hidden = false;
  t.querySelector(".nombre").textContent = o.nombre;
  t.querySelector(".nombre").title = o.nombre;
  t.querySelector(".badge").textContent = "-" + pct(d);
  t.querySelector(".ahora").textContent = clp(o.precio);
  if (ref) t.querySelector(".antes").innerHTML = `<s>${clp(ref)}</s> ${refTxt}`;
  if (o.precio_tarjeta) t.querySelector(".tarjeta").textContent = `Con tarjeta de la tienda: ${clp(o.precio_tarjeta)}`;
  sparkline(t.querySelector(".spark"), o.historial, o.precio);
  if (o.comparados && o.comparados.length) {
    const det = t.querySelector(".comparar");
    det.hidden = false;
    det.querySelector("summary").textContent = `Comparar con ${o.comparados.length} publicación${o.comparados.length > 1 ? "es" : ""}`;
    const ul = det.querySelector("ul");
    for (const c of o.comparados) {
      const li = document.createElement("li");
      li.innerHTML = `<a href="${esc(c.url)}" target="_blank" rel="noopener" title="${esc(c.nombre)}">`
        + `<span><i class="dot ${c.tienda}"></i> ${NOMBRES[c.tienda] || c.tienda}${c.vendedor && !["Falabella", "Ripley"].includes(c.vendedor) ? " · " + esc(c.vendedor) : ""}</span>`
        + `<span><b>${clp(c.precio)}</b></span></a>`;
      ul.append(li);
    }
  }
  t.querySelector(".ir").href = o.url;
  t.querySelector(".visto").textContent = `Detectado ${hace(o.desde)}`;
  return t;
}

function esc(s) {
  return String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

function norm(s) {
  return String(s || "").normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();
}

function render() {
  const q = norm(st.q).split(/\s+/).filter(Boolean);
  const ahora = Date.now() / 1000;
  let lista = st.ofertas.filter((o) => {
    if (!st.tiendas.has(o.tienda)) return false;
    if (!o.tipos.some((t) => st.tipos.has(t))) return false;
    if (descuentoVisible(o) < st.minDesc) return false;
    if (st.cat && o.categoria !== st.cat) return false;
    if (st.soloNuevas && ahora - o.desde > 86400) return false;
    if (q.length) {
      const txt = norm(o.nombre + " " + o.marca + " " + o.categoria);
      if (!q.every((p) => txt.includes(p))) return false;
    }
    return true;
  });
  const orden = {
    desc: (a, b) => descuentoVisible(b) - descuentoVisible(a),
    nuevo: (a, b) => b.desde - a.desde,
    precio: (a, b) => a.precio - b.precio,
    ahorro: (a, b) => ((referencia(b)[0] || 0) - b.precio) - ((referencia(a)[0] || 0) - a.precio),
  }[st.orden];
  lista.sort(orden);

  const g = $("#grilla");
  g.replaceChildren(...lista.slice(0, 300).map(tarjeta));
  $("#vacio").hidden = lista.length > 0;
  const total = st.ofertas.length;
  $("#resumen").textContent = lista.length
    ? `${lista.length} oferta${lista.length > 1 ? "s" : ""}${lista.length > 300 ? " (mostrando 300)" : ""} · ${total} en total`
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
    let clase = "", txt = "sin datos";
    if (s) {
      const atraso = Date.now() / 1000 - (s.ultimo_ok || 0);
      if (!s.ok) clase = atraso > 6 * 3600 ? "bad" : "warn";
      else if (s.bloqueos > 0) clase = "warn";
      txt = s.ok ? `${s.productos} revisados` : "con problemas";
      filas.push(`<tr><td><i class="dot ${t}"></i> ${NOMBRES[t]}</td><td>${s.ok ? "✅" : "⚠️"}</td><td>${(e.por_tienda || {})[t] || 0}</td>`
        + `<td>${s.productos}</td><td>${s.ultimo_ok ? hace(s.ultimo_ok) : "nunca"}</td><td>${s.errores}${s.bloqueos ? ` (${s.bloqueos} bloqueos)` : ""}</td></tr>`);
    }
    span.classList.add(...(clase ? [clase] : []));
    span.innerHTML = `<i></i>${NOMBRES[t]} · ${txt}`;
    span.title = s && s.detalle_errores && s.detalle_errores.length ? s.detalle_errores.join("\n") : "";
    cont.append(span);
  }
  $("#pie").innerHTML = `<p>Revisión #${e.corrida} · ${e.catalogo.toLocaleString("es-CL")} productos con historial · `
    + `alertas al celular: ${e.canal_alertas ? "activadas" : "no configuradas"}</p>`
    + `<table><tr><th>Tienda</th><th>Estado</th><th>En catálogo</th><th>Revisados ahora</th><th>Último OK</th><th>Errores</th></tr>${filas.join("")}</table>`;
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
}

async function cargar() {
  const v = Date.now();
  try {
    const [of, es] = await Promise.all([
      fetch(`data/ofertas.json?v=${v}`).then((r) => r.json()),
      fetch(`data/estado.json?v=${v}`).then((r) => r.json()),
    ]);
    st.ofertas = of.ofertas || [];
    $("#actualizado").textContent = `Actualizado ${hace(of.generado)} · se revisa cada hora`;
    const cats = [...new Set(st.ofertas.map((o) => o.categoria).filter(Boolean))].sort();
    const sel = $("#categoria");
    const actual = sel.value;
    sel.replaceChildren(new Option("Todas las categorías", ""), ...cats.map((c) => new Option(c[0].toUpperCase() + c.slice(1), c)));
    sel.value = cats.includes(actual) ? actual : "";
    pintarEstado(es);
    render();
  } catch (e) {
    $("#actualizado").textContent = "Aún no hay datos. La primera revisión puede tardar unos minutos.";
    $("#vacio").hidden = false;
  }
}

cargarPrefs();
enlazar();
cargar();
setInterval(cargar, 10 * 60 * 1000);
