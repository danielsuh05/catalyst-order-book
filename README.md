# Order book competition

Build the fastest correct limit order book in **Python, Java, or C++**. Practice on your own computer against a deliberately terrible baseline. At the end of the contest, the organizer clones each member's **private** project and runs every entry on the same machine with the same hidden workload. There are no public submission PRs, GitHub Actions, or live leaderboard.

## Start and practice

Create your own **private repository** from this starter repository, or clone it and push it to a new private repository. Do not fork the public repository or open a PR to it: those expose your code. If you use an organization repository, check its member access settings. Give the organizer read access to your private project when it is time to submit.

From the project root, run the command for your language:

| Language | macOS / Linux | Windows |
| --- | --- | --- |
| Python | `python3 setup.py python` | `py -3 setup.py python` |
| Java | `python3 setup.py java` | `py -3 setup.py java` |
| C++ | `python3 setup.py cpp` | `py -3 setup.py cpp` |

Python 3.11+ is the bootstrap prerequisite. Java requires JDK 21+; C++ requires a C++20 `g++` or `clang++`. The setup command checks tooling, suggests an install command if needed, runs public correctness tests, and benchmarks your code and the slow baseline on the same 20,000-operation practice trace. No third-party packages are needed. Practice times are local feedback; they do not determine the winner.

Edit the source for your language, and set `submission.json` to its language name:

| Language | Source file | Manifest |
| --- | --- | --- |
| Python | `solutions/python/order_book.py` | `{"language":"python"}` |
| Java | `solutions/java/OrderBook.java` | `{"language":"java"}` |
| C++ | `solutions/cpp/order_book.hpp` | `{"language":"cpp"}` |

Only that one source file is copied into the organizer's build directory. Keep your implementation self-contained and use only the standard library. You may change anything in your private project while practicing, but the final judge uses the original trusted harness and workload generator from this repository.

The common baseline is [`baseline/python/order_book.py`](baseline/python/order_book.py). It stores orders in one unsorted list, repeatedly scans and sorts the entire book, and deliberately rebuilds redundant views on every call. It is correct but intentionally far slower than the supplied starters. Your practice speedup is `baseline time / your time`, both measured on your machine in the same setup run. You can run setup again after each improvement.

## Order book contract

Keep the public API in the starter source: `add(id, side, price, quantity)`, `modify(id, price, quantity)`, `delete(id)`, `getBestBid()`, and `getBestAsk()`. C++ uses `remove(id)` because `delete` is a keyword. Side is `B` or `S`. Prices and quantities are positive 64-bit integers. IDs are unique within a trace. On `modify`, quantity is the new **remaining** quantity. An empty best side returns `None`, `null`, or `std::nullopt`.

- `add` matches against the best opposing prices while its limit price crosses the spread. Orders at one price match in arrival order. Each execution uses the **resting maker's price**. Any unfilled remainder rests in the book.
- A same-price `modify` changes the remaining quantity in place and keeps queue priority, even if quantity increases. A price change removes the order, matches at the new limit price, and places any remainder at the back of its new price level.
- `add` and `modify` return executions in order as `(maker_id, taker_id, price, quantity)`. `delete` removes a resting order. Each best-price call returns `(price, total resting quantity)` for the best level.
- Duplicate IDs, unknown IDs, invalid sides, and nonpositive price or quantity raise the language's standard argument/value exception. Final timed traces contain valid calls only.

The public tests include hand-checked matching, partial fills, deletions, empty best levels, queue priority, and repricing across the spread. The judge also compares the complete result of every operation with an independent reference model before accepting a score.

## Final scoring

The organizer uses one fixed, unpublished seed to generate the same 1,000,000-operation trace for every entry. The generator and scoring code are public; the seed and resulting trace stay on the organizer's machine. The judge prepares inputs before timing, does two warmups and seven timed runs, then scores the median elapsed time for book calls and result capture. Compilation, trace parsing, and result serialization are outside the timer. All languages share one raw-time ranking, so language runtime differences count.

Use the same machine and toolchain for all entries, with other heavy tasks stopped. Each project is graded independently, so very close scores may move with system load. If you change scoring rules or toolchains, rerun all entries.

Implement the book itself. Reading trace files, inspecting the harness, changing process clocks, spawning workers, or hard-coding results is outside the competition rules.

## Organizer: run the final judge

1. Clone each member's private project into a separate folder. Record the chosen commit for each member and check that `submission.json` names the intended language. Use a fresh organizer checkout of this repository for judging.
2. Put a decimal integer in a private text file outside all project folders and outside the starter repository. Keep that file for repeat runs.
3. Run, from the organizer checkout:

   ```sh
   python3 judge.py --seed-file /private/path/orderbook-seed.txt \
     --output /private/path/orderbook-results.json \
     /path/to/alice-project /path/to/bob-project
   ```

   On Windows, use `py -3 judge.py` and Windows paths. The judge prints the ranking and saves passing and failed results in JSON. A failed entry has no rank.

The judge compiles and runs members' source code locally. Run it on a dedicated machine or disposable VM if you do not fully trust every submission. Keep the seed file outside the participant projects. Only the selected source file is copied into each temporary build directory; participant edits to the harness and tests have no effect on final judging.
