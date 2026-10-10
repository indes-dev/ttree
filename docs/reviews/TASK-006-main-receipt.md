# TASK-006 — Main and installed-command receipt

Observed on 2026-10-10 by the ttree Orc+Agent.

- PR1 is **MERGED** at `71aa7e7a566388f06dabee3fa4f9d007377b4d9a`.
- That main merge contains the checked head `5ccc6c3446b493e036b96dac0a76c440800a79b8`
  and exact production/package source `30ff2b1ce22978fcc747aa2299627c3461ed4d54`.
  Production files on main match that artifact source.
- The five post-merge CI jobs passed:
  https://github.com/indes-dev/ttree/actions/runs/38060044405.
- Issue2 is CLOSED. Existing v0.1.0 tag/history are preserved.
- The existing indes-front user command was replaced offline from the measured,
  hash-verified local artifact. All installed ttree files match wheel
  `68349df0bcc539cbc51696aa9f9b0dded51e51fc73e2f693280e21256f3ca8cb`.
  Its real public DOC smoke count is163tokens, complete=true. The previous user-tool
  environment is retained locally for rollback. No system packages/services/settings
  or privileges changed.
- Final integrated COMMENTED review:
  https://github.com/indes-dev/ttree/pull/1#pullrequestreview-5479319163.
  It is explicitly Orc/Agent acceptance, not a new independent Claude approval.
- The Linux DOC/DOCX/text-PDF upgrade is delivered. No executor or reviewer needs
  resuming. Full evidence, supported-format/resource limits and preserved historical
  coverage qualifications: [TASK-006 completion](TASK-006-completion.md).

This receipt does not publish a tag, AUR package or registry release. Recovery is
a normal merge revert; the local CLI has its retained prior environment. Future
Eryon direct-return integration remains a separate requirement owned by harness.
