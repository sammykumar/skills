---
"sk-skills": minor
---

New `/update-sk-skills` skill: update the skills on this machine without having to remember how you installed them. It detects the route from the evidence on disk (an `sk-skills@<marketplace>` entry in Claude Code's installed-plugins record, a lockfile entry sourced from `sammykumar/skills` at either scope, or a skill directory symlinked into a dev checkout), reports what it found and the exact commands it proposes, then runs the matching update. It stops rather than acting when the two routes coexist, since a machine carrying both has every skill twice with no way to tell which one is running.
