#!/usr/bin/env python3
"""Post .sirius/review.md to its work item as one comment tagging Sirius.

Usage:  submit.py [--confirm] [--force]

Prints the exact comment and posts nothing unless --confirm is given.
--force posts even if the work item already has a rework comment.
"""
import base64, html, json, os, re, subprocess, sys, urllib.error, urllib.request
from pathlib import Path
from typing import NoReturn

API = "api-version=7.1"
COMMENTS_API = "api-version=7.1-preview.4"   # comments have no stable route
DIRECTIVE = "@{agent};rework;yes;{gate};"   # edit here if Sirius changes format
AGENTS = {"FE": "fe-agent", "BE": "be-agent"}   # keyed by the work item title tag
GATE = "ag"                                 # ag agent, hg human, kg knowledge graph
DROP = {"out of scope", "notes"}            # sections that are never submitted


def die(msg) -> NoReturn:
    sys.exit(f"error: {msg}")


def env(key, default=""):
    """Environment, else a .env file in this skill or any parent directory."""
    if os.environ.get(key):
        return os.environ[key]
    for d in [Path(__file__).resolve().parent] + list(Path(__file__).resolve().parents):
        f = d / ".env"
        if f.exists():
            for line in f.read_text().splitlines():
                k, sep, v = line.partition("=")
                if sep and k.strip() == key:
                    return v.strip().strip("'\"")
    return default


def api(url, method="GET", body=None):
    pat = env("AZURE_DEVOPS_PAT") or env("AZURE_DEVOPS_EXT_PAT")
    if not pat:
        die("no PAT — set AZURE_DEVOPS_PAT in .env (see .env.example).")
    token = base64.b64encode(f":{pat}".encode()).decode()
    headers = {"Authorization": f"Basic {token}"}
    data = None
    if body is not None:
        data, headers["Content-Type"] = json.dumps(body).encode(), "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as r:
            return json.loads(r.read().decode() or "{}")
    except urllib.error.HTTPError as e:
        die("PAT rejected — expired or missing Work Items (Read & Write)."
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


def agent_for(meta, title):
    """Which agent to tag. The frontmatter wins, else the work item's title
    tag: [FE-01] is the frontend agent, [BE-01] the backend one."""
    if meta.get("agent"):
        return meta["agent"]
    tag = re.search(r"\[(FE|BE)-\d+\]", title)
    if tag:
        return AGENTS[tag.group(1)]
    die(f"cannot tell which agent to tag from {title!r} — add "
        "`agent: fe-agent` or `agent: be-agent` to the review.md frontmatter.")


def main():
    meta, body = load()
    work_item = meta.get("workItem", "")

    if not body:
        die("the review body is empty.")
    if not work_item.isdigit():
        die("no numeric `workItem:` in the review.md frontmatter.")
    if body.startswith("@"):
        die("the body already starts with an @directive — one is added for you.")

    org = env("AZURE_DEVOPS_ORG", "https://thenbs.visualstudio.com/").rstrip("/")
    fields = api(f"{org}/_apis/wit/workItems/{work_item}?{API}")["fields"]
    title, project = fields["System.Title"], fields["System.TeamProject"]

    directive = DIRECTIVE.format(agent=agent_for(meta, title),
                                 gate=meta.get("gate", GATE))
    # Work item comments are stored as HTML, so escape the characters that would
    # otherwise be swallowed. Newlines survive as they are.
    comment = html.escape(f"{directive}\n{body}", quote=False)

    print(f"--- comment for work item #{work_item}  {title} ---")
    print(comment)
    print("--- end ---\n")

    url = f"{org}/{project}/_apis/wit/workItems/{work_item}/comments?{COMMENTS_API}"

    if "--confirm" not in sys.argv:
        print("Preview only — nothing posted.")
        print("Re-run with --confirm to post it and start the rework.")
        return

    if "--force" not in sys.argv:
        prior = [c for c in api(f"{url}&$top=50").get("comments", [])
                 if directive in c.get("text", "")]
        if prior:
            die("this work item already has a rework comment; posting again starts "
                "a second run. Pass --force if that is what you want.")

    posted = api(url, "POST", {"text": comment})
    print(f"posted comment #{posted['id']}")
    print(f"{org}/{project}/_workitems/edit/{work_item}")


if __name__ == "__main__":
    main()
