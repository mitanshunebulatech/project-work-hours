# PROGRESS.md

**Read this file first — before starting any new work, in any session, on any branch.**

This file exists because this project has had work happening in parallel (multiple
branches, possibly multiple separate AI-assistant sessions) without a shared source
of truth for what's actually decided and what's actually merged. `git log` shows
*what* happened; this file records *why*, and what's still open. Update it as part
of any PR that makes a real decision or finishes a chunk of work — treat it as
part of the deliverable, not an afterthought.

---

## How to use this file (for a human or an AI assistant starting a session)

1. Read the "Decisions Log" below before assuming anything about naming, scope, or
   design — if it's not written here, don't assume a past session's choice still
   holds; ask.
2. Read "In-Flight Work" to see what other branches/sessions are already doing,
   so you don't duplicate or collide with them.
3. Before writing any code: `git checkout main && git pull origin main`, confirm
   what's actually merged matches what this file says. If it doesn't match,
   **stop and reconcile this file first** — don't build on an assumption.
4. When you finish a piece of work: update this file in the same PR (move the
   item from "In-Flight" to "Decisions Log" / a "Done" note), so the next
   session doesn't have to reconstruct it from `git log`.

---

## ⚠️ Open items needing a decision (as of the last reconciliation)

- **Employee module naming**: `main` contains a merged PR ("PM Item 5: relabel
  Users to User Accounts") that renames the "Users" nav label — this appears to
  contradict an earlier explicit decision to keep the "Users" label unchanged.
  **Needs resolution**: was this a deliberate follow-up decision, or should it be
  reverted? Until resolved, don't assume either name is "final."
- **Parallel Onboarding Module work**: `main` already has substantial Onboarding
  Module work merged (schema split, identity-document storage, profile pictures,
  SMTP email service) and a `must-change-password-enforcement` branch in flight
  on top of it. If this was built in a separate session, that session's design
  decisions (sync vs. background email, required vs. optional Department/Role
  at creation, etc.) are the real ones in effect — record them here once known,
  rather than re-deciding them elsewhere.

---

## Decisions Log

Format: `[Item] — Decision — Date/PR reference`

- **RBAC model** — Functional roles/permissions via `roles`/`permissions`/
  `role_permissions` tables, `require_permission()` checks. Legacy `users.role`
  string kept as a fallback during transition. All routers migrated off
  `require_admin` onto permission-based checks. (PR #9)
- **Admin's own leave** — Auto-approved on submission (self-approval block in
  `approve_request()` still applies to the *approval endpoint*; auto-approve is
  a separate code path in `create_request()`), audit-logged as
  `"Auto-approved — admin self-submitted leave"`. (Item 4)
- **Half-day policy** — Configurable via a `work_schedule_policy` singleton
  table (not hardcoded, not folded into `LeavePolicy`), default hours
  11:00–16:00 / 16:00–20:00, editable via `work_schedule:manage` permission.
  (Item 4, migration 0024)
- **Leave preview** — Informational only, never blocks submission. (Item 4)
- **Status casing** — Display-only title-case via a shared `titleCase()` helper
  in `lib/utils.ts`; stored/filtered DB values remain lowercase. (Item 4)
- **Department deletion** — Deactivate-only (soft), no hard-delete endpoint.
  (Item 8, confirmed sufficient)
- **Admin timesheet access** — Admins never log their own hours; `/timesheets`
  redirects an admin to `/admin/timesheets`. (Nav/routing, Item 2/5)
- **Nav labels** — Keep existing labels, reorganize grouping only — **see open
  item above regarding a possible later contradiction of this.**

## In-Flight Work (branches known to exist, not yet merged, as of last check)

> Verify this list against `git branch -a` before trusting it — branches get
> merged/deleted between updates to this file.

- `must-change-password-enforcement` — backend 403 enforcement for forced
  password change (Part 4 of a larger flow); frontend half already merged
  separately.
- `cleanup-entries-reports-dedup`, `work-entry-times`,
  `sprint2-frontend-departments-employees`,
  `sprint2-permissions-departments-employees`, `departments-employees-ui`,
  `frontend/nebula-redesign` — status unverified; check merge state before
  assuming these are current or stale.

## Environment / Secrets

- Real secrets live only in a local, git-ignored `.env` — never in
  `.env.example` (which must contain placeholders only). See
  `.pre-commit-config.yaml` and `.github/workflows/ci.yml` (gitleaks) for the
  automated guardrails against this happening again.
- If a real secret is ever committed: rotating the credential is mandatory —
  deleting the file from a later commit does not remove it from git history.
