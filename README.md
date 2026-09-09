# sirius-review-tools

Two Claude Code skills for reviewing pull requests written by the Sirius agent.

Sirius reworks a PR when you comment on its work item with a directive line like
`@fe-agent;rework;yes;ag;`. Inline comments on the PR itself never reach it, so
today you assemble that comment by hand. These skills do the assembling.

```
Sirius opens a PR
  └─ review it with Claude, or in the Azure DevOps UI ....... sirius-review
                          │
                 .sirius/review.md    ← you read, edit and approve this
                          │
  └─ post it as one comment tagging Sirius .................. sirius-submit
                          │
                Sirius reworks the PR
```

`.sirius/review.md` is the only contract between the two. Claude writes it, but
so could you by hand or any other tool — submit just reads the file.

## Install

Copy or symlink the skill folders into `~/.claude/skills/` (global) or a repo's
`.claude/skills/`:

```bash
ln -s "$PWD"/skills/sirius-* ~/.claude/skills/
```

Then `cp .env.example .env` and add an Azure DevOps PAT with **Code (Read)** and
**Work Items (Read & Write)**. The scripts look for `.env` in their own folder
or any folder above it, so if you copy a skill out of this repo, put `.env`
somewhere above it — `~/.claude/.env` works. `$AZURE_DEVOPS_PAT` in your
environment takes precedence.

Needs Python 3. Nothing else.

## Use

```
/sirius-review          # read the PR, agree findings, write .sirius/review.md
/sirius-submit          # preview it, then post it on your say-so
```

Or run the scripts directly from inside the repo you're reviewing:

```bash
python3 skills/sirius-review/scripts/pr.py [--pr <id>] [--all]
python3 skills/sirius-submit/scripts/submit.py [--confirm] [--no-tag]
```

`pr.py` prints the PR, the right diff base, the work item, the agent and every
unresolved comment thread. `submit.py` posts nothing without `--confirm`, and
refuses if the work item already has a rework comment.

`--no-tag` posts the review **without** the directive line. Sirius never sees
it, so nothing is triggered — use it to read a draft in context on the work
item, then delete the comment and re-run without the flag when you're happy.

## The review document

````markdown
---
pr: 41618
workItem: 96178
# agent: be-agent    # only if the title has no [FE-01]/[BE-01] tag
# gate: hg           # optional, default ag
---

# Sirius PR Review

## Required Changes

### `path/to/file.ts:42`

What is wrong and why, then what to do instead.

## Suggestions

Non-blocking.

## Out of Scope

Not submitted.
````

Only `workItem` is required. Everything is submitted except `Out of Scope`,
`Notes` and HTML comments, with the directive line prepended.

Which agent gets tagged comes from the work item's title tag — `[FE-01]` is
`fe-agent`, `[BE-01]` is `be-agent`. If a title has neither (an `[FS-01]`
full-stack ticket, say), submit refuses rather than guessing, and you set
`agent:` yourself. When the full-stack agent exists, add `"FS": "fs-agent"` to
`AGENTS` in `submit.py` and `pr.py`.

## Notes

Neither skill submits on its own initiative — `sirius-submit` is marked
`disable-model-invocation` and needs `--confirm` on top of that. An agent
filing its own rework request would defeat the point.

`az repos pr` has no command for PR threads, so `pr.py` uses the REST API.
Work item comments are stored as HTML, so `submit.py` escapes `&`, `<` and `>`;
without that a suggested patch containing `input<Project[]>` is silently
swallowed by the renderer.
