#!/usr/bin/env python3
"""Post .sirius/review.md to its work item as one comment tagging Sirius.

Usage:  submit.py [--confirm] [--no-tag] [--force]

Prints the comment and posts nothing unless --confirm is given.
--no-tag leaves the directive line off, so nothing is triggered.
--force posts even if the work item already has a rework comment.
"""
import base64, html, json, os, re, subprocess, sys, urllib.error, urllib.parse, urllib.request
from pathlib import Path
from typing import NoReturn

API = "api-version=7.1"
COMMENTS_API = "api-version=7.1-preview.4"   # comments have no stable route
DROP = {"out of scope", "notes"}             # sections that are never submitted


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


def api(url, method="GET", body=None):
    headers = {"Authorization": f"Basic {token()}"}
    data = None
    if body is not None:
        data, headers["Content-Type"] = json.dumps(body).encode(), "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as r:
            return json.loads(r.read().decode() or "{}")
    except urllib.error.HTTPError as e:
        die("token rejected — expired, or missing Work Items (Read & Write)."
            if e.code in (401, 203)
            else f"HTTP {e.code}: {e.read().decode(errors='replace')[:200]}")
    except urllib.error.URLError as e:
        die(f"network error: {e.reason}")


def load():
    """-> (frontmatter, body). Drops HTML comments and developer-only sections."""
    root = subprocess.run(["git", "rev-parse", "--show-toplevel"],
                          capture_output=True, text=True).stdout.strip()
    if not root:
        die("not inside a git repository.")
    path = os.path.join(root, ".sirius", "review.md")
    if not os.path.exists(path):
        die(f"{path} not found.")
    text = open(path).read()

    meta = {}
    if text.startswith("---"):
        end = text.find("\n---", 3)
        for line in text[3:end].splitlines():
            key, sep, value = line.partition(":")
            key, value = key.strip(), value.split("#")[0].strip()
            if sep and value and not key.startswith("#"):
                meta[key] = value
        text = text[end + 4:]

    kept, skip = [], False
    for line in re.sub(r"<!--.*?-->", "", text, flags=re.S).splitlines():
        if line.startswith("## "):
            skip = line[3:].strip().lower() in DROP
        if not skip:
            kept.append(line)
    return meta, re.sub(r"\n{3,}", "\n\n", "\n".join(kept)).strip()


def agent_for(meta, title, agents):
    """Which agent to tag. The frontmatter wins, else the work item's title tag
    ("[FE-01] ..." -> fe-agent). Both are listed in sirius.json."""
    if meta.get("agent"):
        return meta["agent"]
    tag = re.search(r"\[([A-Z]{2})-\d+\]", title)
    if tag and tag.group(1) in agents:
        return agents[tag.group(1)]
    die(f"no agent for {title!r} — add `agent:` to the review.md frontmatter, "
        "or add its tag to sirius.json.")


def main():
    cfg = settings()
    meta, body = load()
    work_item = meta.get("workItem", "")

    if not body:
        die("the review body is empty.")
    if not work_item.isdigit():
        die("no numeric `workItem:` in the review.md frontmatter.")
    if body.startswith("@"):
        die("the body already starts with an @directive — one is added for you.")

    org = cfg["org"].rstrip("/")
    fields = api(f"{org}/_apis/wit/workItems/{work_item}?{API}")["fields"]
    title = fields["System.Title"]
    # Project names may contain spaces ("Sirius - Template"), which urllib
    # rejects in a request path. Both uses below are URLs.
    project = urllib.parse.quote(fields["System.TeamProject"])

    # Without the directive line the comment is inert: Sirius never sees it, so
    # you can post a draft, read it in context, delete it and post again.
    tagged = "--no-tag" not in sys.argv
    directive = cfg["directive"].format(
        agent=agent_for(meta, title, cfg["agents"]),
        gate=meta.get("gate", cfg["gate"])) if tagged else ""
    # Work item comments are stored as HTML, so escape the characters that would
    # otherwise be swallowed. Newlines survive as they are.
    comment = html.escape(f"{directive}\n{body}" if tagged else body, quote=False)

    kind = "comment" if tagged else "DRAFT comment (no agent tagged)"
    print(f"--- {kind} for work item #{work_item}  {title} ---")
    print(comment)
    print("--- end ---\n")

    url = f"{org}/{project}/_apis/wit/workItems/{work_item}/comments?{COMMENTS_API}"

    if "--confirm" not in sys.argv:
        print("Preview only — nothing posted.")
        print("Re-run with --confirm to post it"
              + ("." if not tagged else " and start the rework."))
        return

    if tagged and "--force" not in sys.argv:
        prior = [c for c in api(f"{url}&$top=50").get("comments", [])
                 if directive in c.get("text", "")]
        if prior:
            die("this work item already has a rework comment; posting again starts "
                "a second run. Pass --force if that is what you want.")

    posted = api(url, "POST", {"text": comment})
    print(f"posted comment #{posted['id']}")
    print(f"{org}/{project}/_workitems/edit/{work_item}")
    if not tagged:
        print("No agent tagged — nothing triggered. Delete the comment in Azure "
              "DevOps and re-run without --no-tag when you are happy with it.")


if __name__ == "__main__":
    main()
