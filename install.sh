#!/usr/bin/env bash
#
# install.sh — link the sirius-* skills into a repo you review in.
#
#   ./install.sh                 # link into the current repo
#   ./install.sh /path/to/repo   # link into another repo
#   ./install.sh --uninstall [/path/to/repo]
#
# Creates symlinks, so `git pull` in this repo updates every repo at once.
# Detects which harnesses the target uses (Claude Code / opencode / pi) and
# links into each, and keeps the working files out of the target's git status.
set -euo pipefail

ROOT="$(cd "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")" && pwd)"
UNINSTALL=0
TARGETS=()
for arg in "$@"; do
  case "$arg" in
    --uninstall) UNINSTALL=1 ;;
    -h|--help) sed -n '2,11p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) TARGETS+=("$arg") ;;
  esac
done
[ ${#TARGETS[@]} -eq 0 ] && TARGETS=("$PWD")

SKILLS=()
for md in "$ROOT"/skills/*/SKILL.md; do
  [ -e "$md" ] || continue
  SKILLS+=("$(dirname "$md")")
done
[ ${#SKILLS[@]} -eq 0 ] && { echo "no skills found in $ROOT/skills" >&2; exit 1; }

# Harness skill dirs, linked when the target already uses that harness or it is
# installed globally.
harness_dir() {
  local target="$1"
  [ -d "$target/.claude" ] || [ -d "$HOME/.claude" ] && echo "$target/.claude/skills"
  [ -d "$target/.opencode" ] || [ -d "$HOME/.config/opencode" ] && echo "$target/.opencode/skills"
  [ -d "$target/.agents" ] || [ -d "$HOME/.pi" ] && echo "$target/.agents/skills"
  return 0
}

for target in "${TARGETS[@]}"; do
  target="$(cd "$target" && pwd)"
  echo "==> $target"
  if [ "$target" = "$ROOT" ]; then
    echo "  (this is sirius-review-tools itself — skills are already here)"
  fi

  while read -r dest; do
    [ -n "$dest" ] || continue
    if [ "$UNINSTALL" = 1 ]; then
      for src in "${SKILLS[@]}"; do
        link="$dest/$(basename "$src")"
        [ -L "$link" ] && { rm -f "$link"; echo "  removed $link"; }
      done
      continue
    fi
    mkdir -p "$dest"
    for src in "${SKILLS[@]}"; do
      link="$dest/$(basename "$src")"
      if [ -L "$link" ] && [ "$(readlink "$link")" = "$src" ]; then continue; fi
      rm -rf "$link"
      ln -s "$src" "$link"
      echo "  linked $(basename "$src") -> $dest"
    done
  done < <(harness_dir "$target")

  [ "$UNINSTALL" = 1 ] && continue

  # Seed config and keep the per-review working files out of git status.
  if [ ! -f "$target/.sirius/config.json" ]; then
    mkdir -p "$target/.sirius"
    cp "$ROOT/config.example.json" "$target/.sirius/config.json"
    echo "  seeded .sirius/config.json — check the agent/gate values"
  fi
  exclude="$target/.git/info/exclude"
  if [ -d "$target/.git" ] && ! grep -qs '^\.sirius/review\.md$' "$exclude"; then
    printf '.sirius/review.md\n.sirius/context.json\n' >> "$exclude"
    echo "  excluded .sirius/review.md + context.json in .git/info/exclude"
  fi
done

echo
echo "Done. Check it works from inside a target repo:  $ROOT/bin/sirius context"
