# docs/WORKFLOW.md

Concrete rules to follow for every change, regardless of who (or which AI
session) is making it. These exist because this repo has had real incidents
from skipping them: a commit landing on the wrong local branch, a merge
reverting a naming decision, a real password committed to `.env.example`.

## Before starting ANY work

```powershell
git checkout main
git pull origin main
git status          # must be clean before branching
git branch --show-current   # confirm you know what you're on right now
```

Never assume local `main` matches remote `main`. Always re-pull, every session,
even if you pulled "recently."

## One branch = one reviewable unit of work

- Branch name should describe the one thing it does:
  `fix-timesheets-start-end-time`, not `misc-fixes`.
- Don't let unrelated work land on the same branch (this is exactly what
  happened when a Timesheets bugfix landed on
  `must-change-password-enforcement` — a branch for something else entirely).
- Before every commit, confirm you're on the branch you think you're on:
  ```powershell
  git branch --show-current
  ```
- Keep branches short-lived: open the PR, merge, delete both local and remote
  copies, same day if possible. Long-lived parallel branches are exactly what
  causes tangled merges later.

## If more than one thread of work is happening at once

(e.g. two separate Claude sessions, or a human + an assistant working at the
same time)

- **Read `PROGRESS.md` first**, in every session, before writing any code —
  it's the shared source of truth for decisions and in-flight work.
- Each thread should touch a clearly separate set of files/modules wherever
  possible. If two threads must touch the same file, merge one before starting
  the other's work on it, not in parallel.
- Any real decision (naming, schema shape, workflow behavior) gets written to
  `PROGRESS.md` in the same PR — don't let it live only in one session's chat
  history, where the other thread can't see it.

## Before pushing

```powershell
python -m alembic upgrade head
python -m alembic current        # must show "(head)"
python -m pytest tests\ -q
cd workhours-frontend
npx tsc --noEmit
npm run build
cd ..
```

CI (`.github/workflows/ci.yml`) now runs all of this automatically on every
push and PR — this is a safety net, not a replacement for checking locally
first. A red X on the PR means something is genuinely broken; don't merge
past it.

## Before merging a PR

- CI must be green (migrations ran clean against a real Postgres, tests pass,
  frontend type-checks and builds, gitleaks found nothing).
- If GitHub shows "Merge conflicts," resolve locally with `git merge
  origin/main` on your branch first — don't force-push over `main`, and don't
  guess at conflict resolution without actually reading both sides of the
  diff.

## After merging

```powershell
git checkout main
git pull origin main
git branch -D <branch-name>
git push origin --delete <branch-name>
```

Update `PROGRESS.md` if this PR made or changed a real decision.

## Secrets

- Real secrets (DB passwords, API keys, `FIELD_ENCRYPTION_KEY`, SMTP
  credentials) go only in a local `.env` file, which is git-ignored.
- `.env.example` must contain placeholder values only, always.
- `pre-commit` (gitleaks) blocks committing real secrets locally;
  CI's gitleaks job blocks it again as a second layer, in case the local hook
  was skipped or not installed on a given machine.
