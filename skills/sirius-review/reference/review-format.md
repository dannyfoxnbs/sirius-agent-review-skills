# The review document

`.sirius/review.md` is what Sirius reads, so every entry is an imperative
instruction anchored to a `file:line` — not an observation.

````markdown
---
workItem: 96178
# agent: be-agent   # only when the title has no [FE-01]/[BE-01] tag
---

# Sirius PR Review

## Required Changes

### `path/to/file.ts:42`

What is wrong and why, then what to do instead. Add a diff block when the
patch is shorter than describing it:

```diff
- const x = 1
+ const x = 2
```

## Suggestions

Non-blocking.

## Out of Scope

A record of what the developer decided not to ask for.
````

`Out of Scope` and `Notes` are developer-only — submit strips them.
