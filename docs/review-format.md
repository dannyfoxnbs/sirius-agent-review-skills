# The review document

`.sirius/review.md` is the interchange format between "a review happened" and
"Sirius is asked to rework". Anything can write it. The submit step only reads
it, so no part of this toolkit is a dependency of any other part.

## Shape

````markdown
---
pr: 41618
workItem: 96178
agent: fe-agent      # optional; overrides .sirius/config.json for this review
gate: ag             # optional
---

# Sirius PR Review

## Required Changes

### `src/example.ts:42`

What is wrong, and why it is wrong.

#### Preferred approach

What to do instead.

#### Suggested patch

```diff
- const canEdit = user.roles.includes('editor');
+ const canEdit = this.permissions.canEdit(user);
```

## Suggestions

Non-blocking. Sirius may apply these.

## Out of Scope

Stripped before submission — a record of what you decided not to ask for.

## Notes

Stripped before submission — scratch space.
````

Only `workItem` is required; `sirius review init` prefills it from
`.sirius/context.json`.

## What gets submitted

Everything under `# Sirius PR Review`, **except**:

- level-2 sections named in `excludeSections` (default `Out of Scope`, `Notes`)
- HTML comments

with the directive line prepended:

```
@fe-agent;rework;yes;ag;
# Sirius PR Review
...
```

`sirius review preview` renders exactly what would be posted, and
`sirius review check` reports anything that would block a submit — a missing
work item, an empty body, a leftover `TODO`, or a body that already starts with
its own `@directive`.

## Writing it well

Sirius is the reader. Write instructions to an agent, not observations to a
human.

- **Anchor every finding** to a `file:line`. "The service is messy" is not
  actionable; "`ProjectService:88` re-derives the permission check" is.
- **Say what to do instead.** A finding without a preferred approach invites the
  agent to guess.
- **Use a diff** when a patch is shorter than the prose describing it.
- **Collapse repetition.** Twenty SonarCloud threads for one rule become one
  instruction naming the rule and listing the lines.
- **Separate blocking from optional.** Everything under `Required Changes`
  should be something you'd re-review for.
- **Keep decisions you made.** `Out of Scope` isn't submitted, but it tells the
  next reviewer that something was considered rather than missed.
