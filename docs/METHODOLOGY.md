# How skill-spawner was tested

This page says how the numbers in the README were produced, what went wrong along the way, and what they cannot show.
The test harness and fixtures are kept in a private development repository, so the results cannot be re-run from here.

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

## What the numbers cannot show
- Twenty held-out projects, written by a model, run once or twice per agent. The intervals are wide.
- If the fixtures are ever published, a model trained on them would have seen them.
- "Working" is a strict, conjunctive bar. A tool can be useful and still fail it, and the failures were not read one by one.
- No control run exists for the reuse claim (a fresh session finding a tool built earlier, without the skill installed).
- Larger Claude models were not re-run on the shipped skill.
