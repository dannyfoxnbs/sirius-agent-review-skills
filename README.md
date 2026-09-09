# sirius-review-tools

A small, optional toolkit for reviewing PRs written by the Sirius coding agent.

Sirius reworks a PR when you comment on its PBI with a directive line like
`@fe-agent;rework;yes;ag;`. That means collecting your review into **one**
comment by hand — inline comments on the PR itself don't reach the agent. These
tools remove the copy-and-paste without changing the Sirius workflow.

Three Claude Code skills and four stdlib-only Python scripts. No orchestration,
no MCP server, no daemon. Every piece is optional and composable, and the only
thing that ever writes to Azure DevOps needs an explicit `--confirm`.

## The loop

```
Sirius opens a PR
  └─ you check out the branch
       ├─ review it with Claude ..................... /sirius-review-branch
       └─ or review it in the Azure DevOps UI,
          then collect your inline comments ......... /sirius-collect-pr-comments
                              │
                     .sirius/review.md   ← you read, edit and approve this
                              │
       └─ post it as one comment that tags Sirius ... /sirius-submit-review
                              │
                    Sirius reworks the PR
```

`.sirius/review.md` is the interchange format, and the only contract. Claude
writes it, but so could you by hand, your IDE, or any other diff reviewer — the
submit step doesn't care where it came from.

## Install

Needs Python 3 and an Azure DevOps PAT with **Code (Read)** and **Work Items
(Read & Write)**, in `$AZURE_DEVOPS_EXT_PAT` or `~/.config/azure-devops/pat`
(`chmod 600`).

```bash
git clone <this repo> ~/repos/sirius-review-tools
cd /path/to/the/repo/you/review
~/repos/sirius-review-tools/install.sh
```

That symlinks the skills into the repo's `.claude/skills/` (and `.opencode/` or
`.agents/` if you use those), seeds `.sirius/config.json`, and keeps the
per-review working files out of `git status`. Because they're symlinks, a
`git pull` here updates every repo you've installed into.

Check it:

```bash
~/repos/sirius-review-tools/bin/sirius context
```

## Skills

| Skill | What it does |
|---|---|
| `sirius-review-branch` | Reviews the current branch's diff **with** you. Finds the PR and base branch, reads the changes and the existing threads, proposes findings, and only writes `.sirius/review.md` once you've agreed the list. |
| `sirius-collect-pr-comments` | You reviewed in the Azure DevOps UI; this pulls your unresolved inline comments and consolidates them into `.sirius/review.md`, collapsing repetitive bot findings. |
| `sirius-submit-review` | Posts the approved document to the linked work item as one comment with the Sirius directive on top. Refuses to run without your explicit go-ahead. |

Neither review skill submits anything. That is deliberate: an agent reviewing an
agent and filing its own rework request takes you out of the loop, which is the
opposite of the point.

## Scripts

`bin/sirius` dispatches; every script also runs standalone.

```bash
sirius context  [--pr <id>] [--json]              # branch -> PR -> base -> work item
sirius comments [--pr <id>] [--all] [--author X]  # existing ADO review threads
                [--json]
sirius review   init | check | preview | render   # work with .sirius/review.md
sirius submit   [--confirm] [--work-item <id>]    # post to the work item
```

- **`context`** caches to `.sirius/context.json` so review and submit agree on
  the same PR and work item. It gives you the real diff base (the PR's target
  branch), which is not always what `origin/HEAD` says.
- **`comments`** defaults to unresolved threads — the actionable ones. Each
  keeps its file, line, status, thread id and full reply chain.
- **`submit`** prints the exact comment and exits without `--confirm`. With it,
  it refuses if the work item already carries a matching directive, because a
  second one starts a second rework run (`--force` to override).

## Configuration

`.sirius/config.json` in the repo you review; every key optional.

```json
{
  "org": "https://thenbs.visualstudio.com/",
  "directive": "@{agent};{action};{flag};{gate};",
  "agent": "fe-agent",
  "gate": "ag",
  "excludeSections": ["Out of Scope", "Notes"]
}
```

`project` and `repo` are derived from the `origin` remote. `agent` is
`fe-agent` or `be-agent`; `gate` is `ag` (agent gate), `hg` (human gate) or
`kg` (knowledge graph). Override either per-review in the review.md
frontmatter. If the directive format changes, edit `directive` and nothing else
needs to move.

## Why REST and not just the az CLI

`az repos pr` has **no** command for threads or comments, so collecting inline
review comments has to go through the REST API. `az repos pr work-item list`
does expose the PR's linked work items, and `az boards work-item update
--discussion` can post a comment — but it can't preview or read comments back,
which the duplicate guard needs. The scripts use REST throughout for one
consistent auth and error path, in the same stdlib-only style as the existing
`read-azure-devops-*` skills. No MCP server: there's nothing here that a
deterministic script doesn't do better.

## Notes on the work item comment

Azure DevOps stores work item comments as HTML. A prose-only review posts
verbatim (newlines survive), which is what a hand-written rework comment looks
like today. As soon as the body contains a fenced code block or an angle
bracket, it's escaped and the code goes in `<pre>` — otherwise a suggested patch
containing `input<Project[]>` gets silently eaten by the renderer. `--format
plain|html` overrides the choice; `sirius review preview` always shows you
exactly what will be sent.

See [`docs/review-format.md`](docs/review-format.md) for the document format.
