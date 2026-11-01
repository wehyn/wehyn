#!/usr/bin/env python3
"""Generate assets/prs-per-month.svg from the user's GitHub pull requests.

Requires the `gh` CLI, authenticated (GH_TOKEN or `gh auth login`).
"""
import json
import subprocess
import sys
from collections import Counter
from datetime import date
from pathlib import Path

LOGIN = "wehyn"
OUT = Path(__file__).resolve().parent.parent / "assets" / "prs-per-month.svg"

QUERY = """
query($login: String!, $cursor: String) {
  user(login: $login) {
    pullRequests(first: 100, after: $cursor) {
      pageInfo { hasNextPage endCursor }
      nodes { createdAt merged }
    }
  }
}
"""


def fetch_pull_requests():
    cursor = None
    nodes = []
    while True:
        cmd = ["gh", "api", "graphql", "-f", f"query={QUERY}", "-f", f"login={LOGIN}"]
        if cursor:
            cmd += ["-f", f"cursor={cursor}"]
        data = json.loads(subprocess.run(cmd, check=True, capture_output=True, text=True).stdout)
        page = data["data"]["user"]["pullRequests"]
        nodes += page["nodes"]
        if not page["pageInfo"]["hasNextPage"]:
            return nodes
        cursor = page["pageInfo"]["endCursor"]


def month_range(first, last):
    y, m = first
    while (y, m) <= last:
        yield (y, m)
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)


def nice_max(peak):
    step = 50 if peak <= 250 else 100 if peak <= 600 else 250
    return max(step * 2, -(-peak // step) * step)


def render(counts, months, total, merged):
    W, H, L, R, T, B = 640, 220, 8, 40, 64, 26
    pw, ph = W - L - R, H - T - B
    top = nice_max(max(counts))
    bw = pw / len(months)

    def y(v):
        return T + ph - v / top * ph

    ticks = [0, top // 2, top]
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" '
        f'role="img" aria-label="Pull requests per month: {total} total, {merged} merged">',
        "<style>text{fill:#8b949e;font:11px -apple-system,Segoe UI,Helvetica,Arial,sans-serif}"
        ".g{stroke:#8b949e;stroke-opacity:.3}"
        ".n{fill:#8b949e;font-size:14px}.t{fill:#2f81f7;font-size:30px;font-weight:600}</style>",
        f'<text class="t" x="{L}" y="34">{total}</text>',
        f'<text class="n" x="{L + 14 + 18 * len(str(total))}" y="34">total pull requests · {merged} merged</text>',
        f'<text x="{L}" y="52">Pull requests per month · {months[0][0]}–{months[-1][0]}</text>',
    ]
    for v in ticks:
        dash = ' stroke-dasharray="3 3"' if v else ""
        parts.append(f'<line class="g" x1="{L}" x2="{W - R}" y1="{y(v):.1f}" y2="{y(v):.1f}"{dash}/>')
        parts.append(f'<text x="{W - R + 6}" y="{y(v) + 4:.1f}">{v}</text>')
    for i, (yr, mo) in enumerate(months):
        if mo == 1 or i == 0:
            parts.append(f'<text x="{L + i * bw:.1f}" y="{H - 8}">{yr}</text>')
    pts = [(L + i * bw + bw / 2, y(v)) for i, v in enumerate(counts)]
    line = " ".join(f"{'ML'[i > 0]}{x:.1f} {py:.1f}" for i, (x, py) in enumerate(pts))
    base = y(0)
    parts.append(f'<path d="{line} L{pts[-1][0]:.1f} {base:.1f} L{pts[0][0]:.1f} {base:.1f}Z" fill="#2f81f7" fill-opacity=".25"/>')
    parts.append(f'<path d="{line}" fill="none" stroke="#2f81f7" stroke-width="2" stroke-linejoin="round"/>')
    parts.append("</svg>")
    return "\n".join(parts) + "\n"


def main():
    prs = fetch_pull_requests()
    if not prs:
        sys.exit("no pull requests returned")
    by_month = Counter((int(p["createdAt"][:4]), int(p["createdAt"][5:7])) for p in prs)
    today = date.today()
    months = list(month_range(min(by_month), (today.year, today.month)))
    counts = [by_month.get(m, 0) for m in months]
    merged = sum(p["merged"] for p in prs)
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(render(counts, months, len(prs), merged))
    print(f"{len(prs)} PRs, {merged} merged, {len(months)} months -> {OUT}")


if __name__ == "__main__":
    main()
