#!/usr/bin/env python3
"""Resolve the review context for the current branch: PR, base branch, work item.

Usage:
    sirius_context.py [--pr <id>] [--json] [--no-cache]

Works out, in order:
  * the git repo + origin remote -> ADO project and repository
  * the current branch -> its open/most recent pull request
  * the PR's target branch  -> the base to diff against
  * the merge base commit   -> a stable diff range
  * the PR's linked work item(s) -> where the Sirius rework comment goes

Everything is discovered read-only. The result is cached to
`.sirius/context.json` so the review and submit steps agree on the same PR and
work item without re-querying.

Auth: PAT with Code (Read). See ado.py.
"""
import json
import sys
import urllib.parse

import ado


def find_repo_id(cfg, pat):
    url = (f"{cfg['org']}/{urllib.parse.quote(cfg['project'])}/_apis/git/repositories/"
           f"{urllib.parse.quote(cfg['repo'])}?{ado.API}")
    return ado.get(url, pat).get("id")


def find_pr_for_branch(cfg, repo_id, branch, pat):
    """The PR whose source is this branch. Prefers active over completed."""
    base = (f"{cfg['org']}/{urllib.parse.quote(cfg['project'])}"
            f"/_apis/git/repositories/{repo_id}/pullrequests")
    q = (f"searchCriteria.sourceRefName=refs/heads/{urllib.parse.quote(branch)}"
         f"&searchCriteria.status=all&$top=20&{ado.API}")
    prs = ado.get(f"{base}?{q}", pat).get("value", [])
    if not prs:
        return None
    active = [p for p in prs if (p.get("status") or "").lower() == "active"]
    # ADO returns newest first; prefer an active PR, else the most recent.
    return (active or prs)[0]


def fetch_pr(cfg, pr_id, pat):
    """Look a PR up by id. PR ids are org-unique, so no project needed."""
    return ado.get(f"{cfg['org']}/_apis/git/pullrequests/{pr_id}?{ado.API}", pat)


def linked_work_items(cfg, repo_id, pr_id, pat):
    url = (f"{cfg['org']}/{urllib.parse.quote(cfg['project'])}/_apis/git/repositories/"
           f"{repo_id}/pullRequests/{pr_id}/workitems?{ado.API}")
    refs = ado.get(url, pat).get("value", [])
    items = []
    for ref in refs:
        wid = ref.get("id")
        if not wid:
            continue
        wi = ado.get(f"{cfg['org']}/_apis/wit/workItems/{wid}?{ado.API}", pat)
        f = wi.get("fields", {})
        items.append({
            "id": int(wid),
            "type": f.get("System.WorkItemType", "?"),
            "title": f.get("System.Title", ""),
            "state": f.get("System.State", ""),
            "agentStatus": f.get("Custom.AgentStatus"),
            "url": f"{cfg['org']}/{cfg['project']}/_workitems/edit/{wid}",
        })
    return items


def short(ref):
    return (ref or "").replace("refs/heads/", "")


def build(cfg, pat, pr_override=None):
    branch = ado.git("rev-parse", "--abbrev-ref", "HEAD")
    if not cfg.get("project") or not cfg.get("repo"):
        ado.die("could not derive the ADO project/repo from the origin remote. "
                "Set them in .sirius/config.json.")

    if pr_override:
        pr = fetch_pr(cfg, pr_override, pat)
        repo = pr.get("repository", {})
        repo_id = repo.get("id")
        # A PR id can point at another repo/project; trust the PR over the remote.
        cfg["repo"] = repo.get("name") or cfg["repo"]
        cfg["project"] = (repo.get("project") or {}).get("name") or cfg["project"]
    else:
        repo_id = find_repo_id(cfg, pat)
        pr = find_pr_for_branch(cfg, repo_id, branch, pat)

    ctx = {
        "branch": branch,
        "project": cfg["project"],
        "repo": cfg["repo"],
        "repoId": repo_id,
    }

    if not pr:
        # No PR yet — still useful for a local review against the default branch.
        ctx["pr"] = None
        ctx["baseBranch"] = short(ado.git("symbolic-ref", "refs/remotes/origin/HEAD")) \
            .replace("origin/", "") or "main"
        ctx["workItems"] = []
    else:
        pr_id = pr.get("pullRequestId")
        ctx["pr"] = {
            "id": pr_id,
            "title": pr.get("title", ""),
            "status": pr.get("status"),
            "isDraft": pr.get("isDraft", False),
            "createdBy": (pr.get("createdBy") or {}).get("displayName"),
            "sourceBranch": short(pr.get("sourceRefName")),
            "url": (f"{cfg['org']}/{cfg['project']}/_git/"
                    f"{urllib.parse.quote(cfg['repo'])}/pullrequest/{pr_id}"),
        }
        ctx["baseBranch"] = short(pr.get("targetRefName"))
        ctx["workItems"] = linked_work_items(cfg, repo_id, pr_id, pat)

    base_ref = f"origin/{ctx['baseBranch']}"
    ctx["mergeBase"] = ado.git("merge-base", base_ref, "HEAD") or None
    ctx["diffRange"] = f"{base_ref}...HEAD"
    ctx["directive"] = ado.directive(cfg)
    return ctx


def render(ctx):
    out = [f"branch      {ctx['branch']}",
           f"repo        {ctx['project']}/{ctx['repo']}"]
    pr = ctx.get("pr")
    if pr:
        draft = " (draft)" if pr["isDraft"] else ""
        out += [f"PR          #{pr['id']}{draft}  [{pr['status']}]  {pr['title']}",
                f"            by {pr['createdBy']}",
                f"            {pr['url']}"]
    else:
        out.append("PR          none found for this branch")
    out += [f"base        {ctx['baseBranch']}",
            f"diff range  {ctx['diffRange']}"]
    if not ctx.get("mergeBase"):
        out.append("            ⚠ no merge base — run `git fetch origin` first")

    wis = ctx.get("workItems") or []
    if wis:
        for wi in wis:
            status = f"  agent-status: {wi['agentStatus']}" if wi.get("agentStatus") else ""
            out += [f"work item   #{wi['id']}  [{wi['type']}/{wi['state']}]  {wi['title']}",
                    f"            {wi['url']}{status}"]
    else:
        out.append("work item   none linked — set `workItem` in .sirius/review.md "
                   "to submit a review")
    out.append(f"directive   {ctx['directive']}")
    return "\n".join(out)


def main():
    argv = sys.argv[1:]
    as_json = "--json" in argv
    no_cache = "--no-cache" in argv
    pr_override = None
    if "--pr" in argv:
        i = argv.index("--pr")
        if i + 1 >= len(argv):
            ado.die("--pr needs an id.")
        pr_override = argv[i + 1].lstrip("#")
        if not pr_override.isdigit():
            ado.die("--pr needs a numeric id.")

    cfg = ado.config()
    ctx = build(cfg, ado.load_pat(), pr_override)

    if not no_cache:
        path = ado.sirius_dir() / "context.json"
        path.write_text(json.dumps(ctx, indent=2) + "\n")
        if not as_json:
            print(f"(cached to {path.relative_to(ado.repo_root())})\n")

    print(json.dumps(ctx, indent=2) if as_json else render(ctx))


if __name__ == "__main__":
    main()
