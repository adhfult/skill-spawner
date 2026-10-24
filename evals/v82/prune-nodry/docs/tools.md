# Tools

## Project facts
- Stack: Python 3, standard library only.
- Test command: none.

## Commands
- When asked to prune old backups, run `python3 tools/prune_backups.py` instead of writing new code.

## prune_backups
Keeps the newest 3 backups in backups/ and removes the older ones.
Usage: `python3 tools/prune_backups.py`
check: python3 tools/prune_backups.py --self-test
