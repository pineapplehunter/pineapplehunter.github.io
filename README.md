# pineapplehunter's website

A static personal site for Shogo Takata. The build uses Python, Ninja, the Tailwind v4 standalone CLI, and Pillow; the published site needs no JavaScript.

## Build and preview

```sh
nix develop
./build.sh
python3 -m http.server --directory dist 8000
```

Open <http://localhost:8000>. `nix develop -c ./build.sh` also works without entering the shell. `./build.sh -n` shows what Ninja would build. `dist/` is generated-only; the generator removes files there that no longer have a target.

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

The URL is `blog/first-post/`. Newest posts appear first. Edit `content/about.md` for the bio and `content/profile.yaml` for the home page, profile links, and projects. The starter information and avatar come from [pineapplehunter's public GitHub profile](https://github.com/pineapplehunter).

## Images and build steps

Put a JPG, PNG, or WebP under `assets/images/`, then reference it as a Markdown image:

```markdown
![Description of the photo](media/bench.jpg)
```

The build generates WebP variants up to 240, 480, and 960 pixels wide without upscaling. Rendered images have intrinsic dimensions and responsive `srcset` attributes. Nested folders work; use the same relative path after `media/`.

`./build.sh` runs `configure.py`, which uses `ninja.ninja_syntax` to emit `.build/build.ninja`. Each page follows this chain:

```text
Markdown + Jinja → intermediate HTML → minified Tailwind CSS → dist HTML with inline CSS
```

Tailwind scans only the intermediate HTML for that page. Edit its theme in `styles/site.css`. To add another preprocessor, follow `tools/images.py`: register a Ninja rule and its input/output edges in `configure.py`, then include the generated files in the `site` target. If rendering consumes a generated file, add it to the render edge's inputs.

## Publish to GitHub Pages

In the repository's **Settings → Pages**, set **Source** to **GitHub Actions**. Push to `main` (or run the workflow manually). The workflow builds and uploads only `dist/`. Internal links are relative so the same output works at either the root of `pineapplehunter.github.io` or under a project repository path. Tailwind v4 targets modern browsers; the underlying pages use standard HTML and native links.
