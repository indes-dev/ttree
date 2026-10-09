"""Read-only CI job audit and dated pypdf advisory refresh (GitHub API via gh).

Usage: python -I review/task-005/ci_and_advisories.py RUN_ID [RUN_ID ...]
"""

import datetime
import json
import subprocess
import sys

REPO = "indes-dev/ttree"


def gh(*args):
    return json.loads(
        subprocess.run(["gh", *args], capture_output=True, text=True, check=True).stdout
    )


print("refreshed_utc", datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"))
for run in sys.argv[1:]:
    data = gh("run", "view", run, "--repo", REPO, "--json", "headSha,event,conclusion,createdAt,jobs")
    print(f"run {run} {data['event']} {data['headSha']} {data['conclusion']} {data['createdAt']}")
    for job in data["jobs"]:
        print(f"  {job['name']}: {job['conclusion']}")

advisories = gh("api", "-X", "GET", "/advisories", "-f", "ecosystem=pip", "-f", "affects=pypdf", "-f", "per_page=100")
print("pypdf advisories (all versions):", len(advisories))
for version in ("6.1.0", "6.19.0"):
    hits = gh("api", "-X", "GET", "/advisories", "-f", "ecosystem=pip", "-f", f"affects=pypdf@{version}", "-f", "per_page=100")
    ids = sorted(a["ghsa_id"] for a in hits)
    print(f"affecting pypdf=={version}: {len(ids)} {ids if version == '6.19.0' else ''}")
