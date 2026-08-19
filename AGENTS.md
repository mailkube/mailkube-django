# Project Rules

`mailkube-django` is a public (Apache-2.0) Django email backend for mailkube, published to PyPI.
Load the relevant rule file from `.rules/` based on the task.

## Rule Index

> **Index every rule (required).** Every file in `.rules/` MUST have a row in the table below. When you
> add or rename a `.rules/` file, add or update its row in the **same change** — an unindexed rule is
> invisible, because this index is what drives progressive disclosure. The `docs` CI job (`scripts/check-rule-index.sh`)
> fails the build if `.rules/` and this index drift. This convention holds for every mailkube repo.

| Rule File | Load When |
|---|---|
| `.rules/SOLID_DRY_KISS.md` | Writing or changing any code — the enforced engineering standards (SOLID, DRY, KISS, coverage, docs) and how to run each gate locally. |
| `.rules/INTEGRATION_CONTRACT.md` | Touching the adapter, the payload mapping, the settings surface, the webhook entry point or the startup checks: the decisions every mailkube framework integration implements identically, whatever the framework. Shared verbatim across every integration; changes are made centrally. |
| `.rules/DJANGO_INTEGRATION.md` | The same tasks, for the **Django realization**: the two-backend contract, `AnymailBaseBackend` vs `AnymailRequestsBackend`, the file map, and the Django-specific deviations. |
| `.rules/SDK_CONTRACT.md` | Understanding what the API guarantees: config, errors, pagination, webhooks. This package adapts that contract; it never re-implements it. Shared verbatim across every SDK; changes are made centrally. |
| `.rules/RELEASE.md` | Touching `release.yml`, `[tool.semantic_release]`, versioning, or the PyPI OIDC publish flow. |
| `.rules/CI_GATES.md` | Adding, removing or weakening a CI job, or when a release fails after the tag was already pushed: why the publish-readiness, dependency-floor, example-compilation and release-permission gates exist. Shared verbatim across every mailkube repo; changes are made centrally. |

## Key Conventions (always apply)

- **Tooling is `uv`**: `uv sync`, `uv run …`; deps in PEP 621 `[project]` + `[dependency-groups]`; `uv.lock` committed.
- **`src/` layout** — code lives in `src/mailkube_django/`; tests in `tests/`.
- **Ruff** for lint **and** format; **line length ≤ 120**; **mypy strict** on `src` (with `django-stubs`).
- **Type-annotate** every function; `from __future__ import annotations` at the top of modules.
- **≥ 90% coverage, line + branch** — enforced by `--cov-fail-under=90`; never lower the gate to make a change pass.
- **Max cyclomatic complexity 10** (ruff `C901`) — split, don't waive.
- **Every public module/class/function has a docstring** (ruff `D`, google convention).
- **No duplication** — the `jscpd` gate blocks at > 1% duplicated code; extract shared logic.
- **`django-anymail` is an extra, never a runtime dependency**, and `backends.py` must never import it.
- **The wire format lives in the SDK**, not here. Both backends call the same SDK verb.
- **The version is never a literal** — `_version.py` reads it from the installed distribution metadata.
- **No models, no migrations.** This package holds no persistent state.
- **Conventional Commits** for PR titles (squash-merged); only `feat:`/`fix:`/`perf:` cut a release.
- **No secrets in the repo** — local config lives in a git-ignored `.env`, excluded from the built package.
- **Keep the `README` current** with user-visible changes. There is no `CHANGELOG.md`; the release
  notes on the GitHub Releases page are the changelog (see `.rules/RELEASE.md`).
