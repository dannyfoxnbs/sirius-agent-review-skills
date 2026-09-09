#!/usr/bin/env python3
"""Shared Azure DevOps plumbing for sirius-review-tools.

Stdlib only, no third-party deps. Every helper script imports this.

Auth: a Personal Access Token from $AZURE_DEVOPS_EXT_PAT or
~/.config/azure-devops/pat (chmod 600); override the path with ADO_PAT_FILE.
Scopes needed: Code (Read) to read PRs and threads, Work Items (Read & Write)
to read a PBI and post the consolidated review comment.

Config: `.sirius/config.json` at the repo root, if present. Every key is
optional and falls back to an env var, then a default. See config.example.json.
"""
import base64
import html
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

API = "api-version=7.1"
# Work item comments live on a preview route even in 7.1.
COMMENTS_API = "api-version=7.1-preview.4"

DEFAULTS = {
    "org": "https://thenbs.visualstudio.com/",
    "project": None,          # discovered from the git remote when unset
    "repo": None,             # discovered from the git remote when unset
    # Sirius rework directive. Rendered with the fields below.
    "directive": "@{agent};{action};{flag};{gate};",
    "agent": "fe-agent",      # be-agent for backend work
    "action": "rework",
    "flag": "yes",
    "gate": "ag",             # ag = agent gate, hg = human gate, kg = knowledge graph
    # review.md sections that are for the developer only and never submitted.
    "excludeSections": ["Out of Scope", "Notes"],
}


def die(msg):
    sys.exit(f"error: {msg}")


# --- repo / config ----------------------------------------------------------

def git(*args, cwd=None):
    """Run a git command, returning stripped stdout ('' on failure)."""
    p = subprocess.run(("git",) + args, capture_output=True, text=True, cwd=cwd)
    return p.stdout.strip() if p.returncode == 0 else ""


def repo_root():
    root = git("rev-parse", "--show-toplevel")
    if not root:
        die("not inside a git repository.")
    return Path(root)


def sirius_dir():
    d = repo_root() / ".sirius"
    d.mkdir(exist_ok=True)
    return d


def config():
    """Merged config: defaults < .sirius/config.json < environment."""
    cfg = dict(DEFAULTS)
    path = repo_root() / ".sirius" / "config.json"
    if path.exists():
        try:
            cfg.update(json.loads(path.read_text()))
        except json.JSONDecodeError as e:
            die(f"{path}: invalid JSON — {e}")
    for key, env in (("org", "ADO_ORG"), ("project", "ADO_PROJECT"),
                     ("repo", "ADO_REPO"), ("agent", "SIRIUS_AGENT"),
                     ("gate", "SIRIUS_GATE")):
        if os.environ.get(env):
            cfg[key] = os.environ[env]
    cfg["org"] = str(cfg["org"]).rstrip("/")
    if not cfg.get("project") or not cfg.get("repo"):
        project, repo = remote_project_repo()
        cfg["project"] = cfg.get("project") or project
        cfg["repo"] = cfg.get("repo") or repo
    return cfg


def remote_project_repo():
    """Parse project + repo out of the origin remote URL.

    Handles both host styles in use: thenbs.visualstudio.com/<project>/_git/<repo>
    and dev.azure.com/<org>/<project>/_git/<repo>.
    """
    url = git("remote", "get-url", "origin")
    m = re.search(r"/([^/]+)/_git/([^/]+?)(?:\.git)?/?$", url)
    if not m:
        return None, None
    return urllib.parse.unquote(m.group(1)), urllib.parse.unquote(m.group(2))


def directive(cfg, agent=None, action=None, gate=None, flag=None):
    """The literal first line that tags Sirius, e.g. '@fe-agent;rework;yes;ag;'."""
    return cfg["directive"].format(
        agent=agent or cfg["agent"], action=action or cfg["action"],
        flag=flag or cfg["flag"], gate=gate or cfg["gate"])


# --- auth / http ------------------------------------------------------------

def load_pat(scope="Code (Read)"):
    pat_file = Path(os.environ.get(
        "ADO_PAT_FILE", Path.home() / ".config" / "azure-devops" / "pat")).expanduser()
    pat = (os.environ.get("AZURE_DEVOPS_EXT_PAT")
           or (pat_file.read_text() if pat_file.exists() else "")).strip()
    if not pat:
        die(f"no PAT. Set $AZURE_DEVOPS_EXT_PAT or write one to {pat_file} "
            f"(chmod 600). Needs the '{scope}' scope.")
    return pat


class ApiError(Exception):
    pass


def request(url, pat, method="GET", body=None):
    token = base64.b64encode(f":{pat}".encode()).decode()
    headers = {"Authorization": f"Basic {token}", "Accept": "application/json"}
    data = None
    if body is not None:
        data = json.dumps(body).encode()
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as r:
            raw = r.read().decode()
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        if e.code in (401, 203):
            raise ApiError("PAT rejected — expired or missing the required scope.")
        if e.code == 404:
            raise ApiError(f"not found (404): {url}")
        raise ApiError(f"HTTP {e.code}: {e.read().decode(errors='replace')[:300]}")
    except urllib.error.URLError as e:
        raise ApiError(f"network error: {e.reason}")


def get(url, pat):
    try:
        return request(url, pat)
    except ApiError as e:
        die(str(e))


# --- text -------------------------------------------------------------------

def to_text(s):
    """ADO stores comment bodies as HTML; flatten to plain text."""
    if not s:
        return ""
    s = re.sub(r"<\s*(br|/p|/div|/li|/tr)\s*/?>", "\n", s, flags=re.I)
    s = re.sub(r"<\s*li\s*>", "- ", s, flags=re.I)
    s = html.unescape(re.sub(r"<[^>]+>", "", s))
    s = s.replace("\xa0", " ")
    return re.sub(r"\n{3,}", "\n\n", s).strip()
