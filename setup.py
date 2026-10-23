"""Participant bootstrap: python3 setup.py python|java|cpp (Windows: py -3 setup.py ...)."""

import argparse
import json
import platform
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SOURCES = {"python": "order_book.py", "java": "OrderBook.java", "cpp": "order_book.hpp"}


def missing_tool(language):
    if language == "java" and (not shutil.which("java") or not shutil.which("javac")):
        return "Java JDK 21+ (java and javac)"
    if language == "java":
        version = subprocess.run(["javac", "-version"], capture_output=True, text=True, check=False)
        match = re.search(r"javac\s+(\d+)", version.stdout + version.stderr)
        if version.returncode or not match:
            return "Java JDK 21+ (javac did not run; on macOS it may be the system stub with no JDK on PATH)"
        if int(match.group(1)) < 21:
            return "Java JDK 21+ (javac is too old)"
    if language == "cpp" and not (shutil.which("g++") or shutil.which("clang++")):
        return "a C++20 compiler (g++ or clang++)"
    return None


def hint(language):
    system = platform.system()
    if language == "java":
        return {"Darwin": "brew install openjdk@21", "Linux": "sudo apt install openjdk-21-jdk",
                "Windows": "winget install EclipseAdoptium.Temurin.21.JDK"}.get(system, "Install a JDK 21+.")
    return {"Darwin": "xcode-select --install", "Linux": "sudo apt install g++",
            "Windows": "Install MSYS2 UCRT64, then run: pacman -S mingw-w64-ucrt-x86_64-gcc; add its bin directory to PATH."}.get(system, "Install g++ or clang++ with C++20 support.")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("language", choices=SOURCES)
    args = parser.parse_args()
    if sys.version_info < (3, 11):
        parser.error("Python 3.11 or newer is required")
    absent = missing_tool(args.language)
    if absent:
        parser.error(f"Missing {absent}. Install it with: {hint(args.language)}; then rerun this command.")
    source = ROOT / "solutions" / args.language / SOURCES[args.language]
    tests = subprocess.run([sys.executable, str(ROOT / "tools" / "public_tests.py"), args.language], check=False)
    if tests.returncode:
        return tests.returncode
    with tempfile.TemporaryDirectory() as temp:
        temp = Path(temp)
        traces = []
        for seed, count in ((7, 100), (33, 400), (91, 1000)):
            trace = temp / f"public-{seed}.trace"
            subprocess.run([sys.executable, str(ROOT / "tools" / "workload.py"), "--seed", str(seed),
                            "--count", str(count), "--out", str(trace)], check=True)
            traces.append(trace)
        benchmark = temp / "practice.trace"
        subprocess.run([sys.executable, str(ROOT / "tools" / "workload.py"), "--seed", "2026",
                        "--count", "20000", "--out", str(benchmark)], check=True)
        common = ["--correctness", *map(str, traces), "--benchmark", str(benchmark),
                  "--warmups", "2", "--runs", "3"]
        result = subprocess.run([sys.executable, str(ROOT / "tools" / "grade.py"), "--language", args.language,
                                 "--source", str(source), *common],
                                check=False, capture_output=True, text=True)
        try:
            outcome = json.loads(result.stdout)
            if outcome["status"] == "passed":
                baseline = subprocess.run([sys.executable, str(ROOT / "tools" / "grade.py"),
                                           "--language", "python", "--source",
                                           str(ROOT / "baseline" / "python" / "order_book.py"), *common],
                                          check=False, capture_output=True, text=True)
                baseline_outcome = json.loads(baseline.stdout)
                if baseline.returncode or baseline_outcome["status"] != "passed":
                    print("The bundled slow baseline failed; please report this repository bug.", file=sys.stderr)
                    return 1
                own_ms = outcome["score_ns"] / 1_000_000
                base_ms = baseline_outcome["score_ns"] / 1_000_000
                print(f"{args.language}: your median {own_ms:.3f} ms")
                print(f"Intentionally slow baseline: {base_ms:.3f} ms")
                print(f"Speedup over baseline: {base_ms / own_ms:.1f}x")
            else:
                print(f"{args.language}: {outcome['error']}", file=sys.stderr)
        except (ValueError, KeyError):
            print(result.stderr or result.stdout or "grader failed", file=sys.stderr)
        return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())

