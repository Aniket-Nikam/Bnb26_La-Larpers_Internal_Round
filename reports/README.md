# Measured report artifacts

Each real run writes `reports/<run_id>/config.json`, restricted raw generator
output, `report.json`, and `summary.md`. Populated run directories are ignored by
Git until a human explicitly reviews and selects a safe artifact for commit.

No benchmark is bundled yet. The repository currently lacks the shared backend,
provisioning utility, and authoritative database reconciliation query, so any
claimed allocation result would be fabricated. Historical supplied results must
use `source: supplied_unreproduced` and remain separate from measured output.
