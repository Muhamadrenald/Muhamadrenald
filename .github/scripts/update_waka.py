"""Update the README section between <!--START_SECTION:waka--> and
<!--END_SECTION:waka--> with WakaTime stats from the all time.

Uses a WakaTime personal OAuth access token (Bearer auth), because plain
API keys are now restricted to plugins. No third-party dependencies.
"""
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request

TOKEN = os.environ["WAKATIME_TOKEN"]
URL = "https://wakatime.com/api/v1/users/current/stats/all_time"
README = os.environ.get("README_PATH", "README.md")
SECTION = "waka"
LANG_COUNT = 6
BAR_WIDTH = 25


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
            with urllib.request.urlopen(req, timeout=30) as resp:
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


def bar(percent):
    filled = round(BAR_WIDTH * percent / 100)
    return ">" * filled + "-" * (BAR_WIDTH - filled)


def build_block(data):
    langs = [l for l in data["languages"] if l["name"] != "Other"][:LANG_COUNT]
    lines = [
        f"{l['name']:<16}{l['text']:<16}{bar(l['percent'])}  {l['percent']:5.2f} %"
        for l in langs
    ]
    total = data.get("human_readable_total", "")
    title = f"**Weekly coding activity** (all time, total: {total})"
    return f"{title}\n\n```txt\n" + "\n".join(lines) + "\n```"


def main():
    data = fetch()
    content = build_block(data)

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

    new_text = pattern.sub(lambda m: f"{m.group(1)}\n{content}\n{m.group(3)}", text)

    if new_text == text:
        print("README already up to date.")
        return

    with open(README, "w", encoding="utf-8") as f:
        f.write(new_text)
    print("README updated.")


if __name__ == "__main__":
    main()
