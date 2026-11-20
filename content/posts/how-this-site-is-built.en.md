---
title: How this site is built
date: 2026-11-20
summary: From a Markdown file to a static page, with Ninja keeping track of the steps.
---

This site starts as a directory of Markdown files. Each post has a title, date, and summary in YAML front matter; its filename, without the language suffix, supplies the URL slug.

## What Ninja runs

`./build.sh` runs `configure.py` to discover the content and write a Ninja build graph. Ninja renders the pages, compiles Tailwind against each page's HTML, and embeds the resulting CSS. The browser doesn't need a separate stylesheet or a JavaScript bundle.

Image processing uses the same build graph. Local images can be referenced from Markdown, and the build generates responsive JPEG XL, WebP, and PNG variants so the browser can pick a supported format and a size that fits.

## Preview locally

```sh
nix develop
./build.sh
python3 -m http.server --directory dist
```

The generated `dist/` directory is also what GitHub Pages serves.
