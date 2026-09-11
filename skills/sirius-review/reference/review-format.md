# The review document

`.sirius/review.md` is what Sirius reads. Two sections, split by who is speaking:

- **Review Comments** — the threads other people and bots left on the PR, one
  entry per distinct comment, with the code it was pointing at.
- **Dev Suggested Feedback** — what the developer running this review wants
  changed, in their own words.

Every entry under either heading is an imperative instruction anchored to a
`file:line` — not an observation. Both headings are equally binding: the agent
has been seen working through `## Review Comments` and stopping there, so the
document carries an explicit instruction under `# PR Feedback` telling it to
address every entry in both sections. Keep that line in place.

Where the fix is already worked out locally, paste it as a snippet: the agent
copies working code more reliably than it reconstructs it from a description.

````markdown
---
workItem: <the work item id pr.py printed in step 1>
---

# PR Feedback

You MUST address every entry under BOTH `## Review Comments` and
`## Dev Suggested Feedback`. Neither section is optional and neither takes
priority. Work through the entries one at a time and do not finish until each
one has been either implemented or explicitly reported as not actioned, with
the reason.

## Review Comments

### `path/to/file.ts:42`

What the reviewer asked for, and what to do about it.

```diff
- const value = JSON.parse(input)
+ const value = schema.parse(input)
```

## Dev Suggested Feedback

### `path/to/file.ts:88`

What the developer wants changed, with the code they worked out locally.
````

Submit derives the agent from the work item title, so add `agent: fe-agent` to
the frontmatter only when the title carries no `[FE-01]`/`[BE-01]` tag. A
`Notes` section, if the developer wants one, stays local — submit strips it.
