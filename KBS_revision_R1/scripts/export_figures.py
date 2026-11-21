"""Export every manuscript figure as a separate raster file at >= 300 dpi (KBS editor request).

TikZ figures are cut out of the manuscript into standalone documents that reuse the manuscript's
own preamble (colors, \\tikzset styles, \\rev macros), compiled with pdflatex, and rasterized with
pdftoppm. Figures that are already PDF files are rasterized directly. Captions stay in the
manuscript. Output: <out_dir>/Figure_<n>.png (numbered in order of appearance).

Run: python export_figures.py --tex <revised matpcr_snjnl.tex> --out_dir <dir> --pdflatex <path> --pdftoppm <path> [--clean]
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import tempfile

DPI = 600  # rendered at 600 dpi so line art stays sharp; >= 300 dpi as required


def preamble(tex: str, clean: bool) -> str:
    pre = tex[: tex.index(r"\begin{document}")]
    pre = re.sub(r"\\documentclass\[[^\]]*\]\{sn-jnl\}", r"\\documentclass[border=4pt,varwidth=372pt]{standalone}", pre)
    # drop sn-jnl-specific caption hacks
    pre = re.sub(r"\\makeatletter.*?\\makeatother", "", pre, flags=re.S)
    if clean:
        pre = r"\def\cleanbuild{1}" + "\n" + pre
    # packages that standalone does not need / that clash
    pre = pre.replace(r"\usepackage{float}", "").replace(r"\usepackage{algorithm}", "").replace(r"\usepackage{algpseudocode}", "")
    pre = pre.replace(r"\usepackage{ragged2e}", "")
    return pre


def figures(tex: str):
    """Yield (kind, payload) in order of appearance for each non-commented figure environment."""
    body = tex[tex.index(r"\begin{document}"):]
    body = "\n".join(l for l in body.split("\n") if not l.lstrip().startswith("%"))
    for m in re.finditer(r"\\begin\{figure\}(\[[^\]]*\])?(.*?)\\end\{figure\}", body, re.S):
        content = m.group(2)
        content = re.sub(r"\\caption\{.*", "", content, flags=re.S)  # caption is in the manuscript
        pdfs = re.findall(r"\\includegraphics(?:\[[^\]]*\])?\s*\{([^}]*)\}", content)
        if r"\begin{tikzpicture}" in content:
            yield "tikz", content
        elif pdfs:
            yield "pdf", pdfs


def run(cmd, cwd):
    r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"{cmd[0]} failed:\n{r.stdout[-3000:]}\n{r.stderr[-2000:]}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tex", required=True)
    ap.add_argument("--out_dir", required=True)
    ap.add_argument("--pdflatex", required=True)
    ap.add_argument("--pdftoppm", required=True)
    ap.add_argument("--clean", action="store_true", help="render \\rev text in black")
    args = ap.parse_args()
    tex = open(args.tex).read()
    texdir = os.path.dirname(os.path.abspath(args.tex))
    os.makedirs(args.out_dir, exist_ok=True)
    pre = preamble(tex, args.clean)
    n = 0
    for kind, payload in figures(tex):
        n += 1
        out_png = os.path.join(os.path.abspath(args.out_dir), f"Figure_{n}")
        with tempfile.TemporaryDirectory() as tmp:
            if kind == "tikz":
                pic = payload.replace(r"\centering", "")
                src = pre + "\\begin{document}\n" + pic.strip() + "\n\\end{document}\n"
                open(os.path.join(tmp, "fig.tex"), "w").write(src)
                run([args.pdflatex, "-interaction=nonstopmode", "-halt-on-error", "fig.tex"], tmp)
                pdf = os.path.join(tmp, "fig.pdf")
            else:
                # several PDF panels stacked in one figure: rasterize each, then stack vertically
                from PIL import Image
                panels = []
                for i, p in enumerate(payload):
                    rel = p if p.endswith(".pdf") else p + ".pdf"
                    hits = [os.path.join(dp, fn) for root in (texdir, os.path.dirname(texdir))
                            for dp, _, fns in os.walk(root) for fn in fns if fn == os.path.basename(rel)]
                    src = hits[0] if hits else os.path.join(texdir, rel)
                    stem = os.path.join(tmp, f"panel{i}")
                    run([args.pdftoppm, "-r", str(DPI), "-png", "-singlefile", src, stem], tmp)
                    panels.append(Image.open(stem + ".png").convert("RGB"))
                w = max(im.width for im in panels)
                canvas = Image.new("RGB", (w, sum(im.height for im in panels)), "white")
                y = 0
                for im in panels:
                    canvas.paste(im, ((w - im.width) // 2, y))
                    y += im.height
                canvas.save(out_png + ".png", dpi=(DPI, DPI))
                print(f"Figure_{n}.png  ({len(payload)} PDF panels)")
                continue
            run([args.pdftoppm, "-r", str(DPI), "-png", "-singlefile", pdf, out_png], tmp)
            from PIL import Image
            im = Image.open(out_png + ".png")
            im.save(out_png + ".png", dpi=(DPI, DPI))
            print(f"Figure_{n}.png  (TikZ, {im.width}x{im.height}px at {DPI} dpi)")
    print(f"{n} figures written to {args.out_dir}")


if __name__ == "__main__":
    main()
