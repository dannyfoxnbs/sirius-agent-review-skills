---
name: sirius-collect-pr-comments
description: Turn review comments already left on an Azure DevOps PR into a consolidated .sirius/review.md for Sirius rework. Use when the developer reviewed the PR in the Azure DevOps UI and wants their inline comments collected into one structured request.
argument-hint: [--pr <id>] [--all]
---

# Collect Azure DevOps PR comments into a Sirius review

The developer has done a normal Azure DevOps code review and left inline
comments. Your job is to gather them into one structured review document.
**You consolidate; the developer approves.** This skill posts nothing.

`SIRIUS="$(dirname "$(dirname "$(readlink -f "${CLAUDE_SKILL_DIR}")")")/bin/sirius"`

## 1. Context and comments

```
$SIRIUS context
$SIRIUS comments --json $ARGUMENTS
```

Unresolved threads only by default — those are the actionable ones. Add `--all`
if the developer wants resolved threads too, and `--author <name>` to keep one
person's comments. Each thread carries its file, line, status, and every comment
in order, so a reply chain reads correctly.

## 2. Triage before consolidating

Group the threads and tell the developer what you found before writing anything:

- **Bot findings** — SonarCloud posts as `SVC_ADO`. These are often
  high-volume and repetitive (the same rule on twenty lines). Collapse them into
  one instruction naming the rule and listing the locations; never restate each
  thread.
- **Human findings** — the substance. Keep the reviewer's own wording where it
  is already clear; a terse "wrong" needs you to ask what they meant rather than
  invent a rationale.
- **Questions, not requests** — "why did you do it this way?" is not a rework
  instruction. Flag these separately and ask the developer whether they want
  them turned into a change or left on the PR.

Ask about anything ambiguous. Never guess at intent behind a short comment.

## 3. Write the review document

```
$SIRIUS review init
```

Fill in `.sirius/review.md`, one heading per file:line or per theme. Preserve
the information that makes a comment actionable — the file, the line, and what
the reviewer actually wanted. Attribute where it helps ("per the reviewer's
comment on thread #358564"), and merge duplicates.

Where a bot rule applies across many lines, write it once:

```markdown
### `dashboard-customization.component.html` — Web:InputWithoutLabelCheck

Every input in this template is missing an associated label (SonarCloud,
lines 14, 19, 32, 37). Add a `<label for>` or `aria-label` to each.
```

```
$SIRIUS review check
```

## 4. Hand back

Show the developer the document, tell them how many threads went in and whether
you dropped or merged any, and let them edit it. Then stop — `sirius-submit-review`
posts it when they approve.
