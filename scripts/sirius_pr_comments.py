#!/usr/bin/env python3
"""Collect review comments already left on an Azure DevOps PR.

Usage:
    sirius_pr_comments.py [--pr <id>] [--all] [--mine] [--author <name>] [--json]

The PR id comes from `.sirius/context.json` (written by sirius_context.py) unless
`--pr` is given.

Defaults to UNRESOLVED, actionable threads — status active or pending. `--all`
also includes resolved/closed/fixed/won't-fix threads, each labelled with its
status. System notifications (votes, reviewer changes, ref updates) are always
skipped: they carry no review content.

Each thread keeps the information needed to turn it into a rework instruction:
file, right/left line, thread id and status, and every comment in the thread
with author and date, so a reply chain reads in order.

`az repos pr` exposes no thread/comment command, so this uses the REST API
directly. Auth: PAT with Code (Read). See ado.py.
"""
import json
import sys
import urllib.parse

import ado

UNRESOLVED = {"active", "pending"}
# Threads ADO opens for its own bookkeeping rather than review feedback.
SKIP_TYPES = {"system"}


def load_pr_id(argv):
    if "--pr" in argv:
        i = argv.index("--pr")
        if i + 1 >= len(argv):
            ado.die("--pr needs an id.")
        return argv[i + 1].lstrip("#")
    path = ado.repo_root() / ".sirius" / "context.json"
    if not path.exists():
        ado.die("no PR id. Pass --pr <id>, or run sirius_context.py first.")
    ctx = json.loads(path.read_text())
    if not (ctx.get("pr") or {}).get("id"):
        ado.die("no PR recorded in .sirius/context.json — pass --pr <id>.")
    return str(ctx["pr"]["id"])


def anchor(ctx):
    """(filePath, line, side) for an inline thread; (None, None, None) if PR-level."""
    if not ctx:
        return None, None, None
    path = ctx.get("filePath")
    right, left = ctx.get("rightFileStart"), ctx.get("leftFileStart")
    if right:
        return path, right.get("line"), "right"
    if left:
        return path, left.get("line"), "left"
    return path, None, None


def collect(org, project, repo_id, pr_id, pat, include_resolved=False):
    url = (f"{org}/{urllib.parse.quote(project)}/_apis/git/repositories/{repo_id}"
           f"/pullRequests/{pr_id}/threads?{ado.API}")
    threads = []
    for th in ado.get(url, pat).get("value", []):
        if th.get("isDeleted"):
            continue
        status = (th.get("status") or "unknown").lower()
        resolved = status not in UNRESOLVED
        if resolved and not include_resolved:
            continue
        comments = []
        for c in th.get("comments", []):
            if c.get("isDeleted") or (c.get("commentType") or "text") in SKIP_TYPES:
                continue
            body = ado.to_text(c.get("content", ""))
            if not body:
                continue
            comments.append({
                "id": c.get("id"),
                "author": (c.get("author") or {}).get("displayName", "?"),
                "date": (c.get("publishedDate") or "")[:10],
                "text": body,
            })
        if not comments:
            continue  # a thread of nothing but system notifications
        path, line, side = anchor(th.get("threadContext"))
        threads.append({
            "threadId": th.get("id"),
            "status": status,
            "resolved": resolved,
            "file": path,
            "line": line,
            "side": side,
            "comments": comments,
        })
    threads.sort(key=lambda t: ((t["file"] or "").lower(), t["line"] or 0, t["threadId"]))
    return threads


def filter_authors(threads, author):
    """Keep threads whose FIRST comment is by a matching author (substring, ci)."""
    needle = author.lower()
    return [t for t in threads if needle in t["comments"][0]["author"].lower()]


def render(pr_id, url, threads, include_resolved):
    scope = "all" if include_resolved else "unresolved"
    out = [f"PR #{pr_id}  —  {len(threads)} {scope} review thread(s)", url, ""]
    if not threads:
        out.append("Nothing to collect. 🎉")
        return "\n".join(out)

    inline = [t for t in threads if t["file"]]
    general = [t for t in threads if not t["file"]]

    current = object()
    for t in inline:
        if t["file"] != current:
            current = t["file"]
            out.append(f"\n{current}")
        loc = f"L{t['line']}" if t["line"] else "file"
        flag = "" if not t["resolved"] else f" [{t['status']}]"
        out.append(f"  #{t['threadId']}  {loc}{flag}")
        for c in t["comments"]:
            body = c["text"].replace("\n", "\n        ")
            out.append(f"      [{c['author']} {c['date']}] {body}")
    if general:
        out.append("\n(general / PR-level)")
        for t in general:
            flag = "" if not t["resolved"] else f" [{t['status']}]"
            out.append(f"  #{t['threadId']}{flag}")
            for c in t["comments"]:
                body = c["text"].replace("\n", "\n        ")
                out.append(f"      [{c['author']} {c['date']}] {body}")
    return "\n".join(out)


def main():
    argv = sys.argv[1:]
    as_json = "--json" in argv
    include_resolved = "--all" in argv
    author = None
    if "--author" in argv:
        i = argv.index("--author")
        if i + 1 >= len(argv):
            ado.die("--author needs a name.")
        author = argv[i + 1]

    cfg = ado.config()
    pat = ado.load_pat()
    pr_id = load_pr_id(argv)

    # PR ids are org-unique, so one lookup gives the repo and project.
    pr = ado.get(f"{cfg['org']}/_apis/git/pullrequests/{pr_id}?{ado.API}", pat)
    repo = pr.get("repository", {})
    repo_id = repo.get("id")
    project = (repo.get("project") or {}).get("name", cfg["project"])
    if not repo_id:
        ado.die(f"could not resolve the repository for PR #{pr_id}.")
    pr_url = (f"{cfg['org']}/{project}/_git/"
              f"{urllib.parse.quote(repo.get('name', ''))}/pullrequest/{pr_id}")

    threads = collect(cfg["org"], project, repo_id, pr_id, pat, include_resolved)
    if author:
        threads = filter_authors(threads, author)

    if as_json:
        print(json.dumps({
            "pr": int(pr_id), "title": pr.get("title", ""), "url": pr_url,
            "includeResolved": include_resolved, "threads": threads,
        }, indent=2))
    else:
        print(render(pr_id, pr_url, threads, include_resolved))


if __name__ == "__main__":
    main()
