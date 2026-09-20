"""Build the website's HTML pages from the content files.

Runs automatically on GitHub every time something is published (including
every save in Pages CMS), and by preview.bat on your own computer.

It writes:
  index.html, sculpture.html, figure.html, work.html, courses.html,
  about.html, exhibitions.html, contact.html, 404.html   (the main pages)
  art/<artwork>.html                                     (one page per artwork)
  sitemap.xml                                            (for search engines)

Everything a search engine needs is written straight into the HTML: titles,
descriptions, the artworks themselves, links between them, and structured
data (schema.org) describing Michael, each artwork and each exhibition.
The page script then adds the interactive parts (slideshow, viewer, filters).

Don't edit the generated .html files by hand; edit this file or the content.
"""
from __future__ import annotations

import datetime as dt
import html
import json
import math
import pathlib
import re
import sys
import unicodedata

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = pathlib.Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else ROOT
C = ROOT / "content"

site = json.loads((C / "site.json").read_text(encoding="utf-8"))
works = json.loads((C / "artworks.json").read_text(encoding="utf-8"))
shows = json.loads((C / "exhibitions.json").read_text(encoding="utf-8"))
teach = json.loads((C / "teaching.json").read_text(encoding="utf-8"))
courses = json.loads((C / "courses.json").read_text(encoding="utf-8")) if (C / "courses.json").exists() else []

BASE = (site.get("site_url") or "https://www.mjartist.com").rstrip("/")
TODAY = dt.date.today()
E = lambda s: html.escape(str(s or ""), quote=True)

# Security policy. Everything is self-hosted except these deliberate exceptions:
#   Instagram  — official post embeds (instagram.com script + frames, its image CDNs)
#   Web3Forms + hCaptcha — the optional contact-form service and its spam check
#   YouTube (privacy mode) and Wix images (until they are imported)
CSP = ("default-src 'self'; "
       "script-src 'self' https://www.instagram.com https://web3forms.com https://js.hcaptcha.com https://*.hcaptcha.com; "
       "style-src 'self' https://*.hcaptcha.com; "
       "img-src 'self' https://static.wixstatic.com https://i.ytimg.com https://*.cdninstagram.com https://*.fbcdn.net https://www.instagram.com data:; "
       "font-src 'self'; media-src 'self'; "
       "connect-src 'self' https://api.web3forms.com https://*.hcaptcha.com https://www.instagram.com; "
       "form-action 'self' mailto: https://api.web3forms.com; "
       "frame-src https://www.youtube-nocookie.com https://www.instagram.com https://*.hcaptcha.com; "
       "base-uri 'none'; object-src 'none'; manifest-src 'self'; "
       "upgrade-insecure-requests")

NAV = [("sculpture.html", "Sculpture"), ("figure.html", "The Figure"), ("work.html", "All work"),
       ("courses.html", "Courses"), ("about.html", "About"), ("exhibitions.html", "Exhibitions"), ("contact.html", "Contact")]


# ---------------------------------------------------------------- helpers
def slug(s: str) -> str:
    s = unicodedata.normalize("NFKD", str(s or "").lower())
    s = "".join(ch for ch in s if not unicodedata.combining(ch)).replace("&", "and")
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")


WIX = re.compile(r"^https://static\.wixstatic\.com/media/([A-Za-z0-9_~.\-]+)$")


def img(u: str, w: int, R: str = "") -> str:
    u = str(u or "").strip()
    m = WIX.match(u)
    if m:
        return f"https://static.wixstatic.com/media/{m[1]}/v1/fit/w_{w},h_{w},q_85,enc_auto/{m[1]}"
    if re.match(r"^/?images/[^\s\"'<>]+$", u):
        return R + u.lstrip("/")
    return ""


def abs_img(u: str, w: int = 1200) -> str:
    s = img(u, w)
    return s if s.startswith("http") else (f"{BASE}/{s}" if s else "")


def paras(t: str, ind: str = "          ") -> str:
    return "\n".join(f"{ind}<p>{E(p.strip())}</p>" for p in str(t or "").split("\n\n") if p.strip())


def safe_url(u: str) -> str:
    u = str(u or "").strip()
    return u if re.match(r"^(https?://|mailto:)", u) else ""


PAGE_OF = {id(a): f"art/{slug(a['title'])}.html" for a in works}
TITLE = {a["title"]: a for a in works}


def lead(a) -> str:
    return f"{a['stage']} for {a['for_work']}" if a.get("stage") and a.get("for_work") else ""


def label(a) -> str:
    return " · ".join(x for x in [lead(a), a.get("medium") or ("" if lead(a) else a.get("type")), a.get("size"), a.get("year")] if x)


def alt(a) -> str:
    kind = a.get("medium") or (a.get("type") or "artwork").lower()
    return f"{a['title']} — {kind} by Michael Joseph"


def views(a) -> int:
    return 1 + len([u for u in a.get("more_images") or [] if img(u, 100)])


def card(a, R="", eager=False, w=900) -> str:
    v = views(a)
    badge = f'<span class="views-badge">{v} views</span>' if v > 1 else ""
    return (f'<figure class="work" id="w-{slug(a["title"])}"><a class="card-link" href="{R}{PAGE_OF[id(a)]}">'
            f'<div class="frame"><img src="{E(img(a["image"], w, R))}" alt="{E(alt(a))}" loading="{"eager" if eager else "lazy"}" decoding="async">{badge}</div></a>'
            f'<figcaption><span class="t">{E(a["title"])}</span><span class="m">{E(label(a))}</span></figcaption></figure>')


def strip(row_id, cards_html):
    return (f'<div class="strip"><button class="strip-btn prev" type="button" aria-label="Previous works" hidden>&larr;</button>'
            f'<div class="strip-row" id="{row_id}">{cards_html}</div>'
            f'<button class="strip-btn next" type="button" aria-label="More works" hidden>&rarr;</button></div>')


def story_html():
    st = site.get("story") or {}
    chs = st.get("chapters") or []
    if not chs:
        return ""
    stage, steps = [], []
    for i, c in enumerate(chs):
        a = TITLE.get(c.get("work") or "")
        src = c.get("image") or (a["image"] if a else "")
        alt_t = alt(a) if a else c.get("title", "")
        if c.get("video"):
            media = (f'<video data-story-video muted loop playsinline preload="none" poster="{E(img(src, 1400))}" aria-label="{E(c.get("title"))}">'
                     f'<source src="{E(c["video"])}" type="video/mp4"></video>')
        else:
            media = f'<img src="{E(img(src, 1400))}" alt="{E(alt_t)}" loading="lazy">'
        stage.append(f'<figure class="{"on" if i == 0 else ""}" data-i="{i}">{media}</figure>')
        link = f'<a class="arrow-link" href="{PAGE_OF[id(a)]}">{E(a["title"])}</a>' if a else ""
        steps.append(f'<li class="story-step" data-i="{i}"><figure class="story-inline"><img src="{E(img(src, 900))}" alt="{E(alt_t)}" loading="lazy"></figure>'
                     f'<p class="story-n">{i + 1:02d}</p><h3>{E(c.get("title"))}</h3><p>{E(c.get("text"))}</p>{link}</li>')
    return f'''    <section class="story" id="story" aria-labelledby="story-h">
      <div class="wrap">
        <header class="story-head">
          <p class="eyebrow">{E(st.get("eyebrow"))}</p>
          <h2 id="story-h">{E(st.get("title"))}</h2>
          <blockquote class="story-quote">“{E(st.get("quote"))}”<cite>Michael Joseph</cite></blockquote>
        </header>
        <div class="story-grid">
          <div class="story-stage" aria-hidden="true">{"".join(stage)}</div>
          <ol class="story-steps">{"".join(steps)}</ol>
        </div>
      </div>
    </section>

'''


def steps_html(steps):
    out = []
    for i, st in enumerate(steps):
        fit = ' class="fit"' if st.get("fit") == "contain" else ""
        out.append(f'<li{fit}><img src="{E(img(st["image"], 1200))}" alt="{E(st["title"])} — bronze casting in Michael Joseph&#39;s foundry" loading="lazy">'
                   f'<span class="n">{i + 1}</span><h3>{E(st["title"])}</h3><p>{E(st["text"])}</p></li>')
    return "".join(out)


def with_families(lst):
    """Finished works, each followed by its own studies and maquettes."""
    ORDER = {"Study": 0, "Maquette": 1}
    inlist = {a["title"] for a in lst}
    out, seen = [], set()
    for a in lst:
        if a.get("for_work") and a["for_work"] in inlist:
            continue
        kids = sorted([k for k in lst if k.get("for_work") == a["title"]], key=lambda k: ORDER.get(k.get("stage"), 2))
        out += kids
        out.append(a)
    return out


TYPE_ORDER = ["Sculpture", "Painting", "Mixed media", "Drawing"]
GROUP_NAME = {"Sculpture": "Sculpture, with its studies and maquettes", "Painting": "Painting",
              "Mixed media": "Mixed media & relief", "Drawing": "Drawing", "": "Other work"}


def catalogue(lst, selected=True):
    """Group works so related pieces sit together: a few highlights first, then by kind
    (a finished piece's studies and maquettes travel with it), then by series."""
    titles = {a["title"] for a in lst}
    has_kids = {a["for_work"] for a in lst if a.get("for_work") in titles}
    in_family = lambda a: a["title"] in has_kids or (a.get("for_work") in titles)
    ser_idx = {s: i for i, s in enumerate(dict.fromkeys(a.get("series") or "" for a in works))}
    groups = []
    chosen = [TITLE[t] for t in (site.get("highlights") or []) if t in TITLE]
    if selected and chosen:          # the list chosen in the editor, in that order
        picked = [a for a in chosen if a in lst]
    else:
        picked = [a for a in lst if selected and a.get("featured") and not a.get("stage") and not in_family(a)][:8]
    if picked and len(lst) > 12:
        groups.append(("Highlights", picked))
    rest = [a for a in lst if a not in picked]
    finals = {a["title"]: a for a in rest if not a.get("stage")}
    for t in TYPE_ORDER + [""]:
        members = [a for a in rest if not (a.get("for_work") in finals) and (a.get("type") or "") == t]
        members.sort(key=lambda a: (0 if a["title"] in has_kids else 1, ser_idx.get(a.get("series") or "", 99)))
        items = []
        for a in members:
            items += [k for k in with_families([x for x in rest if x.get("for_work") == a["title"]] + [a])]
        if items:
            groups.append((GROUP_NAME.get(t, t), items))
    return groups


def catalogue_html(lst, selected=True):
    out = []
    for name, items in catalogue(lst, selected):
        out.append(f'<h2 class="cat-h">{E(name)} <span class="label">{len(items)}</span></h2>')
        out += [card(a, "", False, 700) for a in items]
    return "".join(out)


def date(s):
    try:
        return dt.date.fromisoformat(s)
    except Exception:
        return None


def show_state(x):
    s, e = date(x.get("start")), date(x.get("end")) or date(x.get("start"))
    if not s:
        return "past"
    if s > TODAY:
        return "upcoming"
    return "now" if e and e >= TODAY else "past"


def when(x):
    if x.get("date_text"):
        return x["date_text"]
    s, e = date(x.get("start")), date(x.get("end"))
    f = lambda d, y=True: f"{d.day} {d.strftime('%b %Y' if y else '%b')}"
    if s and e:
        return f(s) if s == e else f"{f(s, s.year != e.year)} – {f(e)}"
    return f"From {f(s)}" if s else ""


def show_row(x):
    st = show_state(x)
    pill = {"now": '<span class="pill now">On now</span>', "upcoming": '<span class="pill">Upcoming</span>'}.get(st, "")
    small = f"<small>{E(x['title'])}</small>" if x.get("title") and x.get("venue") and x["title"] != x["venue"] else ""
    link = safe_url(x.get("link"))
    go = f'<a class="go" href="{E(link)}" target="_blank" rel="noopener noreferrer">Visit ↗</a>' if link else "<span></span>"
    detail = " — ".join(v for v in [x.get("address"), x.get("hours"), x.get("notes")] if v)
    return (f'<li class="show"><div class="when">{pill}<div>{E(when(x))}</div></div>'
            f'<div><h3 class="venue">{E(x.get("venue") or x.get("title"))}{small}</h3><div class="detail">{E(detail)}</div></div>{go}</li>')


PERSON = {
    "@type": "Person", "@id": f"{BASE}/#michael", "name": "Michael Joseph", "url": f"{BASE}/",
    "jobTitle": "Sculptor and artist", "birthDate": "1951",
    "description": "British artist working in drawing, painting and sculpture — Corten and welded steel, and bronze cast in his own foundry.",
    "homeLocation": {"@type": "Place", "name": site.get("location", "West Sussex, England")},
    "knowsAbout": ["Sculpture", "Bronze casting", "Corten steel", "Figurative drawing", "Painting"],
    "award": ["Aviation Painting of the Year, Guild of Aviation Artists (1987)", "Stride Open Drawing Award (2017)"],
    "sameAs": [u for u in [site.get("instagram"), teach.get("profile_link")] if u],
}


# ---------------------------------------------------------------- page shell
def page(path, key, title, desc, main, og=None, ld=None):
    R = "../" if "/" in path else ""
    canonical = f"{BASE}/" if path == "index.html" else f"{BASE}/{path}"
    nav = "\n".join(f'        <a href="{R}{h}">{t}</a>' for h, t in NAV)
    ogimg = abs_img(og or (site.get("hero_image") or ""), 1200)
    graph = [PERSON, {"@type": "WebSite", "@id": f"{BASE}/#site", "url": f"{BASE}/", "name": "Michael Joseph", "publisher": {"@id": PERSON["@id"]}}] + (ld or [])
    ldjson = json.dumps({"@context": "https://schema.org", "@graph": graph}, ensure_ascii=False).replace("</", "<\\/")
    robots = '  <meta name="robots" content="noindex">\n' if key == "404" else ""
    return f'''<!doctype html>
<html lang="en-GB" data-root="{R}">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
  <meta http-equiv="Content-Security-Policy" content="{CSP}">
  <meta name="referrer" content="strict-origin-when-cross-origin">
  <title>{E(title)}</title>
  <meta name="description" content="{E(desc)}">
{robots}  <link rel="canonical" href="{E(canonical)}">
  <meta property="og:type" content="{"article" if key == "art" else "website"}">
  <meta property="og:site_name" content="Michael Joseph">
  <meta property="og:locale" content="en_GB">
  <meta property="og:title" content="{E(title)}">
  <meta property="og:description" content="{E(desc)}">
  <meta property="og:url" content="{E(canonical)}">
  <meta property="og:image" content="{E(ogimg)}">
  <meta name="twitter:card" content="summary_large_image">
  <meta name="theme-color" content="#d4d3cf">
  <link rel="icon" href="{R}favicon.ico?v=6" sizes="48x48">
  <link rel="icon" href="{R}assets/favicon.svg?v=6" type="image/svg+xml">
  <link rel="apple-touch-icon" href="{R}assets/apple-touch-icon.png?v=6">
  <link rel="manifest" href="{R}site.webmanifest">
  <link rel="preload" href="{R}assets/fonts/syne-latin-800-normal.woff2" as="font" type="font/woff2" crossorigin>
  <link rel="stylesheet" href="{R}assets/css/style.css">
  <script src="{R}assets/js/site.js" defer></script>
  <script type="application/ld+json">{ldjson}</script>
</head>
<body data-page="{key}">
  <a class="skip" href="#main">Skip to content</a>
  <header class="site-header">
    <div class="wrap">
      <a class="wordmark" href="{R or './'}">Michael Joseph<span>.</span></a>
      <button class="menu-btn" type="button" aria-expanded="false" aria-controls="nav">Menu</button>
      <nav class="nav" id="nav" aria-label="Main">
{nav}
      </nav>
    </div>
  </header>

  <main id="main">
{main}
  </main>

  <footer class="site-footer">
    <div class="wrap">
      <div class="footer-grid">
        <div>
          <h2>Enquiries &amp; studio visits</h2>
          <p><a class="arrow-link" href="{R}contact.html">Get in touch</a></p>
        </div>
        <div class="col">
          <span class="eyebrow">Contact</span>
          <a data-email href="mailto:{E(site.get("email"))}">{E(site.get("email"))}</a>
          <a data-phone href="{R}contact.html">{E(site.get("phone"))}</a>
          <a data-instagram data-instagram-handle href="{E(site.get("instagram") or "#")}" target="_blank" rel="noopener noreferrer">{E(site.get("instagram_handle") or "Instagram")}</a>
          <a href="{R}courses.html">Courses &amp; tuition</a>
        </div>
        <div class="col">
          <span class="eyebrow">Studio</span>
          <span data-location>{E(site.get("location"))}</span>
          <a href="{R}sculpture.html#foundry">The foundry</a>
        </div>
      </div>
      <div class="footer-base label">
        <span>Art &amp; design &copy; <span data-year>{TODAY.year}</span> Michael Joseph. All rights reserved.</span>
        <span>Images may not be reproduced without permission.</span>
      </div>
    </div>
  </footer>
</body>
</html>
'''


def loop_video(src, poster, label_text, cls="", R=""):
    return (f'<div class="vid {cls}"><video data-loop muted loop playsinline preload="none" poster="{E(R + poster)}" aria-label="{E(label_text)}">'
            f'<source src="{E(R + src)}" type="video/mp4"></video></div>')


# ---------------------------------------------------------------- Instagram
def instagram_feed(limit=8):
    """Latest posts from a Behold JSON feed (https://behold.so, free plan is plenty).
    Fetched when the site is built (daily on GitHub); pictures are saved into
    images/instagram/ so visitors' browsers never contact Instagram."""
    import urllib.request
    url = str(site.get("instagram_feed_url") or "").strip()
    if not re.match(r"^https://feeds\.behold\.so/[A-Za-z0-9_-]+$", url):
        return []
    folder = OUT / "images" / "instagram"
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "mjartist-build"}), timeout=20) as r:
            data = json.loads(r.read(3_000_000))
    except Exception as e:  # never break the build because Instagram is down
        print(f"instagram feed skipped: {e}")
        return []
    folder.mkdir(parents=True, exist_ok=True)
    out, keep = [], set()
    for p in (data.get("posts") or [])[:limit]:
        link = str(p.get("permalink") or "")
        pid = re.sub(r"[^A-Za-z0-9_-]", "", str(p.get("id") or ""))
        sizes = p.get("sizes") or {}
        src = (sizes.get("medium") or {}).get("mediaUrl") or p.get("thumbnailUrl") or p.get("mediaUrl")
        if not (pid and re.match(r"^https://www\.instagram\.com/", link) and str(src or "").startswith("https://")):
            continue
        dest = folder / f"{pid}.jpg"
        if not dest.exists():
            try:
                with urllib.request.urlopen(src, timeout=20) as r:
                    if not r.headers.get("Content-Type", "").startswith("image/"):
                        continue
                    dest.write_bytes(r.read(6_000_000))
            except Exception:
                continue
        keep.add(dest.name)
        out.append({"img": f"images/instagram/{dest.name}", "link": link,
                    "caption": str(p.get("prunedCaption") or p.get("caption") or "")[:220],
                    "date": str(p.get("timestamp") or "")[:10], "video": p.get("mediaType") == "VIDEO"})
    for old in folder.glob("*.jpg"):
        if old.name not in keep:
            old.unlink()
    return out


def instagram_html():
    posts = instagram_feed()
    chosen = [u for u in (site.get("instagram_posts") or []) if re.match(r"^https://www\.instagram\.com/(p|reel)/[A-Za-z0-9_-]+/?$", str(u).strip())]
    if posts:
        cells = "".join(
            f'<li><a href="{E(p["link"])}" target="_blank" rel="noopener noreferrer"><img src="{E(p["img"])}" alt="{E(p["caption"][:120] or "Instagram post by Michael Joseph")}" loading="lazy">'
            f'{"<span class=ig-play>▶</span>" if p["video"] else ""}<span class="ig-cap">{E(p["caption"][:110])}</span></a></li>' for p in posts)
        return f'<ul class="ig-grid">{cells}</ul>'
    if chosen:
        cells = "".join(f'<blockquote class="instagram-media" data-instgrm-permalink="{E(u.strip())}" data-instgrm-version="14"><a href="{E(u.strip())}" target="_blank" rel="noopener noreferrer">View this post on Instagram</a></blockquote>' for u in chosen[:6])
        return f'<div class="ig-embeds">{cells}</div><script async src="https://www.instagram.com/embed.js"></script>'
    return ""


IG_HTML = instagram_html()

# ---------------------------------------------------------------- data views
finished = [a for a in works if not a.get("stage")]
sculptures = sorted([a for a in finished if a.get("type") == "Sculpture"], key=lambda a: not a.get("featured"))
figure_all = [a for a in works if a.get("series") == "The Creative Figure"]
figure_2d = sorted([a for a in figure_all if a.get("type") != "Sculpture" and not a.get("stage")], key=lambda a: not a.get("featured"))
reel = [a for a in works if a.get("hero")] or [a for a in works if a.get("featured")] or works[:6]
if site.get("reel_first") in TITLE:   # the slideshow opens on this work (Tryst, with Michael beside it)
    rf = TITLE[site["reel_first"]]
    reel = [dict(rf, image=site.get("scale_image") or rf["image"])] + [a for a in reel if a is not rf]
series = []
for a in works:
    if (a.get("series") or "Other") not in series:
        series.append(a.get("series") or "Other")

# ---------------------------------------------------------------- pages
pages = {}

# Home -----------------------------------------------------------------
first = reel[0]
home = f'''    <section class="hero">
      <div class="wrap hero-grid">
        <div class="hero-text">
          <p class="eyebrow">{E(site.get("disciplines"))} — {E(site.get("location"))}</p>
          <h1 class="hero-name"><span>Michael</span> <span>Joseph</span></h1>
          <p class="intro" id="intro">{E(site.get("intro"))}</p>
          <div class="links">
            <a class="arrow-link" href="sculpture.html">Sculpture</a>
            <a class="arrow-link" href="figure.html">The Creative Figure</a>
            <a class="arrow-link" href="sculpture.html#foundry">The foundry</a>
          </div>
        </div>
        <figure class="show-reel" id="reel" aria-roledescription="slideshow" aria-label="Selected works">
          <div class="reel-frame"><img class="on" src="{E(img(first["image"], 1400))}" alt="{E(alt(first))}" fetchpriority="high"></div>
          <div class="reel-progress" aria-hidden="true"><i></i></div>
          <figcaption class="reel-bar">
            <span class="t" aria-live="polite">{E(first["title"])}</span>
            <span class="m">{E(label(first))}</span>
            <span class="reel-ctrl">
              <button class="prev" type="button" aria-label="Previous work">&larr;</button>
              <span class="n">1 / {len(reel)}</span>
              <button class="next" type="button" aria-label="Next work">&rarr;</button>
            </span>
          </figcaption>
        </figure>
      </div>
    </section>

{story_html()}    <section class="room stone" aria-labelledby="sculpture-h">
      <div class="wrap">
        <div class="room-head">
          <h2 id="sculpture-h">Sculpture</h2>
          <p>Corten and welded steel, stainless steel, Jesmonite — and bronze cast by hand in Michael's own foundry. Figures and forms for gardens, plinths and open sky.</p>
          <div class="links"><a class="arrow-link" id="sculpture-count" href="sculpture.html">See all {len(sculptures)} sculptures</a></div>
        </div>
        {strip("sculpture-row", "".join(card(a, "", False, 700) for a in sculptures[:12]))}
      </div>
    </section>

    <section class="room sheet" aria-labelledby="figure-h">
      <div class="wrap">
        <div class="room-head">
          <h2 id="figure-h">The Creative Figure</h2>
          <p>{E(site.get("figure_lede"))} Drawing from life in charcoal, ink and paint.</p>
          <div class="links"><a class="arrow-link" id="figure-count" href="figure.html">See the whole series</a></div>
        </div>
        {strip("figure-row", "".join(card(a, "", False, 700) for a in figure_2d[:12]))}
      </div>
    </section>

    <section class="quote">
      <div class="wrap">
        <blockquote id="quote">{E(site.get("quote"))}</blockquote>
        <cite>Michael Joseph</cite>
      </div>
    </section>

    <section class="band" aria-labelledby="teach-h">
      <div class="wrap band-grid">
        <div>
          <p class="eyebrow">Courses &amp; tuition</p>
          <h2 id="teach-h">Learn with Michael</h2>
        </div>
        <div>
          <p>Workshops at the Art Junction studio, livestream life sessions and one-to-one tuition, for beginners and experienced artists. Brave steps, artistic risks, and finding your own voice.</p>
          <div class="links"><a class="arrow-link" href="courses.html">Courses &amp; tuition</a><a class="arrow-link" href="{E(teach.get("courses_link"))}" target="_blank" rel="noopener noreferrer">Upcoming dates ↗</a></div>
        </div>
      </div>
    </section>

    <section class="band ig" data-instagram-block aria-labelledby="ig-h">
      <div class="wrap band-grid">
        <div>
          <p class="eyebrow" id="ig-h">From the studio, on Instagram</p>
          <a class="handle" data-instagram data-instagram-handle href="{E(site.get("instagram"))}" target="_blank" rel="noopener noreferrer">{E(site.get("instagram_handle"))}</a>
        </div>
        <div>
          <p>New work as it happens: charcoal studies, maquettes on the bench, steel being cut and welded, bronze being poured, and pieces arriving at exhibitions.</p>
          <a class="arrow-link" data-instagram href="{E(site.get("instagram"))}" target="_blank" rel="noopener noreferrer">Follow on Instagram ↗</a>
        </div>
      </div>
      {f'<div class="wrap ig-feed">{IG_HTML}</div>' if IG_HTML else ""}
    </section>

    <section class="section" aria-labelledby="ser-h">
      <div class="wrap">
        <div class="section-head">
          <h2 id="ser-h">Every body of work</h2>
          <span class="label">From charcoal to Corten steel</span>
        </div>
        <ul class="series-list" id="series">{"".join(f'<li><a href="work.html?series={slug(s)}"><span class="name">{E(s)}</span><span class="count">{sum(1 for a in works if (a.get("series") or "Other") == s)} works</span></a></li>' for s in series)}</ul>
      </div>
    </section>

    <section class="section" aria-labelledby="ex-h">
      <div class="wrap">
        <div class="section-head">
          <h2 id="ex-h">On view</h2>
          <a class="arrow-link" href="exhibitions.html">All exhibitions</a>
        </div>
        <div id="on-view"><ul class="shows">{"".join(show_row(x) for x in sorted(shows, key=lambda x: x.get("start") or "", reverse=True)[:3])}</ul></div>
      </div>
    </section>'''
pages["index.html"] = ("home", "Michael Joseph — Sculptor & Artist, West Sussex | Steel, Bronze, Drawing & Painting",
                       site.get("tagline"), home, first["image"], [])

# Sculpture --------------------------------------------------------------
F = site["foundry"]
refl = TITLE.get(site.get("reflection_feature") or "")
refl_html = ""
if refl and views(refl) > 1:
    pics = [refl["image"], *refl.get("more_images", [])][:2]
    refl_html = f'''
      <section class="pair" id="reflection" aria-labelledby="refl-h">
        <div class="section-head"><h2 id="refl-h">{E(refl["title"])}</h2><span class="label">{E(refl.get("medium"))} · one piece, two viewpoints</span></div>
        <div class="pair-grid">{"".join(f'<a class="card-link" href="{PAGE_OF[id(refl)]}"><img src="{E(img(u, 1200))}" alt="{E(alt(refl))}" loading="lazy"></a>' for u in pics)}</div>
        <p class="pair-text">{E(site.get("reflection_text"))}</p>
      </section>'''
sp = site.get("spotlight") or {}
spw = TITLE.get(sp.get("work") or "")
spot_html = ""
if spw:
    link = f'<a class="arrow-link" href="{E(sp.get("link"))}">{E(sp.get("link_text"))}</a>' if sp.get("link") else ""
    spot_html = f'''
      <section class="spotlight" id="jesmonite" aria-labelledby="spot-h">
        <a class="card-link spot-img" href="{PAGE_OF[id(spw)]}"><img src="{E(img(spw["image"], 1600))}" alt="{E(alt(spw))}" loading="lazy"></a>
        <div>
          <p class="eyebrow">{E(sp.get("eyebrow"))}</p>
          <h2 id="spot-h">{E(sp.get("title") or spw["title"])}</h2>
          <p class="label">{E(label(spw))}</p>
          <p>{E(sp.get("text"))}</p>
          <div class="links"><a class="arrow-link" href="{PAGE_OF[id(spw)]}">About this work</a>{link}</div>
        </div>
      </section>'''
tryst = TITLE.get(site.get("scale_work") or "")
scale_img = site.get("scale_image") or (tryst or {}).get("image", "")
sculpt = f'''    <section class="s-hero">
      <div class="wrap s-hero-grid">
        <div>
          <p class="eyebrow">Sculpture</p>
          <h1 id="s-title">{E(site.get("sculpture_title"))}</h1>
          <p class="lede" id="s-lede">{E(site.get("sculpture_lede"))}</p>
          <p class="s-quote">“{E(site.get("sculpture_quote"))}”</p>
        </div>
        <figure class="s-hero-vid">
          {loop_video(site["bean_pod_video"], site["bean_pod_poster"], site.get("bean_pod_caption"), "square")}
          <figcaption class="label">{E(site.get("bean_pod_caption"))}</figcaption>
        </figure>
      </div>
    </section>

    <nav class="subnav" aria-label="On this page"><div class="wrap">
      <a href="#collection">The sculptures</a><a href="#about-sculpture">Drawing in space</a><a href="#scale">Scale</a><a href="#studio">Steel</a><a href="#foundry">Bronze</a><a href="#jesmonite">Jesmonite</a><a href="#reflection">Reflection</a><a href="#materials">Materials</a><a href="#s-dev-wrap">Studies &amp; maquettes</a>
    </div></nav>

    <div class="wrap">
      <section class="section first" id="collection" aria-labelledby="col-h">
        <div class="section-head"><h2 id="col-h">The sculptures</h2><span class="label" id="s-count">{len(sculptures)} works</span></div>
        <div class="catalogue" id="s-grid">{"".join(card(a, "", i < 4, 700) for i, a in enumerate(sculptures))}</div>
      </section>

      <div class="s-body" id="about-sculpture">
        <div class="side">
          <p class="eyebrow">Steel · Bronze · Stainless · Jesmonite</p>
          <p class="label">Shown in sculpture gardens across Surrey and Sussex. <a href="exhibitions.html">See exhibitions</a></p>
        </div>
        <div class="prose" id="s-statement">
{paras(site.get("sculpture_statement"))}
        </div>
      </div>

      <section class="scale" id="scale" aria-labelledby="scale-h">
        <figure class="scale-photo work" id="scale-photo">{f'<a class="card-link" href="{PAGE_OF[id(tryst)]}"><img src="{E(img(scale_img, 1600))}" alt="{E(tryst["title"])} beside Michael Joseph, showing its scale" loading="lazy"></a>' if tryst else ""}</figure>
        <div class="scale-side">
          <p class="eyebrow">Scale</p>
          <h2 id="scale-h">From maquette to monument</h2>
          <div id="scale-fig">{f'<img class="scale-graphic" src="{E(site["scale_graphic"])}" alt="{E(tryst["title"] if tryst else "")} and its 25 cm maquette, drawn to scale beside a person">' if site.get("scale_graphic") else ""}</div>
          <p class="label" id="scale-cap">{E(" · ".join(x for x in [tryst.get("title"), tryst.get("medium"), tryst.get("size")] if x) if tryst else "")}</p>
        </div>
      </section>

      <section class="studio" id="studio" aria-labelledby="studio-h">
        <img src="{E(site.get("studio_image"))}" alt="Michael Joseph cutting a steel sculpture in his studio, sparks flying" loading="lazy">
        <div><p class="eyebrow">Steel · the studio</p><h2 id="studio-h">{E(site.get("studio_title"))}</h2><p>{E(site.get("studio_text"))}</p></div>
      </section>
    </div>

    <section class="foundry" id="foundry" aria-labelledby="foundry-h">
      {loop_video(F["loop_video"], F["loop_poster"], "Molten bronze being poured into a mould", "fill")}
      <div class="wrap foundry-text">
        <p class="eyebrow">Bronze · {E(F["eyebrow"])}</p>
        <h2 id="foundry-h">{E(F["title"])}</h2>
        <p>{E(F["lede"])}</p>
      </div>
    </section>

    <div class="wrap">
      <section class="section" aria-labelledby="steps-h">
        <div class="section-head"><h2 id="steps-h">From clay to bronze</h2></div>
        <ol class="steps">{steps_html(F["steps"])}</ol>
        <figure class="film">
          <div class="film-frame"><video controls muted playsinline preload="none" poster="{E(F["film_poster"])}"><source src="{E(F["film"])}" type="video/mp4">Your browser can't play this film.</video><button class="film-play" type="button" aria-label="Play the casting film"></button></div>
          <figcaption class="label">{E(F["film_title"])}</figcaption>
        </figure>
      </section>
{spot_html}{refl_html}
      <section class="section" id="materials" aria-labelledby="mat-h">
        <div class="section-head"><h2 id="mat-h">Materials</h2><span class="label">Chosen for how they hold a line</span></div>
        <ul class="materials-grid" id="materials-list">{"".join(f'<li><h3>{E(m["name"])}</h3><p>{E(m["text"])}</p></li>' for m in site.get("sculpture_materials", []))}</ul>
      </section>

      <section class="section" id="s-dev-wrap" aria-labelledby="dev-h">
        <div class="section-head"><h2 id="dev-h">Studies &amp; maquettes</h2><span class="label">Drawings and small models that led to the finished pieces</span></div>
        <div class="catalogue small" id="s-dev">{"".join(card(a, "", False, 500) for a in with_families([w for w in works if (w.get("stage") and w.get("for_work") in {s["title"] for s in sculptures}) or (w in sculptures and any(k.get("for_work") == w["title"] for k in works))]))}</div>
      </section>
    </div>'''
pages["sculpture.html"] = ("sculpture", "Sculpture — Corten & Welded Steel, Bronze Cast In-House | Michael Joseph",
                           "Sculpture by Michael Joseph: Tryst, over 3 m in Corten and welded steel; bronzes cast by hand in his own foundry; stainless steel, Jesmonite and maquettes. West Sussex.",
                           sculpt, (tryst or {}).get("image"),
                           [{"@type": "VideoObject", "name": F["film_title"], "description": F["lede"],
                             "thumbnailUrl": f"{BASE}/{F['film_poster']}", "contentUrl": f"{BASE}/{F['film']}",
                             "uploadDate": "2020-01-01", "creator": {"@id": PERSON["@id"]}}])

# The Creative Figure ---------------------------------------------------
fig_types = [t for t in ["Drawing", "Painting", "Mixed media", "Sculpture"] if any(a.get("type") == t for a in figure_all)]
figure_page = f'''    <section class="room sheet f-hero" aria-labelledby="f-title">
      <div class="wrap">
        <div class="f-head">
          <div>
            <p class="eyebrow">Series · {len(figure_all)} works</p>
            <h1 id="f-title">{E(site.get("figure_title"))}</h1>
          </div>
          <p class="lede" id="f-lede">{E(site.get("figure_lede"))}</p>
        </div>
        {strip("f-row", "".join(card(a, "", i < 4, 700) for i, a in enumerate(figure_2d[:10])))}
      </div>
    </section>

    <div class="wrap">
      <div class="two-col f-body">
        <div class="side">
          <p class="eyebrow">In Michael's words</p>
          <p class="quote-s" id="f-quote">“{E(site.get("figure_quote"))}”</p>
        </div>
        <div class="prose" id="f-statement">
{paras(site.get("figure_statement"))}
        </div>
      </div>

      <section class="section" aria-labelledby="fg-h">
        <div class="section-head"><h2 id="fg-h">The series</h2><span class="label" id="f-count">{len(figure_all)} works</span></div>
        <div class="filters" id="f-filters" role="group" aria-label="Filter the series">
          <button class="chip" type="button" data-t="" aria-pressed="true">All<sup>{len(figure_all)}</sup></button>{"".join(f'<button class="chip" type="button" data-t="{E(t)}" aria-pressed="false">{E(t)}<sup>{sum(1 for a in figure_all if a.get("type") == t)}</sup></button>' for t in fig_types)}
        </div>
        <div class="catalogue" id="f-grid">{catalogue_html(figure_all, False)}</div>
      </section>
    </div>'''
pages["figure.html"] = ("figure", "The Creative Figure — Figurative Drawing, Painting & Sculpture | Michael Joseph",
                        "The Creative Figure: Michael Joseph's figurative work from life — charcoal and ink drawings, paintings, and the sculptures they became.",
                        figure_page, figure_2d[0]["image"] if figure_2d else None, [])

# All work ---------------------------------------------------------------
work = f'''    <div class="wrap">
      <header class="page-head compact">
        <h1 class="page-title" id="work-title">All work</h1>
        <p><span class="label" id="count">{len(works)} works</span> — select a work to see it larger.</p>
      </header>
      <div class="filters" id="filters" role="group" aria-label="Filter works"></div>
      <div class="catalogue" id="grid">{catalogue_html(works)}</div>
    </div>'''
pages["work.html"] = ("work", "All Work — Sculpture, Drawing & Painting Catalogue | Michael Joseph",
                      "The complete catalogue of Michael Joseph's work: sculpture, drawing, painting and mixed media, from the Creative Figure to Mechanical, Music, Animals and Landscapes.",
                      work, None, [{"@type": "CollectionPage", "name": "All work", "url": f"{BASE}/work.html",
                                    "hasPart": [{"@type": "VisualArtwork", "name": a["title"], "url": f"{BASE}/{PAGE_OF[id(a)]}"} for a in works]}])

# Courses ------------------------------------------------------------------
t = teach
up = [c for c in courses if not date(c.get("start")) or date(c.get("start")) >= TODAY]
def longdate(d):
    return f"{d:%a} {d.day} {d:%b %Y}" if d else ""


def course_row(c):
    link = safe_url(c.get("link"))
    d = date(c.get("start"))
    return (f'<li class="course"><div class="when"><span class="pill">{"Booking now" if d else "Coming soon"}</span><div>{E(c.get("date_text") or longdate(d))}</div><div>{E(c.get("time"))}</div></div>'
            f'<div><h3 class="venue">{E(c.get("title"))}</h3><p class="detail">{E(" · ".join(x for x in [c.get("format"), c.get("price")] if x))}</p><p class="desc">{E(c.get("description"))}</p></div>'
            + (f'<a class="go" href="{E(link)}" target="_blank" rel="noopener noreferrer">Book at Art Junction ↗</a>' if link else "<span></span>") + "</li>")
vid = t.get("video_id") if re.match(r"^[A-Za-z0-9_-]{11}$", t.get("video_id") or "") else ""
courses_page = f'''    <div class="wrap">
      <div class="c-top">
        <div>
          <p class="eyebrow">Courses &amp; tuition · Art Junction</p>
          <h1 id="c-title">{E(t.get("title"))}</h1>
          <p class="lede" id="c-lede">{E(t.get("lede"))}</p>
        </div>
        <div id="c-video" data-video-id="{E(vid)}" data-video-title="{E(t.get("video_title"))}"></div>
      </div>

      <div class="two-col">
        <div class="side">
          <p class="eyebrow">In Michael's words</p>
          <p class="quote-s" id="c-quote">{E(t.get("quote"))}</p>
        </div>
        <div class="prose" id="c-intro">
{paras(t.get("intro"))}
        </div>
      </div>

      <section class="section" aria-labelledby="up-h">
        <div class="section-head"><h2 id="up-h">Upcoming dates</h2><span class="label">Booked and paid through Art Junction</span></div>
        <ul class="courses-list" id="c-dates">{"".join(course_row(c) for c in up) or '<p class="empty-note">New course dates are being planned — see Art Junction for the latest.</p>'}</ul>
      </section>

      <section class="section" aria-labelledby="off-h">
        <div class="section-head"><h2 id="off-h">Ways to learn</h2><a class="arrow-link" data-courses-link href="{E(t.get("courses_link"))}" target="_blank" rel="noopener noreferrer">Upcoming courses ↗</a></div>
        <ul class="offers" id="c-offers">{"".join(f'<li class="offer"><p class="eyebrow">{E(o.get("detail"))}</p><h3>{E(o.get("title"))}</h3><p>{E(o.get("text"))}</p>' + (f'<a class="arrow-link" href="{E(safe_url(o.get("link")))}" target="_blank" rel="noopener noreferrer">{E(o.get("link_text") or "Find out more")}</a>' if safe_url(o.get("link")) else "") + "</li>" for o in t.get("offers", []))}</ul>
      </section>

      <section class="section" aria-labelledby="voice-h">
        <div class="section-head"><h2 id="voice-h">What students say</h2></div>
        <div class="voices" id="c-voices">{"".join(f'<figure class="voice"><blockquote>{E(q.get("text"))}</blockquote><figcaption class="label">{E(q.get("who"))}</figcaption></figure>' for q in t.get("testimonials", []))}</div>
      </section>

      <section class="section" aria-labelledby="book-h">
        <div class="section-head"><h2 id="book-h">Booking</h2></div>
        <p>Courses are run and booked through Art Junction.</p>
        <div class="cta-row">
          <a class="btn" data-courses-link href="{E(t.get("courses_link"))}" target="_blank" rel="noopener noreferrer">See upcoming courses</a>
          <a class="arrow-link" data-profile-link href="{E(t.get("profile_link"))}" target="_blank" rel="noopener noreferrer">Michael at Art Junction ↗</a>
          <a class="arrow-link" data-booking-email href="mailto:{E(t.get("booking_email"))}">{E(t.get("booking_email"))}</a>
        </div>
      </section>
    </div>'''
course_ld = [{"@type": "Course", "name": c.get("title"), "description": c.get("description"),
              "provider": {"@type": "Organization", "name": "Art Junction", "url": "https://www.artjunction.uk/"},
              "instructor": {"@id": PERSON["@id"]}, "url": c.get("link")} for c in courses if c.get("title")]
pages["courses.html"] = ("courses", "Art Courses & One-to-One Tuition with Michael Joseph | Art Junction",
                         "Drawing, painting and sculpture courses with Michael Joseph at Art Junction — in-studio workshops, livestream life sessions, one-to-one tuition, and how-to guides on charcoal, steel and bronze casting.",
                         courses_page, None, course_ld)

# About ------------------------------------------------------------------
about = f'''    <div class="wrap">
      <header class="page-head">
        <p class="eyebrow">About</p>
        <h1 class="page-title" id="statement-title">{E(site.get("statement_title"))}</h1>
      </header>
      <div class="two-col">
        <div class="side">
          <figure class="work" id="about-figure">{f'<img src="{E(img(site.get("about_image"), 1000))}" alt="Work by Michael Joseph" loading="eager">' if site.get("about_image") else ""}</figure>
          <div>
            <p class="eyebrow">Works in</p>
            <ul class="materials" id="materials">{"".join(f"<li>{E(m.strip())}</li>" for m in str(site.get("materials", "")).split(",") if m.strip())}</ul>
          </div>
        </div>
        <div class="prose" id="statement">
{paras(site.get("statement"))}
        </div>
      </div>
    </div>

    <section class="quote">
      <div class="wrap"><blockquote id="pull">{E(site.get("about_quote"))}</blockquote></div>
    </section>

    <section class="section" aria-labelledby="bio-h">
      <div class="wrap">
        <div class="two-col">
          <div class="side">
            <h2 class="page-title" id="bio-h">Michael Joseph <span class="label">b. 1951</span></h2>
            <ol class="timeline" id="timeline">{"".join(f'<li><span class="y">{E(x.get("year"))}</span><span class="x">{E(x.get("text"))}</span></li>' for x in site.get("timeline", []))}</ol>
            <div>
              <p class="eyebrow">Paintings acquired by</p>
              <p class="label" id="collections">{E(site.get("collections"))}</p>
            </div>
          </div>
          <div class="prose" id="biography">
{paras(site.get("biography"))}
          </div>
        </div>
        <p class="label" id="sales-note">{E(site.get("sales_note"))}</p>
      </div>
    </section>'''
pages["about.html"] = ("about", "About Michael Joseph — Sculptor, Painter & Former BA Pilot, West Sussex",
                       "Michael Joseph (b. 1951): Rolls-Royce engineering apprentice, British Airways pilot, award-winning aviation painter, and now a sculptor casting his own bronze. His approach to art: a different perspective.",
                       about, site.get("about_image"), [])

# Exhibitions --------------------------------------------------------------
live = sorted([x for x in shows if show_state(x) != "past"], key=lambda x: x.get("start") or "")
past = sorted([x for x in shows if show_state(x) == "past"], key=lambda x: x.get("start") or "", reverse=True)
by_year = {}
for x in past:
    by_year.setdefault((date(x.get("start")) or dt.date(1900, 1, 1)).year, []).append(x)
exh = f'''    <div class="wrap">
      <header class="page-head">
        <p class="eyebrow">Exhibitions</p>
        <h1 class="page-title">Where to see the work</h1>
        <p>Sculpture gardens, galleries and open shows across Sussex, Surrey and Hampshire.</p>
      </header>
      <section aria-labelledby="cur-h">
        <h2 class="visually-hidden" id="cur-h">Current and upcoming</h2>
        <div id="current">{('<ul class="shows">' + "".join(show_row(x) for x in live) + "</ul>") if live else '<p class="empty-note">No exhibitions are scheduled just now — new dates will appear here.</p>'}</div>
      </section>
      <section aria-labelledby="past-h">
        <h2 class="year-head" id="past-h">Past exhibitions</h2>
        <div id="past">{"".join(f'<h3 class="year-head">{y}</h3><ul class="shows">' + "".join(show_row(x) for x in lst) + "</ul>" for y, lst in by_year.items())}</div>
      </section>
    </div>'''
ex_ld = [{"@type": "ExhibitionEvent", "name": x.get("title") or x.get("venue"), "startDate": x.get("start"), "endDate": x.get("end") or x.get("start"),
          "eventStatus": "https://schema.org/EventScheduled", "eventAttendanceMode": "https://schema.org/OfflineEventAttendanceMode",
          "location": {"@type": "Place", "name": x.get("venue"), "address": x.get("address")},
          "performer": {"@id": PERSON["@id"]}, **({"url": x["link"]} if safe_url(x.get("link")) else {})}
         for x in shows if date(x.get("start")) and not x.get("date_text")]
pages["exhibitions.html"] = ("exhibitions", "Exhibitions — Sculpture Gardens & Galleries in Surrey & Sussex | Michael Joseph",
                             "Where to see Michael Joseph's sculpture and paintings: current, upcoming and past exhibitions at sculpture gardens and galleries in Surrey, Sussex and Hampshire.",
                             exh, None, ex_ld)

# Contact ------------------------------------------------------------------
CAPTCHA = ('<div class="h-captcha" data-captcha="true"></div><script src="https://web3forms.com/client/script.js" async defer></script>'
           if str(site.get("form_access_key") or "").strip() and site.get("form_captcha") else "")
contact = f'''    <div class="wrap">
      <header class="page-head">
        <p class="eyebrow">Contact</p>
        <h1 class="page-title">Enquiries</h1>
        <p id="sales-note">{E(site.get("sales_note"))}</p>
      </header>
      <div class="two-col">
        <div class="side">
          <a class="contact-big" data-email href="mailto:{E(site.get("email"))}">{E(site.get("email"))}</a>
          <p class="label"><a data-phone href="#">{E(site.get("phone"))}</a><br><span data-location>{E(site.get("location"))}</span></p>
        </div>
        <form class="form" id="enquiry" novalidate>
          <div class="field"><label for="f-name">Your name</label><input id="f-name" name="name" autocomplete="name" required maxlength="100"></div>
          <div class="field"><label for="f-email">Your email</label><input id="f-email" name="email" type="email" autocomplete="email" required maxlength="160"></div>
          <div class="field"><label for="f-work">Artwork (optional)</label><input id="f-work" name="work" maxlength="120"></div>
          <div class="field"><label for="f-msg">Message</label><textarea id="f-msg" name="message" required maxlength="4000"></textarea></div>
          <div class="hp" aria-hidden="true"><label for="f-bc">Leave this empty</label><input id="f-bc" type="checkbox" name="botcheck" tabindex="-1" autocomplete="off"><label for="f-web">Website</label><input id="f-web" name="website" tabindex="-1" autocomplete="off"></div>
          {CAPTCHA}
          <button class="btn" type="submit">Send message</button>
          <p class="form-status" id="form-status" role="status" aria-live="polite"></p>
        </form>
      </div>
    </div>'''
pages["contact.html"] = ("contact", "Contact & Enquiries — Buy Work or Commission | Michael Joseph",
                         "Enquire about buying work, commissioning a sculpture, or visiting Michael Joseph's studio in West Sussex.", contact, None, [])

pages["404.html"] = ("404", "Page not found | Michael Joseph", "This page has moved.",
                     '''    <div class="wrap">
      <header class="page-head">
        <p class="eyebrow">404</p>
        <h1 class="page-title">This page has moved or no longer exists.</h1>
        <p><a class="arrow-link" href="/work.html">See the work</a></p>
      </header>
    </div>''', None, [])


# Artwork pages -------------------------------------------------------------
AC = ' aria-current="page"'


def art_media(a, pics, R):
    out = []
    for k, u in enumerate(pics):
        extra = ' fetchpriority="high"' if k == 0 else ""
        view = " — view %d" % (k + 1) if k else ""
        out.append('<figure><img src="%s" alt="%s%s" loading="%s"%s></figure>' % (E(img(u, 1800, R)), E(alt(a)), view, "eager" if k == 0 else "lazy", extra))
    return "".join(out)


def art_family(a, fam, R):
    if len(fam) < 2:
        return ""
    items = "".join('<li><a href="%s%s"%s><img src="%s" alt=""><span>%s</span></a></li>' % (
        R, PAGE_OF[id(k)], AC if k is a else "", E(img(k["image"], 200, R)), E(k.get("stage") or "Finished work")) for k in fam)
    return '<div class="art-family"><p class="eyebrow">From study to finished work</p><ol>%s</ol></div>' % items


_SYNE = None


def title_fit(t):
    """Size a work's title by its widest word (measured in the real font) so no word is ever split."""
    global _SYNE
    try:
        if _SYNE is None:
            from fontTools.ttLib import TTFont
            f = TTFont(ROOT / "assets/fonts/syne-latin-800-normal.woff2")
            _SYNE = (f.getBestCmap(), f["hmtx"].metrics, f["head"].unitsPerEm)
        cmap, hm, upm = _SYNE
        em = max((sum(hm[cmap[ord(c)]][0] if ord(c) in cmap else upm * .7 for c in w) / upm - .035 * len(w)
                  for w in re.split(r"[\s\-—–]+", t) if w), default=0)
    except Exception:  # fontTools missing: estimate
        em = max((len(w) for w in re.split(r"[\s\-—–]+", t)), default=0) * .95
    return f"fit-{min(16, max(4, math.ceil(em * 1.06)))}"


def art_page(a):
    R = "../"
    pics = [u for u in [a["image"], *(a.get("more_images") or [])] if img(u, 100)]
    fam_root = a.get("for_work") or a["title"]
    fam = [TITLE[fam_root]] if fam_root in TITLE and not TITLE[fam_root].get("stage") else []
    fam = [k for k in works if k.get("for_work") == fam_root] + fam
    same = [x for x in works if (x.get("series") or "") == (a.get("series") or "")]
    i = same.index(a)
    prev_a, next_a = same[i - 1] if i > 0 else None, same[i + 1] if i + 1 < len(same) else None
    status = {"available": "Available", "sold": "Sold", "private": "Private collection", "nfs": "Not for sale"}.get((a.get("status") or "").lower(), "")
    rows = [("Type", a.get("type")), ("Stage", lead(a)), ("Medium", a.get("medium")), ("Size", a.get("size")),
            ("Year", a.get("year")), ("Series", a.get("series")), ("Price", a.get("price")), ("Availability", status)]
    kind = (a.get("medium") or a.get("type") or "artwork")
    desc = a.get("notes") or f"{a['title']} by Michael Joseph — {kind.lower() if kind else 'artwork'}{', ' + a['size'] if a.get('size') else ''}. {('A ' + lead(a).lower() + '. ') if lead(a) else ''}From {a.get('series') or 'his work'}; British artist in West Sussex working in drawing, painting and sculpture."
    notes_html = '<p class="art-notes">%s</p>' % E(a["notes"]) if a.get("notes") else ""
    prev_html = '<a href="%s%s">← %s</a>' % (R, PAGE_OF[id(prev_a)], E(prev_a["title"])) if prev_a else "<span></span>"
    next_html = '<a href="%s%s">%s →</a>' % (R, PAGE_OF[id(next_a)], E(next_a["title"])) if next_a else "<span></span>"
    body = f'''    <div class="wrap art">
      <nav class="crumbs label" aria-label="Breadcrumb"><a href="{R}work.html">All work</a> / <a href="{R}work.html?series={slug(a.get("series"))}">{E(a.get("series"))}</a> / <span aria-current="page">{E(a["title"])}</span></nav>
      <div class="art-grid">
        <div class="art-media">
          {art_media(a, pics, R)}
        </div>
        <aside class="art-info">
          <p class="eyebrow">{E(a.get("type") or "Artwork")}</p>
          <h1 class="{title_fit(a["title"])}">{E(a["title"])}</h1>
          <dl>{"".join(f"<dt>{k}</dt><dd>{E(v)}</dd>" for k, v in rows if v)}</dl>
          {notes_html}
          {art_family(a, fam, R)}
          <div class="cta-row">
            <a class="btn" href="{R}contact.html?work={E(a["title"])}">Enquire about this work</a>
            <a class="arrow-link" href="{R}work.html#{slug(a["title"])}">View in the gallery</a>
          </div>
          <nav class="art-nav label" aria-label="More from this series">
            {prev_html}
            {next_html}
          </nav>
        </aside>
      </div>
    </div>'''
    ld = [{"@type": "VisualArtwork", "name": a["title"], "url": f"{BASE}/{PAGE_OF[id(a)]}", "image": [abs_img(u, 1600) for u in pics],
           "creator": {"@id": PERSON["@id"]}, "artform": a.get("type") or "Artwork", "description": desc,
           **({"artMedium": a["medium"]} if a.get("medium") else {}), **({"dateCreated": a["year"]} if a.get("year") else {}),
           **({"isPartOf": {"@type": "CreativeWorkSeries", "name": a["series"]}} if a.get("series") else {})},
          {"@type": "BreadcrumbList", "itemListElement": [
              {"@type": "ListItem", "position": 1, "name": "All work", "item": f"{BASE}/work.html"},
              {"@type": "ListItem", "position": 2, "name": a.get("series") or "Work", "item": f"{BASE}/work.html?series={slug(a.get('series'))}"},
              {"@type": "ListItem", "position": 3, "name": a["title"]}]}]
    ttl = f"{a['title']} — {kind} | Michael Joseph"
    return ("art", ttl, desc[:300], body, a["image"], ld)


# ---------------------------------------------------------------- write
def write(path, data):
    p = OUT / path
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(data, encoding="utf-8")


art_dir = OUT / "art"
if art_dir.exists():
    for old in art_dir.glob("*.html"):
        old.unlink()
for path, (key, ttl, desc, main, og, ld) in pages.items():
    write(path, page(path, key, ttl, desc, main, og, ld))
for a in works:
    key, ttl, desc, main, og, ld = art_page(a)
    write(PAGE_OF[id(a)], page(PAGE_OF[id(a)], key, ttl, desc, main, og, ld))

# sitemap with images
urls = []
for path in ["index.html", "sculpture.html", "figure.html", "work.html", "courses.html", "about.html", "exhibitions.html", "contact.html"]:
    urls.append((f"{BASE}/" if path == "index.html" else f"{BASE}/{path}", []))
for a in works:
    urls.append((f"{BASE}/{PAGE_OF[id(a)]}", [abs_img(u, 1600) for u in [a["image"], *(a.get("more_images") or [])] if img(u, 100)]))
sm = ['<?xml version="1.0" encoding="UTF-8"?>',
      '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:image="http://www.google.com/schemas/sitemap-image/1.1">']
for loc, ims in urls:
    sm.append(f"  <url><loc>{E(loc)}</loc><lastmod>{TODAY.isoformat()}</lastmod>" + "".join(f"<image:image><image:loc>{E(i)}</image:loc></image:image>" for i in ims) + "</url>")
sm.append("</urlset>")
write("sitemap.xml", "\n".join(sm) + "\n")
print(f"built {len(pages)} pages + {len(works)} artwork pages")
