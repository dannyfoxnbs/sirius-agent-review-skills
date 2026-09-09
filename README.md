# sirius-review-tools

Review a Sirius PR with Claude, then send the feedback back as one comment that
tags the agent. Two skills, no dependencies.

## Setup

```bash
git clone <this repo> ~/sirius-review-tools
cd ~/sirius-review-tools
cp .env.example .env                          # paste your token into it
ln -s "$PWD"/skills/sirius-* ~/.claude/skills/
```

The token is an Azure DevOps PAT: **User settings → Personal access tokens →
New token**, with the **Code (Read)** and **Work Items (Read & Write)** scopes.

## Use

Check out the PR branch, then in Claude Code:

```
/sirius-review     review the PR, agree the findings, write .sirius/review.md
/sirius-submit     preview the comment, post it when you say so
```

That's it.

## Settings

`sirius.json` — add a row to `agents` when a new one appears:

```json
{
  "org": "https://thenbs.visualstudio.com/",
  "gate": "ag",
  "directive": "@{agent};rework;yes;{gate};",
  "agents": { "FE": "fe-agent", "BE": "be-agent" }
}
```

The agent is picked from the ticket title — `[FE-01] …` is `fe-agent`. To
override it for one review, put `agent: be-agent` in the `.sirius/review.md`
frontmatter.

## Handy

```bash
# post a draft with no agent tagged — nothing gets triggered
python3 skills/sirius-submit/scripts/submit.py --confirm --no-tag

# read a PR without reviewing it
python3 skills/sirius-review/scripts/pr.py --pr 41618
```

`.sirius/review.md` is a plain Markdown file, so you can write or edit it by
hand and submit that — Claude is optional.
