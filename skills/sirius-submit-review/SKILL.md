---
name: sirius-submit-review
description: Post an approved .sirius/review.md to the linked Azure DevOps work item as one consolidated comment that tags the Sirius agent and starts a rework run. Use only when the developer has explicitly approved the review document.
disable-model-invocation: true
argument-hint: [--work-item <id>]
---

# Submit the review to Sirius

This is the only step that writes to Azure DevOps and the only one that starts a
Sirius rework run. **Never run it on your own initiative** — only when the
developer has read the review and explicitly asked you to submit it.

`SIRIUS="$(dirname "$(dirname "$(readlink -f "${CLAUDE_SKILL_DIR}")")")/bin/sirius"`

## 1. Preview

```
$SIRIUS submit $ARGUMENTS
```

Without `--confirm` this posts nothing. It prints the exact comment text — the
Sirius directive line followed by the review body — the target work item, and
any problems that would block submission.

Show the developer that output verbatim. Check with them:

- Is the **work item** the right one?
- Is the **directive line** right — the correct agent (`fe-agent` for frontend,
  `be-agent` for backend) and gate (`ag` agent gate, `hg` human gate)? Override
  per-review with `agent:` / `gate:` in the review.md frontmatter, or for the
  repo in `.sirius/config.json`.
- Does the body say what they want Sirius to do?

If anything is wrong, fix `.sirius/review.md` and preview again. Do not work
around a reported problem by editing the rendered text — the document is the
source of truth.

## 2. Submit, only on an explicit yes

```
$SIRIUS submit --confirm $ARGUMENTS
```

If the work item already carries a matching directive comment, this refuses and
says so — a second one starts a second rework run. Tell the developer, and pass
`--force` only if they confirm they want another run.

## 3. Report

Print the comment id and the work item URL. Sirius replies on the work item when
the run starts; the developer watches for that. Do not poll for it.
