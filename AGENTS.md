# skill-spawner

A Claude Code plugin with one skill, `build-project-tool` (`plugins/skill-spawner/skills/build-project-tool/SKILL.md`).
See `README.md` for install, measured results and limits.

## Rules for agents editing this repo
- Do not change `SKILL.md` behaviour without measuring it; the README says which skill version each number was measured on.
- Validate: `claude plugin validate .` and `claude plugin validate ./plugins/skill-spawner`. These check the plugin's structure, not the behaviour of the tools it builds. If you have the skill-creator skill installed, its `quick_validate.py` also checks `plugins/skill-spawner/skills/build-project-tool`.
- The skill must not set `disable-model-invocation`: it has to trigger from its description.
- Never read, print or commit secrets. Plain writing in docs: no em dashes, no filler.
