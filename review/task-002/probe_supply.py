"""TASK-002 supply-chain checks (read-only public metadata).

Usage: python probe_supply.py
1. PyPI JSON: which binary wheels exist for the resolved versions per CPython 3.10-3.14
   on Linux x86_64/aarch64, macOS and Windows (build_offline.py uses --only-binary=:all:).
2. GitHub Advisory Database (gh api graphql): advisories for the dependency closure,
   printed with vulnerable ranges so they can be compared with the allowed ranges.
No project data is sent; only public package names are queried.
"""

import json
import subprocess
import urllib.request

PINNED = {"tiktoken": "0.14.0", "regex": "2026.9.29", "pypdf": "6.19.0", "requests": "2.34.2",
          "urllib3": "2.8.0", "idna": "3.20", "charset-normalizer": "3.5.2", "certifi": "2026.7.22"}
PLATFORMS = {"linux-x86_64": ("manylinux", "x86_64"), "linux-aarch64": ("manylinux", "aarch64"),
             "musllinux-x86_64": ("musllinux", "x86_64"), "macos-arm64": ("macosx", "arm64"),
             "macos-x86_64": ("macosx", "x86_64"), "windows-amd64": ("win", "amd64")}


def wheel_matrix():
    for name, version in PINNED.items():
        with urllib.request.urlopen(f"https://pypi.org/pypi/{name}/{version}/json", timeout=30) as response:
            files = [item["filename"] for item in json.load(response)["urls"] if item["filename"].endswith(".whl")]
        if any("-none-any.whl" in f for f in files):
            print(f"{name}=={version}: pure wheel (all platforms)")
            continue
        missing = []
        for minor in range(10, 15):
            tag = f"cp3{minor}"
            for label, (os_part, arch) in PLATFORMS.items():
                ok = any((f"-{tag}-" in f or "abi3" in f) and os_part in f and (arch in f or "universal2" in f)
                         for f in files)
                if not ok:
                    missing.append(f"py3.{minor}/{label}")
        print(f"{name}=={version}: {len(files)} wheels; missing: {missing or 'none'}")


QUERY = """query($pkg: String!) { securityVulnerabilities(first: 50, ecosystem: PIP, package: $pkg) {
  nodes { advisory { ghsaId severity publishedAt summary withdrawnAt } vulnerableVersionRange firstPatchedVersion { identifier } } } }"""


def advisories():
    for name in ["tiktoken", "pypdf", "regex", "requests", "urllib3", "idna", "charset-normalizer", "certifi"]:
        done = subprocess.run(["gh", "api", "graphql", "-f", f"query={QUERY}", "-F", f"pkg={name}"],
                              capture_output=True, text=True, check=True)
        nodes = json.loads(done.stdout)["data"]["securityVulnerabilities"]["nodes"]
        print(f"## {name}: {len(nodes)} advisories (pinned {PINNED[name]})")
        for node in sorted(nodes, key=lambda n: n["advisory"]["publishedAt"], reverse=True):
            advisory, patched = node["advisory"], node["firstPatchedVersion"]
            if advisory["withdrawnAt"]:
                continue
            print(f"  {advisory['ghsaId']} {advisory['severity']:8} {advisory['publishedAt'][:10]} "
                  f"range={node['vulnerableVersionRange']!r} patched={patched and patched['identifier']} "
                  f"{advisory['summary'][:70]}")


if __name__ == "__main__":
    wheel_matrix()
    advisories()
