"""Render Markdown and Jinja templates into the static site."""

import json
import sys
from datetime import date
from pathlib import Path

import yaml
from jinja2 import Environment, FileSystemLoader, select_autoescape
from markdown_it import MarkdownIt
from markupsafe import Markup

mode, output, lang, site_root, alternate, live_reload, *sources = sys.argv[1:]
output = Path(output)
filename = output.relative_to("dist")
depth = len(filename.parent.parts)
# GitHub Pages can serve the 404 at any URL depth.
root = site_root if mode == "404" else "../" * depth or "./"
home = root + ("en/" if lang == "en" else "")
other_lang = "en" if lang == "ja" else "ja"
other_home = "en/" if other_lang == "en" else ""
images = json.loads(Path(".build/images.json").read_text(encoding="utf-8"))

md = MarkdownIt("commonmark", {"html": False})


def picture_attrs(name, sizes):
    if name not in images:
        raise SystemExit(f"Missing local image: assets/images/{name}")
    variants = images[name]
    largest = variants[-1]

    def srcset(ext):
        return ", ".join(f'{root}{v["stem"]}.{ext} {v["width"]}w' for v in variants)

    return {
        "sources": [(f"image/{ext}", srcset(ext)) for ext in ("jxl", "webp")],
        "src": root + variants[min(1, len(variants) - 1)]["stem"] + ".png",
        "srcset": srcset("png"),
        "sizes": sizes,
        "width": largest["width"],
        "height": largest["height"],
    }


def render_image(tokens, idx, options, env):
    token = tokens[idx]
    src = token.attrGet("src")
    if src.startswith("media/"):
        image = picture_attrs(
            src.removeprefix("media/"), "(min-width: 48rem) 42rem, calc(100vw - 2.5rem)"
        )
        alt = md.renderer.renderInlineAsText(token.children, options, env)
        picture = templates.get_template("_picture.html").module.picture
        return picture(image, alt, title=token.attrGet("title"), lazy=True).strip()
    token.attrSet("loading", "lazy")
    token.attrSet("decoding", "async")
    return md.renderer.image(tokens, idx, options, env)


md.renderer.rules["image"] = render_image


def read_post(filename):
    path = Path(filename)
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n") or "\n---\n" not in text[4:]:
        raise SystemExit(f"{path}: add YAML front matter with title, date and summary")
    metadata, body = text[4:].split("\n---\n", 1)
    fields = yaml.safe_load(metadata)
    published = date.fromisoformat(str(fields["date"]))
    slug, post_lang = path.stem.rsplit(".", 1)
    prefix = "en/" if post_lang == "en" else ""
    return {**fields, "body": body, "date": published, "lang": post_lang,
            "url": f"{root}{prefix}blog/{slug}/"}


templates = Environment(
    loader=FileSystemLoader("templates"),
    autoescape=select_autoescape(),
    trim_blocks=True,
    lstrip_blocks=True,
)
def short_date(value):
    if lang == "ja":
        return f"{value.year}年{value.month}月{value.day}日"
    return value.strftime("%d %b %Y").lstrip("0")


templates.filters["short_date"] = short_date
profile = yaml.safe_load(Path("content/profile.yaml").read_text(encoding="utf-8"))
ui = yaml.safe_load(Path("content/ui.yaml").read_text(encoding="utf-8"))[lang]
site_url = profile["site_origin"].rstrip("/") + site_root
alternate_url = alternate.removesuffix("index.html")
alternates = {}
if alternate and mode != "404":
    alternates = {
        lang: site_url + filename.as_posix().removesuffix("index.html"),
        other_lang: site_url + alternate_url,
    }
context = dict(profile=profile, root=root, home=home, section=mode, lang=lang, ui=ui,
               alternates=alternates, other_lang=other_lang,
               live_reload=live_reload == "1", reload_url=site_root + "__live_reload",
               language_href=root + (alternate_url if alternate else other_home),
               language_label=ui["other_language" if alternate else "other_index"])
if mode == "about":
    about, *posts = sources
    context.update(title=ui["about"], description=profile["intro"][lang],
                   portrait=picture_attrs(profile["avatar"], "(min-width: 40rem) 12rem, 7rem"),
                   body=Markup(md.render(Path(about).read_text(encoding="utf-8"))))
elif mode == "blog":
    posts = sources
    context.update(title=ui["writing"], description=ui["writing_description"])
elif mode == "post":
    post = read_post(sources[0])
    context.update(title=post["title"], description=post["summary"],
                   post=post, body=Markup(md.render(post["body"])))
elif mode == "404":
    context.update(title=f'404: {ui["not_found"]}', description=ui["not_found_description"])

if mode in {"about", "blog"}:
    posts = sorted(map(read_post, posts), key=lambda post: post["date"], reverse=True)
    context["posts"] = posts[:3] if mode == "about" else posts
output.write_text(templates.get_template(f"{mode}.html").render(context) + "\n",
                  encoding="utf-8")
