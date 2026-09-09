---
name: sirius-review
description: Review a Sirius-generated pull request with the developer and collect the agreed findings into .sirius/review.md. Use when reviewing an agent-authored branch locally, or when consolidating review comments already left on the Azure DevOps PR.
argument-hint: [--pr <id>] [--all]
---

# Review a Sirius PR

You help the developer review a PR a coding agent wrote. **They decide what
becomes feedback.** This skill writes one file and posts nothing.

## 1. Read the PR

```
python3 ${CLAUDE_SKILL_DIR}/scripts/pr.py $ARGUMENTS
```

Gives you the diff command to run, the work item, the agent, and the open
comment threads. Use that diff command — don't guess the base. If the agent
comes back unknown, ask which one and record it in step 3.

## 2. Find and agree the findings

Review the diff against the repo's own conventions (`CLAUDE.md`, `AGENTS.md`,
nearby code) — correctness, regressions, convention violations, duplication of
what already exists. Skip anything the comment threads already cover. If you
can't name the specific bad outcome, it isn't a finding.

If the developer already reviewed in the Azure DevOps UI, the threads from step
1 are the material. SonarCloud posts as `SVC_ADO`: collapse a rule firing on
twenty lines into one instruction. Ask what a terse comment meant rather than
inventing a reason for it.

Then show the candidates as a numbered list — file:line, one-line gist — and
**ask which to keep**. Expect rejections and additions. Don't write the file
until they've signed off.

## 3. Write `.sirius/review.md`

```markdown
---
workItem: 96178
# agent: be-agent   # only if the title has no [FE-01]/[BE-01] tag
---

# Sirius PR Review

## Required Changes

### `path/to/file.ts:42`

What is wrong and why, then what to do instead. Add a diff code block when a
patch is shorter than describing it.

## Suggestions

Non-blocking.

## Out of Scope

Not submitted — a record of what you decided not to ask for.
```

Sirius reads this, so write imperative instructions anchored to a file:line,
not observations. `Out of Scope` and `Notes` are stripped on submit.

## 4. Stop

Show them the file, let them edit it, and tell them `sirius-submit` posts it.
Do not submit.
