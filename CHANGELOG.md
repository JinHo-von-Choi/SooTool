# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.3] - 2026-04-24

Infrastructure hotfix for the 0.1.2 release: the GitHub Actions CI and
Publish-to-PyPI workflows were running `uv sync --frozen` without the
`symbolic` optional extra, so every `tests/modules/symbolic/*` case failed
with `ModuleNotFoundError: No module named 'sympy'` and the PyPI build job
never finished. No functional changes to tools, policies, or transports
relative to 0.1.2.

### Changed
- `.github/workflows/ci.yml`: `uv sync --frozen` → `uv sync --frozen --extra symbolic` so the Python 3.12 matrix installs `sympy>=1.12` and the symbolic test suite can execute.
- `.github/workflows/publish-pypi.yml`: same extra added to the build job, unblocking the Trusted Publishing path for future releases.

### Fixed
- Repaired the release pipeline broken since CE-M4 (symbolic module) introduction: 0.1.1 and 0.1.2 CI runs had been red because the optional extra was never wired into the workflows.

[0.1.3]: https://github.com/JinHo-von-Choi/SooTool/releases/tag/v0.1.3

## [0.1.2] - 2026-04-24

Current master snapshot: 18 domains, 254 base tools, 10 admin policy-management tools, 5 transport modes.

### Added
- FB-M1 (P0 remediation): `scripts/count_tools.py` registry-backed single source for domain/tool counts; CI guard (ADR-019) gates README, `pyproject.toml`, and CHANGELOG numbers against the live REGISTRY.
- FB-M2: README subtitle "Precision Calc MCP for LLM tool use", CI/PyPI/Python/License badges, and a real `finance.npv` audit-trace sample block.
- FB-M9: GitHub About tagline aligned to "SooTool — Precision Calc MCP: Decimal-only deterministic calculation server for LLM tool use".
- `docs/architecture.md` — ADR-019 (docs-number single source) and ADR-020 (batch deterministic as_completed reordering).
- Batch regression tests covering wall-clock reduction and completion-order independence for `deterministic=True`.
- CE-M2 한국 수직 심화: realestate.kr_local_property (광역 계수), tax.kr_simplified_vat (간이과세), payroll 의료비·교육비·기부금·주택차입이자 공제 4종 — 6 신규 도구 + 정책 YAML 3종.
- CE-M3 결정적 재현성 인증: 모든 응답에 `_meta.integrity`(input_hash·policy_sha256·tool_version·sootool_version·policy_source) post-processor 자동 주입. ADR-021.
- CE-M4 symbolic 하이브리드: symbolic.solve·symbolic.diff (sympy optional extra), AST 화이트리스트 + sympify locals={} 이중 경계, SIGALRM 5초 타임아웃. ADR-022.
- CE-M10 글로벌 세법 1단계 tax_us: federal_income (7 brackets × 4 filing), capital_gains (LTCG + NIIT), state_tax (CA·NY·TX) — 3 신규 도구 + 정책 YAML 5종.

### Changed
- `pyproject.toml` description resynced to match README first paragraph; annotated with "keep in sync" marker (ADR-019).
- `core.batch` deterministic path now collects futures via `as_completed` and reorders by input id, shortening wall-clock to `max(item_time)` while preserving ADR-011 ordering invariant. `item_timeout_s` / `batch_timeout_s` are both enforced (ADR-020).
- README tool-catalog table reflects the updated payroll (5), tax (10), and core (8) counts; running totals aligned to the current REGISTRY.
- 도구 수 253 → 264 (base 243 → 254, admin 10 유지), 계산 도메인 16 → 18 (symbolic·tax_us 신설). 네임스페이스 18 → 20.
- `server.py` `_load_modules`: tax_us·symbolic(optional) import 추가.
- `pyproject.toml`: `[project.optional-dependencies] symbolic = ["sympy>=1.12"]` 추가.
- `scripts/count_tools.py`: `base_tools` 공식을 `total - admin_policy_tools`에서 `total - policy_tools`로 통일하여 CI guard 공식(ADR-019)과 일치. human print 라벨도 `(= 전체 - policy)`로 동기화.
- `core.pipeline.PipelineExecutor._execute`: 선언만 존재하던 `step_timeout_s`/`pipeline_timeout_s`를 `ThreadPoolExecutor(max_workers=1)` + `future.result(timeout=…)` watchdog으로 강제. 초과 시 `status="timeout"` 또는 `"skipped"`(PipelineTimeout) 응답.
- `core.batch.BatchExecutor`: `with ThreadPoolExecutor` 컨텍스트 매니저를 수동 수명 관리(`try/finally` + `shutdown(wait=False, cancel_futures=True)`)로 전환하여 `batch_timeout_s` 이후 호출측 wall-clock이 잔여 worker 완료를 기다리지 않도록 분리.
- `modules/symbolic/_bridge.run_symbolic`: 메인 스레드에서는 기존 SIGALRM 경로, 비메인 스레드(예: `core.batch` worker)에서는 `ThreadPoolExecutor(max_workers=1)` + `future.result(timeout=_EVAL_TIMEOUT_S)` watchdog으로 분기하여 `_EVAL_TIMEOUT_S` 강제.

### Fixed
- CI tool-count-guard(ADR-019) 재현 실패: `README.md` 첫 문단과 `CHANGELOG.md` [Unreleased] 요약을 live REGISTRY 수치(18 domains, 254 base tools, 10 admin policy-management tools)에 맞춰 CI grep 패턴과 정확히 정렬.

### Security
- `middleware.auth.BearerTokenValidator.validate`: 평문 `==` 비교 대신 `hmac.compare_digest`를 사용하여 Bearer 토큰 검증을 constant-time 비교로 전환. 타이밍 공격 표면 제거.

[0.1.2]: https://github.com/JinHo-von-Choi/SooTool/releases/tag/v0.1.2

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
