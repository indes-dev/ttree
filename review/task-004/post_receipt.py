"""Post a sanitized commit-linked PR #1 comment and verify the published body.

Usage: python review/task-004/post_receipt.py BODY_FILE RECEIPT_JSON
Prints the comment URL. Fails unless the API body equals the local body exactly
and the remote branch head equals the local HEAD named in the body.
"""

import hashlib
import json
import subprocess
import sys
from pathlib import Path

REPO = "indes-dev/ttree"
BRANCH = "task-001-office-pdf"


def run(*args, data=None):
    return subprocess.run(
        args, input=data, capture_output=True, text=True, check=True
    ).stdout


body_path, receipt_path = map(Path, sys.argv[1:3])
body = body_path.read_text()
head = run("git", "rev-parse", "HEAD").strip()
remote = run("git", "ls-remote", "origin", "refs/heads/" + BRANCH).split()[0]
if remote != head or head not in body:
    sys.exit("remote head mismatch or body does not name local HEAD")
payload = json.dumps({"body": body})
posted = json.loads(
    run("gh", "api", f"repos/{REPO}/issues/1/comments", "--input", "-", data=payload)
)
fetched = json.loads(run("gh", "api", f"repos/{REPO}/issues/comments/{posted['id']}"))
if fetched["body"] != body:
    sys.exit("published body differs from local body")
receipt = {
    "url": fetched["html_url"],
    "id": fetched["id"],
    "created_at": fetched["created_at"],
    "user": fetched["user"]["login"],
    "head": head,
    "remote_head": remote,
    "body_sha256": hashlib.sha256(body.encode()).hexdigest(),
    "api_body_equal": True,
}
receipt_path.write_text(json.dumps(receipt, indent=2) + "\n")
print(fetched["html_url"])
