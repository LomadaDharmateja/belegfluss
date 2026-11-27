# ADR-0023: Make the repository public: MIT, history kept, ID logs removed, identifiers masked

- **Status:** Proposed (2026-11-27)
- **Date:** 2026-11-27
- **Milestone:** M4b

## Context

The plan has always been to keep the repository private until the app is live on Azure, then make it public, so
employers and reviewers can read the code, the decisions and the evidence. M4a made dev live.

**Two technical reasons to go public now:**
- On GitHub Pro, environment **required reviewers only work in public repositories**
  ([GitHub docs](https://docs.github.com/en/actions/reference/workflows-and-actions/deployments-and-environments)).
  Prod's manual approval (ADR-0022) needs them.
- Actions minutes are free for public repositories.

**What becomes public with the switch:**
- every file of every commit
- commit metadata (author emails)
- old workflow run logs
- release assets

**Checked on 2026-11-27:**
- **History:** no personal terms in any committed file version (full name, employer, city, email addresses).
  The owner's private brief was never committed.
- **Commit metadata:** 179 commits carry the owner's email.
- **Run logs:** 8 deploy and 2 eval-live runs print the Azure subscription, tenant and identity IDs.
- **Screenshots:** 5 milestone screenshots showed the file name of the owner's own receipt.

## Options

1. **Rewrite history** (emails, screenshots) and force-push. Removes everything, but changes every commit ID,
   breaks links to commits and PRs, and is destructive.
2. **Go public as is.** Simple, but the receipt name stays in current screenshots, the run logs show the Azure IDs,
   and future logs keep showing them.
3. **Clean what is current, keep the history:**
   - fix current files
   - delete the runs that show the IDs, after keeping redacted excerpts as evidence
   - mask the IDs from now on
   - noreply commit email from now on

## Decision

**Option 3**, decided with the owner:
- **Licence: MIT.** Copyright holder "LomadaDharmateja": the GitHub handle, no personal name.
  [THIRD_PARTY.md](../THIRD_PARTY.md) covers the components with their own licences. `SECURITY.md` explains private
  vulnerability reporting.
- **History:**
  - **Kept, not rewritten.** The existing commits keep the owner's email, and older screenshot versions stay in the
    history.
  - **New commits** use the GitHub noreply address (repository config). The owner switches on email privacy in
    GitHub.
  - **The five screenshots** now show `receipt.pdf` in place of the real receipt's file name.
- **Run logs:**
  - The 10 deploy and eval-live runs are **deleted** after their key lines were saved, redacted, in
    [evidence/runs-m3-m4a.md](../milestones/evidence/runs-m3-m4a.md). The docs link there instead.
  - Other runs (tests, scans) contain no Azure IDs and stay.
- **Identifiers are masked from now on:**
  - Subscription, tenant and deploy-identity client IDs, the name suffix, the state account and the AI endpoints
    are stored as GitHub **environment secrets**, so logs show `***`.
  - They are identifiers, not credentials: **no credential exists**, and OIDC is still the only way in.
  - The Entra External ID sign-in IDs stay plain variables, because the web app sends them to every browser
    anyway.
- **Release asset:** `eval-dataset-v1.zip` becomes public. Its notes name KoSIT and the Apache-2.0 licence for the
  official renders.
- **Ruleset on `main`:**
  - no force pushes, no deletion
  - changes only through pull requests
  - the secret scan must pass
- **Private vulnerability reporting** is switched on.

## Consequences

- The code, decisions and evidence can be read by anyone. Deleted runs are replaced by excerpts, which are less
  complete than full logs.
- Anyone determined can still read the owner's email in old commit metadata, and the older screenshot versions.
  This is accepted by the owner.
- Logs no longer show the Azure IDs. Someone reading a log sees `***` where an ID would be, explained here.
- The approval gate for prod becomes possible (M4b part 2).

## Sources

- GitHub environments, required reviewers by plan:
  https://docs.github.com/en/actions/reference/workflows-and-actions/deployments-and-environments
- GitHub secrets are masked in logs: https://docs.github.com/en/actions/concepts/security/secrets
- Deleting workflow runs: https://docs.github.com/en/actions/managing-workflow-runs-and-deployments/managing-workflow-runs/deleting-a-workflow-run
- Private vulnerability reporting:
  https://docs.github.com/en/code-security/security-advisories/working-with-repository-security-advisories/configuring-private-vulnerability-reporting-for-a-repository
- Rulesets: https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/about-rulesets
