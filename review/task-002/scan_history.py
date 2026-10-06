"""Non-disclosing scan of the public history for accidental private material.

Usage: python scan_history.py REPO REV_RANGE
Prints only pattern labels, counts and file paths, never matched values.
"""

import re
import subprocess
import sys
from collections import defaultdict

PATTERNS = {
    "private key block": r"-----BEGIN [A-Z ]*PRIVATE KEY-----",
    "GitHub token": r"\b(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{40,}",
    "OpenAI/Anthropic-style key": r"\bsk-(?:ant-)?[A-Za-z0-9_-]{20,}",
    "AWS access key": r"\bAKIA[0-9A-Z]{16}\b",
    "Slack token": r"\bxox[abpors]-[A-Za-z0-9-]{10,}",
    "password assignment": r"(?i)\b(?:password|passwd|secret|api[_-]?key|token)\s*[:=]\s*['\"][^'\"\s]{6,}",
    "absolute home path": r"/home/[a-z][a-z0-9_-]*/|/Users/[A-Za-z][A-Za-z0-9_-]*/|C:\\\\Users\\\\",
    "email address": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b",
    "private vault reference": r"(?i)\bdata/vault\b|\bindes-(?:front|lab)\b|\bcontracts?/",
    "local IP": r"\b(?:10|192\.168|172\.(?:1[6-9]|2\d|3[01]))\.\d{1,3}\.\d{1,3}\b",
}


def main():
    repo, rev_range = sys.argv[1], sys.argv[2]
    log = subprocess.run(["git", "-C", repo, "log", "-p", "--no-color", "--format=commit %H", rev_range],
                         capture_output=True, check=True).stdout.decode("utf-8", "replace")
    hits = defaultdict(lambda: defaultdict(int))
    current = "?"
    for line in log.splitlines():
        if line.startswith("+++ b/"):
            current = line[6:]
        elif line.startswith("+") and not line.startswith("+++"):
            for label, pattern in PATTERNS.items():
                if re.search(pattern, line):
                    hits[label][current] += 1
    authors = subprocess.run(["git", "-C", repo, "log", "--format=%an <%ae> | %cn <%ce>", rev_range],
                             capture_output=True, text=True, check=True).stdout.splitlines()
    print(f"range={rev_range} commits={len(authors)}")
    print(f"distinct author/committer identities: {len(set(authors))}")
    for label in PATTERNS:
        files = hits.get(label, {})
        print(f"{label}: {sum(files.values())} added lines" + (f" in {dict(files)}" if files else ""))


if __name__ == "__main__":
    main()
