---
name: sirius-review
description: Review a Sirius-generated pull request with the developer and collect the agreed findings into .sirius/review.md. Use when reviewing an agent-authored branch locally, or when consolidating review comments already left on the Azure DevOps PR.
argument-hint: [--pr <id>] [--all]
---

# Review a Sirius PR

The developer decides what becomes feedback. This skill writes one file and posts nothing.

## 1. Read the PR

```
python3 ${CLAUDE_SKILL_DIR}/scripts/pr.py $ARGUMENTS
```

It prints a diff command, the work item, the agent, and the open comment
threads. Run that diff command. Ask which agent if it comes back unknown.

## 2. Agree the findings

Review the diff for correctness, regressions, convention violations, and code
duplicating what already exists. Every finding names the specific bad outcome it
prevents. Skip what the threads already cover.

When the developer has already reviewed in the Azure DevOps UI, the threads are
the material. Collapse one rule firing on twenty lines into one instruction, and
ask what a terse comment meant. `pr.py` lists only unresolved threads from
authors worth reading: resolved means the developer is happy with it, and
`ignoreAuthors` in `sirius.json` drops bots that never resolve their own
threads. Both stay out of the feedback; `--all` brings them back.

Show the candidates as a numbered list — file:line, one-line gist — and ask
which to keep. Sign-off on that list is what unblocks step 3.

## 3. Write the review document

`.sirius/review.md`, in the format in
[`reference/review-format.md`](reference/review-format.md).

## 4. Hand back

Show them the file and let them edit it. Posting is `sirius-submit`, and only
when they ask for it.
