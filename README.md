# sirius-review-tools

Attempt at improving the review phase of Sirius.

Review a Sirius PR with Claude, then send the feedback back as one comment that
tags the agent. Two skills, no dependencies.

## Use

Check out the PR branch, then in Claude Code:

```
/sirius-review     review the PR, agree the findings, write .sirius/review.md
/sirius-submit     preview the comment, post it when you say so
```

That's it. `.sirius/review.md` is plain Markdown, so you can write or edit it by
hand and submit that — Claude is optional.

## Setup

You need:

- **An Azure DevOps PAT.** User settings → Personal access tokens → New token,
  with the **Code (Read)** and **Work Items (Read & Write)** scopes. Nothing
  works without it.
- **The Azure DevOps CLI** (`az` with the `azure-devops` extension) installed
  and logged in, for getting the PR branch checked out locally.

Then either paste this into Claude Code:

```
Install the sirius review tools from https://github.com/dannyfoxnbs/sirius-agent-review-loop: clone it to ~/sirius-review-tools,
copy .env.example to .env, and symlink skills/sirius-* into ~/.claude/skills/.
Then ask me to place my Azure DevOps PAT into .env.
```

or do it by hand:

```bash
git clone <this repo> ~/sirius-review-tools
cd ~/sirius-review-tools
cp .env.example .env                          # paste your PAT into it
ln -s "$PWD"/skills/sirius-* ~/.claude/skills/
```

## Settings

`sirius.json` — add a row to `agents` when a new one appears:

```json
{
  "org": "https://thenbs.visualstudio.com/",
  "gate": "ag",
  "directive": "@{agent};rework;yes;{gate};",
  "agents": { "FE": "fe-agent", "BE": "be-agent" },
  "ignoreAuthors": ["Andri.Ferinata@hubexo.com"]
}
```

`ignoreAuthors` hides comment threads from bots that never resolve their own
threads. Email or display name, either works. A thread is only hidden when
_every_ comment in it is from an ignored author — if someone replied, the whole
thread stays. `pr.py --all` shows them again.

The agent is picked from the ticket title — `[FE-01] …` is `fe-agent`. To
override it for one review, put `agent: be-agent` in the `.sirius/review.md`
frontmatter.

## Handy

```bash
# post a draft with no agent tagged — nothing gets triggered (the default)
python3 skills/sirius-submit/scripts/submit.py

# print the comment without posting it
python3 skills/sirius-submit/scripts/submit.py --dry-run

# post it for real, tagging the agent and starting the rework run
python3 skills/sirius-submit/scripts/submit.py --confirm

# read a PR without reviewing it
python3 skills/sirius-review/scripts/pr.py --pr 41618
```
