"""Register responsive image encodes and expose sizes to the HTML renderer."""

import sys
from pathlib import Path

from PIL import Image, ImageOps

IMAGE_DIR = Path("assets/images")
WIDTHS = (240, 480, 960)


def configure_images(ninja, dist):
    for ext in ("png", "webp"):
        ninja.rule(ext, f"$python tools/images.py {ext} $in $out $width $height", f"{ext.upper()} $out")
    ninja.rule("jxl", "$cjxl $in $out --quality=90 --num_threads=1 --quiet", "JPEG XL $out")
    manifest = {}
    outputs = {ext: [] for ext in ("png", "webp", "jxl")}
    for source in sorted(IMAGE_DIR.rglob("*")):
        if source.suffix.lower() not in {".jpg", ".jpeg", ".png", ".webp"}:
            continue
        name = source.relative_to(IMAGE_DIR)
        if any(not part.isascii() or not all(c.isalnum() or c in "-_." for c in part)
               for part in name.parts):
            raise SystemExit(f"{source}: use letters, numbers, hyphens or underscores")
        with Image.open(source) as image:
            width, height = image.size
            if image.getexif().get(274) in {5, 6, 7, 8}:
                width, height = height, width
        variants = []
        for w in sorted({min(candidate, width) for candidate in WIDTHS}):
            h = max(1, round(w * height / width))
            stem = Path("media") / name.with_name(f"{name.name}-{w}")
            targets = {ext: str(dist / f"{stem.as_posix()}.{ext}") for ext in outputs}
            for ext in ("png", "webp"):
                ninja.build(targets[ext], ext, str(source), implicit="tools/images.py",
                            variables={"width": str(w), "height": str(h)})
            ninja.build(targets["jxl"], "jxl", targets["png"])
            for ext, target in targets.items():
                outputs[ext].append(target)
            variants.append({"stem": stem.as_posix(), "width": w, "height": h})
        manifest[name.as_posix()] = variants
    for ext, targets in outputs.items():
        ninja.build(f"images-{ext}", "phony", targets)
    return manifest, [target for targets in outputs.values() for target in targets]


if __name__ == "__main__":
    if sys.argv[1] == "favicon":
        _, _, source, output = sys.argv
        with Image.open(source) as image:
            icon = ImageOps.pad(ImageOps.exif_transpose(image).convert("RGBA"), (48, 48),
                                method=Image.Resampling.LANCZOS)
            icon.save(output, "PNG", optimize=True)
        sys.exit(0)

    _, ext, source, output, width, height = sys.argv
    with Image.open(source) as image:
        image = ImageOps.exif_transpose(image)
        # Convert palette and grayscale images too, preserving any transparency.
        mode = "RGBA" if "A" in image.getbands() or "transparency" in image.info else "RGB"
        resized = image.convert(mode).resize((int(width), int(height)), Image.Resampling.LANCZOS)
        if ext == "png":
            resized.save(output, "PNG", optimize=True)
        else:
            resized.save(output, "WEBP", quality=84)
