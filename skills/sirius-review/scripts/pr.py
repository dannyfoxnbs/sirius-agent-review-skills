#!/usr/bin/env python3
"""Print the pull request for the current branch: diff base, work item, which
Sirius agent owns it, and the open review comments.

Usage:  pr.py [--pr <id>] [--all]

  --pr <id>   use this PR instead of looking one up from the branch
  --all       include resolved comment threads too
"""
import base64, html, json, os, re, subprocess, sys, urllib.error, urllib.request
from pathlib import Path
from typing import NoReturn
from urllib.parse import quote

API = "api-version=7.1"
UNRESOLVED = {"active", "pending"}


def die(msg) -> NoReturn:
    sys.exit(f"error: {msg}")


def find_up(name):
    """The nearest file with this name, from this script's folder upwards."""
    here = Path(__file__).resolve()
    for folder in [here.parent, *here.parents]:
        if (folder / name).exists():
            return folder / name
    die(f"{name} not found. Keep the skills symlinked to sirius-review-tools, "
        f"or put {name} in a folder above them.")


def settings():
    return json.loads(find_up("sirius.json").read_text())


def token():
    pat = os.environ.get("AZURE_DEVOPS_PAT", "")
    if not pat:
        for line in find_up(".env").read_text().splitlines():
            key, sep, value = line.partition("=")
            if sep and key.strip() == "AZURE_DEVOPS_PAT":
                pat = value.strip().strip("'\"")
    if not pat:
        die("no token — put AZURE_DEVOPS_PAT in .env (see .env.example).")
    return base64.b64encode(f":{pat}".encode()).decode()


def git(*args):
    p = subprocess.run(("git",) + args, capture_output=True, text=True)
    return p.stdout.strip() if p.returncode == 0 else ""


def api(url, auth):
    req = urllib.request.Request(url, headers={"Authorization": f"Basic {auth}"})
    try:
        with urllib.request.urlopen(req) as r:
            return json.loads(r.read().decode() or "{}")
    except urllib.error.HTTPError as e:
        die("token rejected — expired, or missing the Code (Read) scope."
            if e.code in (401, 203)
            else f"HTTP {e.code}: {e.read().decode(errors='replace')[:200]}")
    except urllib.error.URLError as e:
        die(f"network error: {e.reason}")


def plain(s):
    """Comment bodies are HTML; flatten to text."""
    s = re.sub(r"<\s*(br|/p|/div|/li)\s*/?>", "\n", s or "", flags=re.I)
    s = html.unescape(re.sub(r"<[^>]+>", "", s)).replace("\xa0", " ")
    return re.sub(r"\n{3,}", "\n\n", s).strip()


def find_pr(org, auth):
    """The PR whose source branch is the one checked out. Prefers an open one."""
    remote = git("remote", "get-url", "origin")
    m = re.search(r"/([^/]+)/_git/([^/]+?)(?:\.git)?/?$", remote)
    if not m:
        die(f"origin is not an Azure DevOps repo: {remote or '(none)'}")
    branch = git("rev-parse", "--abbrev-ref", "HEAD")
    prs = api(f"{org}/{m.group(1)}/_apis/git/repositories/{quote(m.group(2))}"
              f"/pullrequests?searchCriteria.sourceRefName=refs/heads/{quote(branch)}"
              f"&searchCriteria.status=all&$top=10&{API}", auth).get("value", [])
    if not prs:
        die(f"no pull request found for branch {branch}.")
    return next((p for p in prs if p["status"] == "active"), prs[0])


def threads(org, repo, pr_id, auth, show_all):
    """(file, line, id, status, [(author, text)]) per comment thread, sorted."""
    url = (f"{org}/{repo['project']['name']}/_apis/git/repositories/{repo['id']}"
           f"/pullRequests/{pr_id}/threads?{API}")
    out = []
    for t in api(url, auth).get("value", []):
        status = (t.get("status") or "unknown").lower()
        if t.get("isDeleted") or (status not in UNRESOLVED and not show_all):
            continue
        said = [(c["author"]["displayName"], plain(c.get("content")))
                for c in t.get("comments", [])
                if not c.get("isDeleted") and c.get("commentType") != "system"]
        said = [s for s in said if s[1]]
        if not said:
            continue
        ctx = t.get("threadContext") or {}
        anchor = ctx.get("rightFileStart") or ctx.get("leftFileStart") or {}
        out.append((ctx.get("filePath") or "~ general", anchor.get("line") or 0,
                    t["id"], status, said))
    return sorted(out)


def main():
    argv = sys.argv[1:]
    cfg = settings()
    org, auth = cfg["org"].rstrip("/"), token()

    if "--pr" in argv:
        pr_id = argv[argv.index("--pr") + 1].lstrip("#")
        pr = api(f"{org}/_apis/git/pullrequests/{pr_id}?{API}", auth)
    else:
        pr = find_pr(org, auth)
    pr_id, repo = pr["pullRequestId"], pr["repository"]
    project, base = repo["project"]["name"], pr["targetRefName"].split("/")[-1]

    work_items = [w["id"] for w in api(
        f"{org}/{project}/_apis/git/repositories/{repo['id']}"
        f"/pullRequests/{pr_id}/workitems?{API}", auth).get("value", [])]

    # Sirius tickets are titled "[FE-01] ...", "[BE-01] ..." — see sirius.json.
    tag = re.search(r"\[([A-Z]{2})-\d+\]", pr["title"])
    agent = cfg["agents"].get(tag.group(1)) if tag else None

    print(f"PR #{pr_id}  {pr['title']}")
    print(f"  base        {base}   ->  git diff origin/{base}...HEAD")
    print(f"  work item   {', '.join(work_items) or 'none linked'}")
    print(f"  agent       {agent or 'unknown — ask, then set `agent:` in review.md'}")
    print(f"  url         {org}/{project}/_git/{quote(repo['name'])}/pullrequest/{pr_id}")
    if not git("merge-base", f"origin/{base}", "HEAD"):
        print("  warning     no merge base — run `git fetch origin`")

    show_all = "--all" in argv
    found = threads(org, repo, pr_id, auth, show_all)
    print(f"\n{len(found)} {'' if show_all else 'unresolved '}comment thread(s)")
    seen = None
    for path, line, tid, status, said in found:
        if path != seen:
            seen = path
            print(f"\n{path}")
        print(f"  #{tid} {f'L{line}' if line else 'file'} [{status}]")
        for who, what in said:
            print(f"    {who}: " + what.replace("\n", "\n      "))


if __name__ == "__main__":
    main()
