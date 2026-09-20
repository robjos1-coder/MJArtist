"""One-off: copy every artwork image off Wix and into this site's images/ folder.

The catalogue starts out pointing at the original photos on Wix's servers so the
new site works straight away. Run this once (GitHub > Actions > "Publish site" >
Run workflow > tick "Import images from Wix") before cancelling Wix, and every
image becomes a file you own. Content files are rewritten to point at the copies.
"""
import json, pathlib, re, sys, time, urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
IMAGES = ROOT / "images"
WIX = re.compile(r"^https://static\.wixstatic\.com/media/([A-Za-z0-9_~.\-]+)$")
MAX_BYTES = 60 * 1024 * 1024

def slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", s.lower().replace("&", "and")).strip("-") or "image"

def fetch(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "mjartist-image-import"})
    with urllib.request.urlopen(req, timeout=60) as r:  # https only, host checked by regex
        if not r.headers.get("Content-Type", "").startswith("image/"):
            raise ValueError("not an image")
        data = r.read(MAX_BYTES + 1)
        if len(data) > MAX_BYTES:
            raise ValueError("too large")
        return data

DONE: dict[str, str] = {}

def localise(url: str, name: str, used: set) -> str:
    m = WIX.match(url or "")
    if not m:
        return url
    if url in DONE:
        return DONE[url]
    ext = pathlib.Path(m.group(1)).suffix.lower() or ".jpg"
    base, n = slug(name), 1
    fn = f"{base}{ext}"
    while fn in used:
        n += 1; fn = f"{base}-{n}{ext}"
    used.add(fn)
    dest = IMAGES / fn
    if not dest.exists():
        for attempt in range(3):
            try:
                dest.write_bytes(fetch(url)); break
            except Exception as e:
                if attempt == 2:
                    print(f"FAILED {name}: {e}", file=sys.stderr); used.discard(fn); return url
                time.sleep(2)
    print(f"ok  {fn}")
    DONE[url] = f"images/{fn}"
    return DONE[url]

def walk(node, used, hint="image"):
    """Localise every Wix URL anywhere in the tree, whatever key holds it.

    Images sit under assorted keys (hero_image, scale_image, foundry[].image),
    so walk the whole structure rather than naming keys one by one. Strings
    that are not Wix URLs pass through localise() unchanged.
    """
    if isinstance(node, dict):
        title = node.get("title")
        return {k: walk(v, used, title or k.replace("_", "-")) for k, v in node.items()}
    if isinstance(node, list):
        return [walk(v, used, hint) for v in node]
    if isinstance(node, str):
        return localise(node, hint, used)
    return node

def main() -> None:
    IMAGES.mkdir(exist_ok=True)
    used = {p.name for p in IMAGES.iterdir()}
    # The catalogue is split one file per medium; artworks.json is generated.
    for works_f in sorted(ROOT.glob("content/artworks-*.json")):
        doc = json.loads(works_f.read_text(encoding="utf-8"))
        works = doc["items"] if isinstance(doc, dict) and isinstance(doc.get("items"), list) else doc
        for w in works:
            name = w.get("title", "artwork")
            w["image"] = localise(w.get("image", ""), name, used)
            w["more_images"] = [localise(u, f"{name} view", used) for u in w.get("more_images") or []]
        works_f.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    site_f = ROOT / "content/site.json"
    site = json.loads(site_f.read_text(encoding="utf-8"))
    site = walk(site, used)
    site_f.write_text(json.dumps(site, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

if __name__ == "__main__":
    main()
