# ADR-0001: Record architecture decisions as short ADRs

- **Status:** Proposed
- **Date:** 2026-11-23
- **Milestone:** M0

## Context

Belegfluss will change a lot over ten milestones (local → Azure → Kubernetes, new formats such as XRechnung 4.0).
We need to remember *why* something was decided, show the reasoning to reviewers, and change decisions openly when
we learn more.

## Options

1. **No formal record:** decisions live in commit messages and chat. Cheap, but the reasoning gets lost.
2. **Wiki / one big design document:** easy to edit, but history gets overwritten silently.
3. **Architecture Decision Records (ADRs) in the repo:** one short Markdown file per decision, versioned with the
   code, reviewed in pull requests.

## Decision

Use **ADRs in `docs/decisions/NNNN-title.md`** with this template:

```markdown
# ADR-NNNN: <decision in a few words>
- Status: Proposed | Accepted | Superseded by ADR-XXXX
- Date: YYYY-MM-DD
- Milestone: Mn
## Context      — the problem and the facts (with links)
## Options      — at least two, with pros/cons
## Decision     — what we do, and why not the others
## Consequences — what becomes easier, what becomes harder, what we must watch
## Sources      — official links used
```

Rules:
- An accepted ADR is **never rewritten**. If it turns out wrong, a new ADR **supersedes** it, and the old one gets
  "Superseded by ADR-XXXX".
- New ADRs start as *Proposed*. They become *Accepted* after review (pull-request approval).
- Small, local choices (a library inside one module) don't need an ADR. Anything that is hard to reverse, costs
  money, or affects several components does.

## Consequences

- The reasoning for every major choice is reviewable and explainable later.
- Slight overhead per decision (≈ 15 minutes).
- The list in [`README.md`](README.md) must be kept up to date.

## Sources

- Michael Nygard, "Documenting Architecture Decisions" (2011): https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions
