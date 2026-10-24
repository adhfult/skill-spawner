# skill-spawner

A Claude Code plugin with one skill, `skill-spawner` (`plugins/skill-spawner/skills/skill-spawner/SKILL.md`).
See `README.md` for install, measured results and limits.

## Rules for agents editing this repo
- Do not change `SKILL.md` behaviour without measuring it; the README says which skill version each number was measured on.
- Validate: `claude plugin validate .` and `claude plugin validate ./plugins/skill-spawner`. These check the plugin's structure, not the behaviour of the tools it builds. If you have the skill-creator skill installed, its `quick_validate.py` also checks `plugins/skill-spawner/skills/skill-spawner`.
- The skill must not set `disable-model-invocation`: it has to trigger from its description.
- `evals/` is a copy of the private development harness plus six fixtures. Run it as `evals/README.md` says; it spends real money, so pass `--budget`.
- Never read, print or commit secrets. Plain writing in docs: no em dashes, no filler.
