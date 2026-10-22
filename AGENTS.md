# skill-spawner

A Claude Code plugin with one skill, `skill-spawner` (`plugins/skill-spawner/skills/skill-spawner/SKILL.md`).
See `README.md` for install, measured results and limits.

## Rules for agents editing this repo
- Do not change `SKILL.md` behaviour without measuring it; the README numbers are for the shipped text.
- Validate: `claude plugin validate .`, and `quick_validate.py` from the skill-creator skill on `plugins/skill-spawner/skills/skill-spawner`.
- The skill must not set `disable-model-invocation`: it has to trigger from its description.
- Never read, print or commit secrets. Plain writing in docs: no em dashes, no filler.
