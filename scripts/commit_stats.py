
import os
import re
import json
import urllib.parse
import urllib.request
from collections import Counter
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

USERNAME = "roongji5"
README = Path("README.md")
TOKEN = os.environ.get("GH_TOKEN", "")
KST = ZoneInfo("Asia/Seoul")

START = "<!--START_SECTION:commit-time-->"
END = "<!--END_SECTION:commit-time-->"

def fetch_commits():
    commits = []
    total = 0

    for page in range(1, 11):
        params = urllib.parse.urlencode({
            "q": f"author:{USERNAME}",
            "sort": "committer-date",
            "order": "desc",
            "per_page": 100,
            "page": page,
        })

        url = f"https://api.github.com/search/commits?{params}"

        headers = {
            "Accept": "application/vnd.github+json",
            "User-Agent": "github-profile-commit-stats",
        }

        if TOKEN:
            headers["Authorization"] = f"Bearer {TOKEN}"

        request = urllib.request.Request(url, headers=headers)

        with urllib.request.urlopen(request, timeout=30) as response:
            data = json.load(response)

        if page == 1:
            total = data.get("total_count", 0)

        items = data.get("items", [])
        if not items:
            break

        commits.extend(items)

        if len(items) < 100:
            break

    return commits, total


def get_period(hour):
    if 6 <= hour < 12:
        return "Morning"
    if 12 <= hour < 18:
        return "Daytime"
    if 18 <= hour < 24:
        return "Evening"
    return "Night"


def build_stats(commits, total):
    counts = Counter()

    for item in commits:
        date_string = item["commit"]["author"]["date"]
        dt = datetime.fromisoformat(
            date_string.replace("Z", "+00:00")
        ).astimezone(KST)

        counts[get_period(dt.hour)] += 1

    total_count = len(commits)

    periods = [
        ("Morning", "🌅"),
        ("Daytime", "☀️"),
        ("Evening", "🌆"),
        ("Night", "🌙"),
    ]

    lines = ["```text"]

    for name, emoji in periods:
        count = counts[name]
        percent = (
            count / total_count * 100
            if total_count else 0
        )
        filled = round(percent / 5)
        bar = "█" * filled + "░" * (20 - filled)

        lines.append(
            f"{emoji} {name:<8} {count:>4} commits  "
            f"{bar} {percent:5.1f}%"
        )

    lines.append("```")

    if total_count == 0:
        label = "No commits found"
    else:
        top_period = max(periods, key=lambda p: counts[p[0]])[0]
        labels = {
            "Morning": "Early Bird",
            "Daytime": "Daytime Coder",
            "Evening": "Evening Coder",
            "Night": "Night Owl",
        }
        label = labels[top_period]

    note = f"**{label}** · KST · {total_count} commits analyzed"

    if total > total_count:
        note += " · Recent commits sample (API limit: 1,000)"

    return note + "\n\n" + "\n".join(lines)


def update_readme(stats):
    content = README.read_text(encoding="utf-8")

    pattern = re.compile(
        re.escape(START) + r".*?" + re.escape(END),
        re.DOTALL,
    )

    if not pattern.search(content):
        raise RuntimeError(
            "README.md에 commit-time 마커가 없습니다."
        )

    replacement = f"{START}\n{stats}\n{END}"

    updated = pattern.sub(
        lambda _: replacement,
        content,
        count=1,
    )

    if updated != content:
        README.write_text(updated, encoding="utf-8")
        print("README updated")
    else:
        print("No changes")


if __name__ == "__main__":
    commits, total = fetch_commits()
    print(f"Found {len(commits)} commits (search total: {total})")
    stats = build_stats(commits, total)
    update_readme(stats)
