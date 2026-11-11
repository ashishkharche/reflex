#!/usr/bin/env python3
"""Sets up Reflex in an app with no hand-written adapter: finds the stack and a state holder, writes a
generated host, builds it, runs it once, fixes known first-run problems and records a first journey.

    python3 ../reflex/runner/reflex_init.py [app] [--screen <Class>] [--list] [--dry-run]

It writes only under <app>/tests/reflex/ and changes no app file. Standard library only.
Prints one line per step, then PASS, or STOP with the reason and the one next step."""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
REFLEX = HERE.parent
sys.path.insert(0, str(HERE))

OUT = Path("tests/reflex")
SKIP_DIRS = {".git", "build", ".build", "node_modules", ".gradle", ".dart_tool", "Pods", "DerivedData", ".idea",
             ".swiftpm", "checkouts", "ios", "android", "macos", "windows", "linux", "web", ".expo", "dist", "vendor"}
HINTS = ("Home", "Main", "ForYou", "List", "Feed", "Timeline", "Dashboard", "Inbox", "Episodes", "Today")
PENALTIES = ("Activity", "Settings", "Debug", "Onboarding", "Login", "Auth", "Splash", "Preview", "Base", "Abstract", "Widget",
             "Row", "Cell", "Item", "Stats", "Filter")
# A screen that edits or adds one thing is rarely the main screen.
FORM_PREFIX = re.compile(r"^(Edit|Add|Create|New|Compose)[A-Z]")
FAKE_PREFIX = re.compile(r"^(Fake|Test|InMemory|Stub|Noop|NoOp|Dummy|Mock|Preview|Placeholder)[A-Z]")


class Stop(Exception):
    """A first-run problem with no automatic fix. The message is the one next step."""


SAID = []


def say(line):
    SAID.append(line)
    print(line, flush=True)


# ---------- source scanning ----------

def files(root, suffixes, tests=True, skip=SKIP_DIRS):
    root = Path(root)
    for dirpath, dirnames, filenames in os.walk(root):
        rel = Path(dirpath).relative_to(root)
        dirnames[:] = [d for d in dirnames if d not in skip and not d.startswith(".")
                       and (rel / d).as_posix() != OUT.as_posix()]
        for name in filenames:
            if name.endswith(suffixes):
                path = Path(dirpath) / name
                if not tests and is_test_path(path):
                    continue
                yield path


def is_test_path(path):
    parts = Path(path).as_posix()
    return bool(re.search(r"/(src/)?(test|tests|androidTest|androidUnitTest|commonTest|jvmTest|iosTest|testFixtures|"
                          r"__tests__|testing|Tests|UITests|integration_test)(/|$)", parts)) or "/test/" in parts


def read(path):
    try:
        return Path(path).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def balanced(text, start, open_char="(", close_char=")"):
    """The text between the bracket at start and its match, or None."""
    if start >= len(text) or text[start] != open_char:
        return None
    depth = 0
    for i in range(start, len(text)):
        c = text[i]
        if c == open_char:
            depth += 1
        elif c == close_char:
            depth -= 1
            if depth == 0:
                return text[start + 1:i]
    return None


def split_top(text, sep=","):
    out, depth, cur = [], 0, ""
    for c in text:
        if c in "([{<":
            depth += 1
        elif c in ")]}>":
            depth -= 1
        if c == sep and depth == 0:
            out.append(cur)
            cur = ""
        else:
            cur += c
    if cur.strip():
        out.append(cur)
    return [p.strip() for p in out if p.strip()]


def score(name, base, text):
    s = base
    if re.search(r"(ViewModel|ScreenModel|Presenter|Store|Model|Notifier|Cubit|Bloc)$", name):
        s += 3
    s += sum(2 for h in HINTS if h in name)
    s -= sum(3 for p in PENALTIES if p in name)
    s -= 2 if FORM_PREFIX.match(name) else 0
    s += min(3, len(re.findall(r"StateFlow|stateIn|mutableStateOf|notifyListeners|@Published|useState|emit\(", text)))
    return s


def short_name(name):
    return re.sub(r"(ViewModel|ScreenModel|Presenter|Store|Notifier|Cubit|Bloc|Model)$", "", name) or name


# ---------- stack detection ----------

def detect(app):
    """Stacks in the order Reflex prefers: shared Kotlin, Flutter, React Native, Swift."""
    out = []
    if any((app / n).exists() for n in ("settings.gradle.kts", "settings.gradle")):
        out.append("kotlin")
    pub = read(app / "pubspec.yaml")
    if pub and re.search(r"^\s*flutter:\s*$", pub, re.M) or re.search(r"sdk:\s*flutter", pub):
        out.append("flutter")
    pkg = read(app / "package.json")
    if pkg and re.search(r'"(react|react-native|expo)"\s*:', pkg):
        out.append("node")
    if (app / "Package.swift").exists() or list(app.glob("*.xcodeproj")) or list(app.glob("*/Package.swift")) \
            or list(app.glob("*/*/Package.swift")):
        out.append("swift")
    return out


# ---------- Kotlin ----------

KT_CLASS = re.compile(r"^(?:[ \t]*@[\w.]+(?:\([^)]*\))?\s*)*[ \t]*(?:(?:public|internal|open|final|sealed|abstract|data)\s+)*"
                      r"class\s+(\w+)", re.M)


def kotlin_package(text):
    m = re.search(r"^\s*package\s+([\w.]+)", text, re.M)
    return m.group(1) if m else ""


def kotlin_header(text, m):
    """(abstract, constructor params text, supertypes text) for a class match."""
    i = m.end()
    j = i
    while j < len(text) and text[j] in " \t\n" or text[j:j + 1] == "<":
        if text[j] == "<":
            depth = 0
            while j < len(text):
                depth += text[j] == "<"
                depth -= text[j] == ">"
                j += 1
                if depth == 0:
                    break
            continue
        j += 1
    rest = text[j:j + 400]
    k = re.match(r"\s*(?:@\w+(?:\([^)]*\))?\s*)*(?:(?:private|internal|public|protected)\s+)?(?:constructor\s*)?", rest)
    params = None
    p = j + (k.end() if k else 0)
    if text[p:p + 1] == "(":
        params = balanced(text, p)
        p += len(params) + 2
    sup = re.match(r"\s*:\s*([^{\n]+(?:\n\s+[^{\n]+)*)", text[p:p + 600])
    return ("abstract " in text[m.start():m.end()] or "sealed " in text[m.start():m.end()], params or "",
            sup.group(1) if sup else "")


def kotlin_candidates(app):
    out = []
    for path in files(app, (".kt",), tests=False):
        text = read(path)
        if "class " not in text:
            continue
        for m in KT_CLASS.finditer(text):
            abstract, params, sup = kotlin_header(text, m)
            name = m.group(1)
            if abstract:
                continue
            base = 0
            if re.search(r"\b(Android)?ViewModel\s*\(|\bScreenModel\b|\bStateScreenModel\b", sup):
                base = 6
            elif name.endswith("ViewModel") and ("StateFlow" in text or "mutableStateOf" in text):
                base = 4
            if not base:
                continue
            out.append({"stack": "kotlin", "name": name, "class": f"{kotlin_package(text)}.{name}".lstrip("."),
                        "file": path, "score": score(name, base, text), "params": params})
    return sorted(out, key=lambda c: (-c["score"], c["name"]))


def kotlin_param_names(params):
    names = []
    for part in split_top(params):
        part = re.sub(r"@\w+(\([^)]*\))?\s*", "", part)
        part = re.sub(r"^(private|internal|public|protected|override|val|var|vararg|crossinline|noinline|\s)+", "", part).strip()
        m = re.match(r"(\w+)\s*:", part)
        if not m:
            return None
        names.append(m.group(1))
    return names


def kotlin_methods(text):
    """Parameter names by name/arity for every fun in the file."""
    out = {}
    for m in re.finditer(r"\bfun\s+(?:<[^>]*>\s*)?(\w+)\s*\(", text):
        inner = balanced(text, m.end() - 1)
        if inner is None:
            continue
        names = kotlin_param_names(inner)
        if names is not None:
            out.setdefault(f"{m.group(1)}/{len(names)}", names)
    return out


def kotlin_events(app):
    """Subtypes of every sealed type in the app, as package.Name by the sealed type’s simple name."""
    out = {}
    texts = [(kotlin_package(read(p)), read(p)) for p in files(app, (".kt",), tests=False)]
    sealed = {m.group(1) for _, t in texts for m in re.finditer(r"\bsealed\s+(?:interface|class)\s+(\w+)", t)}
    for pkg, text in texts:
        for m in re.finditer(r"\b(?:data\s+)?(?:class|object)\s+(\w+)\s*(?:\([^)]*\))?\s*:\s*([\w.]+)", text):
            base = m.group(2).split(".")[-1]
            if base in sealed:
                out.setdefault(base, []).append(f"{pkg}.{m.group(1)}".lstrip("."))
    return {k: sorted(set(v)) for k, v in sorted(out.items())}


def kotlin_ctors(app):
    """Constructor parameter names of data classes and of classes in a sealed hierarchy, by simple name."""
    out = {}
    for path in files(app, (".kt",), tests=False):
        text = read(path)
        for m in re.finditer(r"\b(?:data\s+class|class)\s+(\w+)\s*(?:<[^>]*>)?\s*(?:(?:private|internal|public)?\s*(?:@\w+\s*)*constructor\s*)?\(", text):
            if not re.match(r"data\b", text[m.start():]) and not re.match(r"\s*:\s*\w", text[m.end() + len(balanced(text, m.end() - 1) or "") + 1:][:80]):
                continue
            inner = balanced(text, m.end() - 1)
            names = kotlin_param_names(inner) if inner is not None else None
            if names is not None:
                out.setdefault(m.group(1), names)
    return dict(sorted(out.items()))


def kotlin_fakes(app):
    out = []
    for path in files(app, (".kt",)):
        text = read(path)
        pkg = kotlin_package(text)
        for m in re.finditer(r"^(?:(?:public|internal|open|final|data)\s+)*class\s+(\w+)", text, re.M):
            if FAKE_PREFIX.match(m.group(1)) and not m.group(1).endswith("Test"):
                out.append(f"{pkg}.{m.group(1)}".lstrip("."))
    return sorted(set(out))


def gradle_project(app, file):
    folder = Path(file).parent
    while folder != app and folder != folder.parent:
        if (folder / "build.gradle.kts").exists() or (folder / "build.gradle").exists():
            rel = folder.relative_to(app).as_posix()
            return ":" + rel.replace("/", ":")
        folder = folder.parent
    return ":"


def run(cmd, cwd=None, env=None, timeout=1800):
    try:
        done = subprocess.run(cmd, cwd=cwd, env=env, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        raise Stop(f"{Path(cmd[0]).name} did not finish in {timeout // 60} minutes. Run it in a terminal to see why")
    return done.returncode, done.stdout + done.stderr


def jdk_env(app=None):
    """JAVA_HOME as the runner picks it. With no SDK set for an Android build, the usual SDK folder."""
    import reflex_runner as rr
    env = dict(os.environ)
    home = rr.java_home()
    if home and jdk_major(home) > 21:
        # Gradle and its Kotlin DSL lag new JDKs: a build script compiled for Java 27 fails as "class file major version 71".
        for version in ("21", "17"):
            done = subprocess.run(["/usr/libexec/java_home", "-v", version], capture_output=True, text=True) \
                if Path("/usr/libexec/java_home").exists() else None
            lts = done.stdout.strip() if done and done.returncode == 0 else ""
            if lts and jdk_major(lts) == int(version):
                if f"JDK {version}:" not in "".join(SAID):
                    say(f"FIX Gradle runs on JDK {version}: the default JDK {jdk_major(home)} is newer than Gradle supports")
                home = lts
                break
    if home:
        env["JAVA_HOME"] = home
    if app and not env.get("ANDROID_HOME") and not env.get("ANDROID_SDK_ROOT") and "sdk.dir" not in read(app / "local.properties"):
        for sdk in (Path.home() / "Library/Android/sdk", Path.home() / "Android/Sdk"):
            if (sdk / "platforms").is_dir():
                env["ANDROID_HOME"] = str(sdk)
                say(f"FIX no Android SDK set for the build, so ANDROID_HOME={sdk} for this run only")
                break
    return env


def jdk_major(home):
    m = re.search(r'JAVA_VERSION="(?:1\.)?(\d+)', read(Path(home) / "release"))
    return int(m.group(1)) if m else 0


def auto_jar():
    jar = REFLEX / "kotlin/build/reflex-auto/libs/reflex-auto.jar"
    sources = list((REFLEX / "kit/kotlin-auto/src/main").rglob("*.kt")) + list((REFLEX / "kit/kotlin/src/main").rglob("*.kt"))
    if jar.exists() and all(s.stat().st_mtime <= jar.stat().st_mtime for s in sources):
        return jar
    say("BUILD reflex auto host jar")
    code, out = run([str(REFLEX / "kotlin/gradlew"), "-p", str(REFLEX / "kotlin"), "--no-daemon", "-q", ":reflex-auto:jar"],
                    env=jdk_env())
    if code or not jar.exists():
        raise Stop("the Reflex auto host did not build: " + gradle_error(out))
    return jar


def gradle_error(out):
    lines = out.splitlines()
    for i, line in enumerate(lines):
        if line.startswith("Reflex:"):
            return line
        if "What went wrong" in line:
            body = " ".join(l.strip() for l in lines[i + 1:i + 4] if l.strip() and not l.startswith("*"))
            return body[:400]
    errors = [l for l in lines if l.startswith("e: ") or "error:" in l]
    return (errors[0] if errors else (lines[-1] if lines else "no output"))[:400]


def kotlin_next_step(why):
    if re.search(r"SDK location not found|ANDROID_HOME|sdk\.dir", why):
        return "install the Android SDK, then set ANDROID_HOME or sdk.dir in local.properties"
    major = re.search(r"Unsupported class file major version (\d+)", why)
    if major:
        return f"set JAVA_HOME to JDK 21 or 17: Gradle can’t run on Java {int(major.group(1)) - 44}"
    m = re.search(r"(?:toolchain|JDK|Java)\D{0,40}(\d{2})", why)
    if m and re.search(r"toolchain|Cannot find a Java installation", why):
        return f"install JDK {m.group(1)}, which the app’s Gradle toolchain asks for"
    return "fix the build error above, then run reflex_init.py again"


def kotlin_setup(app, pick, out):
    text = read(pick["file"])
    project = gradle_project(app, pick["file"])
    config = {"class": pick["class"], "name": short_name(pick["name"]), "fakes": kotlin_fakes(app),
              "params": kotlin_methods(text), "omit": [], "events": kotlin_events(app), "ctors": kotlin_ctors(app)}
    write_json(out / "auto.json", config)
    jar = auto_jar()
    gradlew = app / "gradlew"
    if not gradlew.exists():
        raise Stop("the app has no gradlew. Add the Gradle wrapper, then run reflex_init.py again")
    classpath = out / ".build/classpath.txt"
    task = f"{project}:reflexClasspath" if project != ":" else ":reflexClasspath"
    env = jdk_env(app)
    say(f"BUILD {task} (the app’s JVM unit test classpath, no app file changed)")
    cmd = [str(gradlew), "-p", str(app), "-I", str(HERE / "gradle/reflex-classpath.gradle"), f"-PreflexProject={project}",
           f"-PreflexOut={classpath}", f"-PreflexJar={jar}", task, "--console=plain", "--no-configuration-cache",
           "-Dorg.gradle.unsafe.isolated-projects=false", "-Dorg.gradle.isolated-projects=false",
           "-Dorg.gradle.configuration-cache=false", "--no-configure-on-demand"]
    code, log = run(cmd, cwd=app, env=env)
    (out / ".build").mkdir(parents=True, exist_ok=True)
    (out / ".build/gradle.log").write_text(log)
    if code or not classpath.exists():
        why = gradle_error(log)
        raise Stop(f"Gradle could not make the classpath: {why}. Next: {kotlin_next_step(why)}. Log: {out / '.build/gradle.log'}")
    root = os.path.relpath(app, out)
    return config, {"kotlin": {"command": ["{java}", "-Xmx512m", f"@{{root}}/{OUT.as_posix()}/.build/classpath.txt",
                                           "reflex.kit.auto.AutoHostKt", f"{{root}}/{OUT.as_posix()}/auto.json", "{fixture}"]}}, root


# ---------- shared ----------

def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")


def runner(manifest, journeys, *extra):
    cmd = [sys.executable, str(HERE / "reflex_runner.py"), str(manifest), *map(str, journeys), "--timings", "0", *extra]
    code, out = run(cmd, timeout=900)
    return code, out


def transcript_states(folder):
    states = {}
    for path in Path(folder).glob("transcript-*.ndjson"):
        for line in path.read_text().splitlines():
            entry = json.loads(line)
            if "received" in entry and entry.get("received"):
                states[entry["step"]] = json.loads(entry["received"])
    return states


def differing_keys(a, b, out):
    if isinstance(a, dict) and isinstance(b, dict):
        for key in set(a) | set(b):
            if key not in a or key not in b:
                out.add(key)
            elif a[key] != b[key]:
                if isinstance(a[key], (dict, list)) and isinstance(b[key], type(a[key])) and \
                        (not isinstance(a[key], list) or len(a[key]) == len(b[key])):
                    before = len(out)
                    differing_keys(a[key], b[key], out)
                    if len(out) == before:
                        out.add(key)
                else:
                    out.add(key)
    elif isinstance(a, list) and isinstance(b, list) and len(a) == len(b):
        for x, y in zip(a, b):
            differing_keys(x, y, out)
    return out


def first_line(text, pattern):
    for line in text.splitlines():
        if re.search(pattern, line):
            return line.strip()
    return None


def explain(out):
    """The one next step for a failed first run, from the runner’s output."""
    auto = first_line(out, r"could not build")
    if auto:
        return auto.split("STDERR")[-1].strip(" '") + ". Next: add a test double for that type (a class named " \
               "Fake<Type> that implements it), or pick another screen with --screen"
    if "ClassNotFoundException" in out or "NoClassDefFoundError" in out:
        cls = re.search(r"(?:ClassNotFoundException|NoClassDefFoundError):? ([\w.$/]+)", out)
        return f"the host could not load {cls.group(1) if cls else 'a class'}. Next: run reflex_init.py again to rebuild the classpath"
    if "network=denied" in out:
        chain = re.search(r"network: (.+?) can reach the network", out)
        if chain:
            path = chain.group(1).split(" → ")
            need = path[1] if len(path) > 1 else path[0]
            return (f"the app tried the network and the guard blocked it: {chain.group(1)} is a real client. "
                    f"Next: give {path[0]} a test double for {need} (an interface with a Fake{need} in the app’s "
                    "test sources), or pick another screen with --screen")
        return ("the app tried the network and the guard blocked it. Next: add test doubles for the classes that "
                "reach it, or pick another screen with --screen")
    if "BLOCKED" in out:
        return first_line(out, "BLOCKED")
    warn = first_line(out, r"^WARN")
    stderr = first_line(out, r"^STDERR")
    fail = first_line(out, r"^FAIL")
    return "; ".join(x for x in (fail, warn, stderr) if x)[:900] or out.strip()[-600:]


def first_run(app, out, manifest_platforms, name, rebuild=None, root=None):
    """Probe twice, drop what differs between runs, write the first journey and check it with repeat 3."""
    manifest = out / "reflex.json"
    write_json(manifest, {"sample": name, "protocol": 1, "root": root or os.path.relpath(app, out),
                          "defaultFixture": "default", "platforms": manifest_platforms,
                          "journeys": [f"{OUT.as_posix()}/journeys/*.json"],
                          "note": "Written by runner/reflex_init.py. The host is generated: edit tests/reflex/auto.json, not the host."})
    probe = out / ".build/probe.json"
    write_json(probe, {"name": "probe", "steps": [{"send": {"op": "hello", "protocol": 1}, "expect": {"ok": True}},
                                                   {"ls": True, "expect": {"ok": True}}]})
    runs = []
    for attempt in range(2):
        folder = out / f".build/probe-{attempt + 1}"
        shutil.rmtree(folder, ignore_errors=True)
        code, log = runner(manifest, [probe], "--evidence", str(folder))
        (out / f".build/probe-{attempt + 1}.log").write_text(log)
        if code:
            raise Stop(f"the first run failed: {explain(log)}")
        runs.append(transcript_states(folder))
        if attempt == 0:
            for line in log.splitlines():
                if line.startswith(("GUARD", "SIMULATOR", "WARN", "NOTE")):
                    say(line[:300])
    first, second = runs
    hello = first.get(0, {})
    node = (first.get(1) or {}).get("node") or {}
    omit = differing_keys(node.get("state"), (second.get(1) or {}).get("node", {}).get("state"), set())
    if omit:
        say(f"FIX state keys that differ between runs are left out: {', '.join(sorted(omit))}")
        config_path = out / "auto.json"
        config = json.loads(config_path.read_text())
        config["omit"] = sorted(set(config.get("omit", [])) | omit)
        write_json(config_path, config)
        if rebuild:
            rebuild()
        folder = out / ".build/probe-3"
        shutil.rmtree(folder, ignore_errors=True)
        code, log = runner(manifest, [probe], "--evidence", str(folder))
        if code:
            raise Stop(f"the run failed after leaving out changing keys: {explain(log)}")
        node = transcript_states(folder).get(1, {}).get("node") or node
    action_step = try_actions(manifest, out, hello, node)
    journey = {
        "name": "first-run",
        "note": "Written by reflex_init.py from the settled first state. Next: add a journey that runs the screen’s main action.",
        "steps": [
            {"send": {"op": "hello", "protocol": 1}, "expect": {"ok": True, "node": {"name": node.get("name"), "actions": node.get("actions", [])}}},
            {"ls": True, "expect": {"ok": True, "node": {"name": node.get("name"), "state": node.get("state", {})}}},
        ] + ([action_step] if action_step else []) + [
            {"do": "ReflexNoSuchAction", "expect": {"ok": False, "error": {"code": "action.unknown", "path": "$.action"}}},
        ],
    }
    write_json(out / "journeys/first-run.json", journey)
    code, log = runner(manifest, [], "--repeat", "3")
    (out / ".build/first-run.log").write_text(log)
    if code:
        raise Stop(f"the first journey did not pass 3 times: {explain(log)}")
    return hello, node, log


def try_actions(manifest, out, hello, node, limit=3):
    """A step for the first action with no input that runs offline and ends in the same state twice, or None."""
    inputs = (hello.get("node") or {}).get("inputs") or {}
    tried = []
    for action in [a for a in node.get("actions", []) if a not in inputs][:limit]:
        probe = out / ".build/probe-action.json"
        write_json(probe, {"name": "probe-action", "steps": [{"send": {"op": "hello", "protocol": 1}, "expect": {"ok": True}},
                                                             {"do": action, "expect": {"ok": True}}]})
        states = []
        for attempt in range(2):
            folder = out / f".build/probe-action-{attempt + 1}"
            shutil.rmtree(folder, ignore_errors=True)
            code, log = runner(manifest, [probe], "--evidence", str(folder))
            if code or "network=clean" not in log:
                break
            replies = transcript_states(folder)
            states.append((replies[max(replies)] if replies else {}).get("node", {}).get("state"))
        if len(states) == 2 and states[0] == states[1] and states[0] is not None:
            say(f"JOURNEY first-run also runs {action}: it needs no input, works offline and ends in the same state each time")
            return {"do": action, "expect": {"ok": True, "node": {"state": states[0]}}}
        tried.append(action)
    if tried:
        say(f"NOTE first-run runs no action: {', '.join(tried)} failed, used the network or ended differently each time")
    return None


def gitignore(out):
    (out / ".gitignore").write_text(".build/\n")


def rank_by_use(app, found):
    """Adds up to 3 points for each candidate by how many other source files name it: the main screen is used most."""
    suffix = {"kotlin": (".kt",), "flutter": (".dart",), "node": (".ts", ".tsx", ".js", ".jsx"), "swift": (".swift",)}[found[0]["stack"]]
    texts = [(p, read(p)) for p in files(app, suffix, tests=False)]
    for c in found:
        token = c.get("hook") or c["name"]
        refs = sum(1 for p, t in texts if p != c["file"] and re.search(r"\b" + re.escape(token) + r"\b", t))
        c["score"] += min(3, refs)
    return sorted(found, key=lambda c: (-c["score"], c["name"]))


# ---------- main ----------

def candidates(app, stack):
    return {"kotlin": kotlin_candidates, "flutter": flutter_candidates, "node": node_candidates,
            "swift": swift_candidates}[stack](app)


def main(argv):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("app", nargs="?", default=".")
    parser.add_argument("--screen", help="class, hook or provider to serve (default: the best match)")
    parser.add_argument("--stack", choices=["kotlin", "flutter", "node", "swift"])
    parser.add_argument("--list", action="store_true", help="list stacks and state holders, change nothing")
    parser.add_argument("--dry-run", action="store_true", help="same as --list")
    args = parser.parse_args(argv)
    app = Path(args.app).resolve()
    started = time.monotonic()
    stacks = [args.stack] if args.stack else detect(app)
    if not stacks:
        say("STOP no Gradle, Flutter, React Native or Swift project here. Next: run it from the app’s root folder")
        return 2
    say(f"STACK {', '.join(stacks)}")
    found = []
    for stack in stacks:
        found = candidates(app, stack)
        if found:
            break
    if found:
        found = rank_by_use(app, found)
    held = swift_app_holders(app) if not found and "swift" in stacks else []
    if held:
        more = f" and {len(held) - 1} more" if len(held) > 1 else ""
        verb, it = ("hold", "they are") if more else ("holds", "it is")
        say(f"STOP {held[0][0]} in {held[0][1]}{more} {verb} state, but {it} in the Xcode app target, which a Swift package "
            "can’t import. Next: move the model and the types it uses into a Swift package the app depends on, then run "
            "reflex_init.py again, or write the adapter by hand (docs/add-to-your-app.md)")
        return 2
    if not found:
        say(f"STOP no state holder found in {', '.join(stacks)} sources. Reflex needs the screen’s state in a ViewModel, "
            "notifier, store or hook, not in the views. Next: move it there, or write the adapter by hand (docs/add-to-your-app.md)")
        return 2
    for c in found[:8]:
        say(f"FOUND {c['stack']} {c['name']} score={c['score']} {os.path.relpath(c['file'], app)}")
    if args.list or args.dry_run:
        return 0
    pick = found[0]
    if args.screen:
        match = [c for c in found if c["name"] == args.screen or c.get("class") == args.screen]
        if not match:
            say(f"STOP no state holder named {args.screen}. Next: pick one from the FOUND lines")
            return 2
        pick = match[0]
    say(f"PICK {pick['name']} ({pick['stack']})")
    out = app / OUT
    out.mkdir(parents=True, exist_ok=True)
    gitignore(out)
    try:
        setup = {"kotlin": kotlin_setup, "flutter": flutter_setup, "node": node_setup, "swift": swift_setup}[pick["stack"]]
        result = setup(app, pick, out)
        config, platforms, root = result[:3]
        rebuild = result[3] if len(result) > 3 else None
        hello, node, log = first_run(app, out, platforms, config["name"], rebuild, root)
    except Stop as stop:
        say(f"STOP {stop}")
        return 1
    for line in log.splitlines():
        if line.startswith(("JOURNEY", "SUMMARY", "RESULT", "WARN", "PASS", "REPEAT")):
            say(line[:300])
    actions = node.get("actions", [])
    say(f"ACTIONS {', '.join(actions) if actions else 'none: no public method or event takes only simple values (see NOTE)'}")
    say(f"PASS first run of {pick['name']} in {time.monotonic() - started:.0f}s with no hand-written code. "
        f"Files: {OUT.as_posix()}/. Run: python3 {os.path.relpath(HERE / 'reflex_runner.py', app)} {OUT.as_posix()}/reflex.json")
    stand_ins = "stand-in" in log or "stand-in" in "".join(SAID)
    say("Next: replace the stand-ins the host used with fixtures, then add a journey that runs the main action" if stand_ins
        else "Next: add a journey that runs the screen’s main action")
    return 0


# ---------- Flutter ----------

DART_CLASS = re.compile(r"^(?:(?:abstract|sealed|final|base|interface|mixin)\s+)*class\s+(\w+)(?:<[^>{]*>)?\s+(?:extends\s+([\w<>?, ]+?))?\s*(?:with\s+([\w<>, ]+?))?\s*(?:implements\s+[\w<>, ]+?)?\s*\{", re.M)
DART_SIMPLE = {"int": "0", "double": "0.0", "num": "0", "bool": "false", "String": "''"}
# State holders from Riverpod: the host reads them through a ProviderContainer.
RIVERPOD = re.compile(r"(?:AutoDispose)?(?:Async)?(?:Family)?(?:Async)?Notifier<|_\$")


def dart_abstract(header):
    return bool(re.match(r"(?:\w+\s+)*?(abstract|sealed|interface)\s", header))


def dart_package(app):
    m = re.search(r"^name:\s*(\S+)", read(app / "pubspec.yaml"), re.M)
    return m.group(1) if m else "app"


def dart_classes(app):
    """Every top-level class in the app’s Dart files: name -> (path, header, body)."""
    out = {}
    for path in files(app, (".dart",), skip=SKIP_DIRS - {"test"}):
        text = read(path)
        for m in DART_CLASS.finditer(text):
            body = balanced(text, m.end() - 1, "{", "}") or ""
            out.setdefault(m.group(1), []).append((path, m.group(0), body))
    return out


def flutter_candidates(app):
    out = []
    for path in files(app / "lib", (".dart",)) if (app / "lib").is_dir() else []:
        text = read(path)
        for m in DART_CLASS.finditer(text):
            name, sup, mix = m.group(1), m.group(2) or "", m.group(3) or ""
            kind = None
            if "ChangeNotifier" in sup or "ChangeNotifier" in mix:
                kind = "notifier"
            elif re.match(r"(Cubit|Bloc|StateNotifier|ValueNotifier)<", sup):
                kind = sup.split("<")[0].lower()
            elif RIVERPOD.match(sup):
                kind = "riverpod"
            if not kind or dart_abstract(m.group(0)):
                continue
            if re.search(r"^abstract\s+class\s+" + name + r"\b", text, re.M):
                continue
            body = balanced(text, m.end() - 1, "{", "}") or ""
            entry = {"stack": "flutter", "name": name, "file": path, "kind": kind, "body": body, "super": sup,
                     "score": score(name, 6 if kind == "notifier" else 5, body)}
            if kind == "riverpod":
                entry["provider"], entry["provider_file"] = riverpod_provider(app, name, sup) or (None, None)
                if not entry["provider"]:
                    continue
            out.append(entry)
    return sorted(out, key=lambda c: (-c["score"], c["name"]))


def riverpod_provider(app, name, sup):
    """The provider that creates this notifier: a NotifierProvider variable, or the generated one for @riverpod."""
    if sup.startswith("_$"):
        return name[0].lower() + name[1:] + "Provider", None
    for path in files(app / "lib", (".dart",), tests=False):
        m = re.search(r"\bfinal\s+(\w+)\s*=\s*\w*NotifierProvider(?:\.\w+)*\s*(?:<\s*" + re.escape(name) + r"\b[^(]*>)?\s*\(\s*"
                      r"(?:" + re.escape(name) + r"\.new|\(\)\s*=>\s*" + re.escape(name) + r"\s*\()", read(path))
        if m:
            return m.group(1), path
    return None


def dart_type_args(sup):
    """Bloc<E, S> -> [E, S]."""
    return split_top(sup[sup.find("<") + 1:sup.rfind(">")]) if "<" in sup else []


def dart_params(body, name):
    """(positional, named) constructor parameters as dicts: name, type, required, default."""
    m = re.search(r"(?m)^\s+(?:const\s+)?" + re.escape(name) + r"\s*\(", body)
    if not m:
        return [], []
    inner = balanced(body, m.end() - 1)
    if inner is None:
        return [], []
    positional, named = [], []
    for part in split_top(inner):
        group = None
        if part.startswith("{"):
            group, part = "named", part[1:-1] if part.endswith("}") else part[1:]
        elif part.startswith("["):
            group, part = "optional", part[1:-1] if part.endswith("]") else part[1:]
        for p in split_top(part) if group else [part]:
            p = re.sub(r"@\w+(\([^)]*\))?\s*", "", p).strip()
            required = group is None or p.startswith("required ")
            p = re.sub(r"^(required|covariant|final)\s+", "", p)
            default = None
            if "=" in p:
                p, default = [x.strip() for x in p.split("=", 1)]
            field = re.match(r"(this|super)\.(\w+)$", p)
            if field:
                # Dart 3.12 private named parameters: this._repository is passed as repository.
                entry = {"name": field.group(2).lstrip("_") if group == "named" else field.group(2), "field": field.group(1),
                         "type": dart_field_type(body, field.group(2).lstrip("_"))}
            else:
                tm = re.match(r"(.+?)\s+(\w+)$", p)
                if not tm:
                    continue
                entry = {"name": tm.group(2), "type": tm.group(1).strip()}
            entry.update(required=required and default is None and not (entry["type"] or "").endswith("?"), default=default)
            (named if group == "named" else positional).append(entry)
    return positional, named


def dart_field_type(body, name):
    m = re.search(r"(?m)^\s+(?:late\s+)?(?:final\s+)?([\w<>?, ]+?)\s+_?" + re.escape(name) + r"\s*[;=]", body)
    return m.group(1).strip() if m else None


def dart_import(app, host_dir, path, package):
    path = Path(path)
    part = re.search(r"^part\s+of\s+['\"]([^'\"]+)['\"]", read(path), re.M)
    if part:
        path = (path.parent / part.group(1)).resolve()
    for root in path.parents:
        if (root / "pubspec.yaml").exists():
            if (root / "lib") in path.parents:
                return f"package:{dart_package(root)}/{path.relative_to(root / 'lib').as_posix()}"
            break
    return os.path.relpath(path, host_dir)


def dart_value(app, host_dir, package, classes, type_name, imports, stand_ins):
    base = type_name.rstrip("?").split("<")[0].strip()
    if base in DART_SIMPLE:
        return DART_SIMPLE[base]
    if base in ("List", "Iterable"):
        return "const []"
    if base in ("Map", "Set"):
        return "const {}"
    impls = []
    for cname, defs in classes.items():
        for path, header, body in defs:
            if re.search(r"\b(?:extends|implements|with)\b[^{]*\b" + re.escape(base) + r"\b", header) and not dart_abstract(header):
                pos, named = dart_params(body, cname)
                if any(p["required"] for p in pos + named):
                    continue
                fake = bool(FAKE_PREFIX.match(cname)) or is_test_path(path)
                # A mocktail or mockito mock returns null until stubbed, so a real fake or class comes first.
                impls.append((2 if cname.startswith("Mock") else 0 if fake else 1, cname, path))
    if impls:
        _, cname, path = sorted(impls)[0]
        imports.add(dart_import(app, host_dir, path, package))
        stand_ins.setdefault("_used", {})[base] = (f"mock {cname}, a stand-in: its calls return null until stubbed" if cname.startswith("Mock")
                                                   else f"test double {cname}" if FAKE_PREFIX.match(cname) or is_test_path(path) else cname)
        return f"{cname}()"
    defs = classes.get(base)
    if defs:
        path, header, body = defs[0]
        imports.add(dart_import(app, host_dir, path, package))
        pos, named = dart_params(body, base)
        if not dart_abstract(header) and not any(p["required"] for p in pos + named):
            return f"{base}()"
        stand_ins[base] = path
        stand_ins.setdefault("_used", {})[base] = "stand-in (every call returns null)"
        return f"_StandIn{base}()"
    raise Stop(f"no value for a {type_name} argument: the app has no class named {base}. Next: pick another screen with --screen")


def dart_members(body, kind):
    """(state getters and fields, commands, methods) that are public. Methods that take other types go in skipped."""
    state, commands, methods = [], [], []
    skipped = dart_members.skipped = []
    for m in re.finditer(r"(?m)^  (?:@override\s+)?([\w<>?, ]+?)\s+get\s+([a-z]\w*)\s*(?:=>|\{)", body):
        state.append((m.group(2), m.group(1).strip()))
    for m in re.finditer(r"(?m)^  (?:late\s+)?(?:final\s+)?([A-Z][\w<>?, ]*|int|double|bool|num|String\??)\s+([a-z]\w*)\s*(?:;|=)", body):
        if m.group(1) in ("return", "static", "const") or m.group(2) in [s[0] for s in state]:
            continue
        if m.group(1).startswith("Command"):
            commands.append((m.group(2), m.group(1)))
        else:
            state.append((m.group(2), m.group(1)))
    for m in re.finditer(r"(?m)^  (?:@override\s+)?(void|Future<[^>]*>|Future|FutureOr<[^>]*>)\s+([a-z]\w*)\s*\(([^)]*)\)\s*(?:async\s*)?[{=]", body):
        if m.group(2) in ("dispose", "notifyListeners", "addListener", "removeListener", "close", "emit", "onChange", "build",
                          "onError", "onEvent", "onTransition") or (m.group(2) == "add" and kind == "bloc"):
            continue
        params = dart_simple_params(m.group(3))
        if params is None:
            skipped.append(f"{m.group(2)}({m.group(3).strip()})")
        else:
            methods.append((m.group(2), params))
    if kind in ("cubit", "bloc", "statenotifier"):
        state.append(("state", "dynamic"))
    if kind == "riverpod":
        state = [s for s in state if s[0] != "state"]
    if kind == "valuenotifier":
        state.append(("value", "dynamic"))
    return state, commands, methods


DART_FIELD = {"int": "FieldType.int64()", "String": "FieldType.string", "bool": "FieldType.boolean"}


DART_ENUMS = {}


def dart_enums(app):
    """Every enum in the app’s Dart files: name -> path."""
    out = {}
    for path in files(app, (".dart",), tests=False):
        for m in re.finditer(r"^enum\s+(\w+)", read(path), re.M):
            out.setdefault(m.group(1), path)
    return out


def dart_simple_params(text):
    """[(name, type, named)] when every parameter is an int, String, bool or app enum, else None."""
    params = []
    text = text.strip()
    groups = []
    for part in split_top(text):
        if part.startswith("{") or part.startswith("["):
            named = part.startswith("{")
            for p in split_top(part.strip("{}[]")):
                groups.append((p, named))
        else:
            groups.append((part, False))
    for p, named in groups:
        p = re.sub(r"^(required|final)\s+", "", p.strip())
        p = p.split("=")[0].strip()
        if not p:
            continue
        tm = re.match(r"(\w+)\s+(\w+)$", p)
        if not tm or (tm.group(1) not in DART_FIELD and tm.group(1) not in DART_ENUMS):
            return None
        params.append((tm.group(2), tm.group(1), named))
    return params


def dart_call(params):
    return ", ".join((f"{n}: " if named else "") + (f"{t}.values.byName(a['{n}'] as String)" if t in DART_ENUMS else f"a['{n}'] as {t}")
                     for n, t, named in params)


def dart_schema(params):
    return f", input: Schema({{{', '.join(repr(n) + ': ' + DART_FIELD.get(t, 'FieldType.string') for n, t, _ in params)}}})" if params else ""


def dart_events(classes, base, holder):
    """Bloc events: concrete subclasses of the event type whose constructors take simple values."""
    out, skipped = [], []
    prefix = holder[:-4] if holder.endswith("Bloc") else holder
    for cname, defs in sorted(classes.items()):
        for path, header, body in defs:
            if dart_abstract(header) or not re.search(r"\bextends\s+" + re.escape(base) + r"\b", header):
                continue
            pos, named = dart_params(body, cname)
            fields = [(p["name"], p["type"], False) for p in pos] + [(p["name"], p["type"], True) for p in named]
            ok = all(t in DART_FIELD or t in DART_ENUMS for _, t, _ in fields)
            title = cname[len(prefix):] if cname.startswith(prefix) and len(cname) > len(prefix) else cname
            (out if ok else skipped).append((title, cname, fields) if ok else cname)
            break
    return out, skipped


def dart_models(classes, roots):
    """App classes reachable from the state types that have no toJson: their final fields, subclasses first."""
    seen, order = set(), []
    todo = [t for r in roots for t in re.findall(r"[A-Z]\w*", r or "")]
    while todo:
        name = todo.pop(0)
        if name in seen or name not in classes or name in DART_SIMPLE:
            continue
        seen.add(name)
        path, header, body = classes[name][0]
        subs = [c for c, defs in classes.items() if re.search(r"\bextends\s+" + re.escape(name) + r"\b", defs[0][1])]
        todo += subs
        if re.search(r"\btoJson\s*\(", body) or re.match(r"(?:\w+\s+)*enum\b", header):
            continue
        fields = re.findall(r"(?m)^  (?:late\s+)?final\s+([\w<>?, .]+?)\s+([a-z]\w*)\s*[;=]", body)
        for t, _ in fields:
            todo += re.findall(r"[A-Z]\w*", t)
        if fields:
            order.append((name, path, [f for _, f in fields], bool(subs), any(c in seen for c in re.findall(r"extends\s+(\w+)", header))))
    # A subclass is checked before its parent.
    return sorted(order, key=lambda m: m[3])

DART_JSON = r'''
/// Same JSON every run: models through toJson, commands by their flags, anything else by type name.
Object? _j(Object? v, [int d = 0]) {
  if (v == null || v is bool || v is int || v is String) return v;
  if (v is double) return v.toString();
  if (v is Enum) return v.name;
  if (d > 6) return v.runtimeType.toString();
  if (v is Iterable) return [for (final x in v.take(100)) _j(x, d + 1)];
  if (v is Map) return {for (final e in v.entries) if (!_omit.contains('${e.key}')) '${e.key}': _j(e.value, d + 1)};
  final m = _model(v);
  if (m != null) return _j(m, d + 1);
  final dynamic x = v;
  try {
    final Object? m = x.toJson();
    if (m is Map) return _j(m, d + 1);
  } catch (_) {}
  try {
    return {'running': x.running as bool, 'error': x.error as bool, 'completed': x.completed as bool};
  } catch (_) {}
  try {
    // A Riverpod AsyncValue.
    final loading = x.isLoading as bool, failed = x.hasError as bool;
    return {'isLoading': loading, 'hasError': failed, if (!loading && !failed) 'value': _j(x.value, d + 1)};
  } catch (_) {}
  return v.runtimeType.toString();
}

'''


dart_source_meta = {}


def flutter_source(app, pick, out, drop):
    package = dart_package(app)
    host_dir = out / "host"
    classes = dart_classes(app)
    imports = {dart_import(app, host_dir, pick["file"], package), "host.dart"}
    stand_ins = {}
    pos, named = dart_params(pick["body"], pick["name"]) if pick["kind"] != "riverpod" else ([], [])
    args = []
    for p in pos:
        args.append(dart_value(app, host_dir, package, classes, p["type"] or "dynamic", imports, stand_ins) if p["required"] else None)
    args = [a for a in args if a is not None]
    for p in named:
        if p["required"]:
            args.append(f"{p['name']}: {dart_value(app, host_dir, package, classes, p['type'] or 'dynamic', imports, stand_ins)}")
    DART_ENUMS.clear()
    DART_ENUMS.update(dart_enums(app))
    state, commands, methods = dart_members(pick["body"], pick["kind"])
    skipped = list(dart_members.skipped)
    targs = dart_type_args(pick.get("super", ""))
    events = []
    if pick["kind"] == "bloc" and len(targs) == 2:
        events, skipped_events = dart_events(classes, targs[0], pick["name"])
        skipped += skipped_events
    roots = [t for _, t in state] + (targs[-1:] if pick["kind"] in ("bloc", "cubit", "statenotifier", "riverpod") else [])
    models = []
    for mname, mpath, fields, _, sub in dart_models(classes, roots):
        if f"model:{mname}" in drop["entries"]:
            continue
        imports.add(dart_import(app, host_dir, mpath, package))
        kv = ", ".join(f"'{f}': v.{f}" for f in fields)
        models.append((mname, f"  if (v is {mname}) return {{{repr('type') + ': ' + repr(mname) + ', ' if sub else ''}{kv}}};"))
    for params in [p for _, p in methods] + [f for _, _, f in events]:
        for _, t, _ in params:
            if t in DART_ENUMS:
                imports.add(dart_import(app, host_dir, DART_ENUMS[t], package))
    riverpod = pick["kind"] == "riverpod"
    if riverpod:
        lib = next((n for n in ("hooks_riverpod", "flutter_riverpod", "riverpod") if re.search(r"^\s+" + n + r":", read(app / "pubspec.yaml"), re.M)), "riverpod")
        imports.add(f"package:{lib}/{lib}.dart")
        if pick.get("provider_file"):
            imports.add(dart_import(app, host_dir, pick["provider_file"], package))
    lines = ["// Generated by runner/reflex_init.py. Do not edit: run it again instead.", "// ignore_for_file: type=lint"]
    lines += [f"import '{i}';" for i in sorted(imports)]
    lines += ["", f"const _omit = <String>{{{', '.join(repr(k) for k in sorted(drop.get('omit', [])))}}};", DART_JSON]
    entries = {}
    lines.append("/// App classes with no toJson, by their final fields.")
    lines.append("Map<String, Object?>? _model(Object v) {")
    for mname, line in models:
        entries[len(lines) + 1] = f"model:{mname}"
        lines.append(line)
    lines += ["  return null;", "}", ""]
    dart_source_meta.update(skipped=skipped)
    for base in sorted(k for k in stand_ins if k != "_used"):
        lines += [f"/// Stand-in: the app has no test double for {base}.", f"class _StandIn{base} implements {base} {{",
                  "  @override", "  dynamic noSuchMethod(Invocation invocation) => null;", "}", ""]
    name = short_name(pick["name"])
    lines += [f"class AutoNode extends Node {{", "  AutoNode(this.vm);", f"  final {pick['name']} vm;", "  @override",
              f"  String get name => '{name}';", "  @override", "  Map<String, Object?> get state => {"]
    if riverpod:
        lines.append(f"        'state': _j(_container.read({pick['provider']})),")
    for key, _ in state:
        if key in drop.get("omit", []) or f"state:{key}" in drop["entries"]:
            continue
        entries[len(lines) + 1] = f"state:{key}"
        lines.append(f"        '{key}': _j(vm.{key}),")
    lines += ["      };", "  @override", "  Map<String, NodeAction> get actions => {"]
    for key, ctype in commands:
        title = key[0].upper() + key[1:]
        targs = split_top(ctype[ctype.find("<") + 1:-1]) if "<" in ctype else []
        if ctype.startswith("Command0"):
            line = f"        '{title}': NodeAction((_) => vm.{key}.execute()),"
        elif ctype.startswith("Command1") and len(targs) == 2 and targs[1] in DART_FIELD:
            line = (f"        '{title}': NodeAction((a) => vm.{key}.execute(a['value'] as {targs[1]}), "
                    f"input: Schema({{'value': {DART_FIELD[targs[1]]}}})),")
        else:
            continue
        if f"action:{title}" in drop["entries"]:
            continue
        entries[len(lines) + 1] = f"action:{title}"
        lines.append(line)
    for key, params in methods:
        title = key[0].upper() + key[1:]
        if f"action:{title}" in drop["entries"] or any(f"'{title}'" in l for l in lines):
            continue
        entries[len(lines) + 1] = f"action:{title}"
        lines.append(f"        '{title}': NodeAction((a) => vm.{key}({dart_call(params)}){dart_schema(params)}),")
    for title, cname, fields in events:
        if f"action:{title}" in drop["entries"] or any(f"'{title}'" in l for l in lines):
            continue
        entries[len(lines) + 1] = f"action:{title}"
        lines.append(f"        '{title}': NodeAction((a) => vm.add({'const ' if not fields else ''}{cname}({dart_call(fields)})){dart_schema(fields)}),")
    lines += ["      };", "}", ""]
    if riverpod:
        lines += ["final _container = ProviderContainer();", "", "Future<void> main(List<String> args) async {",
                  f"  // Keep the provider alive the way a watching widget does.",
                  f"  _container.listen({pick['provider']}, (_, __) {{}}, fireImmediately: true);",
                  f"  final vm = _container.read({pick['provider']}.notifier);"]
    else:
        lines += ["Future<void> main(List<String> args) async {", f"  final vm = {pick['name']}({', '.join(args)});"]
    lines += ["  await Session.settle();", f"  await Session('{name}', () => AutoNode(vm)).serveStandardIO();", "}", ""]
    return "\n".join(lines), entries, stand_ins.get("_used", {})


def flutter_setup(app, pick, out):
    import reflex_runner as rr
    host_dir = out / "host"
    host_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy(REFLEX / "samples/stacks/flutter/lib/reflex/host.dart", host_dir / "host.dart")
    config = {"class": pick["name"], "name": short_name(pick["name"]), "omit": [], "file": os.path.relpath(pick["file"], app)}
    write_json(out / "auto.json", config)
    flutter = shutil.which("flutter")
    if not flutter:
        raise Stop("no flutter on PATH. Next: install Flutter, then run reflex_init.py again")
    import flutter_kernel
    if not flutter_kernel.package_config(app):
        say("BUILD flutter pub get")
        code, log = run([flutter, "pub", "get"], cwd=app)
        if code:
            line = first_line(log, r"(?i)error|because|could not|workspace") or log.strip()[-300:]
            raise Stop(f"flutter pub get failed: {line}. Next: make flutter pub get pass in {app}, then run reflex_init.py again")
    drop = {"entries": set(), "omit": []}

    def build():
        drop["omit"] = json.loads((out / "auto.json").read_text()).get("omit", [])
        for attempt in range(8):
            source, entries, used = flutter_source(app, pick, out, drop)
            if attempt == 0:
                for base, choice in sorted(used.items()):
                    say(f"NOTE {base}: {choice}")
                if dart_source_meta.get("skipped"):
                    say("NOTE not actions, an argument type can’t come from wire input: " + ", ".join(dart_source_meta["skipped"]))
            (host_dir / "main.dart").write_text(source, encoding="utf-8")
            say("BUILD Dart host kernel for flutter_tester")
            code, log = run([sys.executable, str(HERE / "flutter_kernel.py"), str(host_dir / "main.dart"), str(out / ".build/host.dill")], cwd=app)
            if code == 0:
                return
            bad = {entries[int(n)] for n in re.findall(r"main\.dart:(\d+):\d+: Error", log) if int(n) in entries}
            if not bad:
                raise Stop(f"the generated Dart host did not compile: {first_line(log, 'Error') or log.strip()[-300:]}. "
                           "Next: write this host by hand from samples/stacks/flutter (docs/add-to-your-app.md)")
            say(f"FIX left out what did not compile: {', '.join(sorted(bad))}")
            drop["entries"] |= bad
        raise Stop("the generated Dart host still did not compile after 8 tries")

    build()
    if not rr.flutter_tester():
        raise Stop("Flutter’s engine has no flutter_tester. Next: run flutter precache once")
    rel = OUT.as_posix()
    return config, {"flutter": {"command": ["{flutter_tester}", "--non-interactive", "--disable-vm-service",
                                            "--dart-entrypoint-args={fixture}", f"{{root}}/{rel}/.build/host.dill"]}}, \
        os.path.relpath(app, out), build


# ---------- React Native and React ----------

def node_candidates(app):
    out = []
    roots = [app / d for d in ("app", "src", "lib") if (app / d).is_dir()] or [app]
    seen = set()
    for root in roots:
        for path in files(root, (".ts", ".tsx", ".js", ".jsx"), tests=False):
            if path in seen or path.name.endswith(".d.ts"):
                continue
            seen.add(path)
            text = read(path)
            providers = re.findall(r"export\s+(?:const|function)\s+(\w+Provider)\b", text)
            hooks = re.findall(r"export\s+(?:const\s+(use[A-Z]\w*)\s*=\s*(?:\(\s*\)|\(\s*\)\s*:\s*[\w<>| ]+)\s*=>|function\s+(use[A-Z]\w*)\s*\(\s*\))", text)
            hooks = [a or b for a, b in hooks]
            if "createContext" in text and "useContext" in text and providers and hooks:
                hook = next((h for h in hooks if "useContext" in text[text.find(h):text.find(h) + 400]), hooks[0])
                out.append({"stack": "node", "name": hook[3:], "hook": hook, "provider": providers[0], "kind": "context",
                            "file": path, "score": score(hook[3:], 6, text)})
            # zustand: create(...), create<T>()(...) and stores wrapped before export, such as createSelectors(_useStore).
            for m in re.finditer(r"(export\s+)?const\s+(_?use[A-Z]\w*)\s*=\s*create(?:<[^>]*>)?\s*\(", text):
                hook = m.group(2)
                if not m.group(1):
                    wrapped = re.search(r"export\s+const\s+(use[A-Z]\w*)\s*=\s*\w+\(\s*" + re.escape(hook) + r"\s*\)", text)
                    if not wrapped:
                        continue
                    hook = wrapped.group(1)
                name = hook.lstrip("_")[3:]
                out.append({"stack": "node", "name": name, "hook": hook, "kind": "zustand", "file": path,
                            "score": score(name, 6, text)})
    return sorted(out, key=lambda c: (-c["score"], c["name"]))


NODE_HOST = r'''// Generated by runner/reflex_init.py. Do not edit: run it again instead.
// React Native defines these. Node does not, and app code may read them at import time.
;(globalThis as any).__DEV__ = true
;(globalThis as any).IS_REACT_ACT_ENVIRONMENT = true

// eslint-disable-next-line @typescript-eslint/no-require-imports
const { Session, string, int64, boolean } = require("./reflexHost")
// eslint-disable-next-line @typescript-eslint/no-require-imports
const React = require("react")
const OMIT = new Set<string>(__OMIT__)
const NAME = __NAME__
// Parameter names and types read from the source, for functions that take only strings, numbers or booleans.
const SIGNATURES: Record<string, [string, string][]> = __SIGS__
const FIELD: Record<string, any> = { string, boolean, number: int64() }

function json(v: any, d = 0, seen = new Set<any>()): any {
  if (v === null || typeof v === "boolean" || typeof v === "string") return v
  if (typeof v === "number") return Number.isInteger(v) ? v : String(v)
  if (typeof v === "bigint") return v
  if (v === undefined || typeof v === "function" || typeof v === "symbol") return undefined
  if (d > 6 || seen.has(v)) return undefined
  if (v instanceof Date) return v.toISOString()
  seen.add(v)
  try {
    if (Array.isArray(v)) return v.slice(0, 100).map((x) => json(x, d + 1, seen) ?? null)
    if (v instanceof Map) return json(Object.fromEntries(v), d, seen)
    if (v instanceof Set) return json([...v], d, seen)
    const out: Record<string, any> = {}
    for (const key of Object.keys(v)) {
      if (OMIT.has(key)) continue
      const x = json(v[key], d + 1, seen)
      if (x !== undefined) out[key] = x
    }
    return out
  } finally {
    seen.delete(v)
  }
}

function nodeOf(value: () => any) {
  return () => {
    const v = value() ?? {}
    const state: Record<string, any> = {}
    const actions: Record<string, any> = {}
    for (const key of Object.keys(v).sort()) {
      if (OMIT.has(key)) continue
      if (typeof v[key] === "function") {
        const title = key[0].toUpperCase() + key.slice(1)
        const sig = SIGNATURES[key]
        if (sig && sig.length) {
          actions[title] = {
            input: { required: Object.fromEntries(sig.map(([n, t]) => [n, FIELD[t]])) },
            run: (a: any) => v[key](...sig.map(([n, t]) => (t === "number" ? Number(a[n]) : a[n]))),
          }
        } else if (v[key].length === 0) {
          actions[title] = { run: () => v[key]() }
        }
        continue
      }
      const x = json(v[key])
      if (x !== undefined) state[key] = x
    }
    return { name: NAME, state, actions }
  }
}
'''

NODE_CONTEXT = r'''
// The state lives in a React context: render the real provider and keep what a probe sees.
// eslint-disable-next-line @typescript-eslint/no-require-imports
const { act } = React
// eslint-disable-next-line @typescript-eslint/no-require-imports
const { create } = require("react-test-renderer")
// eslint-disable-next-line @typescript-eslint/no-require-imports
const source = require(__SOURCE__)
let current: any
const Probe = () => {
  current = source[__HOOK__]()
  return null
}
async function start() {
  await act(async () => {
    create(React.createElement(source[__PROVIDER__], null, React.createElement(Probe)))
  })
  // React commits state after a call returns, so each action runs in act and the reply waits for it.
  new Session(NAME, nodeOf(() => current)).serveStandardIO({
    around: (run: () => unknown) => act(async () => { await run() }),
  })
}
start()
'''

NODE_ZUSTAND = r'''
// The state lives in a zustand store: read it with getState, no rendering needed.
// Native modules (react-native, expo, react-native-*) can’t load in Node: give them stand-ins with empty values.
// eslint-disable-next-line @typescript-eslint/no-require-imports
const Module = require("module")
const NATIVE = /^(react-native($|[-/])|@react-native|expo($|[-/])|@expo\/)/
const stood = new Set<string>()
function standIn(name: string): any {
  const fn = function () {}
  return new Proxy(fn, {
    get: (_t, key) => {
      if (key === "then" || typeof key === "symbol") return undefined
      if (key === "__esModule") return true
      return standIn(String(key))
    },
    // Factories and classes give back an object; other calls return nothing.
    apply: () => (/^(create|make|new|init|get[A-Z]\w*Instance)/.test(name) || /^[A-Z]/.test(name) ? standIn(name + "()") : undefined),
    construct: () => standIn(name),
  })
}
const load = Module._load
Module._load = function (request: string, ...rest: any[]) {
  if (NATIVE.test(request)) {
    if (!stood.has(request)) process.stderr.write(`ReflexKit auto: ${request}: stand-in (a native module, returns empty values)\n`)
    stood.add(request)
    return standIn(request)
  }
  return load.call(this, request, ...rest)
}
// eslint-disable-next-line @typescript-eslint/no-require-imports
const source = require(__SOURCE__)
const store = source[__HOOK__]
new Session(NAME, nodeOf(() => store.getState())).serveStandardIO({ around: async (run: () => unknown) => { await run() } })
'''


def node_signatures(text):
    """({function: [(param, type)]} for functions whose parameters are all string, number or boolean, [the others])."""
    sigs, skipped = {}, []
    for m in re.finditer(r"\b(\w+)\s*[:=]\s*(?:async\s*)?\(([^()]*)\)\s*(?::\s*[\w<>| ]+)?\s*=>", text):
        name, params = m.group(1), [p.strip() for p in m.group(2).split(",") if p.strip()]
        if not params or name in sigs:
            continue
        parsed = [re.match(r"(\w+)\??\s*:\s*(string|number|boolean)$", p) for p in params]
        if all(parsed):
            sigs[name] = [(p.group(1), p.group(2)) for p in parsed]
            if name in skipped:
                skipped.remove(name)
        elif any(":" in p for p in params) and name not in skipped:
            skipped.append(name)
    return sigs, skipped


def node_setup(app, pick, out):
    host_dir = out / "host"
    host_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy(REFLEX / "samples/stacks/react-native/src/reflexHost.js", host_dir / "reflexHost.js")
    config = {"hook": pick["hook"], "name": short_name(pick["name"]), "omit": [], "file": os.path.relpath(pick["file"], app)}
    write_json(out / "auto.json", config)
    modules = app / "node_modules"
    if not modules.is_dir():
        raise Stop("node_modules is missing. Next: install the app’s packages (npm install, yarn or pnpm install), then run reflex_init.py again")
    if pick["kind"] == "context" and not (modules / "react-test-renderer").is_dir():
        react = json.loads(read(modules / "react/package.json") or "{}").get("version", "")
        raise Stop(f"react-test-renderer is not installed. Next: add it as a dev dependency at React’s version, "
                   f"npm install -D react-test-renderer@{react}")
    tsx = modules / "tsx/dist/cli.mjs"
    typescript = pick["file"].suffix in (".ts", ".tsx")
    if typescript and not tsx.exists():
        raise Stop("the state is in TypeScript and tsx is not installed. Next: npm install -D tsx")

    def build():
        omit = json.loads((out / "auto.json").read_text()).get("omit", [])
        src = os.path.relpath(pick["file"].with_suffix(""), host_dir)
        src = src if src.startswith(".") else "./" + src
        body = NODE_CONTEXT if pick["kind"] == "context" else NODE_ZUSTAND
        sigs, _ = node_signatures(read(pick["file"]))
        text = (NODE_HOST + body).replace("__OMIT__", json.dumps(omit)).replace("__NAME__", json.dumps(config["name"])) \
            .replace("__SIGS__", json.dumps(sigs)) \
            .replace("__SOURCE__", json.dumps(src)).replace("__HOOK__", json.dumps(pick["hook"])) \
            .replace("__PROVIDER__", json.dumps(pick.get("provider", "")))
        (host_dir / "host.tsx").write_text(text, encoding="utf-8")
        base = next((n for n in ("tsconfig.json", "jsconfig.json") if (app / n).exists()), None)
        tsconfig = {"compilerOptions": {"jsx": "react-jsx", "allowJs": True}}
        if base:
            tsconfig["extends"] = os.path.relpath(app / base, host_dir)
        write_json(host_dir / "tsconfig.json", tsconfig)

    build()
    _, skipped = node_signatures(read(pick["file"]))
    if skipped:
        say("NOTE not actions, an argument type can’t come from wire input: " + ", ".join(skipped))
    rel = OUT.as_posix()
    command = ["{node}", f"{{root}}/node_modules/tsx/dist/cli.mjs", "--tsconfig", f"{{root}}/{rel}/host/tsconfig.json",
               f"{{root}}/{rel}/host/host.tsx", "{fixture}"]
    if not tsx.exists():
        raise Stop("tsx is not installed and the generated host is TypeScript. Next: npm install -D tsx")
    say("BUILD none: tsx runs the generated host from source")
    return config, {"react": {"command": command}}, os.path.relpath(app, out), build


# ---------- Swift ----------

SWIFT_TYPE = re.compile(r"(?m)^(?P<attrs>(?:[ \t]*@\w+(?:\([^)]*\))?[ \t]*\n?)*)[ \t]*(?:(?:public|open|internal|final|package)\s+)*"
                        r"class\s+(?P<name>\w+)\s*(?::\s*(?P<sup>[^{]+))?\{")


def swift_packages(app):
    return sorted(p.parent for p in files(app, ("Package.swift",)) if p.name == "Package.swift" and OUT.as_posix() not in p.as_posix())


def swift_target(package, path):
    """The target that owns a source file: a target whose path: holds it, else the Sources/<name> folder."""
    text = read(package / "Package.swift")
    for m in re.finditer(r"\.(?:target|executableTarget)\(\s*name:\s*\"([^\"]+)\"", text):
        inner = balanced(text, text.find("(", m.start())) or ""
        where = re.search(r"\bpath:\s*\"([^\"]+)\"", inner)
        if where and (package / where.group(1)).resolve() in path.resolve().parents:
            return m.group(1)
    return path.relative_to(package / "Sources").parts[0]


def swift_app_holders(app):
    """[(name, path)] of observable models in app sources outside any Swift package, best first."""
    inside = [p.resolve() for p in swift_packages(app)]
    out = []
    for path in files(app, (".swift",), tests=False):
        if path.name == "Package.swift" or any(p in path.resolve().parents for p in inside):
            continue
        for m in SWIFT_TYPE.finditer(read(path)):
            attrs, sup, name = m.group("attrs") or "", m.group("sup") or "", m.group("name")
            if "@Observable" in attrs or "ObservableObject" in sup or name.endswith("ViewModel"):
                out.append((score(name, 6, ""), name, os.path.relpath(path, app)))
    return [(n, p) for _, n, p in sorted(out, key=lambda x: (-x[0], x[1]))]


def swift_candidates(app):
    out = []
    for package in swift_packages(app):
        sources = package / "Sources"
        if not sources.is_dir():
            continue
        for path in files(sources, (".swift",), tests=False):
            text = read(path)
            for m in SWIFT_TYPE.finditer(text):
                attrs, sup, name = m.group("attrs") or "", m.group("sup") or "", m.group("name")
                base = 6 if "@Observable" in attrs or "ObservableObject" in sup else (3 if name.endswith("ViewModel") else 0)
                if not base:
                    continue
                target = swift_target(package, path)
                body = balanced(text, m.end() - 1, "{", "}") or ""
                out.append({"stack": "swift", "name": name, "file": path, "package": package, "target": target,
                            "main_actor": "@MainActor" in attrs or "@MainActor" in text[:m.start()][-200:],
                            "body": body, "score": score(name, base, body)})
    return sorted(out, key=lambda c: (-c["score"], c["name"]))


def swift_init(body):
    """Parameter lists of each init, as [(label, type, has default)]."""
    out = []
    for m in re.finditer(r"(?m)^\s+(?:(?:public|internal|package|convenience|required|nonisolated)\s+)*init\s*\(", body):
        inner = balanced(body, m.end() - 1)
        if inner is None:
            continue
        params = []
        for part in split_top(inner):
            pm = re.match(r"(\w+)(?:\s+(\w+))?\s*:\s*([^=]+?)\s*(=.*)?$", part.strip())
            if pm:
                params.append((pm.group(1), pm.group(3).strip(), bool(pm.group(4))))
        out.append(params)
    return out


def swift_value(type_name, package):
    t = type_name.strip()
    simple = {"String": '""', "Int": "0", "Bool": "false", "Double": "0", "Float": "0", "Date": "Date(timeIntervalSince1970: 0)"}
    if t.endswith("?"):
        return "nil"
    if t in simple:
        return simple[t]
    if t.startswith("["):
        return "[:]" if ":" in t else "[]"
    base = re.sub(r"^(any|some)\s+", "", t)
    found = []
    for path in files(package / "Sources", (".swift",)):
        text = read(path)
        for m in re.finditer(r"(?m)^\s*(?:(?:public|internal|final|package)\s+)*(?:struct|class|actor)\s+(\w+)\s*:\s*[^{]*\b" + re.escape(base) + r"\b", text):
            found.append((0 if FAKE_PREFIX.match(m.group(1)) else 1, m.group(1)))
    if found:
        say(f"NOTE {base}: {sorted(found)[0][1]}")
        return f"{sorted(found)[0][1]}()"
    raise Stop(f"no value for a {t} argument. Next: give that argument a default value, or pick another screen with --screen")


def swift_product(package, target):
    text = read(package / "Package.swift")
    for m in re.finditer(r"\.library\(\s*name:\s*\"([^\"]+)\"[^)]*?targets:\s*\[([^\]]*)\]", text, re.S):
        if f'"{target}"' in m.group(2):
            return m.group(1)
    return target


def swift_package_name(package):
    """A path dependency’s identity: its folder name."""
    return package.name


SWIFT_FIELD = {"String": ("FieldType.string", 'args.string("{n}")'), "Bool": ("FieldType.bool", 'args.bool("{n}")'),
               "Int": ("FieldType.int64()", 'Int(args.int64("{n}"))'), "Int64": ("FieldType.int64()", 'args.int64("{n}")')}


def swift_ids(package):
    """Identifiable types whose id is a String or Int, so a parameter of type Order.ID takes that value."""
    out = {}
    for path in files(package, (".swift",), tests=False):
        text = read(path)
        for m in re.finditer(r"\b(?:struct|class|actor)\s+(\w+)[^{]*\{", text):
            body = balanced(text, m.end() - 1, "{", "}") or ""
            idm = re.search(r"(?m)^\s+(?:public\s+|package\s+)?(?:var|let)\s+id\s*:\s*(String|Int)\b", body)
            if idm:
                out.setdefault(f"{m.group(1)}.ID", idm.group(1))
    return out


def swift_methods(body, ids=None):
    """[(name, async, throws, [(label, name, type)])] for methods that return nothing and take String, Int or Bool.
    swift_methods.skipped lists the others that return nothing."""
    out, skipped = [], []
    for m in re.finditer(r"(?m)^ {2,4}(?:(?:public|internal|package|@MainActor|nonisolated)\s+)*func\s+([a-z]\w*)\s*\(([^()]*)\)\s*(async\s*)?(throws\s*)?(->\s*Void\s*)?\{", body):
        params = []
        for part in [p.strip() for p in m.group(2).split(",") if p.strip()]:
            pm = re.match(r"(\w+)(?:\s+(\w+))?\s*:\s*([\w.]+)$", part)
            t = pm and (ids or {}).get(pm.group(3), pm.group(3))
            if not pm or t not in SWIFT_FIELD:
                params = None
                break
            params.append((pm.group(1), pm.group(2) or pm.group(1), t))
        if params is None:
            skipped.append(f"{m.group(1)}({m.group(2).strip()})")
        else:
            out.append((m.group(1), bool(m.group(3)), bool(m.group(4)), params))
    swift_methods.skipped = skipped
    return out


SWIFT_MAIN = '''// Generated by runner/reflex_init.py. Do not edit: run it again instead.
import Foundation
import ReflexKit
@testable import __MODULE__

let omit: Set<String> = [__OMIT__]

@MainActor
final class AutoNode: Node {
  let vm: __CLASS__
  init(_ vm: __CLASS__) { self.vm = vm }
  var name: String { "__NAME__" }
  var state: JSONValue { Reflect.state(of: vm, omit: omit) }
  var actions: [String: NodeAction] {
    [
__ACTIONS__
    ]
  }
}

// Top-level code runs on the main thread, where a SwiftUI ViewModel lives.
MainActor.assumeIsolated {
  let vm = __CLASS__(__ARGS__)
  let node = AutoNode(vm)
  Session(sample: "__NAME__", root: { node }).serveStandardIOOnMain()
}
'''


def swift_setup(app, pick, out):
    host = out / "host"
    (host / "Sources/reflex-host").mkdir(parents=True, exist_ok=True)
    package, target = pick["package"], pick["target"]
    inits = swift_init(pick["body"])
    args = ""
    if inits and not any(all(d for _, _, d in params) for params in inits):
        params = min(inits, key=len)
        args = ", ".join(f"{label}: {swift_value(t, package)}" if label != "_" else swift_value(t, package)
                         for label, t, d in params if not d)
    config = {"class": pick["name"], "name": short_name(pick["name"]), "omit": [], "file": os.path.relpath(pick["file"], app)}
    write_json(out / "auto.json", config)
    tools = re.search(r"swift-tools-version:\s*([\d.]+)", read(package / "Package.swift"))
    tools = tools.group(1) if tools else "5.9"
    platforms = re.search(r"platforms:\s*(\[[^\]]*\])", read(package / "Package.swift"))
    platforms = platforms.group(1) if platforms else "[.macOS(.v14), .iOS(.v17)]"
    six = tuple(int(x) for x in tools.split(".")[:2]) >= (6, 0)
    rel_pkg = os.path.relpath(package, host)
    rel_kit = os.path.relpath(REFLEX / "kit", host)
    product = swift_product(package, target)
    manifest = f'''// swift-tools-version: {tools}
// Generated by runner/reflex_init.py. A Reflex host for {pick['name']}. It is not part of the app build.
import PackageDescription

let package = Package(
  name: "ReflexHost",
  platforms: {platforms},
  dependencies: [
    .package(path: "{rel_pkg}"),
    .package(path: "{rel_kit}"),
  ],
  targets: [
    .executableTarget(
      name: "reflex-host",
      dependencies: [
        .product(name: "{product}", package: "{swift_package_name(package)}"),
        .product(name: "ReflexKit", package: "kit"),
      ],
      {"swiftSettings: [.swiftLanguageMode(.v5)]," if six else ""}
      // App code may read Bundle.main.infoDictionary, which a plain executable lacks.
      linkerSettings: [.unsafeFlags(["-Xlinker", "-sectcreate", "-Xlinker", "__TEXT", "-Xlinker", "__info_plist", "-Xlinker", "Info.plist"])]
    )
  ]
)
'''
    (host / "Package.swift").write_text(manifest, encoding="utf-8")
    (host / "Info.plist").write_text('<?xml version="1.0" encoding="UTF-8"?>\n<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" '
                                     '"http://www.apple.com/DTDs/PropertyList-1.0.dtd">\n<plist version="1.0"><dict>'
                                     '<key>CFBundleIdentifier</key><string>reflex.host</string>'
                                     '<key>CFBundleShortVersionString</key><string>1.0</string>'
                                     '<key>CFBundleVersion</key><string>1</string></dict></plist>\n')
    # The app’s pinned versions: without them SwiftPM may pick newer ones that fail the platform check.
    resolved = sorted(app.glob("*.xcodeproj/project.xcworkspace/xcshareddata/swiftpm/Package.resolved")) + \
        sorted(app.glob("*.xcworkspace/xcshareddata/swiftpm/Package.resolved")) + [package / "Package.resolved"]
    resolved = next((r for r in resolved if r.exists()), None)
    if resolved:
        shutil.copy(resolved, host / "Package.resolved")
        say(f"FIX pinned package versions copied from {os.path.relpath(resolved, app)}")
    methods = swift_methods(pick["body"], swift_ids(package))
    if swift_methods.skipped:
        say("NOTE not actions, an argument type can’t come from wire input: " + ", ".join(swift_methods.skipped))

    def build():
        omit = json.loads((out / "auto.json").read_text()).get("omit", [])
        lines = []
        for name, is_async, throws, params in methods:
            title = name[0].upper() + name[1:]
            argv = ", ".join(("" if label == "_" else f"{label}: ") + SWIFT_FIELD[t][1].format(n=n) for label, n, t in params)
            call = f"{'try? ' if throws else ''}{'await ' if is_async else ''}self.vm.{name}({argv})"
            schema = (f"input: Schema([{', '.join(f'.required({json.dumps(n)}, {SWIFT_FIELD[t][0]})' for _, n, t in params)}]) "
                      if params else "")
            what = "args" if params else "_"
            if is_async:
                lines.append(f'      "{title}": NodeAction({schema.strip()}) {{ {what} in MainActor.assumeIsolated {{ _ = Task {{ {call} }} }} }},')
            else:
                lines.append(f'      "{title}": NodeAction({schema.strip()}) {{ {what} in MainActor.assumeIsolated {{ {call} }} }},')
        source = SWIFT_MAIN.replace("__MODULE__", target).replace("__CLASS__", pick["name"]).replace("__NAME__", config["name"]) \
            .replace("__ARGS__", args).replace("__OMIT__", ", ".join(json.dumps(k) for k in omit)) \
            .replace("__ACTIONS__", "\n".join(lines) or "      :")
        if not lines:
            source = source.replace("    [\n      :\n    ]", "    [:]")
        (host / "Sources/reflex-host/main.swift").write_text(source, encoding="utf-8")
        ios_only = ".macOS" not in platforms
        if ios_only:
            say(f"BUILD Swift host for the iOS simulator: {os.path.relpath(package, app)} declares only iOS ({platforms})")
        else:
            say("BUILD Swift host (Mac first, the iOS simulator when a package is iOS only)")
        cmd = [sys.executable, str(HERE / "swift_host.py"), str(host), "reflex-host"] + (["--simulator"] if ios_only else [])
        code, log = run(cmd, timeout=2400)
        last = log.strip().splitlines()[-1][:300] if log.strip() else "no output"
        say(last)
        if code:
            where = re.search(r"FAIL (\S+?\.swift):\d+", last)
            if where and Path(where.group(1)).resolve().is_relative_to(app) and not Path(where.group(1)).resolve().is_relative_to(host):
                raise Stop(f"the app’s own package does not build outside its Xcode project: {last[5:].replace(str(app) + os.sep, '')}. Next: run the app’s "
                           "setup step first, such as a secrets or code generation script, then run reflex_init.py again")
            raise Stop(f"the generated Swift host did not build: {log.strip()[-400:]}. "
                       "Next: write the host by hand from samples/stacks (docs/add-to-your-app.md)")

    build()
    rel = OUT.as_posix()
    return config, {"swift": {"command": [f"{{root}}/{rel}/host/.build/reflex/reflex-host", "{fixture}"]}}, os.path.relpath(app, out), build


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
