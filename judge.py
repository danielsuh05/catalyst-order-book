"""Run the same final trace against locally cloned private submissions."""

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "tools"))
from grade import SOURCES, grade  # noqa: E402
from workload import generate  # noqa: E402


def trace(path: Path, seed: int, count: int) -> None:
    path.write_text("\n".join(generate(seed, count)) + "\n", encoding="ascii")


def entry(project: Path, correctness: list[Path], benchmark: Path) -> dict:
    label = project.name
    try:
        manifest = json.loads((project / "submission.json").read_text(encoding="utf-8"))
        if not isinstance(manifest, dict) or set(manifest) != {"language"}:
            raise ValueError("invalid submission.json")
        language = manifest["language"]
        if language not in SOURCES:
            raise ValueError("unsupported language")
        source = project / "solutions" / language / SOURCES[language]
        result = grade(language, source, correctness, benchmark, 2, 7)
        return {"name": label, **result}
    except (ValueError, KeyError, OSError, RuntimeError, subprocess.SubprocessError) as exc:
        # Submitted code may print trace data; never echo its stdout or stderr.
        detail = str(exc) if isinstance(exc, ValueError) else "compile, execution, or correctness check failed"
        return {"name": label, "status": "failed", "error": detail}


def main() -> int:
    parser = argparse.ArgumentParser(description="Grade private submissions on this one machine")
    parser.add_argument("--seed-file", required=True, type=Path,
                        help="private text file containing one decimal integer; keep it outside submissions")
    parser.add_argument("--output", type=Path, default=Path("judging-results.json"))
    parser.add_argument("projects", nargs="+", type=Path,
                        help="locally cloned private project directories")
    args = parser.parse_args()
    projects = [project.resolve() for project in args.projects]
    if len({project.name for project in projects}) != len(projects):
        parser.error("project folder names must be unique")
    for project in projects:
        if not project.is_dir():
            parser.error(f"not a project directory: {project}")
    try:
        seed = int(args.seed_file.read_text(encoding="ascii").strip())
    except (OSError, ValueError):
        parser.error("seed file must contain one decimal integer")
    results = []
    with tempfile.TemporaryDirectory(prefix="orderbook-judge-") as directory:
        temp = Path(directory)
        correctness = [temp / "correct-1.trace", temp / "correct-2.trace"]
        trace(correctness[0], seed + 11, 1000)
        trace(correctness[1], seed + 37, 3000)
        benchmark = temp / "benchmark.trace"
        trace(benchmark, seed + 101, 1_000_000)
        for project in projects:
            print(f"Grading {project.name}...", flush=True)
            results.append(entry(project, correctness, benchmark))
    passed = sorted((r for r in results if r["status"] == "passed"),
                    key=lambda r: (r["score_ns"], r["name"]))
    failed = [r for r in results if r["status"] != "passed"]
    for rank, result in enumerate(passed, 1):
        print(f"{rank:>2}. {result['name']:<24} {result['language']:<6} "
              f"{result['score_ns'] / 1_000_000:.3f} ms")
    for result in failed:
        print(f" -- {result['name']}: FAILED ({result['error']})")
    args.output.write_text(json.dumps({"ranked": passed, "failed": failed}, indent=2) + "\n",
                           encoding="utf-8")
    print(f"Saved results to {args.output}")
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())

