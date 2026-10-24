import sys
# TODO: handle empty input
def main(argv):
    if not argv:
        return 2
    return 0  # TODO(ana): return real exit codes

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
