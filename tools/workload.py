"""Public workload shape. The final seed is kept on the organizer's machine."""

import argparse
from pathlib import Path

from reference import ReferenceBook


class StableRandom:
    """SplitMix64, so the same seed produces the same trace across Python versions."""

    def __init__(self, seed):
        self.state = seed & 0xFFFFFFFFFFFFFFFF

    def below(self, bound):
        self.state = (self.state + 0x9E3779B97F4A7C15) & 0xFFFFFFFFFFFFFFFF
        value = self.state
        value = ((value ^ (value >> 30)) * 0xBF58476D1CE4E5B9) & 0xFFFFFFFFFFFFFFFF
        value = ((value ^ (value >> 27)) * 0x94D049BB133111EB) & 0xFFFFFFFFFFFFFFFF
        return (value ^ (value >> 31)) % bound


def generate(seed: int, count: int):
    rng = StableRandom(seed)
    book = ReferenceBook()
    next_id = 1
    for _ in range(count):
        live = tuple(book.by_id)
        choice = rng.below(100)
        if not live or (len(live) < 1000 and choice < 44):
            side = "B" if rng.below(2) else "S"
            price = max(1, 1000 + rng.below(91) - 45)
            qty = rng.below(100) + 1
            op = f"A {next_id} {side} {price} {qty}"
            book.add(next_id, side, price, qty)
            next_id += 1
        elif choice < 67:
            oid = live[rng.below(len(live))]
            _, old_price, _ = book.by_id[oid]
            price = old_price if rng.below(2) else max(1, old_price + rng.below(41) - 20)
            qty = rng.below(100) + 1
            op = f"M {oid} {price} {qty}"
            book.modify(oid, price, qty)
        elif choice < 78:
            oid = live[rng.below(len(live))]
            op = f"D {oid}"
            book.delete(oid)
        else:
            op = "B" if rng.below(2) else "S"
        yield op


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", required=True, type=int)
    parser.add_argument("--count", required=True, type=int)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    args.out.write_text("\n".join(generate(args.seed, args.count)) + "\n", encoding="ascii")


if __name__ == "__main__":
    main()

