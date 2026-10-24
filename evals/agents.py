"""Non-Claude agents for evals/simulate.py (--agent codex|agy|copilot).

Each Session has the interface simulate.py uses for claude: .turn(text) -> dict with the keys turn() returns
(tools, cost, out_tok, turns, text, error, models) plus usage and cost_known=False, and .close().
These CLIs run ONE PROCESS PER TURN with an explicit session id (parallel-safe): codex exec / codex exec resume <thread>,
copilot -p --session-id <uuid>, agy -p --conversation <id>. stdin is /dev/null, stdout is parsed, a hard per-turn
timeout kills the whole process group.

Events are normalized to the harness vocabulary so run() has no per-agent logic:
  shell/command execution            -> {"name": "Bash", "input": {"command": ...}}
  any tool call that mentions SKILL  -> one {"name": "Skill", "input": {"skill": SKILL}} ("triggered")
  a changed file (git status diff)   -> {"name": "Write", "input": {"file_path": <first changed path>}}
For non-Claude agents "triggered" means: a command or tool call opened or mentioned the skill's files (SKILL.md path),
not a native skill-invocation event. Observed per agent: see docs in SCORING-CHANGELOG.md (2026-10-11 agent adapters).
Writes are detected from `git status --porcelain --untracked-files=all` before/after each turn (these agents write
through shell, patch or editor tools with different names); NOISE paths and the installed skill dir are ignored.
cost stays 0.0 and cost_known is False: the agents run on subscription quota. usage holds what the agent reports.

Safety (flags verified against --help): codex -s workspace-write (no network) + approval never; copilot allows
write/shell but denies rm -rf, git push, curl, wget, sudo and all urls, no GitHub MCP; agy --mode accept-edits.
The agents run with the REAL home (they need auth): not sandboxed, canaries only detect. Auth files are never read here.
"""
import json, os, shlex, shutil, signal, subprocess, tempfile, threading, uuid
from pathlib import Path

SKILL = "skill-spawner"
OLD_SKILL = SKILL  # the private harness also accepts the name used before 1.0.5; this copy has no older runs
NOISE = ()  # simulate.py assigns its NOISE tuple
SKILL_DIR = f".agents/skills/{SKILL}/"
SKILL_DIRS = (SKILL_DIR, f".agents/skills/{OLD_SKILL}/")


def mentions(x):
    return any(n in json.dumps(x) for n in (SKILL, OLD_SKILL))


def unwrap(cmd):
    """codex reports `/bin/bash -lc '<script>'`; the harness wants the script."""
    try:
        w = shlex.split(cmd)
    except ValueError:
        return cmd
    return w[2] if len(w) == 3 and w[1] in ("-lc", "-c") and w[0].endswith(("sh", "bash", "zsh")) else cmd


def new(**kw):
    return {"tools": [], "cost": 0.0, "out_tok": 0, "turns": 0, "text": "", "error": None, "models": {}, "usage": None, "cost_known": False, **kw}


def bash(out, cmd):
    out["tools"].append({"name": "Bash", "input": {"command": cmd}})
    out["turns"] += 1


def parse_codex(lines):
    out, sid, seen = new(), None, set()
    for l in lines:
        try:
            e = json.loads(l)
        except ValueError:
            continue
        t, it = e.get("type"), e.get("item") or {}
        if t == "thread.started":
            sid = e.get("thread_id")
        elif t in ("item.started", "item.completed") and it.get("type") != "agent_message":
            if it.get("id") in seen:
                continue
            seen.add(it.get("id"))
            if it.get("type") == "command_execution":
                bash(out, unwrap(it.get("command", "")))
            if mentions({k: v for k, v in it.items() if k != "aggregated_output"}):
                out["tools"].append({"name": "Skill", "input": {"skill": SKILL}})
        elif t == "item.completed":
            out["text"] = it.get("text", "") or out["text"]
        elif t == "turn.completed":
            u = e.get("usage") or {}
            out["usage"] = {k: (out["usage"] or {}).get(k, 0) + v for k, v in u.items()}
            out["out_tok"] += u.get("output_tokens", 0)
        elif t in ("error", "turn.failed"):
            out["error"] = str(e.get("message") or (e.get("error") or {}).get("message") or t)[:300]
    return out, sid


SHELLS = ("bash", "shell", "powershell", "run_command")


def parse_copilot(lines):
    out, sid = new(), None
    for l in lines:
        try:
            e = json.loads(l)
        except ValueError:
            continue
        t, d = e.get("type"), e.get("data") or {}
        if t == "tool.execution_start":
            args = d.get("arguments") or {}
            if d.get("toolName", "").lower() in SHELLS:
                bash(out, args.get("command", ""))
            if mentions([d.get("toolName"), args]) and not any(x["name"] == "Skill" for x in out["tools"]):
                out["tools"].append({"name": "Skill", "input": {"skill": SKILL}})
        elif t == "assistant.message":
            out["text"] = d.get("content") or out["text"]
            if d.get("model"):
                out["models"][d["model"]] = 0
        elif t == "result":
            sid = e.get("sessionId")
            out["usage"] = e.get("usage")
            if e.get("exitCode"):
                out["error"] = f"exit {e['exitCode']}"
    return out, sid


def parse_agy(lines):
    out, sid, seen = new(), None, set()
    for l in lines:
        try:
            e = json.loads(l)
        except ValueError:
            continue
        ev = e.get("event")
        if ev == "init":
            sid = e["conversation_id"]
            out["models"][e["init"].get("model", "?")] = 0
        elif ev == "step_update":
            s = e["step_update"]
            if s.get("step_type") == "tool" and s.get("state") == "ACTIVE" and s.get("step_index") not in seen:
                seen.add(s.get("step_index"))
                p = (s.get("tool_info") or {}).get("parameters") or {}
                if s.get("tool_name") == "run_command":
                    bash(out, next((p[k] for k in ("CommandLine", "command", "Command") if k in p), json.dumps(p)))
                if mentions(p) and not any(x["name"] == "Skill" for x in out["tools"]):
                    out["tools"].append({"name": "Skill", "input": {"skill": SKILL}})
        elif ev == "result":
            r = e["result"]
            sid, out["text"], out["usage"] = r.get("conversation_id") or sid, r.get("response", ""), dict(r.get("usage") or {})
            if r.get("denied_actions"):  # headless accept-edits auto-denies shell commands (no allow rule): make that visible
                out["usage"]["denied_actions"] = [x.get("display_name") for x in r["denied_actions"]]
            out["out_tok"] = (r.get("usage") or {}).get("output_tokens", 0)
            if r.get("status") != "SUCCESS":
                out["error"] = str(r.get("status"))
    return out, sid


def snap(cwd):
    """{path: (status, mtime, size)} of the changed files in a git repo, minus NOISE and the installed skill."""
    r = subprocess.run(["git", "status", "--porcelain", "--untracked-files=all"], cwd=cwd, capture_output=True, text=True).stdout
    s = {}
    for l in r.splitlines():
        f = l[3:].split(" -> ")[-1].strip('"')
        if f.startswith(SKILL_DIRS) or any(n in f for n in NOISE):
            continue
        try:
            st = os.stat(Path(cwd) / f)
            s[f] = (l[:2], st.st_mtime_ns, st.st_size)
        except OSError:
            s[f] = (l[:2], 0, 0)
    return s


def install_skill(d, src):
    """Copy the whole skill folder (SKILL.md + references/) into the project and commit it, so score() ignores it."""
    dst = Path(d) / SKILL_DIR
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(src, dst)
    for c in (["add", "-f", SKILL_DIR], ["commit", "-qm", "chore: install skill"]):
        subprocess.run(["git", *c], cwd=d, capture_output=True)


def agy_rules_ok():
    """agy -p auto-denies every shell command unless ~/.gemini/antigravity-cli/settings.json has permissions.allow rules
    (project hooks and project settings cannot grant them; verified 2026-10-11). Read-only check, never edits the file."""
    try:
        allow = json.load(open(Path.home() / ".gemini/antigravity-cli/settings.json")).get("permissions", {}).get("allow", [])
    except (OSError, ValueError):
        allow = []
    return "command(python3)" in allow


class Session:
    parse = None

    def __init__(self, cwd, a, sim, second=False, timeout=None, pre=""):
        self.cwd, self.a, self.pre, self.first = cwd, a, pre, True
        self.timeout = timeout or sim.get("timeout") or a.timeout
        self.model = (a.second_model or a.model) if second else a.model
        self.sid = None

    def cmd(self, text):
        raise NotImplementedError

    def turn(self, text):
        before = snap(self.cwd)
        if self.first and self.pre:
            text = f"{self.pre}\n\n{text}"
        err = tempfile.TemporaryFile()
        p = subprocess.Popen(self.cmd(text), cwd=self.cwd, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=err,
                             text=True, start_new_session=True)
        hit = []
        t = threading.Timer(self.timeout, lambda: (hit.append(1), os.killpg(p.pid, signal.SIGKILL)))
        t.daemon = True
        t.start()
        lines = p.communicate()[0].splitlines()
        t.cancel()
        try:
            os.killpg(p.pid, signal.SIGKILL)  # stragglers (a dev server the model started) must not outlive the turn
        except ProcessLookupError:
            pass
        if os.environ.get("AGENT_RAW"):  # debug: keep the raw event stream of every turn
            with open(os.environ["AGENT_RAW"], "a") as f:
                f.write("\n".join(lines) + "\n")
        out, sid = self.parse(lines)
        self.sid = sid or self.sid
        if hit:
            out["error"] = "timeout or exit"
        elif p.returncode and not out["error"]:
            err.seek(0)
            out["error"] = f"exit {p.returncode}: " + err.read().decode(errors="replace")[-200:].strip()
        elif not self.sid and not out["error"]:
            out["error"] = "no session id"
        self.first = False
        after = snap(self.cwd)
        changed = sorted(f for f in after if after[f] != before.get(f))
        if changed:
            out["tools"].append({"name": "Write", "input": {"file_path": changed[0]}})
        return out

    def close(self):
        pass


class Codex(Session):
    parse = staticmethod(parse_codex)

    def cmd(self, text):
        c = ["codex", "exec"] + (["resume", self.sid] if self.sid else [])
        c += ["--json", "-c", 'sandbox_mode="workspace-write"', "-c", 'approval_policy="never"']  # resume has no -s
        if self.model:
            c += ["-m", self.model]
        if self.a.effort:
            c += ["-c", f'model_reasoning_effort="{self.a.effort}"']
        return c + [text]


class Copilot(Session):
    parse = staticmethod(parse_copilot)

    def __init__(self, *x, **k):
        super().__init__(*x, **k)
        self.sid = str(uuid.uuid4())

    def cmd(self, text):
        deny = [f"shell({c}:*)" for c in ("rm -rf", "git push", "curl", "wget", "sudo")] + ["url"]
        c = ["copilot", "-p", text, "--session-id", self.sid, "--output-format", "json", "--no-ask-user", "--disable-builtin-mcps",
             "--allow-tool=write", "--allow-tool=shell", *(f"--deny-tool={d}" for d in deny), "--no-auto-update"]
        if self.model:
            c += ["--model", self.model]
        if self.a.effort:
            c += ["--reasoning-effort", self.a.effort]
        return c


class Agy(Session):
    parse = staticmethod(parse_agy)

    def cmd(self, text):
        c = ["agy", "-p", text, "--mode", "accept-edits", "--output-format", "stream-json"]
        c += ["--conversation", self.sid] if self.sid else []
        if self.model:
            c += ["--model", self.model]
        if self.a.effort:
            c += ["--effort", self.a.effort]
        return c


CLASSES = {"codex": Codex, "copilot": Copilot, "agy": Agy}
