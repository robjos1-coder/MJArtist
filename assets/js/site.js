/* Michael Joseph — site script.
   All content comes from /content/*.json (edited through Pages CMS).
   Security: content is only ever inserted with textContent / safe attributes,
   never innerHTML, and every link or image URL is checked before use. */
(() => {
  "use strict";

  // ---------- helpers ----------
  const $ = (s, r = document) => r.querySelector(s);
  const R = document.documentElement.dataset.root || "";   // "" on main pages, "../" on artwork pages
  const cache = {};
  const load = (name) =>
    (cache[name] ||= fetch(`${R}content/${name}.json`, { cache: "no-cache" }).then((r) => {
      if (!r.ok) throw new Error(`Could not load ${name}.json (${r.status})`);
      return r.json();
    }));

  function el(tag, attrs = {}, ...kids) {
    const n = document.createElement(tag);
    for (const [k, v] of Object.entries(attrs)) {
      if (v == null || v === false) continue;
      if (k === "class") n.className = v;
      else if (k === "text") n.textContent = v;
      else if (k.startsWith("on")) n.addEventListener(k.slice(2), v);
      else n.setAttribute(k, v === true ? "" : String(v));
    }
    for (const kid of kids.flat()) if (kid != null && kid !== "") n.append(kid instanceof Node ? kid : document.createTextNode(String(kid)));
    return n;
  }

  // Only allow http(s) and mailto links to be written into the page.
  function safeUrl(u) {
    if (!u) return null;
    try {
      const url = new URL(String(u).trim(), location.href);
      return ["https:", "http:", "mailto:"].includes(url.protocol) ? url.href : null;
    } catch { return null; }
  }

  // Images: local files (uploaded through the CMS) or, until they are imported, Wix originals.
  const WIX = /^https:\/\/static\.wixstatic\.com\/media\/([A-Za-z0-9_~.\-]+)$/;
  function imgSrc(src, w) {
    if (!src) return "";
    const s = String(src).trim();
    const m = s.match(WIX);
    if (m) return `https://static.wixstatic.com/media/${m[1]}/v1/fit/w_${w},h_${w},q_85,enc_auto/${m[1]}`;
    if (/^\/?images\/[^\s"'<>]+$/i.test(s)) return R + s.replace(/^\//, "");
    return ""; // anything else is ignored
  }
  function picture(src, alt, w = 900, eager = false) {
    const i = el("img", { src: imgSrc(src, w), alt: alt || "", loading: eager ? "eager" : "lazy", decoding: "async" });
    if (WIX.test(src || "")) i.setAttribute("srcset", `${imgSrc(src, w)} 1x, ${imgSrc(src, Math.min(w * 2, 2400))} 2x`);
    return i;
  }

  const slug = (s) => String(s || "").toLowerCase().normalize("NFKD").replace(/[̀-ͯ]/g, "").replace(/&/g, "and").replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");
  const paras = (text) => String(text || "").split(/\n\s*\n/).map((p) => p.trim()).filter(Boolean).map((p) => el("p", { text: p }));

  const STATUS = { available: "Available", sold: "Sold", private: "Private collection", nfs: "Not for sale" };
  function labelLine(a) {
    const lead = a.stage && a.for_work ? `${a.stage} for ${a.for_work}` : "";
    const bits = [lead, a.medium || (lead ? "" : a.type), a.size, a.year].filter(Boolean).join(" · ");
    const st = (a.status || "").toLowerCase();
    const line = el("span", { class: "m" });
    if (st === "sold" || st === "available") line.append(el("span", { class: `dot ${st}`, "aria-hidden": "true" }));
    line.append(bits || a.series || "");
    return line;
  }

  const viewCount = (a) => [a.image, ...(a.more_images || [])].filter((u) => imgSrc(u, 100)).length;
  const artPage = (a) => `${R}art/${slug(a.title)}.html`;
  // Studies and maquettes first, then the finished work they led to — the order they were made.
  function withFamilies(list) {
    const titles = new Set(list.map((a) => a.title)), ORD = { Study: 0, Maquette: 1 }, out = [];
    for (const a of list) {
      if (a.for_work && titles.has(a.for_work)) continue;
      out.push(...list.filter((k) => k.for_work === a.title).sort((x, y) => (ORD[x.stage] ?? 2) - (ORD[y.stage] ?? 2)), a);
    }
    return out;
  }

  // Group a list so related pieces sit together: highlights, then by kind (a finished piece's
  // studies travel with it), each kind ordered by series. Mirrors tools/build_site.py.
  const TYPE_ORDER = ["Sculpture", "Painting", "Mixed media", "Drawing", ""];
  let HIGHLIGHTS = [];   // titles chosen in the editor (site.json → highlights)
  const GROUP_NAME = { Sculpture: "Sculpture, with its studies and maquettes", Painting: "Painting", "Mixed media": "Mixed media & relief", Drawing: "Drawing", "": "Other work" };
  function catalogue(list, all, withHighlights) {
    const titles = new Set(list.map((a) => a.title));
    const hasKids = new Set(list.filter((a) => a.for_work && titles.has(a.for_work)).map((a) => a.for_work));
    const inFamily = (a) => hasKids.has(a.title) || (a.for_work && titles.has(a.for_work));
    const serIdx = new Map([...new Set(all.map((a) => a.series || ""))].map((s, i) => [s, i]));
    const groups = [];
    const chosen = HIGHLIGHTS.map((t) => list.find((a) => a.title === t)).filter(Boolean);
    const picked = withHighlights && list.length > 12
      ? (chosen.length ? chosen : list.filter((a) => a.featured && !a.stage && !inFamily(a)).slice(0, 8)) : [];
    if (picked.length) groups.push(["Highlights", picked]);
    const rest = list.filter((a) => !picked.includes(a));
    const finals = new Set(rest.filter((a) => !a.stage).map((a) => a.title));
    for (const t of TYPE_ORDER) {
      const members = rest.filter((a) => !finals.has(a.for_work) && (a.type || "") === t)
        .sort((a, b) => (hasKids.has(a.title) ? 0 : 1) - (hasKids.has(b.title) ? 0 : 1) || (serIdx.get(a.series || "") ?? 99) - (serIdx.get(b.series || "") ?? 99));
      const items = members.flatMap((a) => withFamilies([...rest.filter((x) => x.for_work === a.title), a]));
      if (items.length) groups.push([GROUP_NAME[t] || t, items]);
    }
    return groups;
  }
  // Render groups into a grid; the viewer steps through the whole visible list in order.
  function renderCatalogue(grid, groups) {
    const flat = groups.flatMap(([, items]) => items);
    const nodes = [];
    let i = 0;
    for (const [name, items] of groups) {
      if (groups.length > 1) nodes.push(el("h2", { class: "cat-h" }, name, " ", el("span", { class: "label", text: items.length })));
      for (const a of items) { nodes.push(workFigure(a, i, flat, i < 4)); i++; }
    }
    grid.replaceChildren(...(nodes.length ? nodes : [el("p", { class: "empty-note", text: "No works match — try another filter." })]));
    return flat;
  }

  function workFigure(a, index, list, eager) {
    return el("figure", { class: "work", id: `w-${slug(a.title)}` },
      el("button", { type: "button", "aria-label": `View ${a.title}`, onclick: () => Lightbox.open(list, index) },
        el("div", { class: "frame" }, picture(a.image, `${a.title} — ${a.medium || a.type || "artwork"} by Michael Joseph`, 900, eager),
          viewCount(a) > 1 ? el("span", { class: "views-badge", text: `${viewCount(a)} views` }) : null)),
      el("figcaption", {}, el("span", { class: "t", text: a.title }), labelLine(a)));
  }

  function fail(where, err) {
    console.error(err);
    if (where) where.replaceChildren(el("p", { class: "loading", text: "This section could not be loaded. Please refresh the page." }));
  }

  // ---------- chrome ----------
  function chrome(site) {
    const btn = $(".menu-btn"), nav = $("#nav");
    if (btn && nav) btn.addEventListener("click", () => {
      const open = nav.classList.toggle("open");
      btn.setAttribute("aria-expanded", open);
      btn.textContent = open ? "Close" : "Menu";
    });
    const header = $(".site-header");
    const onScroll = () => header && header.classList.toggle("scrolled", scrollY > 8);
    addEventListener("scroll", onScroll, { passive: true }); onScroll();

    document.querySelectorAll("[data-year]").forEach((n) => (n.textContent = new Date().getFullYear()));
    if (!site) return;
    document.querySelectorAll("[data-email]").forEach((n) => {
      const href = safeUrl(`mailto:${site.email}`);
      if (href) { n.textContent = site.email; n.setAttribute("href", href); }
    });
    document.querySelectorAll("[data-phone]").forEach((n) => {
      n.textContent = site.phone || "";
      const tel = String(site.phone || "").replace(/\(0\)/, "").replace(/[^\d+]/g, "");
      if (tel) n.setAttribute("href", `tel:${tel}`);
    });
    document.querySelectorAll("[data-location]").forEach((n) => (n.textContent = site.location || ""));
    const ig = safeUrl(site.instagram);
    document.querySelectorAll("[data-instagram]").forEach((n) => { if (ig) { n.href = ig; n.hidden = false; } });
    document.querySelectorAll("[data-instagram-block]").forEach((n) => { n.hidden = !ig; });
    document.querySelectorAll("[data-instagram-handle]").forEach((n) => { n.textContent = site.instagram_handle || "Instagram"; });
  }

  // ---------- lightbox ----------
  const Lightbox = (() => {
    let list = [], i = 0, box, img, title, dl, notes, count, enquire, details, views, dev, lastFocus, touchX = null, ALL = [];
    const ORDER = { Study: 0, Maquette: 1 };
    // Every piece connected to a work: its studies and maquettes, then the finished work.
    function chainFor(a) {
      const root = a.for_work || a.title;
      const kids = ALL.filter((w) => w.for_work === root).sort((x, y) => (ORDER[x.stage] ?? 2) - (ORDER[y.stage] ?? 2));
      const fin = ALL.find((w) => w.title === root && !w.for_work);
      return kids.length ? [...kids, ...(fin ? [fin] : [])] : [];
    }
    function build() {
      box = el("div", { class: "lightbox", role: "dialog", "aria-modal": "true", "aria-label": "Artwork viewer", hidden: true });
      img = el("img", { alt: "" });
      title = el("h2");
      dl = el("dl");
      notes = el("p");
      count = el("span", { class: "lb-count" });
      enquire = el("a", { class: "arrow-link", href: `${R}contact.html`, text: "Enquire about this work" });
      details = el("a", { class: "arrow-link", href: "#", text: "Full details & share link" });
      views = el("div", { class: "lb-views" });
      dev = el("div", { class: "lb-dev" });
      box.append(
        el("div", { class: "lb-stage" }, img,
          el("button", { class: "lb-btn lb-prev", type: "button", "aria-label": "Previous work", onclick: () => go(-1), text: "←" }),
          el("button", { class: "lb-btn lb-next", type: "button", "aria-label": "Next work", onclick: () => go(1), text: "→" })),
        el("aside", { class: "lb-panel" }, count, title, dl, views, notes, dev, enquire, details),
        el("button", { class: "lb-btn lb-close", type: "button", onclick: close, text: "Close ×" }));
      box.addEventListener("click", (e) => { if (e.target === box || e.target.classList.contains("lb-stage")) close(); });
      box.addEventListener("touchstart", (e) => (touchX = e.touches[0].clientX), { passive: true });
      box.addEventListener("touchend", (e) => {
        if (touchX == null) return;
        const dx = e.changedTouches[0].clientX - touchX; touchX = null;
        if (Math.abs(dx) > 50) go(dx < 0 ? 1 : -1);
      });
      document.body.append(box);
    }
    function render() {
      const a = list[i];
      img.src = imgSrc(a.image, 2000); img.alt = a.title;
      title.textContent = a.title;
      count.textContent = `${i + 1} / ${list.length} — ${a.series || ""}`;
      dl.replaceChildren();
      const rows = [["Type", a.type], ["Stage", a.stage && a.for_work ? `${a.stage} for ${a.for_work}` : ""], ["Medium", a.medium], ["Size", a.size], ["Year", a.year], ["Price", a.price], ["Status", STATUS[(a.status || "").toLowerCase()] || ""]];
      for (const [k, v] of rows) if (v) dl.append(el("dt", { text: k }), el("dd", { text: v }));
      notes.textContent = a.notes || ""; notes.hidden = !a.notes;
      // other photographs of the same piece
      const pics = [a.image, ...(a.more_images || [])].filter((u) => imgSrc(u, 200));
      views.replaceChildren(...(pics.length > 1 ? [el("span", { class: "lb-h", text: `${pics.length} views` }),
        el("div", { class: "lb-thumbs" }, ...pics.map((u, k) => el("button", { type: "button", "aria-label": `View ${k + 1}`, "aria-pressed": k === 0, onclick: (e) => {
          img.src = imgSrc(u, 2000); views.querySelectorAll("button").forEach((b) => b.setAttribute("aria-pressed", b === e.currentTarget));
        } }, el("img", { src: imgSrc(u, 160), alt: "" }))))] : []));
      // development: studies → maquette → finished work
      const chain = chainFor(a);
      dev.replaceChildren(...(chain.length > 1 ? [el("span", { class: "lb-h", text: "From study to finished work" }),
        el("ol", { class: "lb-chain" }, ...chain.map((c, k) => el("li", {}, el("button", { type: "button", "aria-current": c === a ? "true" : null, onclick: () => { list = chain; i = k; render(); } },
          el("img", { src: imgSrc(c.image, 160), alt: "" }), el("span", { text: c.stage || "Finished work" })))))] : []));
      enquire.href = `${R}contact.html?work=${encodeURIComponent(a.title)}`;
      details.href = artPage(a);
      history.replaceState(null, "", `#${slug(a.title)}`);
      // preload neighbours
      [1, -1].forEach((d) => { const n = list[(i + d + list.length) % list.length]; if (n) new Image().src = imgSrc(n.image, 2000); });
    }
    function go(d) { i = (i + d + list.length) % list.length; render(); }
    function key(e) {
      if (e.key === "Escape") close();
      else if (e.key === "ArrowRight") go(1);
      else if (e.key === "ArrowLeft") go(-1);
      else if (e.key === "Tab") { // keep focus inside
        const f = [...box.querySelectorAll("button, a[href]")];
        const first = f[0], last = f[f.length - 1];
        if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); }
        else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
      }
    }
    function setAll(w) { ALL = w || []; }
    function open(l, idx) {
      if (!box) build();
      list = l; i = idx; lastFocus = document.activeElement;
      render(); box.hidden = false; document.body.style.setProperty("overflow", "hidden");
      document.addEventListener("keydown", key);
      box.querySelector(".lb-close").focus();
    }
    function close() {
      box.hidden = true; document.body.style.removeProperty("overflow");
      document.removeEventListener("keydown", key);
      history.replaceState(null, "", location.pathname + location.search);
      if (lastFocus) lastFocus.focus();
    }
    return { open, setAll };
  })();

  // ---------- nav: highlight Sculpture / The Figure / All work from the address ----------
  function markNav() {
    const here = location.pathname.split("/").pop() || "index.html";
    const q = new URLSearchParams(location.search);
    document.querySelectorAll("#nav a").forEach((a) => {
      const u = new URL(a.getAttribute("href"), location.href);
      const file = u.pathname.split("/").pop();
      let on = file === here;
      if (on && file === "work.html") {
        const t = u.searchParams.get("type"), s = u.searchParams.get("series");
        on = (t || "") === (q.get("type") || "") && (s || "") === (q.get("series") || "");
      }
      on ? a.setAttribute("aria-current", "page") : a.removeAttribute("aria-current");
    });
  }

  // ---------- home page reel: a slow cross-fade through chosen works ----------
  const Reel = (() => {
    const DUR = 6000;
    function mount(root, list, fixedStart) {
      if (!root || !list.length) return;
      const frame = $(".reel-frame", root), t = $(".t", root), m = $(".m", root), n = $(".n", root), bar = $(".reel-progress i", root);
      const reduce = matchMedia("(prefers-reduced-motion: reduce)").matches;
      let i = fixedStart ? 0 : Math.floor(Math.random() * list.length), timer = null, paused = false;
      const imgs = list.map((a, k) => el("img", { src: k === i ? imgSrc(a.image, 1400) : "", alt: a.title, decoding: "async" }));
      const btn = el("button", { type: "button", class: "reel-zoom", "aria-label": "View this work larger", onclick: () => Lightbox.open(list, i) });
      const hp = el("button", { type: "button", class: "reel-hover prev", "aria-label": "Previous work", text: "\u2190", onclick: (e) => { e.stopPropagation(); show(i - 1); } });
      const hn = el("button", { type: "button", class: "reel-hover next", "aria-label": "Next work", text: "\u2192", onclick: (e) => { e.stopPropagation(); show(i + 1); } });
      frame.replaceChildren(...imgs, btn, hp, hn);
      bar.parentElement.style.setProperty("--dur", `${DUR}ms`);
      // The frame takes each work's own shape, so nothing is ever letterboxed.
      // CSS eases the change, and the reduced-motion rule turns that easing off.
      function fit(im) {
        if (im.naturalWidth && im.naturalHeight) frame.style.setProperty("--ar", im.naturalWidth + " / " + im.naturalHeight);
      }
      function show(k) {
        i = (k + list.length) % list.length;
        const a = list[i];
        if (!imgs[i].getAttribute("src")) imgs[i].src = imgSrc(a.image, 1400);
        const cur = imgs[i];
        if (cur.complete) fit(cur);
        else cur.addEventListener("load", () => { if (imgs[i] === cur) fit(cur); }, { once: true });
        imgs.forEach((im, j) => im.classList.toggle("on", j === i));
        const nx = imgs[(i + 1) % list.length]; if (!nx.getAttribute("src")) nx.src = imgSrc(list[(i + 1) % list.length].image, 1400);
        t.textContent = a.title;
        m.textContent = [a.type, a.medium, a.year].filter(Boolean).join(" · ") || a.series || "";
        n.textContent = `${i + 1} / ${list.length}`;
        bar.classList.remove("run"); void bar.offsetWidth; if (!reduce && !paused) bar.classList.add("run");
        schedule();
      }
      function schedule() { clearTimeout(timer); if (!reduce && !paused && list.length > 1) timer = setTimeout(() => show(i + 1), DUR); }
      function pause(p) { paused = p; root.classList.toggle("paused", p); if (p) clearTimeout(timer); else schedule(); }
      $(".reel-ctrl .prev", root).addEventListener("click", () => show(i - 1));
      $(".reel-ctrl .next", root).addEventListener("click", () => show(i + 1));
      root.addEventListener("mouseenter", () => pause(true));
      root.addEventListener("mouseleave", () => pause(false));
      root.addEventListener("focusin", () => pause(true));
      root.addEventListener("focusout", () => pause(false));
      document.addEventListener("visibilitychange", () => pause(document.hidden));
      show(i);
    }
    return { mount };
  })();

  // ---------- scale diagram: sculpture height against a 1.8 m person ----------
  function scaleDiagram(h, label, name) {
    const NS = "http://www.w3.org/2000/svg";
    const top = Math.max(5, Math.ceil(h + 1)), W = 300, H = 440, G = 400, px = (G - 30) / top;
    const n = (tag, at = {}, txt) => { const e = document.createElementNS(NS, tag); for (const [k, v] of Object.entries(at)) e.setAttribute(k, v); if (txt != null) e.textContent = txt; return e; };
    const svg = n("svg", { viewBox: `0 0 ${W} ${H}`, class: "scale-svg", role: "img", "aria-label": `${name}: ${label || h + " m"}, shown beside a 1.8 metre person` });
    svg.append(n("line", { x1: 44, y1: G, x2: W - 6, y2: G, class: "s-ground" }));
    for (let m = 0; m <= top; m++) {
      const y = G - m * px;
      svg.append(n("line", { x1: 38, y1: y, x2: 44, y2: y, class: "s-tick" }), n("text", { x: 32, y: y + 4, class: "s-num", "text-anchor": "end" }, `${m} m`));
      if (m) svg.append(n("line", { x1: 44, y1: y, x2: W - 6, y2: y, class: "s-grid" }));
    }
    // person, 1.8 m
    const ph = 1.8 * px, pxX = 92;
    svg.append(n("circle", { cx: pxX, cy: G - ph + ph * 0.07, r: ph * 0.07, class: "s-person" }),
      n("rect", { x: pxX - ph * 0.1, y: G - ph + ph * 0.15, width: ph * 0.2, height: ph * 0.85, rx: ph * 0.08, class: "s-person" }),
      n("text", { x: pxX, y: G + 22, class: "s-lab", "text-anchor": "middle" }, "1.8 m"));
    // sculpture as an open lattice of line
    const sx = 150, sw = 110, sh = h * px, sy = G - sh;
    const g = n("g", { class: "s-work" });
    g.append(n("rect", { x: sx, y: sy, width: sw, height: sh }));
    for (let k = 1; k < 9; k++) g.append(n("line", { x1: sx, y1: sy + (sh * k) / 9, x2: sx + sw, y2: sy + (sh * (k + 1.4)) / 9 > G ? G : sy + (sh * (k + 1.4)) / 9 }));
    for (let k = 1; k < 4; k++) g.append(n("line", { x1: sx + (sw * k) / 4, y1: sy, x2: sx + (sw * k) / 4 - 14, y2: G }));
    svg.append(g, n("path", { d: `M${sx + sw / 2 - 8} ${sy - 8} L${sx + sw / 2} ${sy - 22} L${sx + sw / 2 + 8} ${sy - 8}`, class: "s-arrow" }),
      n("text", { x: sx + sw / 2, y: G + 22, class: "s-lab", "text-anchor": "middle" }, name),
      n("text", { x: sx + sw / 2, y: sy - 30, class: "s-big", "text-anchor": "middle" }, label || `${h} m`));
    return svg;
  }



  // ---------- privacy-friendly video: nothing loads from YouTube until the visitor presses play ----------
  function videoFacade(id, title) {
    if (!/^[A-Za-z0-9_-]{11}$/.test(id || "")) return null;
    const box = el("div", { class: "video" });
    const btn = el("button", { type: "button", class: "video-play", "aria-label": `Play video: ${title}`, onclick: () => {
      box.replaceChildren(el("iframe", {
        src: `https://www.youtube-nocookie.com/embed/${id}?autoplay=1&rel=0`, title,
        allow: "autoplay; encrypted-media; picture-in-picture; fullscreen", allowfullscreen: true,
        referrerpolicy: "strict-origin-when-cross-origin", loading: "lazy",
        sandbox: "allow-scripts allow-same-origin allow-presentation allow-popups" }));
    } }, el("img", { src: `https://i.ytimg.com/vi/${id}/hqdefault.jpg`, alt: "", loading: "lazy" }), el("span", { class: "video-icon", "aria-hidden": "true", text: "\u25B6" }), el("span", { class: "video-note", text: "Plays from YouTube" }));
    box.append(btn);
    return box;
  }

  // ---------- big translucent play button over the full film (hidden while it plays) ----------
  function filmPlay() {
    document.querySelectorAll(".film-frame").forEach((f) => {
      const v = $("video", f), b = $(".film-play", f);
      if (!v || !b) return;
      const sync = () => f.classList.toggle("playing", !v.paused && !v.ended);
      b.addEventListener("click", () => { v.play().catch(() => {}); v.focus(); });
      ["play", "playing", "pause", "ended"].forEach((e) => v.addEventListener(e, sync));
    });
  }

  // ---------- silent looping films: play only while on screen; a button to pause; still image if motion is reduced ----------
  // iOS will not start a video that has nothing buffered: play() rejects, and
  // every call site was discarding that rejection. Load first, then retry once
  // the data arrives.
  function playSoon(v) {
    v.muted = true;
    if (v.preload !== "auto") { v.preload = "auto"; if (!v.readyState) v.load(); }
    const again = () => { const r = v.play(); if (r && r.catch) r.catch(() => {}); };
    const p = v.play();
    if (p && p.catch) p.catch(() => v.addEventListener("canplay", again, { once: true }));
  }

  function loops() {
    const reduce = matchMedia("(prefers-reduced-motion: reduce)").matches;
    document.querySelectorAll("video[data-loop]").forEach((v) => {
      v.muted = true;
      const wrap = v.parentElement;
      let userPaused = reduce;
      const btn = el("button", { type: "button", class: "vid-toggle", "aria-label": reduce ? "Play film" : "Pause film", text: reduce ? "Play" : "Pause" });
      const sync = () => { btn.textContent = v.paused ? "Play" : "Pause"; btn.setAttribute("aria-label", v.paused ? "Play film" : "Pause film"); };
      btn.addEventListener("click", () => { if (v.paused) { userPaused = false; playSoon(v); } else { userPaused = true; v.pause(); } });
      v.addEventListener("play", sync); v.addEventListener("pause", sync);
      wrap.append(btn);
      if ("IntersectionObserver" in window) {
        new IntersectionObserver((es) => es.forEach((e) => {
          if (e.isIntersecting && !userPaused) playSoon(v); else if (!e.isIntersecting) v.pause();
        }), { threshold: 0.2 }).observe(v);
      } else if (!userPaused) playSoon(v);
    });
  }

  // ---------- galleries that run sideways: arrow buttons instead of scrollbars ----------
  function strips() {
    document.querySelectorAll(".strip").forEach((wrap) => {
      const row = $(".strip-row", wrap), prev = $(".strip-btn.prev", wrap), next = $(".strip-btn.next", wrap);
      if (!row || !prev || !next) return;
      const step = () => Math.max(240, row.clientWidth * 0.85);
      const update = () => {
        const max = row.scrollWidth - row.clientWidth - 4;
        prev.disabled = row.scrollLeft <= 4; next.disabled = row.scrollLeft >= max;
        wrap.classList.toggle("fits", max <= 0);
      };
      prev.hidden = next.hidden = false;
      prev.addEventListener("click", () => row.scrollBy({ left: -step(), behavior: "smooth" }));
      next.addEventListener("click", () => row.scrollBy({ left: step(), behavior: "smooth" }));
      row.addEventListener("scroll", update, { passive: true });
      addEventListener("resize", update);
      row.querySelectorAll("img").forEach((i) => i.addEventListener("load", update, { once: true }));
      update();
    });
  }

  // ---------- home page story: pictures change as each chapter reaches the middle of the screen ----------
  function story() {
    const sec = $("#story"); if (!sec || !("IntersectionObserver" in window)) return;
    const figs = [...sec.querySelectorAll(".story-stage figure")], steps = [...sec.querySelectorAll(".story-step")];
    const reduce = matchMedia("(prefers-reduced-motion: reduce)").matches;
    sec.classList.add("story-live");
    const set = (i) => {
      figs.forEach((f) => {
        const on = Number(f.dataset.i) === i; f.classList.toggle("on", on);
        const v = $("video", f); if (v) { if (on && !reduce) playSoon(v); else v.pause(); }
      });
      steps.forEach((s) => s.classList.toggle("on", Number(s.dataset.i) === i));
    };
    const io = new IntersectionObserver((es) => es.forEach((e) => { if (e.isIntersecting) set(Number(e.target.dataset.i)); }),
      { rootMargin: "-45% 0px -45% 0px" });
    steps.forEach((st) => io.observe(st));
    set(0);
  }

  // ---------- exhibitions ----------
  const today = () => { const d = new Date(); d.setHours(0, 0, 0, 0); return d; };
  const parse = (s) => (s && /^\d{4}-\d{2}-\d{2}$/.test(s) ? new Date(`${s}T00:00:00`) : null);
  const fmt = (d, opts) => d.toLocaleDateString("en-GB", opts);
  function whenText(x) {
    if (x.date_text) return x.date_text;
    const s = parse(x.start), e = parse(x.end);
    if (s && e) {
      if (s.getTime() === e.getTime()) return fmt(s, { day: "numeric", month: "short", year: "numeric" });
      const sameYear = s.getFullYear() === e.getFullYear();
      return `${fmt(s, sameYear ? { day: "numeric", month: "short" } : { day: "numeric", month: "short", year: "numeric" })} – ${fmt(e, { day: "numeric", month: "short", year: "numeric" })}`;
    }
    return s ? `From ${fmt(s, { day: "numeric", month: "short", year: "numeric" })}` : "";
  }
  function stateOf(x) {
    const s = parse(x.start), e = parse(x.end) || s, t = today();
    if (!s) return "past";
    if (s > t) return "upcoming";
    if (e >= t) return "now";
    return "past";
  }
  function showRow(x) {
    const st = stateOf(x);
    const link = safeUrl(x.link);
    const venue = el("h3", { class: "venue" }, x.venue || x.title, x.title && x.venue && x.title !== x.venue ? el("small", { text: x.title }) : null);
    return el("li", { class: "show" },
      el("div", { class: "when" },
        st === "now" ? el("span", { class: "pill now", text: "On now" }) : st === "upcoming" ? el("span", { class: "pill", text: "Upcoming" }) : null,
        el("div", { text: whenText(x) })),
      el("div", {}, venue, el("div", { class: "detail", text: [x.address, x.hours, x.notes].filter(Boolean).join(" — ") })),
      link ? el("a", { class: "go", href: link, target: "_blank", rel: "noopener noreferrer", text: "Visit ↗" }) : el("span"));
  }
  const byStart = (a, b) => (parse(a.start) || 0) - (parse(b.start) || 0);

  // ---------- pages ----------
  const pages = {
    async home(site) {
      const intro = $("#intro"); if (intro) intro.textContent = site.intro || site.tagline || "";
      const q = $("#quote"); if (q) q.textContent = site.quote || "";
      const [works, shows] = await Promise.all([load("artworks"), load("exhibitions").catch(() => [])]);

      // rotating works beside the name
      let reelList = works.filter((w) => w.hero);
      if (!reelList.length) reelList = works.filter((w) => w.featured);
      if (!reelList.length) reelList = works.slice(0, 6);
      const rf = works.find((w) => w.title === site.reel_first);
      if (rf) reelList = [{ ...rf, image: site.scale_image || rf.image }, ...reelList.filter((w) => w !== rf)];
      Reel.mount($("#reel"), reelList, !!rf);

      // the two strands
      const rank = (a) => (a.featured ? 0 : 1);
      const sculpture = works.filter((w) => w.type === "Sculpture" && !w.stage).sort((a, b) => rank(a) - rank(b));
      const figure = works.filter((w) => w.series === "The Creative Figure" && w.type !== "Sculpture" && !w.stage).sort((a, b) => rank(a) - rank(b));
      const fill = (id, list, countId, noun) => {
        const row = $(id); if (!row) return;
        const shown = list.slice(0, 12);
        row.replaceChildren(...shown.map((a, i) => workFigure(a, i, shown, false)));
        const c = $(countId); if (c) c.textContent = `See all ${list.length} ${noun}`;
      };
      fill("#sculpture-row", sculpture, "#sculpture-count", "sculptures");
      fill("#figure-row", figure, "#figure-count", "drawings & paintings");

      // other bodies of work
      const seriesList = $("#series");
      const groups = new Map();
      for (const w of works) { const s = w.series || "Other"; if (!groups.has(s)) groups.set(s, []); groups.get(s).push(w); }
      seriesList.replaceChildren(...[...groups].map(([name, list]) =>
        el("li", {}, el("a", { href: `work.html?series=${slug(name)}` },
          el("span", { class: "name", text: name }),
          el("span", { class: "count", text: `${list.length} work${list.length === 1 ? "" : "s"}` }),
          el("span", { class: "strip", "aria-hidden": "true" }, ...list.slice(0, 5).map((a) => picture(a.image, "", 300)))))));

      // exhibitions teaser
      const box = $("#on-view");
      const live = shows.filter((x) => stateOf(x) !== "past").sort(byStart);
      if (live.length) {
        box.replaceChildren(el("ul", { class: "shows" }, ...live.slice(0, 4).map(showRow)));
      } else {
        const past = shows.filter((x) => stateOf(x) === "past").sort((a, b) => byStart(b, a)).slice(0, 3);
        box.replaceChildren(
          el("p", { class: "empty-note", text: "New dates will be announced soon. Recently shown at:" }),
          el("ul", { class: "shows" }, ...past.map(showRow)));
      }
    },

    async work() {
      const works = await load("artworks");
      const grid = $("#grid"), filters = $("#filters"), countEl = $("#count"), title = $("#work-title");
      const TYPES = ["Sculpture", "Drawing", "Painting", "Mixed media"].filter((t) => works.some((w) => w.type === t));
      const series = [...new Set(works.map((w) => w.series || "Other"))];
      const params = new URLSearchParams(location.search);
      let type = TYPES.find((t) => slug(t) === params.get("type")) || "";
      let ser = series.find((s) => slug(s) === params.get("series")) || "";

      const matches = (w) => (!type || w.type === type) && (!ser || (w.series || "Other") === ser);
      function chip(label, group, value, n) {
        return el("button", { class: "chip", type: "button", "data-g": group, "data-v": value, "aria-pressed": "false", onclick: () => {
          if (group === "type") type = type === value ? "" : value; else ser = ser === value ? "" : value;
          if (!value) { type = ""; ser = ""; }
          const u = new URL(location.href);
          type ? u.searchParams.set("type", slug(type)) : u.searchParams.delete("type");
          ser ? u.searchParams.set("series", slug(ser)) : u.searchParams.delete("series");
          u.hash = ""; history.replaceState(null, "", u);
          draw(); markNav();
        } }, label, n != null ? el("sup", { text: n }) : null);
      }
      filters.replaceChildren(
        chip("All work", "all", "", works.length),
        el("span", { class: "sep", "aria-hidden": "true" }),
        ...TYPES.map((t) => chip(t, "type", t, works.filter((w) => w.type === t).length)),
        el("span", { class: "sep", "aria-hidden": "true" }),
        ...series.map((s) => chip(s, "series", s, works.filter((w) => (w.series || "Other") === s).length)));

      function draw() {
        const list = renderCatalogue(grid, catalogue(works.filter(matches), works, !type && !ser));
        countEl.textContent = `${list.length} work${list.length === 1 ? "" : "s"}`;
        if (title) title.textContent = [type, ser].filter(Boolean).join(" · ") || "All work";
        filters.querySelectorAll(".chip").forEach((c) => {
          const g = c.dataset.g, v = c.dataset.v;
          c.setAttribute("aria-pressed", g === "all" ? !type && !ser : g === "type" ? v === type : v === ser);
        });
        return list;
      }
      const list = draw();
      let h = ""; try { h = decodeURIComponent(location.hash.slice(1)); } catch { /* ignore malformed links */ }
      if (h) { const idx = list.findIndex((a) => slug(a.title) === h); if (idx >= 0) Lightbox.open(list, idx); }
    },

    async sculpture(site) {
      const works = await load("artworks");

      // scale: the tallest piece against a person
      const big = works.find((w) => w.title === site.scale_work);
      if (big) {
        $("#scale-photo").replaceChildren(el("button", { type: "button", "aria-label": `View ${big.title}`, onclick: () => Lightbox.open([big], 0) },
          picture(site.scale_image || big.image, `${big.title} beside Michael Joseph, showing its scale`, 1600)));
        $("#scale-cap").textContent = [big.title, big.medium, big.size].filter(Boolean).join(" · ");
        if (!site.scale_graphic) $("#scale-fig").replaceChildren(scaleDiagram(Number(site.scale_height_m) || 3, site.scale_label || "", big.title));
      } else $("#scale").hidden = true;

      // materials
      $("#materials-list").replaceChildren(...(site.sculpture_materials || []).map((m) =>
        el("li", {}, el("h3", { text: m.name }), el("p", { text: m.text }))));

      // the collection
      const finished = works.filter((w) => w.type === "Sculpture" && !w.stage).sort((a, b) => (a.featured ? 0 : 1) - (b.featured ? 0 : 1));
      $("#s-count").textContent = `${finished.length} works`;
      $("#s-grid").replaceChildren(...finished.map((a, i) => workFigure(a, i, finished, i < 4)));
      const dev = withFamilies(works.filter((w) => (w.stage && finished.some((f) => f.title === w.for_work)) || (finished.includes(w) && works.some((k) => k.for_work === w.title))));
      if (dev.length) $("#s-dev").replaceChildren(...dev.map((a, i) => workFigure(a, i, dev, false)));
      else $("#s-dev-wrap").hidden = true;
    },

    async courses() {
      const t = await load("teaching");
      $("#c-title").textContent = t.title || "Courses";
      $("#c-lede").textContent = t.lede || "";
      $("#c-intro").replaceChildren(...paras(t.intro));
      const v = videoFacade(t.video_id, t.video_title || "Michael Joseph"); if (v) $("#c-video").replaceChildren(v); else $("#c-video").hidden = true;
      $("#c-offers").replaceChildren(...(t.offers || []).map((o) => {
        const href = safeUrl(o.link);
        return el("li", { class: "offer" }, el("p", { class: "eyebrow", text: o.detail || "" }), el("h3", { text: o.title }), el("p", { text: o.text || "" }),
          href ? el("a", { class: "arrow-link", href, target: "_blank", rel: "noopener noreferrer", text: o.link_text || "Find out more" }) : null);
      }));
      $("#c-quote").textContent = t.quote || "";
      $("#c-voices").replaceChildren(...(t.testimonials || []).map((q) => el("figure", { class: "voice" }, el("blockquote", { text: q.text }), el("figcaption", { class: "label", text: q.who || "" }))));
      const cl = safeUrl(t.courses_link), pl = safeUrl(t.profile_link);
      document.querySelectorAll("[data-courses-link]").forEach((a) => { if (cl) a.href = cl; });
      document.querySelectorAll("[data-profile-link]").forEach((a) => { if (pl) a.href = pl; });
      const em = safeUrl(`mailto:${t.booking_email || ""}`);
      document.querySelectorAll("[data-booking-email]").forEach((a) => { if (em && t.booking_email) { a.href = em; a.textContent = t.booking_email; } });

      // dated courses (content/courses.json): upcoming first, past ones drop off automatically
      const list = await load("courses").catch(() => []);
      const now = today();
      const upcoming = list.filter((c) => { const d = parse(c.start); return !d || d >= now; })
        .sort((a, b) => (parse(a.start) || Infinity) - (parse(b.start) || Infinity));
      $("#c-dates").replaceChildren(...(upcoming.length ? upcoming.map((c) => {
        const link = safeUrl(c.link), d = parse(c.start);
        return el("li", { class: "course" },
          el("div", { class: "when" }, el("span", { class: "pill", text: d ? "Booking now" : "Coming soon" }),
            el("div", { text: c.date_text || (d ? fmt(d, { weekday: "short", day: "numeric", month: "short", year: "numeric" }) : "") }),
            el("div", { text: c.time || "" })),
          el("div", {}, el("h3", { class: "venue", text: c.title }),
            el("p", { class: "detail", text: [c.format, c.price].filter(Boolean).join(" · ") }),
            el("p", { class: "desc", text: c.description || "" })),
          link ? el("a", { class: "go", href: link, target: "_blank", rel: "noopener noreferrer", text: "Book at Art Junction \u2197" }) : el("span"));
      }) : [el("p", { class: "empty-note", text: "New course dates are being planned — see Art Junction for the latest." })]));
    },

    async figure(site) {
      const works = await load("artworks");
      const all = works.filter((w) => w.series === "The Creative Figure");
      const flat = all.filter((w) => w.type !== "Sculpture" && !w.stage).sort((a, b) => (a.featured ? 0 : 1) - (b.featured ? 0 : 1)).slice(0, 10);
      $("#f-row").replaceChildren(...flat.map((a, i) => workFigure(a, i, flat, i < 4)));
      const grid = $("#f-grid"), count = $("#f-count"), chips = [...document.querySelectorAll("#f-filters .chip")];
      function draw(t) {
        const list = renderCatalogue(grid, catalogue(all.filter((w) => !t || w.type === t), works, false));
        count.textContent = `${list.length} works`;
        chips.forEach((c) => c.setAttribute("aria-pressed", c.dataset.t === t));
      }
      chips.forEach((c) => c.addEventListener("click", () => draw(c.dataset.t)));
      draw("");
    },

    async about(site) {
      $("#statement-title").textContent = site.statement_title || "A Different Perspective";
      $("#statement").replaceChildren(...paras(site.statement));
      $("#biography").replaceChildren(...paras(site.biography));
      $("#pull").textContent = site.about_quote || site.quote || "";
      const fig = $("#about-figure");
      if (fig && site.about_image) fig.replaceChildren(picture(site.about_image, `Work by ${site.name}`, 1000, true));
      $("#timeline").replaceChildren(...(site.timeline || []).map((t) =>
        el("li", {}, el("span", { class: "y", text: t.year || "" }), el("span", { class: "x", text: t.text || "" }))));
      $("#materials").replaceChildren(...String(site.materials || "").split(",").map((m) => m.trim()).filter(Boolean).map((m) => el("li", { text: m })));
      const col = $("#collections"); if (col) col.textContent = site.collections || "";
      const sale = $("#sales-note"); if (sale) sale.textContent = site.sales_note || "";
    },

    async exhibitions() {
      const shows = await load("exhibitions");
      const live = shows.filter((x) => stateOf(x) !== "past").sort(byStart);
      const past = shows.filter((x) => stateOf(x) === "past").sort((a, b) => byStart(b, a));
      $("#current").replaceChildren(live.length ? el("ul", { class: "shows" }, ...live.map(showRow))
        : el("p", { class: "empty-note", text: "No exhibitions are scheduled just now — new dates will appear here." }));
      const byYear = new Map();
      for (const x of past) { const y = (parse(x.start) || new Date(0)).getFullYear() || "Earlier"; if (!byYear.has(y)) byYear.set(y, []); byYear.get(y).push(x); }
      $("#past").replaceChildren(...[...byYear].flatMap(([y, list]) => [el("h3", { class: "year-head", text: y }), el("ul", { class: "shows" }, ...list.map(showRow))]));
    },

    async contact(site) {
      const note = $("#sales-note"); if (note) note.textContent = site.sales_note || "";
      const form = $("#enquiry"), status = $("#form-status");
      const work = new URLSearchParams(location.search).get("work");
      if (work) $("#f-work").value = work.slice(0, 120);
      const key = String(site.form_access_key || "").trim();
      const opened = Date.now();
      const thanks = "Thank you — your message has been sent. Michael will reply by email.";

      // Spam filters. Bots are dropped silently (they are shown a normal "thank you");
      // real people get a plain explanation if something needs changing.
      function spamCheck(d) {
        if (d.botcheck || d.website) return "bot";                          // hidden honeypot fields filled in
        if (Date.now() - opened < 4000) return "bot";                        // filled in faster than a person can
        const msg = String(d.message || "");
        if (/<\s*a\s|\[url|\[link|<\/?(script|iframe)/i.test(msg)) return "Please remove any HTML or link codes from your message.";
        if ((msg.match(/https?:\/\/|www\./gi) || []).length > 2) return "Please include no more than two web links.";
        if (msg.trim().length < 10) return "Please write a little more in your message.";
        if (!/^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(String(d.email || "").trim())) return "Please check your email address.";
        try { const last = Number(sessionStorage.getItem("mj-sent") || 0); if (Date.now() - last < 60000) return "Thanks — your last message has just gone. Please wait a minute before sending another."; } catch { /* storage unavailable */ }
        return "";
      }

      form.addEventListener("submit", async (e) => {
        e.preventDefault();
        if (!form.reportValidity()) return;
        const data = Object.fromEntries(new FormData(form));
        const problem = spamCheck(data);
        if (problem === "bot") { form.reset(); status.textContent = thanks; return; }
        if (problem) { status.textContent = problem; return; }
        const captcha = form.querySelector(".h-captcha") ? String(data["h-captcha-response"] || form.querySelector("[name='h-captcha-response']")?.value || "") : "";
        if (form.querySelector(".h-captcha") && !captcha) { status.textContent = "Please complete the “I am human” check."; return; }
        const subject = `Website enquiry${data.work ? ` — ${data.work}` : ""}`;
        if (!/^[0-9a-f-]{36}$/i.test(key)) {
          // No form service configured: open the visitor's own email app instead.
          const body = `${data.message}\n\n— ${data.name}\n${data.email}`;
          location.href = `mailto:${encodeURIComponent(site.email)}?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`;
          status.textContent = "Your email app should now open with the message ready to send.";
          return;
        }
        const btn = form.querySelector("button[type=submit]");
        btn.disabled = true; status.textContent = "Sending…";
        try {
          const r = await fetch("https://api.web3forms.com/submit", {
            method: "POST", headers: { "Content-Type": "application/json", Accept: "application/json" },
            body: JSON.stringify({ access_key: key, subject, from_name: "mjartist.com", name: String(data.name).slice(0, 100), email: String(data.email).slice(0, 160),
              artwork: String(data.work || "").slice(0, 120), message: String(data.message).slice(0, 4000), botcheck: false, ...(captcha ? { "h-captcha-response": captcha } : {}) }),
          });
          const j = await r.json().catch(() => ({}));
          if (!r.ok || !j.success) throw new Error(j.message || r.status);
          form.reset(); status.textContent = thanks;
          try { sessionStorage.setItem("mj-sent", String(Date.now())); } catch { /* ignore */ }
        } catch (err) {
          console.error(err);
          status.textContent = `The message couldn't be sent. Please email ${site.email} directly.`;
        } finally { btn.disabled = false; }
      });
    },
  };

  // ---------- boot ----------
  document.addEventListener("DOMContentLoaded", async () => {
    let site = null;
    try { site = await load("site"); } catch (e) { console.error(e); }
    HIGHLIGHTS = (site && Array.isArray(site.highlights)) ? site.highlights : [];
    chrome(site);
    markNav();
    loops();
    filmPlay();
    const page = document.body.dataset.page;
    if (!pages[page]) { story(); strips(); return; }
    story();
    try { if (["home", "work", "sculpture", "figure"].includes(page)) Lightbox.setAll(await load("artworks")); await pages[page](site || {}); } catch (e) { fail($("main"), e); }
    strips();
  });
})();
