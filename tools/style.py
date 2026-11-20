"""Compile just one page's Tailwind classes, then embed the result."""

import subprocess
import sys
from pathlib import Path
from tempfile import NamedTemporaryFile

_, mode, source, *args = sys.argv
html = Path(source)
if mode == "compile":
    output, tailwind = args
    stylesheet = Path("styles/site.css").read_text(encoding="utf-8")
    # Tailwind resolves @source paths relative to its input file.
    with NamedTemporaryFile(mode="w", suffix=".css", dir=html.parent, encoding="utf-8") as entry:
        entry.write(f'{stylesheet}\n@source "./{html.name}";\n')
        entry.flush()
        subprocess.run(
            [tailwind, "--input", entry.name, "--output", output, "--minify"],
            check=True,
        )
else:
    stylesheet, output = args
    css = Path(stylesheet).read_text(encoding="utf-8")
    page = html.read_text(encoding="utf-8")
    Path(output).write_text(page.replace("<!-- inline-css -->", f"<style>{css}</style>", 1),
                            encoding="utf-8")
