"""Measure rendered HTML and its local assets, then fill in the size markers."""

import gzip
import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

MARKERS = (b"@@PAGE-HTML@@", b"@@PAGE-HTML-GZIP@@",
           b"@@PAGE-TOTAL@@", b"@@PAGE-TOTAL-GZIP@@")


class AssetLinks(HTMLParser):
    def __init__(self):
        super().__init__()
        self.urls = set()

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag in {"img", "source", "script"} and attrs.get("src"):
            self.urls.add(attrs["src"])
        if tag in {"img", "source"} and attrs.get("srcset"):
            for entry in attrs["srcset"].split(","):
                if entry.strip():
                    self.urls.add(entry.split()[0])
        if tag == "link" and attrs.get("href"):
            relations = set(attrs.get("rel", "").split())
            if relations & {"stylesheet", "icon", "preload", "modulepreload"}:
                self.urls.add(attrs["href"])


def asset_paths(html, output, site_root):
    links = AssetLinks()
    links.feed(html.decode("utf-8"))
    links.close()
    dist = Path("dist").resolve()
    assets = set()
    for url in links.urls:
        parts = urlsplit(url)
        if parts.scheme or parts.netloc or not parts.path:
            continue
        path = unquote(parts.path)
        if path.startswith("/"):
            if not path.startswith(site_root):
                continue
            asset = dist / path.removeprefix(site_root)
        else:
            asset = output.parent / path
        asset = asset.resolve()
        if asset.is_relative_to(dist):
            assets.add(asset)
    return assets


def gzip_size(data):
    return len(gzip.compress(data, compresslevel=9, mtime=0))


def main(rendered, output, site_root):
    html = rendered.read_bytes()
    html_size, html_gzip = len(html), gzip_size(html)
    total_size, total_gzip = html_size, html_gzip
    for path in sorted(asset_paths(html, output, site_root)):
        data = path.read_bytes()
        total_size += len(data)
        total_gzip += gzip_size(data)

    for marker, size in zip(MARKERS, (html_size, html_gzip, total_size, total_gzip), strict=True):
        html = html.replace(marker, f"{size / 1024:.1f} KiB".encode("ascii"))
    output.write_bytes(html)


if __name__ == "__main__":
    _, rendered, output, site_root = sys.argv
    main(Path(rendered), Path(output), site_root)
