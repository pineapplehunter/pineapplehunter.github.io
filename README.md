# pineapplehunter's website

A static personal site for Shogo Takata. The build uses Python, Ninja, the Tailwind v4 standalone CLI, Pillow, and libjxl; the published site needs no JavaScript except for the optional theme override.

## Build and preview

```sh
nix develop
./build.sh
python3 -m http.server --directory dist 8000
```

Open <http://localhost:8000>. `nix develop -c ./build.sh` also works without entering the shell. To preview Ninja's work without building, run `python3 configure.py` followed by `ninja -f .build/build.ninja -n`. `dist/` is generated-only; the generator removes files there that no longer have a target.

## Write a post

Write in Japanese first. Add `content/posts/first-post.ja.md` using a lowercase, hyphen-separated slug:

```markdown
---
title: 最初の記事
date: 2026-11-20
summary: 記事一覧とページの説明に使う短い概要。
---

本文はここから。記事内の見出しにはレベル2から使います。
```

The Japanese post is published at `/blog/first-post/`. Add an optional `content/posts/first-post.en.md` with the same slug and English front matter and text to publish it at `/en/blog/first-post/`. The English index lists Japanese-only posts with a label and links to their originals until an English translation is added.

The Japanese index is at `/` and the English index at `/en/`. Edit `content/about.ja.md` and `content/about.en.md` for the bios, `content/profile.yaml` for shared profile links, localized details, and the public site origin used in `hreflang` links, and `content/ui.yaml` for interface labels. The starter information and avatar come from [pineapplehunter's public GitHub profile](https://github.com/pineapplehunter).

## Images and build steps

Put a JPG, PNG, or WebP under `assets/images/`, then reference it as a Markdown image:

```markdown
![Description of the photo](media/bench.jpg)
```

The build generates JPEG XL, WebP, and PNG variants up to 240, 480, and 960 pixels wide, without upscaling. A native `<picture>` lets the browser choose the first format it supports in that order and pick a responsive size. Nested folders work; use the same relative path after `media/`.

`./build.sh` runs `configure.py`, which uses `ninja.ninja_syntax` to emit `.build/build.ninja`. The script forwards all arguments to `configure.py`. For a project site, run `./build.sh --base-path /my-repo`; the default is `/`. To use Ninja options, run Ninja directly after configuring.

Each page follows this chain:

```text
Markdown + Jinja → intermediate HTML → per-page Tailwind CSS → dist HTML with inline CSS
```

Tailwind scans only the intermediate HTML for that page. Edit its theme in `styles/site.css`. To add another preprocessor, follow `tools/images.py`: register a Ninja rule and its input/output edges in `configure.py`, then include the generated files in the `site` target. If rendering consumes a generated file, add it to the render edge's inputs.

## Publish to GitHub Pages

In the repository's **Settings → Pages**, set **Source** to **GitHub Actions**. Push to `main` (or run the workflow manually). The workflow builds and uploads only `dist/`. Regular pages use relative links so they work at the domain root or under a repository path. GitHub Pages serves the Japanese `dist/404.html` for missing URLs, with a link to `/en/404.html`; the workflow passes GitHub Pages’ base path to `./build.sh --base-path` so its navigation works even from a nested URL. To preview its design with the local server, open `/404.html` directly. Tailwind v4 targets modern browsers; the underlying pages use standard HTML and native links.
