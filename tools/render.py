"""Render Markdown and Jinja templates into the static site."""

import base64
import hashlib
import json
import re
import sys
from datetime import date
from pathlib import Path

import yaml
from jinja2 import Environment, FileSystemLoader, select_autoescape
from markdown_it import MarkdownIt
from markdown_it.token import Token
from markupsafe import Markup, escape
from mdit_py_plugins.footnote import footnote_plugin

mode, output, lang, site_root, alternate, live_reload_arg, stylesheet, *sources = sys.argv[1:]
live_reload = live_reload_arg == "1"
output = Path(output)
output_dir = "dist" if output.is_relative_to("dist") else ".build/unmeasured"
filename = output.relative_to(output_dir)
depth = len(filename.parent.parts)
# GitHub Pages can serve the 404 at any URL depth.
root = site_root if mode == "404" else "../" * depth or "./"
home = root + ("en/" if lang == "en" else "")
other_lang = "en" if lang == "ja" else "ja"
other_home = "en/" if other_lang == "en" else ""
images = json.loads(Path(".build/images.json").read_text(encoding="utf-8"))

md = MarkdownIt("commonmark", {"html": False}).use(footnote_plugin, inline=False)
FOOTNOTE_REF = re.compile(r"\[\^([^ \n\]]+)\]")


def collect_undefined_footnote(state, silent):
    # Defined notes, code spans, and escaped brackets have already been handled.
    match = FOOTNOTE_REF.match(state.src, state.pos, state.posMax)
    if match is None:
        return False
    if not silent:
        state.env.setdefault("undefined_footnotes", set()).add(match[1])
        state.pending += match[0]
    state.pos = match.end()
    return True


md.inline.ruler.after("footnote_ref", "undefined_footnote", collect_undefined_footnote)


def caption_figures(state):
    tokens = state.tokens
    for idx in range(len(tokens) - 2, 0, -1):
        opening, inline, closing = tokens[idx - 1:idx + 2]
        if (opening.type, inline.type, closing.type) != ("paragraph_open", "inline", "paragraph_close"):
            continue
        if opening.hidden or not inline.children or len(inline.children) != 1:
            continue
        image = inline.children[0]
        if image.type != "image" or not (caption := image.attrGet("title")):
            continue
        image.attrs.pop("title")
        opening.type, opening.tag = "figure_open", "figure"
        closing.type, closing.tag = "figure_close", "figure"
        tokens[idx + 1:idx + 1] = [
            Token("figcaption_open", "figcaption", 1, block=True),
            Token("inline", "", 0, children=[Token("text", "", 0, content=caption)]),
            Token("figcaption_close", "figcaption", -1, block=True),
        ]


md.core.ruler.after("footnote_tail", "caption_figures", caption_figures)


def render_markdown(text, source):
    env = {}
    tokens = md.parse(text, env)
    missing = sorted(env.get("undefined_footnotes", ()))
    if missing:
        severity = "warning" if live_reload else "error"
        for label in missing:
            print(f"{source}: {severity}: undefined footnote reference [^{label}]", file=sys.stderr)
        if not live_reload:
            raise SystemExit(1)
    return Markup(md.renderer.render(tokens, md.options, env))


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
        name = src.removeprefix("media/")
        variants = images.get(name)
        if variants and variants[0].get("format") == "svg":
            token.attrSet("src", root + src)
            for key in ("width", "height"):
                token.attrSet(key, str(variants[0][key]))
        else:
            image = picture_attrs(name, "(min-width: 48rem) 42rem, calc(100vw - 2.5rem)")
            alt = md.renderer.renderInlineAsText(token.children, options, env)
            picture = templates.get_template("_picture.html").module.picture
            return picture(image, alt, title=token.attrGet("title"), lazy=True).strip()
    token.attrSet("loading", "lazy")
    token.attrSet("decoding", "async")
    return md.renderer.image(tokens, idx, options, env)


def render_footnote_caption(tokens, idx, options, env):
    # Repeated references keep the same number, with distinct backlink targets.
    return f'[{tokens[idx].meta["id"] + 1}]'


def render_footnote_block_open(tokens, idx, options, env):
    return ('<section class="footnotes" aria-labelledby="footnotes-heading">\n'
            f'<h2 id="footnotes-heading">{escape(ui["footnotes"])}</h2>\n<ol>\n')


md.renderer.rules.update(image=render_image, footnote_caption=render_footnote_caption,
                         footnote_block_open=render_footnote_block_open)


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
css_digest = hashlib.sha384(Path(stylesheet).read_bytes()).digest()
css_integrity = "sha384-" + base64.b64encode(css_digest).decode("ascii")
context = dict(profile=profile, root=root, home=home, section=mode, lang=lang, ui=ui,
               css_integrity=css_integrity,
               alternates=alternates, other_lang=other_lang,
               live_reload=live_reload, reload_url=site_root + "__live_reload",
               language_href=root + (alternate_url if alternate else other_home),
               language_label=ui["other_language" if alternate else "other_index"])
if mode == "about":
    about, *posts = sources
    context.update(title=ui["about"], description=profile["intro"][lang],
                   portrait=picture_attrs(profile["avatar"], "(min-width: 40rem) 12rem, 7rem"),
                   body=render_markdown(Path(about).read_text(encoding="utf-8"), about))
elif mode == "blog":
    posts = sources
    context.update(title=ui["writing"], description=ui["writing_description"])
elif mode == "post":
    post = read_post(sources[0])
    context.update(title=post["title"], description=post["summary"],
                   post=post, body=render_markdown(post["body"], sources[0]))
elif mode == "404":
    context.update(title=f'404: {ui["not_found"]}', description=ui["not_found_description"])

if mode in {"about", "blog"}:
    posts = sorted(map(read_post, posts), key=lambda post: post["date"], reverse=True)
    context["posts"] = posts[:3] if mode == "about" else posts
output.write_text(templates.get_template(f"{mode}.html").render(context) + "\n",
                  encoding="utf-8")
