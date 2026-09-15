# Branch Protection / Merge Requirements

The CI workflow (`.github/workflows/pr-checks.yml`) only _runs_ checks — GitHub
does not block merging on a failed check unless branch protection (or a
repository ruleset) requires it. A repository admin needs to configure this
once in **Settings → Branches** (Branch protection rules) or **Settings →
Rules → Rulesets**, for the `main` branch:

1. **Require a pull request before merging** — disable direct pushes to `main`.
2. **Require status checks to pass before merging**, and select these required
   checks (job names from `pr-checks.yml`):
   - `Frontend (lint, format, build)`
   - `Python (backend) — lint, format, test`
   - `Python (ai_service) — lint, format, test`
   - `Python (reporting) — lint, format, test`
   - (`Dependency security scan` is advisory/`continue-on-error`; not
     recommended as a required check until the dependency set stabilizes.)
3. **Require branches to be up to date before merging**, so PRs are always
   tested against the latest `main`.
4. **Require conversation resolution before merging.**
5. **Do not allow bypassing the above settings** (uncheck exemptions for
   admins, or explicitly acknowledge if an exception is needed).
6. Optionally: **Require linear history** and **restrict who can push to
   matching branches**, if the team wants an extra guard against direct pushes.

These settings cannot be applied by CI or from this codebase — they must be
configured manually via the GitHub UI or API by someone with admin access to
the repository.
