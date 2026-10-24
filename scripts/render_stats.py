#!/usr/bin/env python3
"""生成个人主页的活跃度统计卡片（今日 / 累计）。"""

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

USER = os.environ.get("STATS_USER", "xunyyds").strip()
TOKEN = os.environ.get("STATS_TOKEN", "").strip()
TZ = timezone(timedelta(hours=8))
TZ_NAME = "UTC+8"

THEMES = {
    "light": {
        "bg": "#ffffff",
        "border": "#d1d9e0",
        "divider": "#d8dee4",
        "text": "#1f2328",
        "muted": "#59636e",
        "faint": "#8c959f",
        "accent": "#2f81f7",
        "commit": "#1a7f37",
        "pr": "#8250df",
    },
    "dark": {
        "bg": "#0d1117",
        "border": "#30363d",
        "divider": "#30363d",
        "text": "#e6edf3",
        "muted": "#9198a1",
        "faint": "#6e7681",
        "accent": "#4493f8",
        "commit": "#3fb950",
        "pr": "#ab7df8",
    },
}

FONT = (
    "-apple-system,BlinkMacSystemFont,'Segoe UI','Noto Sans SC',"
    "'PingFang SC','Hiragino Sans GB','Microsoft YaHei',sans-serif"
)


def api(path, params, token):
    url = "https://api.github.com" + path + "?" + urllib.parse.urlencode(params, safe=":")
    req = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": USER + "-activity-stats",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    if token:
        req.add_header("Authorization", "Bearer " + token)
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp)


def count(path, query, token, attempts=4):
    last = None
    for attempt in range(attempts):
        try:
            return int(api(path, {"q": query, "per_page": 1}, token)["total_count"])
        except urllib.error.HTTPError as exc:
            last = exc
            if exc.code in (401, 422):
                break
            time.sleep(3 * (attempt + 1))
        except (urllib.error.URLError, TimeoutError) as exc:
            last = exc
            time.sleep(3 * (attempt + 1))
    raise RuntimeError("GitHub API 查询失败：" + str(last))


def collect():
    now = datetime.now(TZ)
    since = now.replace(hour=0, minute=0, second=0, microsecond=0)
    since_text = since.strftime("%Y-%m-%dT%H:%M:%S+08:00")

    queries = {
        "commits_today": ("/search/commits", "author:" + USER + " committer-date:>=" + since_text),
        "commits_total": ("/search/commits", "author:" + USER),
        "prs_today": ("/search/issues", "author:" + USER + " type:pr created:>=" + since_text),
        "prs_total": ("/search/issues", "author:" + USER + " type:pr"),
    }

    def run(token, label):
        stats = {}
        for key, (path, query) in queries.items():
            stats[key] = count(path, query, token)
        stats["updated"] = now.strftime("%Y-%m-%d %H:%M")
        print("[" + label + "] " + json.dumps(stats, ensure_ascii=False), file=sys.stderr)
        return stats

    if TOKEN:
        try:
            return run(TOKEN, "token")
        except RuntimeError as exc:
            print("令牌查询失败，回退匿名：" + str(exc), file=sys.stderr)
    return run("", "anonymous")

def esc(value):
    return (
        str(value)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def render(stats, theme_name):
    theme = THEMES[theme_name]
    width, height = 880, 190
    today_x, total_x = 566, 756

    def text_width(text, size):
        total = 0.0
        for ch in text:
            total += size if ord(ch) > 0x2E80 else size * 0.6
        return total

    def row(center_y, dot, label, latin, today, total):
        latin_x = 48 + round(text_width(label, 14.5)) + 9
        parts = [
            '<circle cx="34" cy="%d" r="4" fill="%s"/>' % (center_y, dot),
            '<text x="48" y="%d" class="label">%s</text>' % (center_y + 5, esc(label)),
            '<text x="%d" y="%d" class="latin">%s</text>' % (latin_x, center_y + 5, esc(latin)),
        ]
        value_fill = theme["text"] if today else theme["faint"]
        if today:
            pill_w = 30 + 15 * len(str(today))
            parts.append(
                '<rect x="%.1f" y="%d" width="%d" height="30" rx="9" fill="%s" fill-opacity="0.12"/>'
                % (today_x - pill_w / 2.0, center_y - 15, pill_w, dot)
            )
        parts.append(
            '<text x="%d" y="%d" class="value" fill="%s">%s</text>'
            % (today_x, center_y + 8, value_fill, esc(today))
        )
        parts.append(
            '<text x="%d" y="%d" class="value" fill="%s">%s</text>'
            % (total_x, center_y + 8, theme["text"], esc(total))
        )
        return "".join(parts)

    lines = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" viewBox="0 0 %d %d"'
        ' role="img" aria-label="活跃度统计">' % (width, height, width, height),
        "<defs><style>",
        "text{font-family:" + FONT + ";white-space:pre}",
        ".title{font-size:17px;font-weight:650;fill:%s;letter-spacing:.3px}" % theme["text"],
        ".updated{font-size:11.5px;fill:%s}" % theme["muted"],
        ".head{font-size:10.5px;fill:%s;letter-spacing:1.4px}" % theme["muted"],
        ".label{font-size:14.5px;font-weight:600;fill:%s}" % theme["text"],
        ".latin{font-size:9.5px;fill:%s;letter-spacing:1.1px}" % theme["faint"],
        ".value{font-size:23px;font-weight:700;text-anchor:middle;"
        "font-variant-numeric:tabular-nums}",
        "</style></defs>",
        '<rect x="0.5" y="0.5" width="%d" height="%d" rx="16" fill="%s" stroke="%s"/>'
        % (width - 1, height - 1, theme["bg"], theme["border"]),
        '<rect x="26" y="26" width="4" height="21" rx="2" fill="%s"/>' % theme["accent"],
        '<text x="40" y="43" class="title">活跃度统计</text>',
        '<text x="%d" y="42" class="updated" text-anchor="end">更新于 %s · %s</text>'
        % (width - 26, esc(stats["updated"]), TZ_NAME),
        '<line x1="26" y1="60" x2="%d" y2="60" stroke="%s"/>' % (width - 26, theme["divider"]),
        '<text x="48" y="86" class="head">指标</text>',
        '<text x="%d" y="86" class="head" text-anchor="middle">今日</text>' % today_x,
        '<text x="%d" y="86" class="head" text-anchor="middle">累计</text>' % total_x,
        '<line x1="26" y1="98" x2="%d" y2="98" stroke="%s" stroke-opacity="0.6"/>'
        % (width - 26, theme["divider"]),
        row(126, theme["commit"], "提交", "COMMITS", stats["commits_today"], stats["commits_total"]),
        row(162, theme["pr"], "PR", "PULL REQUESTS", stats["prs_today"], stats["prs_total"]),
        "</svg>",
    ]
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="dist")
    parser.add_argument("--stats-json", help="跳过联网，用已有统计渲染（本地预览用）")
    args = parser.parse_args()

    if args.stats_json:
        with open(args.stats_json, encoding="utf-8") as fh:
            stats = json.load(fh)
    else:
        stats = collect()

    os.makedirs(args.out, exist_ok=True)
    for name, suffix in (("light", ""), ("dark", "-dark")):
        path = os.path.join(args.out, "stats" + suffix + ".svg")
        with open(path, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(render(stats, name))
        print("wrote " + path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
