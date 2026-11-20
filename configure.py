#!/usr/bin/env python3
"""Discover content and write the Ninja build graph (run via ./build.sh)."""

import argparse
import json
import re
import shlex
import shutil
import sys
from pathlib import Path

from ninja import ninja_syntax

from tools.images import configure_images

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--base-path", default="/", help="URL path where the site is hosted (default: /)")
base_path = parser.parse_args().base_path.strip("/")
site_root = f"/{base_path}/" if base_path else "/"

work = Path(".build")
dist = Path("dist")
work.mkdir(exist_ok=True)

posts = sorted(Path("content/posts").glob("*.md"))
for post in posts:
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", post.stem):
        raise SystemExit(f"{post}: use a lowercase, hyphen-separated filename")

with (work / "build.ninja").open("w", encoding="utf-8") as file:
    ninja = ninja_syntax.Writer(file)
    ninja.variable("builddir", str(work))
    ninja.variable("python", ninja_syntax.escape(shlex.quote(sys.executable)))
    tailwind = shutil.which("tailwindcss")
    if not tailwind:
        raise SystemExit("Install Tailwind CSS v4 or run nix develop -c ./build.sh")
    ninja.variable("tailwindcss", ninja_syntax.escape(shlex.quote(tailwind)))
    cjxl = shutil.which("cjxl")
    if not cjxl:
        raise SystemExit("Install libjxl's cjxl or run nix develop -c ./build.sh")
    ninja.variable("cjxl", ninja_syntax.escape(shlex.quote(cjxl)))
    ninja.rule("render", "$python tools/render.py $mode $out $args $in", "Render $out")
    ninja.rule("tailwind", "$python tools/style.py compile $in $out $tailwindcss", "Tailwind $out")
    ninja.rule("inline", "$python tools/style.py inline $in $out", "Inline CSS $out")

    images, outputs = configure_images(ninja, dist)
    manifest = work / "images.json"
    data = json.dumps(images, indent=2) + "\n"
    if not manifest.exists() or manifest.read_text(encoding="utf-8") != data:
        manifest.write_text(data, encoding="utf-8")

    render_deps = [
        "tools/render.py",
        "content/profile.yaml",
        str(manifest),
        *map(str, sorted(Path("templates").glob("*.html"))),
    ]

    def page(filename, mode, sources=(), args=""):
        html = work / "html" / filename
        css = work / "css" / Path(filename).with_suffix(".css")
        final = dist / filename
        ninja.build(str(html), "render", list(map(str, sources)), implicit=render_deps,
                    variables={"mode": mode, "args": args})
        ninja.build(str(css), "tailwind", str(html),
                    implicit=["styles/site.css", "tools/style.py"])
        ninja.build(str(final), "inline", [str(html), str(css)], implicit="tools/style.py")
        outputs.append(str(final))

    page("index.html", "blog", posts)
    page("about/index.html", "about", ["content/about.md", *posts])
    # A 404 can be served at any URL depth, so it needs site-rooted links.
    page("404.html", "404", args=ninja_syntax.escape(shlex.quote(site_root)))
    for post in posts:
        page(f"blog/{post.stem}/index.html", "post", [post])
    ninja.build("site", "phony", outputs)
    ninja.default("site")

# dist/ is generated-only: don't deploy URLs left over after a rename or deletion.
keep = set(outputs)
for path in sorted(dist.rglob("*"), key=lambda path: len(path.parts), reverse=True):
    if path.is_dir() and not path.is_symlink():
        if not any(path.iterdir()):
            path.rmdir()
    elif str(path) not in keep:
        path.unlink()
