---
title: What I did to keep this site lightweight
date: 2026-11-20
summary: How I turn Markdown into static pages with a custom build pipeline.
---

## Introduction

This article is about how I designed this site and the choices I made along the way.
I write the pages in **Markdown** and **build them into a static site with ninja** a common tool used to build C project.
I’ll explain why I took that approach as well as how it works.

This article comes to about **@@PAGE-TOTAL-GZIP@@** after gzip compression, including its images and CSS.
I’ll break down that number and explain how I measured it in “Actual page size.”

## How I approached the site’s design

There are plenty of ways to build a website, but pages have generally been getting bigger over time.
According to HTTP Archive[^archive], the **median desktop page weighed about 3 MB** as of November 2026.
In other words, this isn’t a handful of unusually heavy pages pulling up an average.
About half the pages in the survey were that size or larger.

Fast internet connections make it easy not to notice, but 3 MB is quite a lot. For a sense of scale, it’s roughly:

- 1,500 printed pages of text, assuming about 2 KB of text per page.[^paper]
- 4.6 times a hard-drive size once attributed to Bill Gates as being all anybody would need.[^bill]
- One MP3 song.[^mp3]

There are plenty of other comparisons,[^howbig][^filesize] but spending 3 MB on a page that’s mostly text seems wasteful.

The Markdown source for this article is only **@@PAGE-MARKDOWN@@**.
It feels wasteful to load hundreds of kilobytes of JavaScript libraries and hundreds more of stylesheets just to display it.
And it only gets worse with ads.

Most of this site is text with an occasional diagram, so I wanted each page to be as lightweight as possible.

[^archive]: <https://httparchive.org/reports/page-weight>
[^paper]: <https://www.techwalla.com/articles/how-many-printed-pages-is-one-megabyte>
[^mp3]: <https://filesize.org/calculators/audio-file-size/>
[^bill]: <https://www.computerworld.com/article/1563853/the-640k-quote-won-t-go-away-but-did-gates-really-say-it.html>
[^howbig]: <https://usefoyer.com/how-big-is/1-megabyte>
[^filesize]: <https://kordu.tools/blog/file-size-reference-how-big-is-a-megabyte/>

## How do you make a page lightweight?

**Just write it in HTML.**

That’s it.

## How do you make a page lightweight? (Take two)

Of course, if you want a modern-looking page, HTML alone only gets you so far.
Plain HTML has its advantages,[^vanilla][^14k] but you might still want to adjust the design or add a little interactivity.
This page, for example, uses JavaScript for the theme toggle.

The idea is to ship only the CSS and JavaScript the page needs.
Tailwind can scan the source files and generate only the CSS for the utilities the site uses.
And for something as small as a theme toggle, there’s no need for a library: I can write that code directly.

[^vanilla]: <https://www.vanillahtml.com/blog/html-is-enough>
[^14k]: <https://jaimebuilds.com/lab/the-14kb-rule/>

## Rendering Markdown

So how does the Markdown become HTML?
Static site generators such as Hugo[^hugo] and VuePress[^vuepress] are common choices, but if you need a custom build pipeline some times a general ourpose build tool does the job better.
With AI tools available, it’s straightforward to put together a script that turns Markdown into HTML using a template.
Even if you write it yourself, getting a Markdown parser up and running isn’t particularly hard, so a small custom renderer is quite manageable.

For this site, I had AI write the Python script that generates the HTML.
Ninja[^ninja] runs it alongside other build tasks, such as image conversion.

Ninja is often associated with C and C++ builds through tools like CMake and Meson, but it can run any build graph.
Here, that means it can run tasks like these together:

- Render Markdown to HTML.
- Parse multiple Markdown files to generate an index.
- Convert photos to several formats: JPEG XL, WebP, and PNG.

![build.sh calls configure.py to generate build.ninja. Ninja follows the graph to produce HTML from Markdown, Jinja, and YAML; shared CSS from site.css and the Jinja templates; and JPEG XL, WebP, and PNG images from the source images. The outputs go into dist/.](media/build-pipeline-en.svg "Static site build graph")

`configure.py` writes the file dependencies to `build.ninja`.
Ninja runs the conversions and uses those dependencies to decide what needs rebuilding when an input changes.
The HTML and shared CSS are generated separately, so Tailwind doesn’t need the finished HTML as an input.

For example, if I edit only `styles/site.css`, Ninja regenerates the CSS without rendering the Markdown again.
If the resulting stylesheet changes, it remeasures this article and updates just the size figures in the rendered HTML.

If all you want to do is render HTML, it’s reasonable to use an existing tool.
But this setup lets me do something a little more unusual: measure the page as part of its own build.
More on that below. The same setup also makes it easy to add live reload with watchexec.[^watchexec]

[^hugo]: <https://gohugo.io/>
[^vuepress]: <https://vuepress.vuejs.org/>
[^ninja]: <https://ninja-build.org/>
[^watchexec]: <https://watchexec.github.io/>

## The browser only needs HTML to show the text

After all that talk about CSS and JavaScript, this might sound contradictory.
The important point is that **the article text is already in the HTML**. You don’t need CSS or JavaScript to read it.

CSS and JavaScript are enhancements.
With JavaScript enabled, the browser can start displaying the article without waiting for the shared stylesheet.
If you’re reading this on a desktop, try selecting the slowest network preset in your browser’s developer tools and reloading.
You should be able to see the HTML appear before the full styling kicks in.

## Actual page size

- **Original Markdown:** @@PAGE-MARKDOWN@@
- **HTML only:** @@PAGE-HTML@@ (gzipped: @@PAGE-HTML-GZIP@@)
- **HTML and all referenced local assets:** @@PAGE-TOTAL@@ (gzipped: @@PAGE-TOTAL-GZIP@@)

![page_size.py measures the source Markdown, the rendered HTML, and its local assets. It combines those measurements with the original HTML by replacing the placeholders, then writes the publishable HTML to dist/.](media/page-size-build-en.svg "How the measured sizes get into the HTML")

If you were wondering why I went to the trouble of using Ninja, this is one example of what the build graph makes possible: the page can report its own size without any JavaScript running in the browser.

Ninja gives the measurement step three inputs: the source Markdown, the rendered HTML, and the generated assets.
The Markdown figure is the size of the original file on disk.
It isn’t served to readers, so it’s excluded from the page total.
For that total, the script counts the HTML and the local files it directly references: the shared CSS, the diagrams, and the favicon.
It counts each file only once.
The uncompressed total is the sum of their byte sizes.
For the gzip total, I compress each file separately at level 9 and add up the results.

After measuring, the script replaces the placeholders I wrote in Markdown with the calculated numbers in the generated HTML.
That substitution changes the HTML’s size slightly, so the figures are approximate.
They also don’t account for HTTP headers or caching, so they’re not the same as the actual transfer size in a browser but they should be close enough.

## Deployment

GitHub Pages is a good fit for hosting static HTML, so that’s what I use.
GitHub Actions builds the site, and the output is what you see here.

In the GitHub Actions run history, the deployment takes around 40 seconds, while rendering itself takes only a couple of seconds.

![GitHub Actions builds the site, and only the generated dist/ directory is published to GitHub Pages.](media/pages-deploy-en.svg "From a GitHub Actions build to GitHub Pages")

## Conclusion

With common approaches to web development, even a simple page can easily reach several megabytes.
I designed this page to avoid that. A small Python renderer handles the Markdown, and Ninja runs the build graph that ties rendering and asset processing together.

If you’re thinking about making a static site, you don’t necessarily need a framework. For something like this site, a small custom build can be enough to keep the pages lightweight.
