"""Register WebP resize edges and expose sizes to the HTML renderer."""

import sys
from pathlib import Path

from PIL import Image, ImageOps

IMAGE_DIR = Path("assets/images")
WIDTHS = (240, 480, 960)


def configure_images(ninja, dist):
    ninja.rule("webp", "$python tools/images.py $in $out $width $height", "WebP $out")
    manifest, outputs = {}, []
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
            url = Path("media") / name.with_name(f"{name.name}-{w}.webp")
            target = str(dist / url)
            ninja.build(target, "webp", str(source), implicit="tools/images.py",
                        variables={"width": str(w), "height": str(h)})
            outputs.append(target)
            variants.append({"url": url.as_posix(), "width": w, "height": h})
        manifest[name.as_posix()] = variants
    return manifest, outputs


if __name__ == "__main__":
    _, source, output, width, height = sys.argv
    with Image.open(source) as image:
        image = ImageOps.exif_transpose(image)
        # Convert palette and grayscale images too, preserving any transparency.
        mode = "RGBA" if "A" in image.getbands() or "transparency" in image.info else "RGB"
        image.convert(mode).resize(
            (int(width), int(height)), Image.Resampling.LANCZOS
        ).save(output, "WEBP", quality=84)
