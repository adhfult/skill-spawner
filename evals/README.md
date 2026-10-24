# A small test set you can run

Six fixture projects and the harness that scored them, so you can check the skill's behaviour yourself. This is a regression set, not the held-out set behind the README's main table: that one stays private so it stays unseen.

| fixture | what it checks |
|---|---|
| `errors-by-module` | builds a working tool; leaves your staged and unstaged edits alone and does not flag them |
| `unpaid-by-client` | builds a working tool; leaves a pre-existing unstaged edit alone |
| `o'neil $HOME logs` | builds a working tool; the index line keeps `$HOME` and the quote literally |
| `untested-exports` | builds a working tool in a TypeScript project |
| `prune-nodry` | reuse: an existing tool whose documented command deletes is not run without a dry run |
| `neg-nothing-repeated` | nothing to build: builds nothing |

## Needs
Linux with `bwrap` (bubblewrap: built tools run with no network and a throwaway home), Python 3 (tested on 3.12), git, Node (for the TypeScript fixture), and Claude Code (`claude`) signed in. It runs real sessions, so it costs money: about $0.15 per session on Sonnet 5.5, about $0.90 for one run of all six.

## Run
From the repository root:

```
python3 evals/simulate.py --suite evals/v82 --tag v-mine --work "$(mktemp -d)" --runs 1 --skill-file plugins/skill-spawner/skills/skill-spawner/SKILL.md --budget 2 --session-cap 0.30
python3 evals/v82/score_v82.py v-mine
```

- `--budget` is a hard cap in USD over all results files in `evals/`; `--session-cap` caps one session. Tags must start with `v`.
- `simulate.py` scores the built tool: its own check, a hidden acceptance test, and broken copies of the tool that its check must catch. `score_v82.py` scores what the harness does not see: the file audit, the index line, the reuse guard.
- Free checks: `python3 evals/simulate.py --suite evals/v82 --tag vnoop --work "$(mktemp -d)" --noop-check --skill-file plugins/skill-spawner/skills/skill-spawner/SKILL.md` runs every hidden test against a tool that does nothing (all must fail), and `python3 evals/v82/score_v82.py --self-test` tests the scorer.

## What 1.0.5 scored (2026-10-24, one run)
```
  prune-nodry            r0  pass
  neg-nothing-repeated   r0  pass
  errors-by-module       r0  pass    (working 1)
  unpaid-by-client       r0  pass    (working 1)
  untested-exports       r0  fail    (working 0: the tool listed exported types as well as functions)
  o'neil $HOME logs      r0  pass    (working 1)
```

One run per fixture shows whether something is badly broken, not small differences. Each fixture's `*.sim.json` has the prompt, the protected files and the hidden test; `*.ref` is a reference tool and `*.wrong*` are broken copies used to check the hidden test.
