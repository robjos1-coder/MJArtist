"""Shrink oversized photos so the site stays fast.

Runs automatically on GitHub every time something is published. Any image in
images/ wider or taller than MAX_EDGE px (e.g. straight off a phone) is resized,
rotated the right way up, stripped of hidden metadata (camera GPS location etc.)
and re-saved as a high-quality JPEG. Small images are left alone.
"""
import json, pathlib, sys
from PIL import Image, ImageOps

MAX_EDGE = 2400
QUALITY = 86
ROOT = pathlib.Path(__file__).resolve().parent.parent
IMAGES = ROOT / "images"
EXTS = {".jpg", ".jpeg", ".png", ".webp", ".tif", ".tiff", ".heic"}
Image.MAX_IMAGE_PIXELS = 120_000_000  # guard against decompression bombs

def process(path: pathlib.Path) -> pathlib.Path | None:
    try:
        with Image.open(path) as im:
            has_meta = bool(im.info.get("exif")) or bool(im.getexif())
            big = max(im.size) > MAX_EDGE
            convert = path.suffix.lower() in {".tif", ".tiff", ".heic", ".webp"} or (path.suffix.lower() == ".png" and big)
            if not (big or has_meta or convert):
                return None
            im = ImageOps.exif_transpose(im)
            if im.mode in ("RGBA", "LA", "P"):
                bg = Image.new("RGB", im.size, (255, 255, 255))
                im = im.convert("RGBA"); bg.paste(im, mask=im.split()[-1]); im = bg
            else:
                im = im.convert("RGB")
            im.thumbnail((MAX_EDGE, MAX_EDGE), Image.LANCZOS)
            out = path.with_suffix(".jpg")
            im.save(out, "JPEG", quality=QUALITY, optimize=True, progressive=True)  # no exif written
        if out != path:
            path.unlink()
        return out
    except Exception as e:  # never fail the publish because of one odd file
        print(f"skip {path.name}: {e}", file=sys.stderr)
        return None

def fix_references(renamed: dict[str, str]) -> None:
    if not renamed:
        return
    for f in (ROOT / "content").glob("*.json"):
        text = f.read_text(encoding="utf-8")
        new = text
        for old, nu in renamed.items():
            new = new.replace(old, nu)
        if new != text:
            json.loads(new)  # make sure we never write broken JSON
            f.write_text(new, encoding="utf-8")

def main() -> None:
    renamed, changed = {}, 0
    for p in sorted(IMAGES.rglob("*")):
        if p.is_file() and p.suffix.lower() in EXTS:
            out = process(p)
            if out:
                changed += 1
                if out.name != p.name:
                    renamed[f"images/{p.relative_to(IMAGES).as_posix()}"] = f"images/{out.relative_to(IMAGES).as_posix()}"
    fix_references(renamed)
    print(f"optimised {changed} image(s)")

if __name__ == "__main__":
    main()
