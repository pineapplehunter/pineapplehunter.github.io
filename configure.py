#!/usr/bin/env python3
"""Discover content and write the Ninja build graph (run via ./build.sh)."""

import argparse
import json
import re
import shlex
import shutil
import sys
from pathlib import Path

import yaml
from ninja import ninja_syntax

from tools.images import IMAGE_DIR, configure_images
from tools.page_size import MARKERS

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--base-path", default="/", help="URL path where the site is hosted (default: /)")
parser.add_argument("--live-reload", action="store_true",
                    help="Embed the live-reload script for the local preview server")
args = parser.parse_args()
base_path = args.base_path.strip("/")
site_root = f"/{base_path}/" if base_path else "/"

work = Path(".build")
dist = Path("dist")
work.mkdir(exist_ok=True)

prefixes = {"ja": "", "en": "en/"}
posts = {lang: {} for lang in prefixes}
for post in sorted(Path("content/posts").glob("*.md")):
    match = re.fullmatch(r"([a-z0-9]+(?:-[a-z0-9]+)*)\.(ja|en)\.md", post.name)
    if not match:
        raise SystemExit(f"{post}: use a filename like example-post.ja.md or example-post.en.md")
    slug, lang = match.groups()
    posts[lang][slug] = post
for slug in posts["en"].keys() - posts["ja"].keys():
    raise SystemExit(f"{posts['en'][slug]}: missing the Japanese source {slug}.ja.md")

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
    ninja.variable("site_root", ninja_syntax.escape(shlex.quote(site_root)))
    ninja.variable("live_reload", "1" if args.live_reload else "0")
    stylesheet = str(dist / "assets/site.css")
    ninja.variable("stylesheet", stylesheet)
    ninja.rule("render",
               "$python tools/render.py $mode $out $lang $site_root $alternate $live_reload $stylesheet $in",
               "Render $out")
    # Tailwind leaves the output untouched when the generated CSS is unchanged.
    ninja.rule("tailwind", "$tailwindcss --input $in --output $out --minify --silent",
               "Tailwind $out", restat=True)

    images, outputs = configure_images(ninja, dist)
    profile = yaml.safe_load(Path("content/profile.yaml").read_text(encoding="utf-8"))
    favicon = str(dist / "favicon.png")
    ninja.rule("favicon", "$python tools/images.py favicon $in $out", "Favicon $out")
    ninja.build(favicon, "favicon", str(IMAGE_DIR / profile["avatar"]), implicit="tools/images.py")
    outputs.append(favicon)
    manifest = work / "images.json"
    data = json.dumps(images, indent=2) + "\n"
    if not manifest.exists() or manifest.read_text(encoding="utf-8") != data:
        manifest.write_text(data, encoding="utf-8")

    templates = list(map(str, sorted(Path("templates").glob("*.html"))))
    ninja.build("template-inputs", "phony", templates)
    ninja.build(stylesheet, "tailwind", "styles/site.css", implicit="template-inputs")
    outputs.append(stylesheet)
    ninja.rule("page_size", "$python tools/page_size.py $in $out $site_root", "Measure $out")
    ninja.build("page-size-inputs", "phony", [*outputs, "tools/page_size.py"])

    ninja.build("render-inputs", "phony",
                ["template-inputs", "tools/render.py", "content/profile.yaml",
                 "content/ui.yaml", str(manifest), stylesheet])

    def page(filename, mode, lang, sources=(), alternate=""):
        html = str(dist / filename)
        rendered = html
        if mode == "post":
            source = sources[0].read_bytes()
            if any(marker in source for marker in MARKERS):
                rendered = str(work / "unmeasured" / filename)
                ninja.build(html, "page_size", [rendered, str(sources[0])],
                            implicit="page-size-inputs")
        ninja.build(rendered, "render", list(map(str, sources)), implicit="render-inputs",
                    variables={"mode": mode, "lang": lang, "alternate": shlex.quote(alternate)})
        outputs.append(html)

    for lang, prefix in prefixes.items():
        other = "en" if lang == "ja" else "ja"
        other_prefix = prefixes[other]
        listing = (posts["ja"] | posts[lang]).values()
        page(prefix + "index.html", "blog", lang, listing, other_prefix + "index.html")
        page(prefix + "about/index.html", "about", lang,
             [f"content/about.{lang}.md", *listing], other_prefix + "about/index.html")
        page(prefix + "404.html", "404", lang, alternate=other_prefix + "404.html")
        for slug, post in posts[lang].items():
            route = f"blog/{slug}/index.html"
            alternate = other_prefix + route if slug in posts[other] else ""
            page(prefix + route, "post", lang, [post], alternate)
    site_inputs = outputs
    if args.live_reload:
        # Signal the browser only after all site outputs are up to date.
        stamp = str(work / "live-reload")
        ninja.rule("reload_stamp", "touch $out", "Update live reload")
        ninja.build(stamp, "reload_stamp", outputs)
        site_inputs = [*outputs, stamp]
    ninja.build("site", "phony", site_inputs)
    ninja.default("site")

# dist/ is generated-only: don't deploy URLs left over after a rename or deletion.
keep = set(outputs)
for path in sorted(dist.rglob("*"), key=lambda path: len(path.parts), reverse=True):
    if path.is_dir() and not path.is_symlink():
        if not any(path.iterdir()):
            path.rmdir()
    elif str(path) not in keep:
        path.unlink()
