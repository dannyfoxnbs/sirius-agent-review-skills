---
name: sirius-review-branch
description: Review the Sirius-generated PR on the current branch with the developer, and collect the agreed findings into .sirius/review.md. Use when reviewing an agent-authored branch/PR locally before asking Sirius to rework it.
argument-hint: [--pr <id>]
---

# Review the current branch for Sirius rework

You are helping a developer review a PR that a coding agent wrote. **You assist;
the developer decides.** Nothing becomes feedback until they say so, and nothing
is posted anywhere by this skill.

`SIRIUS="$(dirname "$(dirname "$(readlink -f "${CLAUDE_SKILL_DIR}")")")/bin/sirius"`

## 1. Establish context

```
$SIRIUS context $ARGUMENTS
```

This prints the PR, its target branch, the diff range and the linked work item,
and caches them to `.sirius/context.json`. If it reports no merge base, tell the
developer to `git fetch origin` and stop — everything downstream would be wrong.

If no PR is found, ask whether to review against the printed base branch anyway.

## 2. Read the changes

Use the `diffRange` from step 1 — do not guess the base:

```
git diff --stat <diffRange>
git diff <diffRange>
```

For a large diff, read `--stat` first and work through the files in priority
order rather than dumping everything.

## 3. Check what has already been said

```
$SIRIUS comments
```

Existing ADO threads — human and bot (SonarCloud posts as `SVC_ADO`). Do not
re-raise a finding someone has already made; instead note that it is already
covered, and tell the developer so they can decide whether to consolidate it
into the review.

## 4. Review

Read the project's own conventions first (`CLAUDE.md`, `AGENTS.md`, nearby code)
and judge the diff against **those**, not against generic best practice. Look
for, in priority order:

1. **Correctness** — logic errors, wrong conditionals, unhandled null/undefined,
   bad async/await, races, off-by-one.
2. **Regressions** — changed behaviour callers depend on, broken contracts,
   removed guards.
3. **Convention violations** — the agent not following patterns this repo
   already uses. This is the most common failure in agent-written code and the
   most valuable thing to catch.
4. **Code quality** — duplication of something that already exists, dead code,
   missing error handling.

For each candidate finding, be concrete: name the file and line, say what
actually goes wrong, and say what to do instead. If you cannot name a specific
bad outcome, it is not a finding — drop it.

## 5. Agree the findings with the developer

Present the candidates as a short numbered list — file:line, one-line gist,
severity — and **ask which to keep**. Expect them to reject some, reword others,
and add findings of their own that you missed. Discuss freely; this is the point
of the skill. Do not proceed to step 6 until they have signed off on a set.

## 6. Write the review document

```
$SIRIUS review init
```

Then edit `.sirius/review.md`: agreed blocking items under `## Required
Changes`, nice-to-haves under `## Suggestions`, and anything you considered and
dropped under `## Out of Scope` (that section is stripped before submission, but
records the decision). Follow the template's shape — a `file:line` heading, what
is wrong, `#### Preferred approach`, and a `#### Suggested patch` diff where a
concrete patch is clearer than prose.

Write it as instructions **to an agent**: imperative, specific, no hedging.

```
$SIRIUS review check
```

Fix anything it reports. Then show the developer the document and tell them to
edit it directly if they want changes — it is theirs, not yours.

## 7. Stop

Do **not** submit. Tell them the review is ready and that
`sirius-submit-review` posts it once they have approved it.
