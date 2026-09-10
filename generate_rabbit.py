#!/usr/bin/env python3
"""Regenerates rabbit-contributions.svg from live public GitHub contribution data.
No external dependencies (stdlib only) so it runs anywhere without a pip install step."""
import os
import re
import json
import datetime
import urllib.request

USERNAME = os.environ.get("GH_USERNAME") or os.environ.get("GITHUB_REPOSITORY_OWNER") or "Mottii"
OUT_PATH = os.environ.get("OUT_PATH", "rabbit-contributions.svg")

CELL = 11
GAP = 3
STEP = CELL + GAP
LEFT_PAD = 14
TOP_PAD = 24
BOTTOM_PAD = 10
RIGHT_PAD = 14
SECONDS_PER_STEP = 0.11
BOUNCE_H = 5.5
LOOP_REPEATS = 10

LEVEL_COLOR = {0: "#0d1f16", 1: "#0f4d28", 2: "#158a3d", 3: "#22c955", 4: "#39ff6e"}
FLASH_BRIGHT = "#cfffd8"
FLASH_DIM = "#1c3f2a"


def fetch_contributions(username):
    url = f"https://github.com/users/{username}/contributions"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=20) as resp:
        html = resp.read().decode("utf-8")

    tbody_match = re.search(r"<tbody>(.*?)</tbody>", html, re.S)
    if not tbody_match:
        raise RuntimeError("Could not find contribution calendar in response")
    tbody = tbody_match.group(1)
    rows = re.findall(r"<tr[^>]*>(.*?)</tr>", tbody, re.S)

    date_level = {}
    for row in rows:
        pairs = re.findall(r'data-date="([^"]+)"[^>]*data-level="(\d+)"', row)
        for d, lvl in pairs:
            date_level[datetime.date.fromisoformat(d)] = int(lvl)

    if not date_level:
        raise RuntimeError("No contribution cells parsed")
    return date_level


def build_grid(date_level):
    mind, maxd = min(date_level), max(date_level)

    def row_of(d):
        return (d.weekday() + 1) % 7  # Sunday -> 0 ... Saturday -> 6

    start_sunday = mind - datetime.timedelta(days=row_of(mind))
    num_days = (maxd - start_sunday).days + 1
    num_weeks = (num_days + 6) // 7

    grid = [[None] * num_weeks for _ in range(7)]
    for d, lvl in date_level.items():
        offset = (d - start_sunday).days
        col = offset // 7
        row = offset % 7
        grid[row][col] = (d.isoformat(), lvl)
    return grid, num_weeks


def cell_xy(row, col):
    x = LEFT_PAD + col * STEP + CELL / 2
    y = TOP_PAD + row * STEP + CELL / 2
    return x, y


def build_svg(grid, num_weeks, username):
    rows = 7
    width = LEFT_PAD + num_weeks * STEP - GAP + RIGHT_PAD
    height = TOP_PAD + rows * STEP - GAP + BOTTOM_PAD

    path_cells = []
    for col in range(num_weeks):
        row_order = range(rows) if col % 2 == 0 else range(rows - 1, -1, -1)
        for row in row_order:
            cell = grid[row][col]
            if cell is None:
                continue
            d, lvl = cell
            path_cells.append((row, col, d, lvl))

    n = len(path_cells)
    total_dur = round(SECONDS_PER_STEP * (n - 1), 3)

    def begin_list(t):
        return ";".join(f"{round(t + i * total_dur, 3)}s" for i in range(LOOP_REPEATS))

    svg = [
        f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" '
        f'viewBox="0 0 {width} {height}" width="100%" height="{height}">',
        f'<rect x="0" y="0" width="{width}" height="{height}" fill="#0D0208"/>',
        f'<text x="{LEFT_PAD}" y="16" font-family="monospace" font-size="12" '
        f'fill="#39ff6e" opacity="0.85">{username}@github: hopping through a year of commits</text>',
    ]

    cell_ids = {}
    for row, col, d, lvl in path_cells:
        x = LEFT_PAD + col * STEP
        y = TOP_PAD + row * STEP
        cid = f"c{row}_{col}"
        cell_ids[(row, col)] = cid
        svg.append(
            f'<rect id="{cid}" x="{x}" y="{y}" width="{CELL}" height="{CELL}" rx="2" '
            f'fill="{LEVEL_COLOR[lvl]}"><title>{d}: level {lvl}</title></rect>'
        )

    for idx, (row, col, d, lvl) in enumerate(path_cells):
        t = idx * SECONDS_PER_STEP
        cid = cell_ids[(row, col)]
        base = LEVEL_COLOR[lvl]
        flash = FLASH_DIM if lvl == 0 else FLASH_BRIGHT
        dur = 0.3 if lvl == 0 else 0.55
        bl = begin_list(t)
        svg.append(
            f'<animate xlink:href="#{cid}" attributeName="fill" '
            f'values="{base};{flash};{base}" begin="{bl}" dur="{dur}s" repeatCount="1"/>'
        )
        if lvl > 0:
            x, y = cell_xy(row, col)
            svg.append(
                f'<g transform="translate({x},{y})" opacity="0">'
                f'<path d="M0,-6 L1.4,-1.4 L6,0 L1.4,1.4 L0,6 L-1.4,1.4 L-6,0 L-1.4,-1.4 Z" fill="#eaffef"/>'
                f'<animate attributeName="opacity" values="0;1;0" begin="{bl}" dur="0.9s" repeatCount="1"/>'
                f'<animateTransform attributeName="transform" type="scale" '
                f'values="0.2;1.3;0.2" additive="sum" begin="{bl}" dur="0.9s" repeatCount="1"/>'
                f'</g>'
            )

    pts = [cell_xy(r, c) for (r, c, d, l) in path_cells]
    path_d = "M " + " L ".join(f"{x:.1f},{y:.1f}" for x, y in pts)

    svg.append("<g>")
    svg.append(f'''
  <g id="rabbit-bounce">
    <g fill="none">
      <ellipse cx="-3" cy="-6" rx="1.5" ry="3.6" fill="#f7f7f7" stroke="#111" stroke-width="0.5" transform="rotate(-18 -3 -6)"/>
      <ellipse cx="-3" cy="-6" rx="0.7" ry="2.2" fill="#ff9db3" transform="rotate(-18 -3 -6)"/>
      <ellipse cx="3" cy="-6" rx="1.5" ry="3.6" fill="#f7f7f7" stroke="#111" stroke-width="0.5" transform="rotate(18 3 -6)"/>
      <ellipse cx="3" cy="-6" rx="0.7" ry="2.2" fill="#ff9db3" transform="rotate(18 3 -6)"/>
      <ellipse cx="0" cy="0" rx="5.2" ry="4.2" fill="#f7f7f7" stroke="#111" stroke-width="0.6"/>
      <circle cx="-1.6" cy="-0.8" r="0.6" fill="#111"/>
      <circle cx="1.9" cy="2.6" r="1.1" fill="#ffffff" stroke="#111" stroke-width="0.3"/>
    </g>
    <animateTransform attributeName="transform" type="translate"
      values="0,0; 0,-{BOUNCE_H}; 0,0" keyTimes="0;0.5;1"
      dur="{SECONDS_PER_STEP:.3f}s" repeatCount="indefinite"/>
  </g>
''')
    svg.append(
        f'<animateMotion id="hop" xlink:href="#rabbit-bounce" path="{path_d}" '
        f'rotate="auto" dur="{total_dur}s" repeatCount="indefinite"/>'
    )
    svg.append("</g>")
    svg.append("</svg>")
    return "".join(svg)


def main():
    date_level = fetch_contributions(USERNAME)
    grid, num_weeks = build_grid(date_level)
    svg = build_svg(grid, num_weeks, USERNAME)
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        f.write(svg)
    total = sum(v for v in date_level.values())
    print(f"Wrote {OUT_PATH} ({len(svg)} bytes) for {USERNAME}, {len(date_level)} days scanned")


if __name__ == "__main__":
    main()
