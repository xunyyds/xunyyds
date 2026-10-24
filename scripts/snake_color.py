#!/usr/bin/env python3
"""给贪吃蛇 SVG 换上一套随机主色（每次访问颜色不同）。"""

import re
import secrets
import sys

PALETTE = [
    "ff0000",
    "ff9f1a",
    "ffe14d",
    "3ddc84",
    "38bdf8",
    "a78bfa",
    "ff6bd6",
]


def recolor(path):
    with open(path, encoding="utf-8") as fh:
        svg = fh.read()
    if not re.search(r"--cs:[^;}]", svg):
        raise SystemExit("SVG 里没有颜色变量 --cs：" + path)
    svg, hits = re.subn(r"--cs:[^;}]+", "--cs:#" + secrets.choice(PALETTE), svg, count=1)
    if hits != 1:
        raise SystemExit("换色失败：" + path)
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(svg)


def main():
    for path in sys.argv[1:]:
        recolor(path)
        print("recolored " + path)


if __name__ == "__main__":
    main()
