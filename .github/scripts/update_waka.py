"""Generate a WakaTime stats card (SVG) and embed it in the README section
between <!--START_SECTION:waka--> and <!--END_SECTION:waka-->.

Uses a WakaTime personal OAuth access token (Bearer auth), because plain
API keys are now restricted to plugins. No third-party dependencies.
"""
import hashlib
import html
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone

TOKEN = os.environ["WAKATIME_TOKEN"]
RANGE = os.environ.get("WAKATIME_RANGE", "all_time")
URL = f"https://wakatime.com/api/v1/users/current/stats/{RANGE}"
README = os.environ.get("README_PATH", "README.md")
SVG_PATH = os.environ.get("SVG_PATH", "assets/waka-stats.svg")
SECTION = "waka"
LANG_COUNT = 6

RANGE_LABELS = {
    "all_time": "All time",
    "last_7_days": "Last 7 days",
    "last_30_days": "Last 30 days",
    "last_6_months": "Last 6 months",
    "last_year": "Last year",
}

LANG_COLORS = {
    "PHP": "#8892BF",
    "Blade Template": "#F7523F",
    "TypeScript": "#3178C6",
    "JavaScript": "#F1E05A",
    "Python": "#4B8BBE",
    "Markdown": "#519ABA",
    "JSON": "#CBCB41",
    "HTML": "#E34C26",
    "CSS": "#A371F7",
    "Bash": "#89E051",
    "PowerShell": "#5391FE",
    "SQL": "#E38C00",
    "YAML": "#E5534B",
    "Dart": "#00B4AB",
    "Vue.js": "#41B883",
    "Text": "#9AA0A6",
    "Git Config": "#F14E32",
}
FALLBACK_COLORS = ["#A371F7", "#3FB950", "#58A6FF", "#D29922", "#F778BA", "#79C0FF"]

STYLE = """
  text { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif; }
  .bg { fill: #0d1117; stroke: #30363d; }
  .title { fill: #e6edf3; font-size: 20px; font-weight: 700; }
  .label { fill: #e6edf3; font-size: 14px; font-weight: 600; }
  .muted { fill: #8b949e; font-size: 13px; }
  .tiny { fill: #6e7681; font-size: 11px; }
  .accent { fill: #a371f7; font-size: 20px; font-weight: 700; }
  .track { fill: #21262d; }
  .rule { stroke: #21262d; }
  @media (prefers-color-scheme: light) {
    .bg { fill: #ffffff; stroke: #d0d7de; }
    .title, .label { fill: #1f2328; }
    .muted { fill: #656d76; }
    .tiny { fill: #8c959f; }
    .accent { fill: #8250df; }
    .track { fill: #eaeef2; }
    .rule { stroke: #eaeef2; }
  }
"""


def fetch():
    req = urllib.request.Request(
        URL,
        headers={
            "Authorization": f"Bearer {TOKEN}",
            "User-Agent": "waka-readme-oauth/1.0",
            "Accept": "application/json",
        },
    )
    for attempt in range(1, 6):
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                if resp.status == 202:  # stats still being calculated
                    print(f"Attempt {attempt}: stats not ready (202), retrying...")
                    time.sleep(20)
                    continue
                return json.load(resp)["data"]
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", "replace")[:300]
            sys.exit(f"WakaTime API error {e.code}: {body}")
        except urllib.error.URLError as e:
            print(f"Attempt {attempt}: network error: {e}")
            time.sleep(10)
    sys.exit("Unable to fetch WakaTime stats after several attempts.")


def render_svg(data, today=None):
    today = today or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    langs = [l for l in data["languages"] if l["name"] != "Other"][:LANG_COUNT]
    top = max((l["percent"] for l in langs), default=1) or 1

    w, pad, header_h, row_h = 720, 32, 100, 40
    h = header_h + row_h * len(langs) + 48
    track_x, track_w = 200, 300

    total = html.escape(data.get("human_readable_total", ""))
    avg = data.get("human_readable_daily_average")
    range_label = RANGE_LABELS.get(RANGE, RANGE)

    defs, rows = [], []
    for i, l in enumerate(langs):
        color = LANG_COLORS.get(l["name"], FALLBACK_COLORS[i % len(FALLBACK_COLORS)])
        y = header_h + i * row_h + 20
        fill_w = max(12, round(track_w * l["percent"] / top))
        defs.append(
            f'<linearGradient id="g{i}" x1="0" y1="0" x2="1" y2="0">'
            f'<stop offset="0" stop-color="{color}" stop-opacity="0.55"/>'
            f'<stop offset="1" stop-color="{color}"/></linearGradient>'
        )
        rows.append(
            f'<circle cx="{pad + 4}" cy="{y - 5}" r="4" fill="{color}"/>'
            f'<text x="{pad + 16}" y="{y}" class="label">{html.escape(l["name"])}</text>'
            f'<rect x="{track_x}" y="{y - 11}" width="{track_w}" height="12" rx="6" class="track"/>'
            f'<rect x="{track_x}" y="{y - 11}" width="{fill_w}" height="12" rx="6" fill="url(#g{i})"/>'
            f'<text x="{track_x + track_w + 16}" y="{y}" class="muted">{html.escape(l["text"])}</text>'
            f'<text x="{w - pad}" y="{y}" class="muted" text-anchor="end">{l["percent"]:.1f}%</text>'
        )

    avg_el = (
        f'<text x="{w - pad}" y="68" class="muted" text-anchor="end">'
        f"avg {html.escape(avg)} / day</text>"
        if avg
        else ""
    )

    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" '
        f'role="img" aria-label="WakaTime coding activity">'
        f"<style>{STYLE}</style><defs>{''.join(defs)}</defs>"
        f'<rect x="0.5" y="0.5" width="{w - 1}" height="{h - 1}" rx="16" class="bg"/>'
        f'<text x="{pad}" y="46" class="title">Coding Activity</text>'
        f'<text x="{pad}" y="68" class="muted">{html.escape(range_label)} · top {len(langs)} languages</text>'
        f'<text x="{w - pad}" y="46" class="accent" text-anchor="end">{total}</text>'
        f"{avg_el}"
        f'<line x1="{pad}" y1="84" x2="{w - pad}" y2="84" class="rule" stroke-width="1"/>'
        f"{''.join(rows)}"
        f'<text x="{pad}" y="{h - 18}" class="tiny">Updated {today} UTC · powered by WakaTime</text>'
        f"</svg>\n"
    )


def update_readme(svg):
    version = hashlib.md5(svg.encode("utf-8")).hexdigest()[:8]
    block = (
        '<div align="center">\n'
        f'  <img src="{SVG_PATH}?v={version}" alt="WakaTime coding activity" width="720" />\n'
        "</div>"
    )

    with open(README, encoding="utf-8") as f:
        text = f.read()

    pattern = re.compile(
        rf"(<!--START_SECTION:{SECTION}-->)(.*?)(<!--END_SECTION:{SECTION}-->)",
        re.DOTALL,
    )
    if not pattern.search(text):
        sys.exit(
            f"Markers <!--START_SECTION:{SECTION}--> / <!--END_SECTION:{SECTION}--> "
            f"not found in {README}."
        )

    new_text = pattern.sub(lambda m: f"{m.group(1)}\n{block}\n{m.group(3)}", text)
    if new_text != text:
        with open(README, "w", encoding="utf-8") as f:
            f.write(new_text)
        print("README updated.")
    else:
        print("README already up to date.")


def main():
    data = fetch()
    svg = render_svg(data)

    os.makedirs(os.path.dirname(SVG_PATH) or ".", exist_ok=True)
    with open(SVG_PATH, "w", encoding="utf-8") as f:
        f.write(svg)
    print(f"Wrote {SVG_PATH}.")

    update_readme(svg)


if __name__ == "__main__":
    main()
