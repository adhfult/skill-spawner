# skill-spawner

Turns a chore you repeat into a small, tested tool that future AI sessions know how to reuse.

You tell your coding agent "I keep doing X by hand". skill-spawner reads the project, proposes a tool with the evidence for it, waits for your pick, then builds the tool with its own check and writes it into `docs/tools.md` and `AGENTS.md`. The next session reads that line and runs the tool instead of solving the chore again. The name: it spawns tools (and, when a chore needs judgment, a project-local skill) from the work you keep repeating.

Beta (1.0.5-beta), for Claude Code with Sonnet 5.5 or better. Issues and feedback are welcome.

## Example
Request, on a fixture project: "photos/ has the same pictures saved under different names and I eyeball them to find duplicates. can you find the identical ones for me"

```
Detect
- Stack: Python 3, stdlib only.
- Test command: none.
- Constraints: don't edit `album.py`, never read or commit secrets, and keep commits small.
- Repeated manual work: you eyeball `photos/` for duplicates (your words). `photos/` has 6 files, and `album.py:3` only lists their names.
Proposal
1. `dupes.py` finds identical photos by hashing file contents (SHA-256), so renamed copies are caught. Evidence: "I eyeball them to find duplicates". It prints groups of identical files and is read-only, so it is a dry run by nature. It adds `dupes.py` with a `--self-test` flag, plus `docs/tools.md`.
I recommend 1. I'll also add a line to the Commands section of `AGENTS.md`. Say no to skip. Pick one or more numbers, or say go for my recommendation.
```

After "go" it wrote `dupes.py` and ran `python3 dupes.py --self-test` (passing, including a missing-folder failure case). It then found the duplicate groups. `git status` showed only the new files plus the `AGENTS.md` line; `album.py` was untouched.

## Install
In Claude Code:

```
/plugin marketplace add adhfult/skill-spawner
/plugin install skill-spawner@skill-spawner
```

Or in one step on Claude Code 2.1.275+: `/plugin install skill-spawner --marketplace adhfult/skill-spawner`.
The skill triggers on its own, or you can call it as `/skill-spawner:skill-spawner`. Already installed: `/plugin marketplace update skill-spawner`, then `/plugin update skill-spawner@skill-spawner`, and restart Claude Code.

Without the plugin system, copy `plugins/skill-spawner/skills/skill-spawner/` to `~/.claude/skills/skill-spawner/` and call it as `/skill-spawner`.

To uninstall: `/plugin uninstall skill-spawner@skill-spawner` (and `/plugin marketplace remove skill-spawner` to drop the marketplace), or delete the folder you copied. Tools it already built stay in your project as ordinary files you can remove with git.

### Other agents
The skill is a plain `SKILL.md` folder, so it also works in Codex and Copilot CLI, where it was measured (table below). The install steps below were tested on 2026-10-22 with Codex 0.163, Copilot CLI 1.0.102 and Antigravity 1.4.5; each installs the same `SKILL.md`.

- Codex and Copilot CLI in one command, with Vercel's installer:
  `npx skills@1.7.0 add adhfult/skill-spawner --skill skill-spawner -g -y -a codex -a github-copilot`.
  It copies the skill to `~/.agents/skills/skill-spawner/`, which both read.
- Copilot CLI as a plugin instead: `copilot plugin marketplace add adhfult/skill-spawner`, then `copilot plugin install skill-spawner@skill-spawner`. Use this or the line above, not both.
- Codex by hand: copy `plugins/skill-spawner/skills/skill-spawner/` into `~/.agents/skills/` (all projects) or the project's `.agents/skills/`.
- Antigravity: copy the same folder into `~/.gemini/config/skills/` (all projects) or the project's `.agents/skills/`. The `npx` installer does not reach the global Antigravity folder. Antigravity could not be measured, because its headless mode runs one command per turn.

## Use
Say "build me a tool for this project" or "I keep doing X by hand, make a tool". You can also describe a chore and ask for it now ("I eyeball photos/ for duplicates, find them for me"). It then proposes a dry-run tool for it and waits for your pick, rather than doing the chore once by hand.
Reply with numbers, or "go" for its recommendation. Then check `git status` and `git diff`.

It will not push, deploy, send, delete or install a dependency without asking. Tools that change files, send or delete run as a dry run by default.

### Configure (optional)
Put these lines in your project `AGENTS.md` or global `CLAUDE.md` (lines set before 1.0.5 need the `skill-spawner:` prefix):
- `skill-spawner: propose N, build M` limits how many tools it proposes and builds.
- `skill-spawner: auto` (experimental) builds the recommended set without the pick, new files only.
- `skill-spawner: index ~/notes/project-tools.md` appends a one-line entry per tool to a global index. Off unless set.

It also follows your own rules in `CLAUDE.md` / `AGENTS.md` (languages, test command, AI setup). Any AI inside a tool uses a local OpenAI-compatible server such as Ollama unless your rules say otherwise, and never a paid API unless you ask.

## What the evidence shows
Measured on 20 held-out projects written from real "I keep doing X by hand" posts, none of which the skill was tuned on. A session counts as working only if the tool's own check passes, a hidden acceptance test passes, a deliberately broken copy of the tool fails its check, and no protected source file was edited.

- **Most of these numbers were measured on the 1.0.2 text.** The current text (1.0.5) scored 16 of 20 working on the same held-out set in one run (1.0.4: 15 of 20; 1.0.2: 32 of 40 in two runs).
- **It builds tools that work.** Claude Sonnet 5.5 produced a working tool in 32 of 40 sessions (80%). Codex reached 14 to 17 of 20 across four models (70 to 85%), and Copilot CLI 15 of 20 (75%).
- **It documents what it builds.** The `AGENTS.md` Commands line was written in all 32 working Sonnet sessions, against 0 of the 12 plain-prompting sessions whose tool passed the hidden test. That plain prompt did not ask for documentation, so this shows the skill adds the step, not that a well-worded prompt could not.
- **Later sessions reuse the tool.** On 1.0.5, a fresh session asked for the same chore ran the tool the first one built in 20 of 20 held-out projects (in the test setup, whose system prompt named the skill in both sessions).
- **A good rule in `CLAUDE.md` gets close.** Against a strong standing rule with no skill (check `docs/tools.md` for an existing tool, else write one script with a self-check, document it, add an `AGENTS.md` line), 1.0.5 passed the hidden test in 18 of 20 projects against 14 of 20, and the fresh session reused the tool in 20 of 20 against 19 of 20. The correctness gap is not statistically clear (p=0.24). The skill also waits for your pick before writing anything (the rule wrote first in all 20) and printed no planted key (the rule's sessions printed one, once), but it cost about 45% more per chore ($0.27 against $0.19, both sessions) and adds one turn. If you only want reuse, that rule is a fair alternative.
- **It leaves your code alone.** No Sonnet session edited a protected file (0 of 40, against 2 of 20 without the skill).
- **It knows when not to build.** On projects with no repeated chore, it built nothing in 7 of 8 Sonnet sessions and 16 of 16 Haiku sessions.
- **Against plain prompting**, Sonnet's hidden-test pass rate is higher with the skill (33/40 against 12/20), but at this sample size the gap is not statistically clear (p=0.11).

### Results in full
Held-out set, one clean session per fixture and run, Wilson 95% intervals, skill text 1.0.2.

| agent and model | sessions | working | hidden test, also catching broken copies: skill / no skill |
|---|---|---|---|
| Claude Code, Sonnet 5.5 | 40 | 32/40, 80% [0.65-0.90] | 33/40 / 12/20 |
| Claude Code, Haiku 5.5 | 40 | 21/40, 52% [0.37-0.67] | 27/40 / 25/40 |
| Codex, gpt-6.1-sol | 20 | 17/20, 85% [0.64-0.95] | 15/20 / not run |
| Codex, gpt-6-sol | 20 | 17/20, 85% [0.64-0.95] | 18/20 / not run |
| Codex, gpt-6-luna | 20 | 14/20, 70% [0.48-0.85] | 16/20 / not run |
| Codex, gpt-6-astra | 20 | 14/20, 70% [0.48-0.85] | 14/20 / not run |
| Copilot CLI, default model | 20 | 15/20, 75% [0.53-0.89] | 15/20 / not run |

- The two columns test different things, so they need not nest. "Working" needs the tool's own check to catch deliberately broken copies of the tool. The hidden-test column needs the hidden test to pass and also to catch broken copies (at least half of the kinds of breakage applied).
- On 24 harder chores (file renames and merges, CSV reports, repository checks), Sonnet delivered a working, documented tool in 31 of 48 sessions (65%) under a scoring rule relaxed after the sessions were read (21 of 48 under the original rule). These chores were used for tuning afterwards, so read this as a development result.
- Negative projects (nothing should be built): Haiku 16/16, Copilot 8/8, gpt-6-luna 8/8, Sonnet 7/8, gpt-6.1-sol 7/8, gpt-6-sol 7/8.
- Cost per session: Sonnet about $0.20, Haiku about $0.014. Codex and Copilot use subscription quota.

How the numbers were produced, what changed in each version and what the numbers cannot show: [docs/METHODOLOGY.md](docs/METHODOLOGY.md).

## Limits
- **Use Sonnet 5.5 or better. Haiku 5.5 is not recommended.** On the 24 harder chores it delivered only one session in eight (12 of 96), mostly because the skill did not trigger (20 of 96). In 20 of the 96 sessions it edited files it should have left alone, always in sessions where the skill had not triggered; a run without the skill did the same, so the skill does not cause it, but it does not prevent it either.
- **Check `git status` and `git diff` after every run.** In reuse tests, 6 of 48 sessions edited protected files. The skill compares `git status` and per-file line counts with a snapshot taken at the start and reports any edit to an existing file (`EDITED EXISTING FILE`), but that is a report, not a lock. A second edit to a file you had already changed is missed if it leaves the line counts identical.
- **Secrets are protected by an instruction, not a lock.** Add a real deny rule to your agent. For Claude Code, in `~/.claude/settings.json`: `{"permissions": {"deny": ["Read(./.env)", "Read(./.env.*)"]}}`. In the tests no planted key ever appeared in the output of a tool the skill built. In about one Haiku reuse session in ten, the model itself printed it into the transcript; Sonnet sessions never did.
- **A repo you did not write can name the tool it runs.** When `docs/tools.md` or `AGENTS.md` already lists a tool for the chore, the skill runs it without a pick, after reading the tool's file. If the command fetches code from the network, pipes into a shell, uses `sudo` or runs a file outside the project, it shows the command and asks. This does not stop a hostile repo that hides its payload inside an in-project script. In a repo you cloned, read `docs/tools.md` and `AGENTS.md` before saying "do the chore".
- **Small samples.** Twenty held-out projects, one or two runs per agent, with fixtures written by a model. The intervals above are wide.
- **The held-out set and most fixtures are not in this repository**, so the main numbers cannot be re-run from here. A small regression set with the harness that scored it is in [`evals/`](evals/README.md), so you can check the skill's behaviour yourself.
- Codex sessions ran with the author's global rules loaded, so they are not clean-environment runs.

## Repo layout
- `plugins/skill-spawner/skills/skill-spawner/SKILL.md`: the skill.
- `.claude-plugin/marketplace.json`, `plugins/skill-spawner/.claude-plugin/plugin.json`: manifests.
- `docs/METHODOLOGY.md`: how it was tested, and what changed in each version.
- `evals/`: a small test set you can run, with the harness that scored it.

## Contact and license
Issues and feedback: GitHub Issues on this repository.

MIT, see `LICENSE`. Copyright (c) 2026 adhfult.
