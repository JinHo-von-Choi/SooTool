# Policy File Management Guide

작성자: 최진호
작성일: 2026-04-23

## Overview

SooTool M8 introduces a dual-store policy management system that allows
tax, real estate, and other regulatory policy YAML files to be updated
without modifying the source code repository or redeploying the server.

Changes go through a draft -> validate -> activate lifecycle with a full
append-only audit trail.

## Dual Store Architecture

```
Package store (read-only, ships with SooTool)
  src/sootool/policies/<domain>/<name>_<year>.yaml

Override store (user-writable)
  $SOOTOOL_POLICY_DIR/<domain>/<name>_<year>.yaml   (if env set)
  $XDG_DATA_HOME/sootool/policies/<domain>/...      (default)
  ~/.local/share/sootool/policies/<domain>/...      (XDG fallback)
```

The loader checks the override store first. If no override file exists,
it falls back to the package store. If neither has the requested
domain/name/year, `UnsupportedPolicyError` is raised.

On server startup, the effective override directory is logged at INFO level.

## Admin Mode

Write tools (`policy_propose`, `policy_activate`, `policy_rollback`,
`policy_import`) require admin mode. Two ways to enable:

1. Environment variable: `SOOTOOL_ADMIN_MODE=1`
2. CLI flag: `uv run python -m sootool --admin`

Either condition is sufficient. Without admin mode, write tools return:
```json
{"error": "admin_required", "message": "..."}
```

## Available Tools

| Tool | Admin | Description |
|-|-|-|
| sootool.policy_list | no | List all known policies and their sources |
| sootool.policy_get | no | Get a specific policy's content |
| sootool.policy_history | no | View audit log for a policy |
| sootool.policy_diff | no | Semantic diff between two versions |
| sootool.policy_validate | no | Validate YAML without writing |
| sootool.policy_propose | yes | Create a draft + run validation |
| sootool.policy_activate | yes | Promote draft to override store |
| sootool.policy_rollback | yes | Remove override, revert to package |
| sootool.policy_export | no | Export as portable bundle |
| sootool.policy_import | yes | Import a bundle into override store |

## Typical Annual Update Workflow

1. Obtain the official policy notice (고시문) and prepare the YAML content.
2. Propose a draft:
   ```
   policy_propose(domain="tax", name="kr_income", year=2027, yaml_content=...,
                  notice_no="기획재정부 고시 제2026-XX호",
                  source_url="https://law.go.kr/...",
                  effective_date="2027-01-01")
   ```
3. Review the validation report and year-over-year diff returned in the response.
4. Activate the draft:
   ```
   policy_activate(draft_id="drf-...")
   ```
5. Verify by calling `tax.kr_income` and checking `policy_source == "override"` in the trace.

## Validation Pipeline

Each `policy_propose` and `policy_validate` call runs 6 stages:

| Stage | Check |
|-|-|
| 1 | Safe YAML parse (yaml.SafeLoader, no Python object tags) |
| 2 | Required metadata fields: sha256, effective_date, notice_no, source_url, data |
| 3 | Domain-specific pydantic schema (bracket types, rate types) |
| 4 | Cross-field: bracket upper strictly monotone, last upper=None, 0<=rate<=1 |
| 5 | Year-over-year sensitivity: rate change > threshold -> warning |
| 6 | SHA256 integrity (auto_fix_sha256=True re-computes on mismatch) |

Sensitivity threshold priority: call arg `sensitivity_threshold` > env
`SOOTOOL_POLICY_DIFF_THRESHOLD` > default 0.5 (50 percentage points).

## Draft Lifecycle

- Drafts are stored in `$SOOTOOL_DRAFT_DIR` (or XDG_RUNTIME_DIR/sootool/drafts/).
- TTL: 24 hours. Expired drafts are removed on server startup (`gc_expired_drafts`).
- Draft files have 0600 permissions; the directory is 0700.
- Draft ID format: `drf-<uuid4hex>`.

## Audit Log

All write operations append a JSON Lines entry to:

```
$SOOTOOL_STATE_DIR/policy_audit.jsonl       (if env set)
$XDG_STATE_HOME/sootool/policy_audit.jsonl  (default)
~/.local/state/sootool/policy_audit.jsonl   (XDG fallback)
```

File permissions are 0600. Each entry contains:

```json
{
  "ts":            "2026-04-23T09:00:00Z",
  "audit_id":      "aud-<hex>",
  "actor":         "user:cli",
  "action":        "activate",
  "domain":        "tax",
  "name":          "kr_income",
  "year":          2027,
  "draft_id":      "drf-<hex>",
  "sha256_before": "<old hash or null>",
  "sha256_after":  "<new hash>",
  "source_url":    "...",
  "notice_no":     "...",
  "validation":    {"status": "ok", "findings": []}
}
```

View history for a policy: `policy_history(domain="tax", name="kr_income")`.

## Trace Extension in Calculation Tools

When a policy-backed tool (`tax.kr_income`, `tax.capital_gains_kr`,
`realestate.kr_acquisition_tax`, etc.) loads a policy, the response
includes extra fields:

```json
{
  "tax": "...",
  "policy_source":         "package",
  "policy_audit_id":       null,
  "policy_sha256":         "6e29cc...",
  "policy_effective_date": "2026-01-01"
}
```

When `policy_source == "override"`, a hint is added to `_meta.hints`:

```json
{
  "signal":           "override_policy_in_use",
  "suggestion":       "이 결과는 사용자 덮어쓰기 정책을 사용합니다. policy_history로 변경 이력을 확인하세요.",
  "recommended_tool": "sootool.policy_history"
}
```

## Bundle Signing (Optional)

`policy_export` can optionally include an ed25519 signature when
`include_signature=True` and `private_key_b64` is provided.

`policy_import` verifies signatures when `require_signature=True` or
when `SOOTOOL_POLICY_REQUIRE_SIGNATURE=1` is set.

The `cryptography` package is required for signing/verification. By
default signatures are disabled and teams can opt in.

## Rollback

To revert to the package default:

```
policy_rollback(domain="tax", name="kr_income", year=2027)
```

This removes the override file and invalidates the loader cache.
The audit log records the rollback event.

## Security Notes

- All writes use atomic file replacement (tmp -> fsync -> rename).
- Override directories are created with 0700, files with 0600.
- Audit log file permissions are 0600.
- `yaml.SafeLoader` is enforced; Python object tags are rejected.
- `source_url` is stored as metadata only — no automatic URL fetching.
