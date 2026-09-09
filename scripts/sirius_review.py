#!/usr/bin/env python3
"""Work with the review document, `.sirius/review.md`.

Usage:
    sirius_review.py init     [--force]     scaffold review.md from the template
    sirius_review.py check                  validate it and report problems
    sirius_review.py preview  [--format ..] print the exact comment that would post
    sirius_review.py render   [--format ..] print only the comment body (no banner)

review.md is the interchange format. Anything can write it — Claude Code, a
developer by hand, an IDE, another diff reviewer — and the submit step only
cares about the resulting document. Nothing here touches the network.

Document shape:

    ---
    pr: 41618
    workItem: 96178
    agent: fe-agent          # optional, overrides .sirius/config.json
    gate: ag                 # optional
    ---

    # Sirius PR Review

    ## Required Changes
    ### `src/example.ts:42`
    ...

Level-2 sections named in `excludeSections` (default: Out of Scope, Notes) are
for the developer only and are stripped before submission, as are HTML comments.

Formats (`--format`):
    auto   plain when the body is prose-only, HTML when it contains code (default)
    plain  post verbatim; ADO preserves the newlines
    html   escape everything, <br> for newlines, <pre> for fenced code
"""
import html
import json
import re
import sys
from pathlib import Path

import ado

TEMPLATE = Path(__file__).resolve().parent.parent / "templates" / "review.md"
FENCE = re.compile(r"^\s*```", re.M)
HTML_COMMENT = re.compile(r"<!--.*?-->", re.S)


# --- document parsing -------------------------------------------------------

def review_path():
    return ado.repo_root() / ".sirius" / "review.md"


def split_frontmatter(text):
    """-> (meta dict, body str). Frontmatter is optional."""
    meta = {}
    if not text.startswith("---"):
        return meta, text
    end = text.find("\n---", 3)
    if end == -1:
        return meta, text
    for line in text[3:end].splitlines():
        line = line.strip()
        if not line or line.startswith("#") or ":" not in line:
            continue
        key, _, value = line.partition(":")
        value = value.split("#")[0].strip().strip("'\"")
        if value:
            meta[key.strip()] = value
    body = text[end + 4:]
    return meta, body.lstrip("\n")


def strip_sections(body, excluded):
    """Drop level-2 sections whose heading matches one in `excluded`."""
    if not excluded:
        return body
    wanted = {e.strip().lower() for e in excluded}
    out, skipping, in_fence = [], False, False
    for line in body.splitlines():
        if FENCE.match(line):
            in_fence = not in_fence
        if not in_fence and line.startswith("## "):
            skipping = line[3:].strip().rstrip(":").lower() in wanted
        if not skipping:
            out.append(line)
    return "\n".join(out)


def load(cfg=None):
    """-> (meta, cleaned body). Exits with a clear message if unusable."""
    path = review_path()
    if not path.exists():
        ado.die(f"{path} not found. Run `sirius_review.py init` first.")
    meta, body = split_frontmatter(path.read_text())
    cfg = cfg or ado.config()
    body = HTML_COMMENT.sub("", body)
    body = strip_sections(body, cfg.get("excludeSections"))
    body = re.sub(r"\n{3,}", "\n\n", body).strip()
    return meta, body


def problems(meta, body, cfg):
    """Everything wrong with the document, as a list of human-readable strings."""
    found = []
    if not body:
        found.append("the review body is empty after stripping excluded sections")
    if not meta.get("workItem"):
        found.append("no `workItem:` in the frontmatter — the rework comment has "
                     "nowhere to go (run sirius_context.py to find it)")
    elif not str(meta["workItem"]).isdigit():
        found.append(f"`workItem: {meta['workItem']}` is not a numeric id")
    if meta.get("pr") and not str(meta["pr"]).isdigit():
        found.append(f"`pr: {meta['pr']}` is not a numeric id")
    directive_line = ado.directive(cfg, meta.get("agent"), meta.get("action"),
                                   meta.get("gate"), meta.get("flag"))
    if body.startswith("@"):
        found.append("the body already starts with an @directive — submit adds "
                     f"`{directive_line}` itself, so remove it")
    if re.search(r"(?m)^\s*(TODO|TBD|FIXME|\.\.\.)\s*$", body):
        found.append("the body still contains a placeholder line (TODO/TBD/...)")
    return found


# --- rendering --------------------------------------------------------------

def needs_html(body):
    """Plain text survives ADO intact only if nothing looks like markup."""
    return bool(FENCE.search(body) or re.search(r"[<>]", body))


def esc(s):
    """Escape only &, < and > — quotes are safe in a text node and
    escaping them would leave &#x27; noise for the agent to read."""
    return html.escape(s, quote=False)


def to_html(body):
    """Escaped HTML: <pre> for fenced blocks, <br> for prose newlines."""
    out, buf, in_fence = [], [], False
    for line in body.splitlines():
        if FENCE.match(line):
            if in_fence:
                out.append("<pre>" + esc("\n".join(buf)) + "</pre>")
                buf = []
            in_fence = not in_fence
            continue
        (buf if in_fence else out).append(
            line if in_fence else esc(line) + "<br>")
    if buf:  # unclosed fence — keep the content rather than lose it
        out.append("<pre>" + esc("\n".join(buf)) + "</pre>")
    return "\n".join(out)


def render(meta, body, cfg, fmt="auto"):
    """-> (comment text ready to post, format actually used)."""
    if fmt == "auto":
        fmt = "html" if needs_html(body) else "plain"
    elif fmt not in ("plain", "html"):
        ado.die(f"unknown --format {fmt!r} (auto|plain|html)")
    line = ado.directive(cfg, meta.get("agent"), meta.get("action"),
                         meta.get("gate"), meta.get("flag"))
    if fmt == "html":
        return f"{esc(line)}<br>\n{to_html(body)}", fmt
    return f"{line}\n{body}", fmt


# --- commands ---------------------------------------------------------------

def cmd_init(argv):
    path = review_path()
    if path.exists() and "--force" not in argv:
        ado.die(f"{path} already exists. Edit it, or pass --force to overwrite.")
    if not TEMPLATE.exists():
        ado.die(f"template missing: {TEMPLATE}")
    text = TEMPLATE.read_text()

    ctx_path = ado.repo_root() / ".sirius" / "context.json"
    if ctx_path.exists():
        ctx = json.loads(ctx_path.read_text())
        pr = (ctx.get("pr") or {}).get("id", "")
        wis = ctx.get("workItems") or []
        wi = wis[0]["id"] if wis else ""
        text = (text.replace("pr: ", f"pr: {pr}", 1)
                    .replace("workItem: ", f"workItem: {wi}", 1))
        if pr:
            print(f"prefilled from context.json: pr={pr} workItem={wi or '(none linked)'}")
    else:
        print("no .sirius/context.json — fill in pr/workItem by hand, "
              "or run sirius_context.py first")

    path.parent.mkdir(exist_ok=True)
    path.write_text(text)
    print(f"wrote {path.relative_to(ado.repo_root())}")


def cmd_check(_argv):
    cfg = ado.config()
    meta, body = load(cfg)
    found = problems(meta, body, cfg)
    words = len(body.split())
    print(f"{review_path().relative_to(ado.repo_root())}: "
          f"pr={meta.get('pr', '-')} workItem={meta.get('workItem', '-')} "
          f"{words} words")
    if found:
        print(f"\n{len(found)} problem(s):")
        for p in found:
            print(f"  - {p}")
        sys.exit(1)
    print("ready to submit ✓")


def fmt_arg(argv):
    if "--format" in argv:
        i = argv.index("--format")
        if i + 1 >= len(argv):
            ado.die("--format needs a value (auto|plain|html)")
        return argv[i + 1]
    return "auto"


def cmd_preview(argv):
    cfg = ado.config()
    meta, body = load(cfg)
    text, fmt = render(meta, body, cfg, fmt_arg(argv))
    found = problems(meta, body, cfg)
    print(f"--- would post to work item #{meta.get('workItem', '?')} "
          f"as {fmt} ({len(text)} chars) ---")
    print(text)
    print("--- end ---")
    if found:
        print(f"\n⚠ {len(found)} problem(s) — submit will refuse:")
        for p in found:
            print(f"  - {p}")
        sys.exit(1)


def cmd_render(argv):
    cfg = ado.config()
    meta, body = load(cfg)
    print(render(meta, body, cfg, fmt_arg(argv))[0])


def main():
    argv = sys.argv[1:]
    cmds = {"init": cmd_init, "check": cmd_check,
            "preview": cmd_preview, "render": cmd_render}
    if not argv or argv[0] not in cmds:
        ado.die("usage: sirius_review.py init|check|preview|render [options]")
    cmds[argv[0]](argv[1:])


if __name__ == "__main__":
    main()
