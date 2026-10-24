# How skill-spawner was tested

This page says how the numbers in the README were produced, what went wrong along the way, and what they cannot show.
The held-out set and most fixtures are kept in a private development repository, so the main results cannot be re-run from here. Six regression fixtures and the harness that scores them are in `evals/` ([how to run them](../evals/README.md)).

## What "working" means
A session counts as **working** only if all of these hold, judged by code the model never sees:
1. The tool's own check (the `check:` line it wrote in `docs/tools.md`) passes.
2. A hidden acceptance test, written per fixture, passes on the tool's documented command.
3. Mutating the tool (comparison flip, boolean constant, off-by-one, logic swap, early return) makes its own check fail, so the check tests something.
4. No protected file (the fixture's own code) was edited.

The no-skill control has no `check:` lines, so it is scored on the hidden test alone.

## The test sets
- **Development fixtures** (68). The skill was tuned on these, so results on them likely overstate performance on new projects.
- **Held-out set** (20 projects). Written from real "I keep doing X by hand" posts and frozen before the measured runs. The skill was never changed
  in response to them, and failures on it were counted, not read.
- **Negative projects** (8). A one-off ask, or a repository with no repeated chore. Passing means nothing was built.
- **Harder chores** (24). A later set, scored with the same bar except that the hidden test accepts an exit status of 1 when the tool crashed nowhere. That rule was chosen after the sessions were read, and the set was used for tuning afterwards, so it is a development result.

## Safeguards
- A **no-skill control** with the same prompts, replies and scoring. Without it, nobody knows whether the skill adds anything.
- **Hidden tests hardened**: a tool that only echoes every input file passed 44 of 61 early tests. After tightening, it passes 0 of 61.
- **Sandboxed scoring**: model-written code runs under `bwrap` with no network and a throwaway home folder.
- **Canaries**: fake secrets planted in each fixture, and a file outside the work folder, to catch leaks and stray writes.
- **Wilson 95% intervals** on the main results table.
- **Outside review**: five other models reviewed the first claim, and a later review re-derived every headline number from the raw results.

## What went wrong, and how it was found
1. **An early "about 95% working" figure was overfit.** It came from fixtures the skill had been tuned on. On the held-out set the same skill scores 80% (Sonnet 5.5) and 52% (Haiku 5.5). The outside reviews asked for a held-out set, which exposed it.
2. **The first tests were too easy.** The echo-everything tool above passed most of them. A deliberate "no-op check" found it, and the tests were tightened.
3. **The skill had not been compared with plain prompting.** The control showed a clear gain only in documentation; the gain in working tools is not statistically clear.
4. **A tidy-looking change made things worse.** Splitting the skill into a short core plus a reference file led Haiku to skip the documenting step (0 working tools in 35 sessions). It was reverted to one file.
5. **A guess instead of a measurement.** A first write-up said the control had been scored too harshly. Rescoring the affected sessions moved one result, and the gap shrank from p=0.03 to p=0.11. The README carries the corrected number.
6. **Contamination.** Codex sessions read the author's global rules, so they were not clean-environment runs. Antigravity's headless mode runs one command per turn and soft-denies commands outside an allow list, so it cannot be measured with this harness.

## Changes by version, and what each was measured on
The README's main table was measured on the 1.0.2 text.

- **1.0.3** adds a guard to the reuse step. When a project already names a tool for the chore, the skill runs project code (`python3 tools/x.py`, `npm run x`, `make x`) without a new pick, but if the command fetches code from the network, pipes into a shell, uses `sudo` or runs a file outside the project, it shows the command and asks. Measured on reuse only: 8 of 16 reuse sessions against 10 of 16 for 1.0.2 in a same-day run on development fixtures (n=16 shows only a large drop). It asked instead of running in 2 of 2 hostile test repos, where 1.0.2 tried to run the command in both, and still ran an in-project `npm run` tool without asking (one session each).
- **1.0.4** fixes five problems an outside review found in 1.0.3: (1) the final file check compares `git status --porcelain` with a snapshot taken at the start, in both the staged and unstaged columns, and never offers `git checkout` for a file you had already changed; (2) four rules that contradicted each other (`auto` and the Commands line, "unless the user said no" and "Done means", `TOOLS.md`, outside folders passed as an argument); (3) the optional index line is written in single quotes, so `$` and backticks in a path stay literal; (4) the reuse step reads the tool's file and runs only a documented command that is its dry run, otherwise it asks; (5) `.ts` self-checks under `node --test` are written only when `node --version` is 23.6 or newer, or 22.18 or newer, else as `.js`. Measured with Sonnet 5.5, two runs per fixture, on six new fixtures: the snapshot was taken before the first file write in 12 of 12 sessions (0 of 12 for 1.0.3), and no session flagged or reverted a pre-existing change. 1.0.3 did not fail these either: Sonnet noticed on its own that the file was already modified, escaped `$HOME` itself and ran `--dry-run` itself, so the fixes rest on a review of the text, not on a measured difference. Catching a new staged edit could not be tested, because a session that follows the rules never stages one. The old-Node failure could not be reproduced (the test machine runs Node 24). On the held-out projects, one run: 15 of 20 working, no protected file edited.
- **1.0.5** renames the skill to `skill-spawner`, so it is called `/skill-spawner:skill-spawner` and its configuration lines start with `skill-spawner:`. Lines set before 1.0.5 need the new prefix. It also closes two gaps in the final file check that an outside review found: it records `git diff --numstat HEAD` at the start and compares it at the end, so a second edit to a file you had already changed is caught unless the line counts come out identical; and a new file outside the approved list is reported as `UNAPPROVED NEW FILE` with a question, instead of passing silently. A first draft used `git stash create` for the snapshot; Claude Code asks for permission before that command, so both test sessions fell back to a weaker check, and it was replaced. Measured with Sonnet 5.5, one run of the six fixtures in `evals/`: 5 of 6 pass, the counts were taken in all six sessions without a permission prompt, and no pre-existing change was flagged; the failure is the TypeScript tool listing exported types as well as functions, as in 1.0.4. A comparison on the 20 held-out projects, one run, with a second fresh session asking for the chore again: the skill against no skill plus a strong standing rule (check `docs/tools.md` and `AGENTS.md` for an existing tool and run it, else write one script with a self-check, document it in `docs/tools.md`, add an `AGENTS.md` Commands line, dry run by default). Hidden test passed: 18 of 20 against 14 of 20 (Fisher p=0.24). The second session ran the existing tool: 20 of 20 against 19 of 20. Worked and was reused without new code: 16 of 20 against 14 of 20. Planted key printed by the model: 0 against 1. Protected files edited: 0 in both. Cost for both sessions: $5.46 against $3.77 in total.

## What the numbers cannot show
- Twenty held-out projects, written by a model, run once or twice per agent. The intervals are wide.
- If the fixtures are ever published, a model trained on them would have seen them.
- "Working" is a strict, conjunctive bar. A tool can be useful and still fail it, and the failures were not read one by one.
- The reuse comparison (1.0.5, against a strong standing rule) is one run on 20 projects. Each arm used its own setup: the skill installed in both sessions, or the rule in both sessions. The test system prompt also named the skill in both sessions of the skill arm, which a real fresh session does not have. It compares setups, not wording alone.
- Larger Claude models were not re-run on the shipped skill.
