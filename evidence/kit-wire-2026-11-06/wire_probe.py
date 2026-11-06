#!/usr/bin/env python3
"""Raw wire probe: sends each case's exact bytes to the Swift and Kotlin CLIs of both reflex samples and
compares stdout byte for byte. Payload escapes: <LF> <CR> <xHH>; <EOF> at the end suppresses the final LF."""
import os, re, shutil, subprocess, sys
R = os.environ.get("REFLEX_ROOT") or os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
JAVA = os.path.realpath(shutil.which("java"))
SAMPLES = {
 "inventory": {"swift": [f"{R}/swift/.build/debug/inventory-cli", "happy"],
               "kotlin": [JAVA, "-Xmx96m", "-cp", f"{R}/kotlin/cli/build/install/cli/lib/*", "reflex.MainKt", "happy"]},
 "outbox": {"swift": [f"{R}/samples/outbox/swift/.build/debug/outbox-cli", "fake"],
            "kotlin": [JAVA, "-Xmx96m", "-cp", f"{R}/samples/outbox/kotlin/cli/build/install/cli/lib/*", "reflex.outbox.MainKt", "fake"]},
}
MAP = {"inventory": [('"action":"Start","input":{"seconds":90,"upNext":', '"action":"OpenProduct","input":{"id":'),
                     ('"action":"Start","input":{"seconds":90,', '"action":"OpenProduct","input":{"id":"shirt",')],
       "outbox": [('"action":"Start","input":{"seconds":90,"upNext":', '"action":"Enqueue","input":{"key":"k","body":'),
                  ('"action":"Start","input":{"seconds":90,', '"action":"Enqueue","input":{"key":"k","body":"b",')]}
def encode(text):
    eof = text.endswith("<EOF>")
    if eof: text = text[:-5]
    out = bytearray()
    for part in re.split(r"(<x[0-9A-Fa-f]{2}>|<LF>|<CR>)", text):
        if part == "<LF>": out += b"\n"
        elif part == "<CR>": out += b"\r"
        elif re.fullmatch(r"<x[0-9A-Fa-f]{2}>", part): out.append(int(part[2:4], 16))
        else: out += part.encode("utf-8")
    return bytes(out) if eof else bytes(out) + b"\n"
def show(b):
    return b.decode("utf-8", "backslashreplace")
NL = b"\n"
only = sys.argv[2:] if len(sys.argv) > 2 else None
same = differ = 0
for raw in open(sys.argv[1], encoding="utf-8"):
    raw = raw.rstrip("\n")
    if not raw or raw.startswith("#"): continue
    cid, hello, payload = raw.split("\t", 2)
    if only and cid not in only: continue
    for sample, cmds in SAMPLES.items():
        p = payload
        for a, b in MAP[sample]: p = p.replace(a, b)
        data = (b'{"op":"hello","protocol":1}\n' if hello == "y" else b"") + encode(p)
        res = {k: subprocess.run(c, input=data, capture_output=True, timeout=20) for k, c in cmds.items()}
        s, k = res["swift"], res["kotlin"]
        tag = f"== {cid} sample={sample} hello={hello} sent_hex={data.hex()}"
        print(tag)
        if s.stdout == k.stdout and s.returncode == k.returncode:
            same += 1
            print(f"BYTES identical exit={s.returncode} lines={s.stdout.count(NL)}")
            for line in s.stdout.split(b"\n")[1 if hello == 'y' else 0:]:
                if line: print("both:   " + show(line))
        else:
            differ += 1
            print(f"BYTES DIFFER swift_exit={s.returncode} kotlin_exit={k.returncode} swift_lines={s.stdout.count(NL)} kotlin_lines={k.stdout.count(NL)}")
            for name, r in (("swift", s), ("kotlin", k)):
                for line in r.stdout.split(b"\n")[1 if hello == 'y' else 0:]:
                    if line: print(f"{name}: " + show(line))
                if r.stderr: print(f"{name} stderr: " + show(r.stderr[:300]))
print(f"PROBE cases={same+differ} identical={same} differ={differ}")
sys.exit(0 if differ == 0 else 1)
