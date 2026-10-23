"""Trusted build/test/benchmark driver. Copies only one participant source file."""

import argparse
import json
import os
import shutil
import statistics
import subprocess
import sys
import tempfile
from pathlib import Path

from protocol import reference_digest

ROOT = Path(__file__).resolve().parent.parent
SOURCES = {"python": "order_book.py", "java": "OrderBook.java", "cpp": "order_book.hpp"}


def command(language, build):
    if language == "python":
        return [sys.executable, str(build / "harness" / "python_harness.py")]
    if language == "java":
        return ["java", "-cp", str(build / "classes"), "JavaHarness"]
    return [str(build / ("book_harness.exe" if os.name == "nt" else "book_harness"))]


def prepare(language, source, build):
    (build / "harness").mkdir()
    dest = build / "solutions" / language
    dest.mkdir(parents=True)
    shutil.copy2(source, dest / SOURCES[language])
    if language == "python":
        shutil.copy2(ROOT / "harness" / "python_harness.py", build / "harness")
    elif language == "java":
        shutil.copy2(ROOT / "harness" / "JavaHarness.java", build / "harness")
        (build / "classes").mkdir()
        subprocess.run(["javac", "-encoding", "UTF-8", "-d", str(build / "classes"),
                        str(dest / "OrderBook.java"), str(build / "harness" / "JavaHarness.java")],
                       check=True, capture_output=True, text=True, timeout=45)
    else:
        shutil.copy2(ROOT / "harness" / "cpp_harness.cpp", build / "harness")
        compiler = shutil.which("g++") or shutil.which("clang++")
        if not compiler:
            raise RuntimeError("g++ or clang++ is required")
        binary = build / ("book_harness.exe" if os.name == "nt" else "book_harness")
        subprocess.run([compiler, "-std=c++20", "-O2", "-DNDEBUG", "-o", str(binary),
                        str(build / "harness" / "cpp_harness.cpp")],
                       check=True, capture_output=True, text=True, timeout=45)


def invoke(language, build, trace, warmups, runs):
    cmd = command(language, build)
    cmd += [str(trace), str(warmups), str(runs)] if language != "python" else [str(trace), "--warmups", str(warmups), "--runs", str(runs)]
    done = subprocess.run(cmd, check=True, capture_output=True, text=True, timeout=120,
                          env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"})
    return json.loads(done.stdout.strip())


def grade(language, source, correctness, benchmark, warmups, runs):
    if source.name != SOURCES[language] or not source.is_file():
        raise ValueError(f"expected a {SOURCES[language]} source file")
    with tempfile.TemporaryDirectory() as temp:
        build = Path(temp)
        prepare(language, source, build)
        for trace in correctness:
            expected = reference_digest(trace)
            actual = invoke(language, build, trace, 0, 1)
            if actual["digest"] != expected:
                raise ValueError(f"wrong result on {trace.name}")
        expected = reference_digest(benchmark)
        measured = invoke(language, build, benchmark, warmups, runs)
        if measured["digest"] != expected:
            raise ValueError("wrong result on benchmark trace")
        times = measured["times_ns"]
        if len(times) != runs or not all(type(t) is int and t > 0 for t in times):
            raise ValueError("invalid timing result")
        return {"status": "passed", "language": language, "score_ns": int(statistics.median(times)),
                "times_ns": times, "digest": measured["digest"]}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--language", required=True, choices=SOURCES)
    p.add_argument("--source", required=True, type=Path)
    p.add_argument("--correctness", required=True, nargs="+", type=Path)
    p.add_argument("--benchmark", required=True, type=Path)
    p.add_argument("--warmups", type=int, default=2)
    p.add_argument("--runs", type=int, default=7)
    p.add_argument("--out", type=Path)
    args = p.parse_args()
    try:
        if not 0 <= args.warmups <= 10 or not 1 <= args.runs <= 20:
            raise ValueError("invalid run count")
        result = grade(args.language, args.source, args.correctness, args.benchmark, args.warmups, args.runs)
    except (ValueError, RuntimeError, subprocess.SubprocessError, OSError) as exc:
        # Participant stdout/stderr may contain hidden trace data; never publish it.
        detail = "compile or execution failed; reproduce with public tests"
        if isinstance(exc, ValueError) and not isinstance(exc, json.JSONDecodeError):
            detail = str(exc)
        result = {"status": "failed", "language": args.language, "error": detail}
    payload = json.dumps(result, separators=(",", ":"))
    if args.out:
        args.out.write_text(payload + "\n", encoding="utf-8")
    else:
        print(payload)
    return 0 if result["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())

