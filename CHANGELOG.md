# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

Current master snapshot (CE wave 완료 후): 16 domains, 243 base tools, 10 admin policy-management tools, 5 transport modes.

### Added
- FB-M1 (P0 remediation): `scripts/count_tools.py` registry-backed single source for domain/tool counts; CI guard (ADR-019) gates README, `pyproject.toml`, and CHANGELOG numbers against the live REGISTRY.
- FB-M2: README subtitle "Precision Calc MCP for LLM tool use", CI/PyPI/Python/License badges, and a real `finance.npv` audit-trace sample block.
- FB-M9: GitHub About tagline aligned to "SooTool — Precision Calc MCP: Decimal-only deterministic calculation server for LLM tool use".
- `docs/architecture.md` — ADR-019 (docs-number single source) and ADR-020 (batch deterministic as_completed reordering).
- Batch regression tests covering wall-clock reduction and completion-order independence for `deterministic=True`.

### Changed
- `pyproject.toml` description resynced to match README first paragraph; annotated with "keep in sync" marker (ADR-019).
- `core.batch` deterministic path now collects futures via `as_completed` and reorders by input id, shortening wall-clock to `max(item_time)` while preserving ADR-011 ordering invariant. `item_timeout_s` / `batch_timeout_s` are both enforced (ADR-020).
- README tool-catalog table reflects the updated payroll (5), tax (10), and core (8) counts; running totals aligned to the current REGISTRY.

### Added (CE-M2+M3+M4+M10)
- CE-M2 한국 수직 심화: realestate.kr_local_property (광역 계수), tax.kr_simplified_vat (간이과세), payroll 의료비·교육비·기부금·주택차입이자 공제 4종 — 6 신규 도구 + 정책 YAML 3종.
- CE-M3 결정적 재현성 인증: 모든 응답에 `_meta.integrity`(input_hash·policy_sha256·tool_version·sootool_version·policy_source) post-processor 자동 주입. ADR-021.
- CE-M4 symbolic 하이브리드: symbolic.solve·symbolic.diff (sympy optional extra), AST 화이트리스트 + sympify locals={} 이중 경계, SIGALRM 5초 타임아웃. ADR-022.
- CE-M10 글로벌 세법 1단계 tax_us: federal_income (7 brackets × 4 filing), capital_gains (LTCG + NIIT), state_tax (CA·NY·TX) — 3 신규 도구 + 정책 YAML 5종.

### Changed
- 도구 수 253 → 264 (base 243 → 254, admin 10 유지), 계산 도메인 16 → 18 (symbolic·tax_us 신설). 네임스페이스 18 → 20.
- server.py _load_modules: tax_us·symbolic(optional) import 추가.
- pyproject: [project.optional-dependencies] symbolic = ["sympy>=1.12"] 추가.

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

Initial public release. Decimal-only calculation MCP server with 16 domains,
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
