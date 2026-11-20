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

Add a Markdown file to `content/posts/` with a lowercase, hyphen-separated filename such as `first-post.md`:

```markdown
---
title: First post
date: 2026-11-20
summary: A short description for the writing index and page metadata.
---

Start with a paragraph, then use level-two headings for sections.
```

The post URL is `blog/first-post/`. The home page lists all posts, newest first. Edit `content/about.md` for the bio and `content/profile.yaml` for the profile details, links, and projects on `about/`. The starter information and avatar come from [pineapplehunter's public GitHub profile](https://github.com/pineapplehunter).

## Images and build steps

Put a JPG, PNG, or WebP under `assets/images/`, then reference it as a Markdown image:

```markdown
![Description of the photo](media/bench.jpg)
```

The build generates JPEG XL, WebP, and PNG variants up to 240, 480, and 960 pixels wide, without upscaling. A native `<picture>` lets the browser choose the first format it supports in that order and pick a responsive size. Nested folders work; use the same relative path after `media/`.

`./build.sh` runs `configure.py`, which uses `ninja.ninja_syntax` to emit `.build/build.ninja`. The script forwards all arguments to `configure.py`. For a project site, run `./build.sh --base-path /my-repo`; the default is `/`. To use Ninja options, run Ninja directly after configuring.

Each page follows this chain:

```text
Markdown + Jinja → intermediate HTML → minified Tailwind CSS → dist HTML with inline CSS
```

Tailwind scans only the intermediate HTML for that page. Edit its theme in `styles/site.css`. To add another preprocessor, follow `tools/images.py`: register a Ninja rule and its input/output edges in `configure.py`, then include the generated files in the `site` target. If rendering consumes a generated file, add it to the render edge's inputs.

## Publish to GitHub Pages

In the repository's **Settings → Pages**, set **Source** to **GitHub Actions**. Push to `main` (or run the workflow manually). The workflow builds and uploads only `dist/`. Regular pages use relative links so they work at the domain root or under a repository path. GitHub Pages serves `dist/404.html` for missing URLs; the workflow passes GitHub Pages’ base path to `./build.sh --base-path` so its navigation works even from a nested URL. To preview its design with the local server, open `/404.html` directly. Tailwind v4 targets modern browsers; the underlying pages use standard HTML and native links.
