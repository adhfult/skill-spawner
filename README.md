# skill-spawner

Stop repeating chores by hand. **skill-spawner** is a Claude Code plugin whose skill, `build-project-tool`, reads the project you are in, finds the chores you repeat, and builds a small, tested tool for each one you pick.

It cites the file where it saw each chore, waits for your go-ahead, writes nothing before it, and is built to leave your existing code alone. Every tool it builds comes with its own check, a `docs/tools.md` entry and an `AGENTS.md` line, so the next session finds the tool and runs it instead of redoing the work.

Beta (1.0.3-beta). Issues and feedback are welcome.

## What the evidence shows
Measured on 20 held-out projects written from real "I keep doing X by hand" posts, none of which the skill was tuned on. A session counts as working only if the tool's own check passes, a hidden acceptance test passes, a deliberately broken copy of the tool fails its check, and no protected source file was edited.

- **It builds tools that work.** Claude Sonnet 5.5 produced a working tool in 32 of 40 sessions (80%). Codex reached 14 to 17 of 20 across four models (70 to 85%), and Copilot CLI 15 of 20 (75%).
- **It documents what it builds.** The `AGENTS.md` Commands line was written in all 32 working Sonnet sessions, against 0 of the 12 plain-prompting sessions whose tool passed the hidden test. This is how a later session finds and reuses the tool.
- **It leaves your code alone.** No Sonnet session edited a protected file (0 of 40, against 2 of 20 without the skill).
- **It knows when not to build.** On projects with no repeated chore, it built nothing in 7 of 8 Sonnet sessions and 16 of 16 Haiku sessions.
- **It also builds on harder chores.** On 24 further chores (file renames and merges, CSV reports, and repository checks such as dead doc links or commit-message format), Sonnet delivered a working, documented tool in 31 of 48 sessions (65%) under a scoring rule relaxed after the sessions were read: a tool that exits 1 to report findings no longer fails the hidden test. Under the original rule it was 21 of 48 (44%). These chores were used for tuning afterwards, so read this as a development result.

Use Sonnet 5.5 or better. See "Limits" below for what these numbers do not show.

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
The skill triggers on its own, or you can call it as `/skill-spawner:build-project-tool`.

Without the plugin system, copy `plugins/skill-spawner/skills/build-project-tool/` to `~/.claude/skills/build-project-tool/` and call it as `/build-project-tool`.

To uninstall: `/plugin uninstall skill-spawner@skill-spawner` (and `/plugin marketplace remove skill-spawner` to drop the marketplace), or delete the folder you copied. Tools it already built stay in your project as ordinary files you can remove with git.

### Other agents
The skill is a plain `SKILL.md` folder, so it also works in Codex and Copilot CLI, where it was measured (table below). The install steps below were tested on 2026-10-22 with Codex 0.163, Copilot CLI 1.0.102 and Antigravity 1.4.5; each installs the same `SKILL.md`.

- Codex and Copilot CLI in one command, with Vercel's installer:
  `npx skills@1.7.0 add adhfult/skill-spawner --skill build-project-tool -g -y -a codex -a github-copilot`.
  It copies the skill to `~/.agents/skills/build-project-tool/`, which both read.
- Copilot CLI as a plugin instead: `copilot plugin marketplace add adhfult/skill-spawner`, then `copilot plugin install skill-spawner@skill-spawner`. Use this or the line above, not both.
- Codex by hand: copy `plugins/skill-spawner/skills/build-project-tool/` into `~/.agents/skills/` (all projects) or the project's `.agents/skills/`.
- Antigravity: copy the same folder into `~/.gemini/config/skills/` (all projects) or the project's `.agents/skills/`. The `npx` installer does not reach the global Antigravity folder. Antigravity could not be measured, because its headless mode runs one command per turn.

## Use
Say "build me a tool for this project" or "I keep doing X by hand, make a tool". You can also describe a chore and ask for it now ("I eyeball photos/ for duplicates, find them for me"). It then proposes a dry-run tool for it and waits for your pick, rather than doing the chore once by hand.
Reply with numbers, or "go" for its recommendation. Then check `git status` and `git diff`.

It will not push, deploy, send, delete or install a dependency without asking. Tools that change files, send or delete run as a dry run by default.

### Configure (optional)
Put these lines in your project `AGENTS.md` or global `CLAUDE.md`:
- `build-project-tool: propose N, build M` limits how many tools it proposes and builds.
- `build-project-tool: auto` (experimental) builds the recommended set without the pick, new files only.
- `build-project-tool: index ~/notes/project-tools.md` appends a one-line entry per tool to a global index. Off unless set.

It also follows your own rules in `CLAUDE.md` / `AGENTS.md` (languages, test command, AI setup). Any AI inside a tool uses a local OpenAI-compatible server such as Ollama unless your rules say otherwise, and never a paid API unless you ask.

## Results in full
Held-out set, one clean session per fixture and run, Wilson 95% intervals.

| agent and model | sessions | working | hidden test, also catching broken copies: skill / no skill |
|---|---|---|---|
| Claude Code, Sonnet 5.5 | 40 | 32/40, 80% [0.65-0.90] | 33/40 / 12/20 |
| Claude Code, Haiku 5.5 | 40 | 21/40, 52% [0.37-0.67] | 27/40 / 25/40 |
| Codex, gpt-6.1-sol | 20 | 17/20, 85% [0.64-0.95] | 15/20 / not run |
| Codex, gpt-6-sol | 20 | 17/20, 85% [0.64-0.95] | 18/20 / not run |
| Codex, gpt-6-luna | 20 | 14/20, 70% [0.48-0.85] | 16/20 / not run |
| Codex, gpt-6-astra | 20 | 14/20, 70% [0.48-0.85] | 14/20 / not run |
| Copilot CLI, default model | 20 | 15/20, 75% [0.53-0.89] | 15/20 / not run |

- Against plain prompting, Sonnet's hidden-test pass rate is higher with the skill (33/40 against 12/20), but at this sample size the gap is not statistically clear (p=0.11). Haiku shows no gap (27/40 against 25/40). The clearest measured improvement is documentation, above.
- The two columns test different things, so they need not nest. "Working" needs the tool's own check to catch deliberately broken copies of the tool. The hidden-test column needs the hidden test to pass and also to catch broken copies (at least half of the kinds of breakage applied). For gpt-6.1-sol (17 working, 15 hidden), two tools passed the hidden test, but it caught broken copies of only 2 of 5 kinds, so that column does not count them, while their own checks did catch them.
- Reuse: a fresh session finding and using the tool the first one built succeeded in 15 of 20 Sonnet sessions and 7 of 20 Haiku sessions.
- Negative projects (nothing should be built): Haiku 16/16, Copilot 8/8, gpt-6-luna 8/8, Sonnet 7/8, gpt-6.1-sol 7/8, gpt-6-sol 7/8.
- Cost per session: Sonnet about $0.20, Haiku about $0.014. Codex and Copilot use subscription quota.

How the numbers were produced and what they cannot show: [docs/METHODOLOGY.md](docs/METHODOLOGY.md).

## Limits
- **Use Sonnet 5.5 or better. Haiku 5.5 is not recommended.** On the 24 harder chores it delivered only one session in eight (12 of 96), mostly because the skill did not trigger (it triggered in 20 of 96 sessions, and delivered in 10 of those 20). In 20 of the 96 sessions it edited files it should have left alone, always in sessions where the skill had not triggered, and 15 of the 20 followed a scripted "go ahead" reply. A run without the skill edited protected files in as many sessions, so this is Haiku's behaviour on these prompts rather than something the skill adds, but the skill does not prevent it. On the held-out projects Haiku edited a protected file in 4 of 40 sessions.
- **Check `git status` and `git diff` after every run.** In reuse tests (a fresh session using a tool built earlier, on development fixtures, Sonnet and Haiku), 6 of 48 sessions edited protected files. The skill reports any edit to an existing file (`EDITED EXISTING FILE`), but that is a report, not a lock.
- **Secrets are protected by an instruction, not a lock.** Add a real deny rule to your agent. For Claude Code, in `~/.claude/settings.json`: `{"permissions": {"deny": ["Read(./.env)", "Read(./.env.*)"]}}`. In the tests no planted key ever appeared in the output of a tool the skill built. In about one Haiku reuse session in ten, the model itself printed it into the transcript with a `cat` or `git show`; Sonnet sessions never did.
- **A repo you did not write can name the tool it runs.** When `docs/tools.md` or `AGENTS.md` already lists a tool for the chore, the skill runs it without a pick. Since 1.0.3 it first checks the command: it runs project code (`python3 tools/x.py`, `npm run x`, `make x`) as before, but if the command fetches code from the network, pipes into a shell, uses `sudo` or runs a file outside the project, it shows the command and asks. This does not stop a hostile repo that puts its payload inside an in-project script, and it applies only when the skill runs, not when an agent follows an `AGENTS.md` line on its own. In a repo you cloned, read `docs/tools.md` and `AGENTS.md` before saying "do the chore". The results above were measured on the 1.0.2 text. The 1.0.3 change was measured on reuse only: 8 of 16 reuse sessions against 10 of 16 for 1.0.2 in a same-day run on development fixtures (n=16 shows only a large drop). It asked instead of running in 2 of 2 hostile test repos, where 1.0.2 tried to run the command in both, and still ran an in-project `npm run` tool without asking (one session each).
- **Small samples.** Twenty held-out projects, one or two runs per agent, with fixtures written by a model. The intervals above are wide, and the 24-chore result is not a clean held-out test.
- **The test harness and fixtures (about 46 MB) are not in this repository**, so the numbers cannot be re-run from here.
- Codex sessions ran with the author's global rules loaded, so they are not clean-environment runs.

## Repo layout
- `plugins/skill-spawner/skills/build-project-tool/SKILL.md`: the skill.
- `.claude-plugin/marketplace.json`, `plugins/skill-spawner/.claude-plugin/plugin.json`: manifests.
- `docs/METHODOLOGY.md`: how it was tested.

## Contact and license
Issues and feedback: GitHub Issues on this repository.

MIT, see `LICENSE`. Copyright (c) 2026 adhfult.
