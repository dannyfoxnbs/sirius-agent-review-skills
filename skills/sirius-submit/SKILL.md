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

Posts nothing. Show them the output and confirm the work item, the directive
line and the body are what they want. Fix `.sirius/review.md` if not, and
preview again.

## 2. Post

```
python3 ${CLAUDE_SKILL_DIR}/scripts/submit.py --confirm
```

Add `--no-tag` to post it as a draft with no directive line — nothing is
triggered, they read it on the work item, delete it, and re-run without the
flag when happy.

If the work item already has a rework comment, this refuses; only add `--force`
if they confirm they want a second run.

Report the comment id and URL. Sirius replies on the work item when the run
starts — don't poll for it.
