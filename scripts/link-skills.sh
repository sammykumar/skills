#!/usr/bin/env bash
set -euo pipefail

# NOTE: This is a dev-only script, intended for use by maintainers of this repo.
# It is not a supported installer.
#
# Links the repository's skills into the local skill directories used by each
# agent harness. Each entry is a symlink into this repo, so a `git pull` is all
# that's needed to keep them current.
#
# Claude Code gets the promoted skills (engineering/, productivity/) from the
# published sk-skills plugin at user scope. Linking those into ~/.claude/skills
# as well would give every repo two copies of each one, a release-pinned copy
# and a working-tree copy, with no way to tell which is running. So they are
# linked into this repo's own .claude/skills/ instead, scoping the dogfooding to
# the repo doing the dogfooding:
#
#   - <repo>/.claude/skills: promoted skills, Claude Code, this repo only
#   - ~/.claude/skills:      non-promoted skills, Claude Code, everywhere
#   - ~/.agents/skills:      every skill, Codex, everywhere when Codex has no SK Skills plugin

REPO="$(cd "$(dirname "$0")/.." && pwd)"

is_promoted() {
  case "$1" in
    "$REPO"/skills/engineering/* | "$REPO"/skills/productivity/*) return 0 ;;
    *) return 1 ;;
  esac
}

codex_sk_skills_plugin_enabled() {
  local config="$HOME/.codex/config.toml"
  [ -f "$config" ] || return 1
  awk '
    /^\[plugins\."sk-skills@sammykumar"\]$/ { in_plugin = 1; next }
    in_plugin && /^enabled[[:space:]]*=[[:space:]]*true[[:space:]]*$/ { enabled = 1; exit }
    in_plugin && /^\[/ { exit }
    END { exit(enabled ? 0 : 1) }
  ' "$config"
}

# Collect the repo's skills once, link into every destination.
names=()
srcs=()
while IFS= read -r -d '' skill_md; do
  src="$(dirname "$skill_md")"
  names+=("$(basename "$src")")
  srcs+=("$src")
done < <(find "$REPO/skills" -name SKILL.md -not -path '*/node_modules/*' -not -path '*/deprecated/*' -print0)

# Each destination takes one of four slices: promoted, non-promoted, all, or
# skipped when Codex already receives these skills from its plugin.
for DEST in "$REPO/.claude/skills" "$HOME/.claude/skills" "$HOME/.agents/skills"; do
  case "$DEST" in
    "$REPO"/*) want="promoted" ;;
    "$HOME/.claude/skills") want="other" ;;
    *) want="all" ;;
  esac
  if [ "$DEST" = "$HOME/.agents/skills" ] && codex_sk_skills_plugin_enabled; then
    want="skip"
  fi

  # If $DEST is a symlink that resolves into this repo, we'd end up writing the
  # per-skill symlinks back into the repo's own skills/ tree. Detect and bail
  # out instead of polluting the working copy. The repo's own .claude/skills is
  # a real directory we create, so it is exempt.
  if [ -L "$DEST" ] && [ "$want" != "promoted" ]; then
    resolved="$(readlink -f "$DEST")"
    case "$resolved" in
      "$REPO" | "$REPO"/*)
        echo "error: $DEST is a symlink into this repo ($resolved)." >&2
        echo "Remove it (rm \"$DEST\") and re-run; the script will recreate it as a real dir." >&2
        exit 1
        ;;
    esac
  fi

  mkdir -p "$DEST"

  if [ "$want" = "skip" ]; then
    for target in "$DEST"/*; do
      [ -L "$target" ] || continue
      case "$(readlink "$target")" in
        "$REPO"/*)
          rm "$target"
          echo "unlinked $(basename "$target") (now served by the Codex SK Skills plugin)"
          ;;
      esac
    done
    continue
  fi

  # The repo-local directory should hold the promoted set and nothing else, so
  # prune our own symlinks that have gone stale: a skill that was renamed, one
  # that left a promoted bucket, or a non-promoted skill that user scope now
  # serves everywhere. Anything that is not our symlink is left alone.
  if [ "$want" = "promoted" ]; then
    for target in "$DEST"/*; do
      [ -L "$target" ] || continue
      resolved="$(readlink -f "$target" 2>/dev/null || true)"
      if [ -z "$resolved" ] || [ ! -d "$resolved" ]; then
        rm "$target"
        echo "pruned $(basename "$target") (dangling symlink)"
      elif ! is_promoted "$resolved"; then
        rm "$target"
        echo "pruned $(basename "$target") (not a promoted skill)"
      fi
    done
  fi

  for i in "${!names[@]}"; do
    name="${names[$i]}"
    src="${srcs[$i]}"
    target="$DEST/$name"

    if [ "$want" = "promoted" ] && ! is_promoted "$src"; then
      continue
    fi
    if [ "$want" = "other" ] && is_promoted "$src"; then
      # Previously linked here, now served by the plugin. Remove our own stale
      # symlink so the skill has exactly one source, and leave anything else be.
      if [ -L "$target" ]; then
        case "$(readlink "$target")" in
          "$REPO"/*)
            rm "$target"
            echo "unlinked $name (now served by the sk-skills plugin)"
            ;;
        esac
      fi
      continue
    fi

    if [ -e "$target" ] && [ ! -L "$target" ]; then
      rm -rf "$target"
    fi

    ln -sfn "$src" "$target"
    echo "linked $name -> $src ($DEST)"
  done
done
