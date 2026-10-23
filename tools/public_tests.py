"""Hand-checked behavioral fixtures, run against a selected implementation."""

import argparse
import subprocess
import tempfile
from pathlib import Path

from grade import ROOT, SOURCES, command, invoke, prepare
from protocol import digest_lines, reference_digest

TRACE = """B
S
A 1 B 100 10
A 2 B 100 5
B
A 3 S 99 12
B
S
M 2 100 8
A 4 B 100 1
A 5 S 100 4
B
M 4 101 2
B
A 6 S 101 2
B
D 2
B
A 7 S 103 5
A 8 B 102 4
M 8 104 4
S
A 9 B 100 1
A 10 B 101 1
M 9 101 1
A 11 S 101 1
B
M 9 101 2
A 12 B 101 1
A 13 S 101 1
B
"""
EXPECTED = [
    "B|-", "S|-", "A|", "A|", "B|100,15",
    "A|1,3,100,10;2,3,100,2", "B|100,3", "S|-", "M|", "A|",
    "A|2,5,100,4", "B|100,5", "M|", "B|101,2",
    "A|4,6,101,2", "B|100,4", "D", "B|-", "A|", "A|", "M|7,8,103,4", "S|103,1",
    "A|", "A|", "M|", "A|10,11,101,1", "B|101,1", "M|", "A|", "A|9,13,101,1", "B|101,2",
]


def main():
    p = argparse.ArgumentParser()
    p.add_argument("language", choices=SOURCES)
    p.add_argument("--source", type=Path, help="source file to test instead of the starter")
    args = p.parse_args()
    with tempfile.TemporaryDirectory() as path:
        temp = Path(path)
        trace = temp / "edge.trace"
        trace.write_text(TRACE, encoding="ascii")
        expected = digest_lines(EXPECTED)
        assert reference_digest(trace) == expected, "reference disagrees with hand-checked fixture"
        build = temp / "build"
        build.mkdir()
        source = args.source or ROOT / "solutions" / args.language / SOURCES[args.language]
        prepare(args.language, source, build)
        assert invoke(args.language, build, trace, 0, 1)["digest"] == expected, "book disagrees with fixture"
        for invalid in ("D 999\n", "A 1 B 0 1\n", "A 1 X 100 1\n",
                        "A 1 B 100 1\nA 1 B 100 1\n", "A 1 B 100 1\nM 1 100 0\n"):
            trace.write_text(invalid, encoding="ascii")
            cmd = command(args.language, build)
            cmd += ([str(trace), "0", "1"] if args.language != "python" else
                    [str(trace), "--warmups", "0", "--runs", "1"])
            done = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            assert done.returncode != 0, "invalid request was accepted"
    print(f"{args.language}: public behavioral tests passed")


if __name__ == "__main__":
    main()

