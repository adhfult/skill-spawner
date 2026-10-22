# skill-spawner

A Claude Code plugin with one skill, `build-project-tool` (`plugins/skill-spawner/skills/build-project-tool/SKILL.md`).
See `README.md` for install, measured results and limits.

## Rules for agents editing this repo
- Do not change `SKILL.md` behaviour without measuring it; the README says which skill version each number was measured on.
- Validate: `claude plugin validate .`, and `quick_validate.py` from the skill-creator skill on `plugins/skill-spawner/skills/build-project-tool`.
- The skill must not set `disable-model-invocation`: it has to trigger from its description.
- Never read, print or commit secrets. Plain writing in docs: no em dashes, no filler.
