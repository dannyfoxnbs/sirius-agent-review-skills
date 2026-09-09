---
name: sirius-submit
description: Post an approved .sirius/review.md to its Azure DevOps work item as one comment tagging the Sirius agent, which starts a rework run. Use only when the developer has explicitly asked to submit the review.
disable-model-invocation: true
---

# Submit the review to Sirius

This starts a real rework run. **Only run it when the developer explicitly asks.**

## 1. Preview

```
python3 ${CLAUDE_SKILL_DIR}/scripts/submit.py
```

Posts nothing. Prints the exact comment — directive line plus review body — and
the target work item's title. Show that output and check with them:

- Is that the right work item? The title is printed with it.
- Is the directive right? The agent comes from the work item's title tag —
  `[FE-01]` means `fe-agent`, `[BE-01]` means `be-agent`. Anything else and it
  refuses until you add `agent:` to the frontmatter. Gate is `ag` (agent) by
  default; `hg` for a human gate, via `gate:`.
- Does the body say what they want Sirius to do?

Fix `.sirius/review.md` if not, and preview again.

## 2. Post a draft first, if they want one

```
python3 ${CLAUDE_SKILL_DIR}/scripts/submit.py --confirm --no-tag
```

Posts the review with **no directive line**, so Sirius never sees it. Useful for
reading it in context on the work item before committing to a run. They delete
the comment in Azure DevOps and re-run without `--no-tag` when happy.

A draft needs no agent, so this also works on a work item whose title has no
`[FE-01]`/`[BE-01]` tag.

## 3. Submit on an explicit yes

```
python3 ${CLAUDE_SKILL_DIR}/scripts/submit.py --confirm
```

If the work item already has a rework comment this refuses — a second one starts
a second run. Only add `--force` if they confirm they want that. (A `--no-tag`
draft never blocks this; it has no directive to match.)

Report the comment id and URL. Sirius replies on the work item when the run
starts; don't poll for it.
