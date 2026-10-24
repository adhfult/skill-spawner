import argparse, sys
from pathlib import Path

KEEP = 3


def old_ones(folder):
    files = sorted(Path(folder).glob("wiki-*.tar.gz"))
    return files[:-KEEP] if len(files) > KEEP else []


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="only list what would be deleted")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args(argv)
    if a.self_test:
        assert old_ones("/nonexistent") == []
        print("ok")
        return 0
    for f in old_ones("backups"):
        print(("would delete " if a.dry_run else "deleting ") + str(f))
        if not a.dry_run:
            f.unlink()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
