"""Render Markdown and Jinja templates to unstyled HTML for Tailwind."""

import json
import sys
from datetime import date
from pathlib import Path

import yaml
from jinja2 import Environment, FileSystemLoader, select_autoescape
from markdown_it import MarkdownIt
from markupsafe import Markup

mode, output, *sources = sys.argv[1:]
output = Path(output)
depth = len(output.relative_to(".build/html").parent.parts)
root = "../" * depth or "./"
images = json.loads(Path(".build/images.json").read_text(encoding="utf-8"))

md = MarkdownIt("commonmark", {"html": False})


def image_attrs(name, sizes):
    if name not in images:
        raise SystemExit(f"Missing local image: assets/images/{name}")
    variants = images[name]
    largest = variants[-1]
    return {
        "src": root + variants[min(1, len(variants) - 1)]["url"],
        "srcset": ", ".join(f'{root}{v["url"]} {v["width"]}w' for v in variants),
        "sizes": sizes,
        "width": largest["width"],
        "height": largest["height"],
    }


def render_image(tokens, idx, options, env):
    token = tokens[idx]
    src = token.attrGet("src")
    if src.startswith("media/"):
        for key, value in image_attrs(
            src.removeprefix("media/"), "(min-width: 48rem) 42rem, calc(100vw - 2.5rem)"
        ).items():
            token.attrSet(key, str(value))
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
    return {**fields, "body": body, "date": published,
            "url": f'{root}blog/{path.stem}/'}


templates = Environment(
    loader=FileSystemLoader("templates"),
    autoescape=select_autoescape(),
    trim_blocks=True,
    lstrip_blocks=True,
)
templates.filters["short_date"] = lambda value: value.strftime("%d %b %Y").lstrip("0")
profile = yaml.safe_load(Path("content/profile.yaml").read_text(encoding="utf-8"))
context = dict(profile=profile, root=root, section=mode)
if mode == "home":
    context.update(title=profile["name"], description=profile["intro"],
                   portrait=image_attrs(profile["avatar"], "(min-width: 40rem) 12rem, 7rem"))
elif mode == "about":
    context.update(title="About", description=f'About {profile["name"]}.',
                   body=Markup(md.render(Path(sources[0]).read_text(encoding="utf-8"))))
elif mode == "blog":
    context.update(title="Writing", description=f'Posts by {profile["name"]}.')
elif mode == "post":
    post = read_post(sources[0])
    context.update(title=post["title"], description=post["summary"],
                   post=post, body=Markup(md.render(post["body"])))

if mode in {"home", "blog"}:
    posts = sorted(map(read_post, sources), key=lambda post: post["date"], reverse=True)
    context["posts"] = posts[:3] if mode == "home" else posts
output.write_text(templates.get_template(f"{mode}.html").render(context) + "\n",
                  encoding="utf-8")
