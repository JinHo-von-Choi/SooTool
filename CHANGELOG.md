# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.1] - 2026-04-24

Infrastructure patch: GitHub Actions CI and PyPI Trusted Publishing workflows.
No functional changes to tools, policies, or transports.

### Added
- `.github/workflows/ci.yml` — ruff, mypy, pytest, MCP stdio smoke, `uv build` on push and pull requests
- `.github/workflows/publish-pypi.yml` — automated PyPI upload on GitHub Release publish, manual TestPyPI target via `workflow_dispatch`
- `.github/workflows/README.md` — Trusted Publishing setup guide

### Changed
- Version bump 0.1.0 → 0.1.1

[0.1.1]: https://github.com/JinHo-von-Choi/SooTool/releases/tag/v0.1.1

## [0.1.0] - 2026-04-23

Initial public release. Decimal-only calculation MCP server with 15 domains,
236 base tools, 10 admin policy-management tools, and 5 transport modes.

### Added
- Phase 1 — Core kernel (M1~M4): Decimal operators, CalcTrace, REGISTRY
  auto-discovery, `core.batch` parallel executor, `core.pipeline` DAG runner
  with resume, payload guard, trace-level filter.
- Phase 1 — Transports (M5): multi-transport runtime (stdio, HTTP, SSE,
  WebSocket, Unix socket) with unified hardening middleware, origin guard,
  payload size limit, per-session isolation.
- Phase 1 — Skill guide (M6~M7): `sootool.skill_guide` MCP tool,
  `_meta.hints` injection pipeline, bilingual (KO+EN) playbooks and triggers
  covering tax / finance / payroll / realestate / policy-management flows.
- Phase 1 — Policy management (M8): 10 admin MCP tools implementing the
  propose → activate → rollback workflow with 6-stage YAML validation,
  SHA256 integrity check, signature chain, audit log, and `policy_source` /
  `sha256` / `audit_id` trace extensions on all policy-dependent tools.
- Phase 4 — Safe expression evaluator (P4-M1, ADR-017): AST-based `core.calc`
  with Decimal results, mpmath transcendentals, and explicit variable binding.
- Phase 4 — Engineering domain Tier 1~3 (P4-M2~M4): 50 tools covering
  electrical, fluid, thermal, mechanical, civil, chemistry engineering, and
  SI prefix conversions.
- Phase 4 — Domain Tier A (P4-M5): 25 tools across 6 domains with 6 policy
  YAML sources (capital gains, corporate, gift, inheritance, withholding,
  property tax).
- Phase 4 — Domain Tier B/C (P4-M6~M7): 60 tools covering the remaining
  statistics, probability, geometry, crypto, and project-management
  surfaces plus the new `math` domain.
- Architecture Decision Records ADR-001 through ADR-017 covering kernel
  invariants, transport hardening, skill-guide contract, policy management,
  and AST calculator design.

### Fixed
- SSE legacy endpoint 307 redirect regression: normalised `/messages` and
  `/messages/` to the same handler so MCP SSE clients no longer see spurious
  redirects during initialization.
- Skill-guide playbook scenario field alignment: `scenario` keys now match
  the trigger table across KO and EN catalogues, eliminating silent lookup
  misses from bilingual clients.

### Infrastructure
- 1748 pytest cases passing, `ruff check` clean, `mypy --strict` clean within
  the documented relaxations (ADR-011).
- Five-transport end-to-end smoke tests (`scripts/mcp_smoke_*.py`) wired into
  the release checklist.
- Registry surface: 236 base tools + 10 admin policy tools = 246 tools
  exposed via `tools/list` once `sootool.policy_mgmt.tools` is imported.

[0.1.0]: https://github.com/JinHo-von-Choi/SooTool/releases/tag/v0.1.0
