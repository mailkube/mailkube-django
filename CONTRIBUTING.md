# Contributing to mailkube-django

Thanks for helping improve **mailkube-django**, a [mailkube](https://mailkube.com) SDK.
Contributions of all kinds are welcome: bug reports, fixes, docs, and features.

By contributing you agree that your contributions are licensed under the project's
[Apache License 2.0](LICENSE) (inbound = outbound). **No CLA and no sign-off are required.**
Please also read our [Code of Conduct](CODE_OF_CONDUCT.md).

## Development setup

Requires [uv](https://docs.astral.sh/uv/) (and Node.js for the `jscpd` duplication check).

```bash
git clone https://github.com/mailkube/mailkube-django
cd mailkube-django

uv sync --extra anymail                              # create the env + install everything
# `uv sync` alone gives the zero-extra install. Both are valid; only the --extra environment
# can reach the 90% coverage gate, because anymail_backend.py is absent from the other one.
uv run pre-commit install                            # ruff + format + jscpd hooks
uv run pre-commit install --hook-type commit-msg     # Conventional Commits hook
```

`uv.lock` is committed and CI installs it with `--frozen`, so run `uv lock` in the same
change whenever you touch a dependency. Otherwise CI fails at install rather than resolving
around it, which is the point.

## Quality gates

Every change must pass the same checks CI runs (see [.rules/SOLID_DRY_KISS.md](.rules/SOLID_DRY_KISS.md)):

```bash
uv run ruff check .                          # lint incl. complexity (C901) + docstrings (D)
uv run ruff format --check .                 # formatting
uv run mypy src                              # strict types
uv run pytest                                # tests + 90% line+branch coverage gate
npx --yes jscpd@4 --config .jscpd.json .     # duplication (DRY) gate, blocks at > 1%
./scripts/check-rule-index.sh                # every .rules/*.md indexed in AGENTS.md
```

`uv run pre-commit run --all-files` runs the lint/format/jscpd hooks in one shot.

## Branches

`develop` is the integration branch: open pull requests against it, and CI runs on every push to
it. `main` is the release branch — merging `develop` into it is what cuts a version, so nothing
lands there except through that merge. See [.rules/RELEASE.md](.rules/RELEASE.md).

Dependency updates target `develop` for the same reason. Their configuration names the branch
explicitly, and a branch that does not resolve produces no pull requests at all, with no error —
so if updates go quiet, check that `develop` still exists before looking anywhere else.

### Required checks

Both branches require **every** job in `ci.yml`, not just the test legs. `build` and `floor`
exist precisely to fail on the pull-request path, so a job that is not required is a job a
merge can walk past, and the release path builds only *after* it has already tagged. The
contexts to require:

```
test (3.12, 5.2)   test (3.12, 6.1)   test (3.13, 5.2)   test (3.13, 6.1)   test (3.14, 6.1)
zero-extra   build   floor   dry   docs   PR-title
```

`PR-title` is the job *name* in `pr-title.yml`, not its id; GitHub matches the name. A matrix
job registers one context per leg, so copy them from a completed run rather than typing them
and assuming they matched.

## Commit & PR conventions

This project follows **[Conventional Commits](https://www.conventionalcommits.org/)**. A CI check
enforces the **PR title** (PRs are **squash-merged** using it), and it drives releases: only
`feat:`, `fix:`, and `perf:` cut a new version. See [.rules/RELEASE.md](.rules/RELEASE.md).

Suggested scopes, one per thing this package actually has: `backends` (the standalone
backend), `anymail` (the ESP backend and its payload), `payload`, `webhooks`, `checks`, `ci`,
`deps`, `docs`.

```
feat(anymail): map merge_metadata onto SDK variables
fix(payload): keep a text attachment's utf-8 bytes intact
docs: document the webhook receiver signature
```

## Reporting bugs / requesting features

Open an issue using the templates. For **security vulnerabilities**, do not open a public
issue — follow [SECURITY.md](SECURITY.md) instead.
