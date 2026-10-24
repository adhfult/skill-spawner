"""Harness v9: the hidden second batch (M1) and the reuse session (M4) are graded in a GRADING COPY of the session folder.
Plain logic, stdlib only. Anything that runs commands (sandbox, git) is passed in by simulate.py as `sh` / `git`, so this
file never imports simulate.py (running `python3 evals/simulate.py` makes that module `__main__`).

sim.json keys used here (all optional; a fixture without "next" is not graded this way):
  "next": {
    "inputs":  globs of the input files the user's batch consists of; the grading copy deletes them and installs <name>.next/
    "outputs": globs of files a real run creates (default: hidden.files + hidden.gone); untracked matches are deleted
    "kind":    "content" | "multiset" | "partition" | "rows" | "exit", or a list of them
    "rows":    [[strings that must share one output line], ...]     (kind rows, static, checked against .ref by the gate)
    "exit":    0 | "nonzero"                                         (kind exit: status of the first dry command)
    "named_paths": globs compared by path (content/multiset); default: compared by content, wherever the tool wrote them
    "arg": values for a path placeholder (default: hidden.arg);  "setup_cmd": builds git state on top of the base commit
    "none": [strings that must not appear on any output line that does not talk about skipping]
    "order": [strings in the output files in this order]; "gone": [globs]; "unchanged": [globs]; "file_has": {path: [strings]}
    "volatile": [regex] replaced by <V> before comparing (timestamps)
  }
  "ref_usage": the reference tool's documented commands (dry run first, then the write command)
  "do_now": true when the prompt asks for the real run
"""
import csv, fnmatch, hashlib, io, re, shutil
from collections import Counter
from pathlib import Path

GIT_ENV = {"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t", "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"}  # sandboxed HOME has no git identity
DOCS = ("AGENTS.md", "CLAUDE.md", "README.md", "docs", ".claude", ".agents")  # what a session writes to make the tool findable; kept in the copy
TEXT_SUFFIX = {".txt", ".csv", ".tsv", ".md"}  # trailing spaces are noise only here
PH = r"\S*(?:<[^>]*>|\[[^\]]*\])\S*|(?<!\S)~\S*"  # a path or date placeholder in a documented command (a ~/path example counts)
NOT_USE = re.compile(r"\s(?:--self-test|--help|-h|--version)\b")  # a self-test or help line is not the tool's use
RUNNER = {".py": "python3", ".sh": "bash", ".js": "node", ".mjs": "node"}
# a tool may say what it left out. Words a chore's own output uses for the thing it must NOT report (fail, remove, drop, refuse) stay out:
# they would make the 'none' check pass a wrong tool. The legacy hidden_test list in simulate.py is wider on purpose: old scores stay.
SKIP_SAY = re.compile(r"skip|ignor|exclud|unstaged|untracked|not |invalid|warn|error|duplicate|already|left alone|no id|left out|unmatched|omit")


def kinds(g):
    k = g.get("kind", "content")
    return [k] if isinstance(k, str) else list(k)


def baseline_commit(git, d, sim):
    """The last commit setup() makes: init, wip key, drop key, then one per sim['commits'] (counted from the root, so a
    model that committed or reset does not move it)."""
    revs = git(d, "rev-list", "--reverse", "HEAD").split()
    return revs[2 + len(sim.get("commits", []))]


def _matches(root, globs):
    return sorted({p for g in globs for p in root.glob(g)})


def grading_copy(src, dst, name, sim, projects, sh, git):
    """Copy session folder `src` to `dst`: git back to the base commit (tracked files restored, extra branches dropped),
    session documentation kept, the visible inputs replaced by <name>.next/, then the next setup command."""
    g = sim["next"]
    shutil.rmtree(dst, ignore_errors=True)
    shutil.copytree(src, dst, symlinks=True)
    base = baseline_commit(git, dst, sim)
    kept = {}
    for n in DOCS:
        p = dst / n
        for f in ([p] if p.is_file() else sorted(q for q in p.rglob("*") if q.is_file()) if p.is_dir() else []):
            kept[f.relative_to(dst)] = f.read_bytes()
    git(dst, "reset", "-q", "--mixed", base)
    git(dst, "checkout", "-q", "--", ".")
    for ref in git(dst, "for-each-ref", "--format=%(refname:short)", "refs/heads").split():
        if ref != git(dst, "rev-parse", "--abbrev-ref", "HEAD").strip():
            git(dst, "branch", "-q", "-D", ref)
    git(dst, "stash", "clear")
    for rel, data in kept.items():
        (dst / rel).parent.mkdir(parents=True, exist_ok=True)
        (dst / rel).write_bytes(data)
    tracked = set(git(dst, "ls-files", "-z").split("\0"))
    hid = sim.get("hidden", {})
    outputs = g.get("outputs", [*hid.get("files", []), *hid.get("gone", [])])
    for p in _matches(dst, g.get("inputs", [])):
        shutil.rmtree(p) if p.is_dir() and not p.is_symlink() else p.unlink(missing_ok=True)
    for p in _matches(dst, outputs):
        if p.is_file() and str(p.relative_to(dst)) not in tracked:
            p.unlink(missing_ok=True)
    nxt = projects / f"{name}.next"
    if nxt.is_dir():
        shutil.copytree(nxt, dst, dirs_exist_ok=True, symlinks=True)
    if g.get("setup_cmd"):
        sh(g["setup_cmd"], dst, GIT_ENV, 120)
    return dst


def variants(cmd, arg):
    """A documented command with its placeholder filled in, optional [parts] dropped, or the argument appended (as hidden_test does)."""
    first = re.sub(r"\s*\[[^\]]*\]", "", re.sub(PH, arg, cmd, count=1))
    bare = re.sub(r"\s+-{1,2}[\w-]+\s+(?:" + PH + ")", "", cmd)  # `--dir <folder>` with no value given: run without the option
    out = [re.sub(PH, arg, cmd), first, f"{cmd} {arg}".strip(), bare]
    for v in list(out):  # `./tool.py` without the exec bit still counts: run it through its interpreter
        m = re.match(r"\./(\S+?(\.\w+))(?=\s|$)", v)
        if m and m.group(2) in RUNNER:
            out.append(f"{RUNNER[m.group(2)]} {m.group(1)}" + v[m.end():])
    return list(dict.fromkeys(out))


def tree(root):
    return {str(p.relative_to(root)): p.read_bytes() for p in sorted(root.rglob("*"))
            if p.is_file() and ".git" not in p.parts and "__pycache__" not in p.parts}


def run_commands(d, cmds, g, sh, mut_re, timeout=60, judge_writing=True):
    """Run documented commands in `d`: non-mutating first (then 'unchanged' is checked), mutating after. For each command
    the first variant that exits 0 counts. Self-test and help lines are not run. Returns a Run: rcs (first dry command's rc first),
    key_rcs (the first dry and the first writing command's rc: the only ones M1 judges; the writing one only when judge_writing, i.e.
    when the fixture's reference scopes a writing command), text, created/changed files, ok flags."""
    args = g.get("arg", [""])
    cmds = [c for c in cmds if not NOT_USE.search(c)]
    is_mutating = lambda c: mut_re.search(re.sub(r"\[[^\]]*\]", "", c))  # optional [--flag] parts are not run
    before = tree(d)
    snap = lambda: {k: v for pat in g.get("unchanged", []) for k, v in tree(d).items() if fnmatch.fnmatch(k, pat)}
    unchanged0, text, rcs, stable, mid, firsts = snap(), "", [], True, None, []  # firsts: output of each command's first attempt (decision 0033)
    ordered = sorted(cmds, key=lambda c: bool(is_mutating(c)))
    for c in ordered:
        if mid is None and is_mutating(c):
            mid = snap()
            stable = mid == unchanged0
        done, first = None, None
        for arg in args:
            for v in variants(c, arg):
                rc, out = sh(v, d, g.get("env"), timeout)
                text += out
                first = out if first is None else first
                done = rc if done is None or rc == 0 else done
                if rc == 0:
                    break
            if done == 0:
                break
        rcs.append(127 if done is None else done)
        firsts.append(first or "")
    if mid is None:
        stable = snap() == unchanged0
    after = tree(d)
    changed = {k: v for k, v in after.items() if before.get(k) != v}
    n_dry = sum(not is_mutating(c) for c in ordered)  # M1 reads the first dry command and the first writing command; other examples may be broken
    key_rcs = ([rcs[0]] if n_dry else []) + ([rcs[n_dry]] if judge_writing and n_dry < len(rcs) else [])
    key_text = "".join(([firsts[0]] if n_dry else []) + ([firsts[n_dry]] if judge_writing and n_dry < len(rcs) else []))
    return {"rcs": rcs, "key_rcs": key_rcs, "key_text": key_text, "text": text, "files": changed, "gone": sorted(set(before) - set(after)), "stable": stable}


def _norm(data, suffix, volatile):
    try:
        s = data.decode()
    except UnicodeDecodeError:
        return data
    s = s.replace("\r\n", "\n")
    if suffix in TEXT_SUFFIX:
        s = "\n".join(l.rstrip() for l in s.split("\n"))
    for v in volatile:
        s = re.sub(v, "<V>", s)
    return s


def _selected(files, g):
    named = g.get("named_paths")
    return {k: v for k, v in files.items() if not named or any(fnmatch.fnmatch(k, n) for n in named)}


def _bag(files, g):
    vol, by_path = g.get("volatile", []), bool(g.get("named_paths"))  # a path the prompt names is part of the answer
    return Counter(((k if by_path else ""), _norm(v, Path(k).suffix, vol)) for k, v in _selected(files, g).items())


def _rows_bag(files, g):
    out = Counter()
    for k, v in _selected(files, g).items():
        if Path(k).suffix != ".csv":
            continue
        rows = list(csv.reader(io.StringIO(v.decode(errors="replace"))))
        if not rows:
            continue
        head, key = [h.strip() for h in rows[0]], (k if g.get("named_paths") else "")
        out[(key, "!header", tuple(sorted(head)))] = 1  # a header-only file still has to carry the right header
        for r in rows[1:]:
            if not any(c.strip() for c in r):
                continue
            if len(r) != len(head):  # zip would drop the extra cells
                out[(key, "!cells", tuple(c.strip() for c in r))] += 1
            else:
                out[(key, *sorted((h, c.strip()) for h, c in zip(head, r)))] += 1
    return out


def _partition(files, g):
    named = bool(g.get("named_paths"))  # names the prompt gives (folder 01, file img_8.jpg) are part of the answer
    groups = {}
    for k, v in _selected(files, g).items():
        groups.setdefault(str(Path(k).parent), []).append((Path(k).name, v))
    return Counter((parent if named else "", tuple(sorted((n if named else "", hashlib.sha1(x).hexdigest()) for n, x in vs)))
                   for parent, vs in groups.items())


def _has(line, s):
    """Does `line` (lowercase) hold s? A plain number must stand alone (3 is not in 30, 880 is not in 8800, 5 is not in 1.5)."""
    s = s.lower()
    if s.isdigit():
        return re.search(rf"(?<!\d)(?<!\d\.){s}(?!\d)(?!\.\d)", line) is not None
    return s in line


CRASH = re.compile(r"Traceback \(most recent call last\)|^\w*Error:", re.M)  # a Python traceback (it may start mid-line, after output with no newline) or an uncaught error line (Error:, TypeError:, ...)


def compare(g, ref, tool):
    """(ok, reason). `ref` is a Run from the reference tool or None (rows and exit are static). Invariants (order, gone,
    unchanged, file_has) are checked on `tool` whatever the kind."""
    ks = kinds(g)
    bad_rc = [rc for rc in tool.get("key_rcs", tool["rcs"]) if rc != 0]
    if "exit" in ks:
        want = g.get("exit", 0)
        got = tool["rcs"][0] if tool["rcs"] else 127
        if (got == 0) != (want == 0):
            return False, f"exit status {got}, wanted {want}"
    elif bad_rc:
        # decision 0033: a report may exit 1 on findings; that is no failure unless the output shows a crash. 2 and above still fail.
        if any(rc != 1 for rc in bad_rc) or CRASH.search(tool.get("key_text", tool["text"])):  # the key commands' first attempts only: later argument variants may print usage errors
            return False, f"a documented command exited {bad_rc[0]}"
    if not tool["stable"]:
        return False, "a dry run changed files matching 'unchanged'"
    text = tool["text"] + "\n".join(v.decode(errors="replace") for v in tool["files"].values())
    low = text.lower()
    for grp in g.get("rows", []) if "rows" in ks else []:
        if not any(all(_has(line, s) for s in grp) for line in low.splitlines()):
            return False, f"no output line holds {grp}"
    if ref is not None and g.get("named_paths") and {"content", "multiset"} & set(ks) and set(_selected(tool["files"], g)) != set(_selected(ref["files"], g)):
        return False, "the named files differ from the reference's"  # e.g. a header-only day's file was not written
    if "content" in ks and ref is not None and _bag(tool["files"], g) != _bag(ref["files"], g):
        return False, "created or changed files differ from the reference"
    if "multiset" in ks and ref is not None and _rows_bag(tool["files"], g) != _rows_bag(ref["files"], g):
        return False, "CSV rows differ from the reference"
    if "partition" in ks and ref is not None and _partition(tool["files"], g) != _partition(ref["files"], g):
        return False, "grouping differs from the reference"
    for s in g.get("none", []):
        if any(s.lower() in l for l in low.splitlines() if not SKIP_SAY.search(l)):
            return False, f"'{s}' is reported but must not be"
    at, joined = -1, "\n".join(v.decode(errors="replace").lower() for _, v in sorted(tool["files"].items()))
    for s in g.get("order", []):
        at = joined.find(s.lower(), at + 1)
        if at < 0:
            return False, f"'{s}' missing or out of order"
    return True, "ok"


def invariants(d, g):
    """Checks on the tool's grading copy after the run: nothing matching 'gone' exists, each 'file_has' file holds its strings."""
    for pat in g.get("gone", []):
        if list(d.glob(pat)):
            return False, f"'{pat}' still exists"
    for f, want in g.get("file_has", {}).items():
        p = d / f
        if not p.is_file() or not all(w.lower() in p.read_text(errors="replace").lower() for w in want):
            return False, f"{f} lacks {want}"
    return True, "ok"
