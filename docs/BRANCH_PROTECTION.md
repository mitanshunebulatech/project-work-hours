# docs/BRANCH_PROTECTION.md

One-time setup in GitHub's UI (not code) that makes the CI workflow and PR
discipline actually mandatory, instead of just "recommended and easy to skip
under time pressure."

## Steps

1. Go to `https://github.com/mitanshunebulatech/project-work-hours/settings/branches`
2. Under "Branch protection rules," click **Add branch protection rule**.
3. Branch name pattern: `main`
4. Enable:
   - ☑ **Require a pull request before merging**
     - This alone would have prevented direct pushes to `main` — everything
       must go through a reviewable PR.
   - ☑ **Require status checks to pass before merging**
     - Search for and select: `Backend (migrations + pytest)`,
       `Frontend (typecheck + build)`, `Secret scan (gitleaks)`
       (these names come from `.github/workflows/ci.yml` — they'll only
       appear in this list after the workflow has run at least once, so push
       the CI workflow file first, open one PR to trigger it, then come back
       here to select them)
     - ☑ **Require branches to be up to date before merging** — forces a
       fresh `git merge origin/main` before merge, catching conflicts like
       the `.env.example`/`AdminLeaveQueue.tsx` one earlier, before merge
       rather than after.
   - ☑ **Require conversation resolution before merging** (optional, but
     useful if you start using PR comments for review)
5. Click **Create** (or **Save changes**).

## What this buys you

- Nobody (including an AI-assistant session working unsupervised) can push
  broken migrations, a failing test suite, or a leaked secret straight to
  `main` — GitHub will physically block the merge button until CI is green.
- Every change has a PR, which means every change has a diff you can review
  before it lands — no more discovering after the fact that a naming decision
  got silently reversed.

## Note on solo/AI-assisted workflows

This doesn't slow down single-person work meaningfully — it's still just
`git push origin <branch>` + clicking "Merge" once CI passes. What it removes
is the ability to *accidentally* skip the check, which is exactly the failure
mode that's caused rework earlier in this project (unmerged local work assumed
to be pushed, a schema-breaking change merged without tests catching it,
credentials committed).
