---
name: sirius-submit
description: Post an approved .sirius/review.md to its work item as one comment tagging the Sirius agent.
disable-model-invocation: true
---

# Submit the review to Sirius

This starts a real rework run. Run it only when the developer explicitly asks.

## 1. Preview

```
python3 ${CLAUDE_SKILL_DIR}/scripts/submit.py
```

Posts nothing. Show them the work item, the directive line and the body, fix
`.sirius/review.md` if any of it is wrong, and preview again.

## 2. Post

```
python3 ${CLAUDE_SKILL_DIR}/scripts/submit.py --confirm
```

`--no-tag` posts it as a draft with no directive line, so nothing is triggered:
they read it on the work item, delete it, and re-run without the flag.

It refuses if the work item already has a rework comment — add `--force` only
when they confirm they want a second run.

Report the comment id and URL. Sirius replies on the work item when the run
starts; leave them to watch for it.
