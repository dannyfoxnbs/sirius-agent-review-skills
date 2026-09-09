---
name: sirius-submit
description: Post an approved .sirius/review.md to its work item as one comment, as a draft by default or tagging the Sirius agent on --confirm.
disable-model-invocation: true
---

# Submit the review to Sirius

## 1. Draft

```
python3 ${CLAUDE_SKILL_DIR}/scripts/submit.py
```

Posts the review to the work item with no directive line, so no agent is
tagged and nothing is triggered. They read it in context on the work item, fix
`.sirius/review.md` if any of it is wrong, delete the comment, and draft again.

Add `--dry-run` to print the comment without posting anything at all.

## 2. Post for real

```
python3 ${CLAUDE_SKILL_DIR}/scripts/submit.py --confirm
```

`--confirm` adds the directive line that tags the agent. This starts a real
rework run — only ever with an explicit ask from the developer, and only once
their draft is deleted, or the work item ends up with both.

It refuses if the work item already has a rework comment — add `--force` only
when they confirm they want a second run.

Report the comment id and URL. Sirius replies on the work item when the run
starts; leave them to watch for it.
