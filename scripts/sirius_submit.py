#!/usr/bin/env python3
"""Post the approved review to the linked work item as ONE Sirius comment.

Usage:
    sirius_submit.py                       # preview only — posts nothing
    sirius_submit.py --confirm             # actually post
    sirius_submit.py --confirm --work-item 96178 --format plain

This is the only step that writes to Azure DevOps, and it never runs without
`--confirm`. The developer stays the decision maker: nothing reaches Sirius
until they have read the preview and asked for it explicitly.

The comment is `.sirius/review.md` (see sirius_review.py) with the Sirius
directive prepended as the first line, e.g.

    @fe-agent;rework;yes;ag;
    <the review body>

Work item comments are stored as HTML, so a body containing fenced code or
angle brackets is escaped and wrapped in <pre>; prose-only bodies post
verbatim. `--format` overrides that choice.

`az boards work-item update --discussion` can post a comment, but it offers no
way to preview or to read the comment back, so this uses the REST API directly.

Auth: PAT with Work Items (Read & Write). See ado.py.
"""
import json
import sys
import urllib.parse

import ado
import sirius_review as review


def work_item_id(argv, meta):
    if "--work-item" in argv:
        i = argv.index("--work-item")
        if i + 1 >= len(argv):
            ado.die("--work-item needs an id.")
        return argv[i + 1].lstrip("#")
    if meta.get("workItem"):
        return str(meta["workItem"])
    ctx_path = ado.repo_root() / ".sirius" / "context.json"
    if ctx_path.exists():
        wis = json.loads(ctx_path.read_text()).get("workItems") or []
        if wis:
            return str(wis[0]["id"])
    ado.die("no work item. Add `workItem:` to .sirius/review.md, pass "
            "--work-item <id>, or run sirius_context.py to discover it.")


def already_posted(org, project, wid, pat, directive_line):
    """Most recent comment that starts with the same directive, if any.

    Re-running is a real risk — a duplicate directive kicks off a second Sirius
    rework — so warn rather than silently stacking comments.
    """
    url = (f"{org}/{urllib.parse.quote(project)}/_apis/wit/workItems/{wid}"
           f"/comments?$top=50&{ado.COMMENTS_API}")
    try:
        data = ado.request(url, pat)
    except ado.ApiError:
        return None  # read failure shouldn't block a submit
    head = directive_line.strip()
    for c in sorted(data.get("comments", []),
                    key=lambda c: c.get("createdDate", ""), reverse=True):
        if ado.to_text(c.get("text", "")).strip().startswith(head):
            return {"id": c.get("id"),
                    "author": (c.get("createdBy") or {}).get("displayName", "?"),
                    "date": (c.get("createdDate") or "")[:16]}
    return None


def post(org, project, wid, pat, text):
    url = (f"{org}/{urllib.parse.quote(project)}/_apis/wit/workItems/{wid}"
           f"/comments?{ado.COMMENTS_API}")
    return ado.request(url, pat, method="POST", body={"text": text})


def main():
    argv = sys.argv[1:]
    confirm = "--confirm" in argv
    force = "--force" in argv

    cfg = ado.config()
    meta, body = review.load(cfg)
    found = review.problems(meta, body, cfg)
    text, fmt = review.render(meta, body, cfg, review.fmt_arg(argv))
    wid = work_item_id(argv, meta)
    project = meta.get("project") or cfg["project"]
    wi_url = f"{cfg['org']}/{project}/_workitems/edit/{wid}"

    print(f"--- review comment for work item #{wid} "
          f"({fmt}, {len(text)} chars) ---")
    print(text)
    print("--- end ---\n")

    if found:
        print(f"⚠ {len(found)} problem(s) — refusing to submit:")
        for p in found:
            print(f"  - {p}")
        sys.exit(1)

    if not confirm:
        print("Preview only — nothing was posted.")
        print(f"Target: {wi_url}")
        print("Re-run with --confirm to post it and start the Sirius rework.")
        return

    pat = ado.load_pat("Work Items (Read & Write)")
    prior = already_posted(cfg["org"], project, wid, pat,
                           ado.directive(cfg, meta.get("agent"), meta.get("action"),
                                         meta.get("gate"), meta.get("flag")))
    if prior and not force:
        print(f"⚠ work item #{wid} already has a matching directive comment "
              f"(#{prior['id']} by {prior['author']} on {prior['date']}).")
        print("Posting again starts a second Sirius rework run. "
              "Pass --force if that is what you want.")
        sys.exit(1)

    try:
        result = post(cfg["org"], project, wid, pat, text)
    except ado.ApiError as e:
        ado.die(f"posting failed: {e}")

    print(f"posted comment #{result.get('id')} to work item #{wid}")
    print(wi_url)
    print("Sirius should reply on the work item once the rework run starts.")


if __name__ == "__main__":
    main()
