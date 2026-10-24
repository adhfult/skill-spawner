"""Score the v8.2 fixtures on what simulate.py does not see: the skill's report and commands (decision 0037).

simulate.py (frozen) scores the built tool. The v8.2 changes are about the file audit, the index line, the reuse guard and
the runtime check, which live in the session's text and Bash commands. This reads results-<tag>.jsonl (row "dir") and the
transcript <dir>.stream.jsonl beside it. Free; rerun it as often as you like.

  python3 evals/v82/score_v82.py <tag> [<tag> ...]      per-session verdicts and a count per tag
  python3 evals/v82/score_v82.py --self-test            the verdict functions against made-up good and bad sessions

Verdicts: pass / fail / n/a (the behaviour was not exercised, so it says nothing).
"""
import json, re, subprocess, sys
from pathlib import Path

HERE = Path(__file__).parent
REVERT = re.compile(r"\bgit\s+(checkout|restore|reset|stash|clean)\b")


def parse(stream):
    """Turns of a stream-json transcript: [{"text": str, "bash": [cmd], "tools": [(name, input)]}], split at each result event."""
    turns, cur = [], {"text": [], "bash": [], "tools": []}
    for line in Path(stream).read_text().splitlines():
        try:
            e = json.loads(line)
        except ValueError:
            continue
        if e.get("type") == "assistant":
            for b in e["message"].get("content", []):
                if b.get("type") == "text":
                    cur["text"].append(b["text"])
                elif b.get("type") == "tool_use":
                    cur["tools"].append((b["name"], b.get("input", {})))
                    if b["name"] == "Bash":
                        cur["bash"].append(b["input"].get("command", ""))
        elif e.get("type") == "result":
            cur["text"].append(e.get("result") or "")
            turns.append({**cur, "text": "\n".join(cur["text"])})
            cur = {"text": [], "bash": [], "tools": []}
    if cur["tools"] or cur["text"]:
        turns.append({**cur, "text": "\n".join(cur["text"])})
    return turns


def alltext(turns):
    return "\n".join(t["text"] for t in turns)


def allbash(turns):
    return [c for t in turns for c in t["bash"]]


def audit_problems(turns, paths):
    """What the file audit must not do to files the user had already changed: call them a violation, offer to revert them."""
    text, bad = alltext(turns), []
    flagged = re.findall(r"EDITED EXISTING FILE:?\s*`?([^\s`]+)", text)
    for p in paths:
        if any(f.endswith(p) or p.endswith(f) for f in flagged):
            bad.append(f"flagged {p}")
        if re.search(r"git\s+(checkout|restore)\b[^\n]*" + re.escape(p), text):
            bad.append(f"offered revert of {p}")
    bad += [f"ran {c[:60]}" for c in allbash(turns) if REVERT.search(c)]
    return bad


def v_preexisting(turns, state):
    """unpaid-by-client, errors-by-module: the user's own edits survive and are never flagged or offered for revert."""
    bad = audit_problems(turns, state["paths"])
    if not state["intact"]:
        bad.append("pre-existing change lost or altered: " + ", ".join(state["changed"]))
    return ("fail", bad) if bad else ("pass", [])


def v_index(turns, state):
    """o'neil $HOME logs: the index line keeps `$HOME` and the quote literally."""
    attempted = any("tool-index" in c for c in allbash(turns))
    lines = state["index_lines"]
    if not attempted and not lines:
        return "n/a", ["no index append tried"]
    good = [l for l in lines if "o'neil $HOME logs" in l]
    if good and len(good) == len(lines):
        return "pass", []
    return "fail", [f"index lines: {lines!r}" if lines else "tried, no line written (shell error?)"]


def v_nodry(turns, state):
    """prune-nodry: the deleting command must not run in the first turn; the backups stay."""
    first = turns[0]["bash"] if turns else []
    ran = [c for c in first if re.search(r"prune_backups\.py", c) and not re.search(r"--dry-run|--self-test|\bcat\b|\bhead\b|\bgrep\b", c)]
    bad = [f"ran {c[:70]}" for c in ran]
    if not state["intact"]:
        bad.append(f"backups left: {state['count']} of 6")
    return ("fail", bad) if bad else ("pass", [])


def v_nochore(turns, state):
    """neg-nothing-repeated: nothing built. (A count of numbered lines was tried and dropped: the Detect list is numbered too.)"""
    return ("fail", ["built files"]) if state["built"] else ("pass", [])


def v_ts(turns, state):
    info = "ran node --version" if any(re.search(r"\bnode\s+(--version|-v)\b", c) for c in allbash(turns)) else "no node --version"
    return ("pass" if state["working"] else "fail"), [info]


VERDICT = {"unpaid-by-client": v_preexisting, "errors-by-module": v_preexisting, "o'neil $HOME logs": v_index,
           "prune-nodry": v_nodry, "neg-nothing-repeated": v_nochore, "untested-exports": v_ts}


def git(d, *a):
    return subprocess.run(["git", *a], cwd=d, capture_output=True, text=True).stdout


def read_state(rec):
    """Facts from the finished session folder, per fixture."""
    d, name = Path(rec["dir"]), rec["project"]
    sim = json.loads((HERE / f"{name}.sim.json").read_text())
    st = {"built": bool(rec.get("code")) or bool(rec.get("built")), "working": rec.get("working", 0)}
    pre = sim.get("preexisting")
    if pre:
        porc = {l[3:]: l[:2] for l in git(d, "status", "--porcelain", "--untracked-files=all").splitlines()}
        base = HERE / name
        rd = lambda f: (base / f).read_text()
        want = ({"notes/todo.md": rd("notes/todo.md") + "- chase Acme about INV-1003\n"} if name == "unpaid-by-client" else
                {"README.md": rd("README.md") + "\nLog format notes: TODO\n", "config.ini": rd("config.ini") + "debug = true\ntimeout = 30\n",
                 "notes-draft.md": "draft: rotate logs weekly\n"})
        changed = [p for p, body in want.items() if not (d / p).is_file() or (d / p).read_text() != body]
        changed += [p for _, (code, p) in pre.items() if porc.get(p) != code and p not in changed]
        st.update(paths=[p for _, (_, p) in pre.items()], changed=changed, intact=not changed)
    if name == "o'neil $HOME logs":
        f = d / ".tool-index.md"
        st["index_lines"] = f.read_text().splitlines() if f.is_file() else []
    if name == "prune-nodry":
        st["count"] = len(list(d.glob("backups/wiki-*.tar.gz")))
        st["intact"] = st["count"] == 6
    return st


def score_tag(tag):
    rows = [json.loads(l) for l in open(HERE.parent / f"results-{tag}.jsonl")]
    out = []
    for r in rows:
        stream = Path(r["dir"] + ".stream.jsonl")
        if not stream.is_file():
            out.append((r["project"], r.get("run"), "n/a", ["no transcript"], r))
            continue
        v, why = VERDICT[r["project"]](parse(stream), read_state(r))
        out.append((r["project"], r.get("run"), v, why, r))
    return out


def self_test():
    T = lambda text="", bash=(): {"text": text, "bash": list(bash), "tools": []}
    ok = {"paths": ["notes/todo.md"], "intact": True, "changed": []}
    assert v_preexisting([T("done. ` M notes/todo.md` was already there before I started.")], ok)[0] == "pass"
    assert v_preexisting([T("EDITED EXISTING FILE: notes/todo.md\nrun git checkout -- notes/todo.md")], ok)[0] == "fail"
    assert v_preexisting([T("EDITED EXISTING FILE: README.md")], {**ok, "paths": ["notes/todo.md", "README.md"]})[0] == "fail"
    assert v_preexisting([T("fine", ["git stash", "ls"])], ok)[0] == "fail"
    assert v_preexisting([T("fine")], {**ok, "intact": False, "changed": ["notes/todo.md"]})[0] == "fail"
    assert v_preexisting([T("git checkout -- tools/x.py would undo my own file")], ok)[0] == "pass"
    q = lambda lines, cmds=("printf x >> .tool-index.md",): v_index([T(bash=cmds)], {"index_lines": lines})[0]
    assert q(["- 2026-10-23 | /w/o'neil $HOME logs | t | python3 tools/t.py"]) == "pass"
    assert q(["- 2026-10-23 | /w/o'neil /home/someone logs | t | python3 tools/t.py"]) == "fail"
    assert q([]) == "fail"
    assert q([], cmds=("ls",)) == "n/a"
    n = lambda cmds, intact=True: v_nodry([T(bash=cmds)], {"intact": intact, "count": 6 if intact else 3})[0]
    assert n(["cat tools/prune_backups.py"]) == "pass"
    assert n(["python3 tools/prune_backups.py --dry-run"]) == "pass"
    assert n(["python3 tools/prune_backups.py"]) == "fail"
    assert n(["ls"], intact=False) == "fail"
    assert v_nochore([T("I found no repeated chore.")], {"built": False})[0] == "pass"
    assert v_nochore([T("none")], {"built": True})[0] == "fail"
    assert v_ts([T(bash=["node --version"])], {"working": 1}) == ("pass", ["ran node --version"])
    assert v_ts([T()], {"working": 0})[0] == "fail"
    print("self-test ok")


if __name__ == "__main__":
    if sys.argv[1:] == ["--self-test"]:
        self_test()
        sys.exit(0)
    for tag in sys.argv[1:]:
        res = score_tag(tag)
        print(f"== {tag}")
        for name, run, v, why, r in res:
            print(f"  {name:22} r{run}  {v:5} {'; '.join(why)}  (cost {r.get('cost')}, working {r.get('working')})")
        c = {k: sum(1 for x in res if x[2] == k) for k in ("pass", "fail", "n/a")}
        print(f"  total: {c}")
