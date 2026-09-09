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

Prints the PR, the diff command to use, the work item id, and every unresolved
comment thread. Use the diff command it gives you — not a guessed base.

## 2. Gather findings

Two sources, either or both:

- **The diff.** Read the repo's own `CLAUDE.md` / `AGENTS.md` and nearby code
  first, then judge the changes against *those* conventions. Look for
  correctness bugs, regressions, convention violations (the most common failure
  in agent-written code) and duplication of things that already exist.
- **The comment threads** from step 1, when the developer has already reviewed
  in the Azure DevOps UI. SonarCloud posts as `SVC_ADO` — collapse a rule that
  fires on twenty lines into one instruction, don't restate each thread. Ask
  what a terse comment meant rather than inventing a rationale for it.

Skip anything a thread already covers. If you cannot name the specific bad
outcome, it is not a finding.

## 3. Agree the list

Show the candidates as a numbered list — file:line, one-line gist — and **ask
which to keep**. Expect rejections, rewordings, and additions of their own.
Discuss as long as they want. Do not write the file until they have signed off.

## 4. Write `.sirius/review.md`

```markdown
---
pr: 41618
workItem: 96178
# agent: be-agent   # optional, default fe-agent
# gate: hg          # optional, default ag
---

# Sirius PR Review

## Required Changes

### `path/to/file.ts:42`

What is wrong and why, then what to do instead. Add a diff code block
when a patch is shorter than describing it.

## Suggestions

Non-blocking.

## Out of Scope

Not submitted — a record of what you decided not to ask for.
```

Sirius is the reader, so write imperative instructions anchored to a file:line,
not observations. `Out of Scope` and `Notes` are stripped before submission.

## 5. Stop

Show them the file and let them edit it — it is theirs. Tell them
`sirius-submit` posts it when they are ready. Do not submit.
