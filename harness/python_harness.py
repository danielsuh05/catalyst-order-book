import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "solutions" / "python"))
from order_book import OrderBook  # noqa: E402

OFFSET = 0xCBF29CE484222325
PRIME = 0x100000001B3
MASK = 0xFFFFFFFFFFFFFFFF


def record(book, op):
    kind = op[0]
    if kind == "A":
        return kind, book.add(op[1], op[2], op[3], op[4])
    elif kind == "M":
        return kind, book.modify(op[1], op[2], op[3])
    elif kind == "D":
        book.delete(op[1])
        return kind, None
    else:
        level = book.getBestBid() if kind == "B" else book.getBestAsk()
        return kind, level


def canonical(result):
    kind, value = result
    if kind == "D":
        return "D"
    if kind in ("B", "S"):
        return kind + "|" + ("-" if value is None else f"{value.price},{value.quantity}")
    return kind + "|" + ";".join(f"{t.maker_id},{t.taker_id},{t.price},{t.quantity}" for t in value)


def parse(path):
    result = []
    with open(path, encoding="ascii") as stream:
        for line in stream:
            p = line.split()
            if not p:
                continue
            if p[0] == "A":
                result.append(("A", int(p[1]), p[2], int(p[3]), int(p[4])))
            elif p[0] == "M":
                result.append(("M", int(p[1]), int(p[2]), int(p[3])))
            elif p[0] == "D":
                result.append(("D", int(p[1])))
            else:
                result.append((p[0],))
    return result


def run(ops):
    book = OrderBook()
    start = time.perf_counter_ns()
    results = [record(book, op) for op in ops]
    elapsed = time.perf_counter_ns() - start
    value = OFFSET
    for result in results:
        line = canonical(result)
        for b in (line + "\n").encode("ascii"):
            value = ((value ^ b) * PRIME) & MASK
    return elapsed, f"{value:016x}"


def main():
    p = argparse.ArgumentParser()
    p.add_argument("trace")
    p.add_argument("--warmups", type=int, default=0)
    p.add_argument("--runs", type=int, default=1)
    args = p.parse_args()
    ops = parse(args.trace)
    for _ in range(args.warmups):
        run(ops)
    measurements = [run(ops) for _ in range(args.runs)]
    if len({digest for _, digest in measurements}) != 1:
        raise RuntimeError("inconsistent result digest")
    print(json.dumps({"digest": measurements[0][1], "times_ns": [t for t, _ in measurements]}))


if __name__ == "__main__":
    main()

