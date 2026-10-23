"""Independent, deliberately simple correctness oracle."""

from collections import deque


class ReferenceBook:
    def __init__(self):
        self.by_id = {}
        self.buy = {}
        self.sell = {}

    def add(self, oid, side, price, qty):
        if oid in self.by_id or side not in ("B", "S") or price <= 0 or qty <= 0:
            raise ValueError("invalid add")
        return self._place(oid, side, price, qty)

    def modify(self, oid, price, qty):
        if oid not in self.by_id or price <= 0 or qty <= 0:
            raise ValueError("invalid modify")
        side, old_price, _ = self.by_id[oid]
        if price == old_price:
            self.by_id[oid] = (side, price, qty)
            return []
        self.delete(oid)
        return self._place(oid, side, price, qty)

    def delete(self, oid):
        if oid not in self.by_id:
            raise ValueError("unknown order")
        side, price, _ = self.by_id.pop(oid)
        levels = self.buy if side == "B" else self.sell
        levels[price].remove(oid)
        if not levels[price]:
            del levels[price]

    def best_bid(self):
        return self._best(self.buy, max)

    def best_ask(self):
        return self._best(self.sell, min)

    def _best(self, levels, pick):
        if not levels:
            return None
        price = pick(levels)
        return (price, sum(self.by_id[oid][2] for oid in levels[price]))

    def _place(self, oid, side, price, qty):
        other = self.sell if side == "B" else self.buy
        trades = []
        while qty and other:
            best = min(other) if side == "B" else max(other)
            if (side == "B" and price < best) or (side == "S" and price > best):
                break
            maker = other[best][0]
            mside, mprice, mqty = self.by_id[maker]
            amount = min(qty, mqty)
            trades.append((maker, oid, mprice, amount))
            qty -= amount
            if amount == mqty:
                other[best].popleft()
                del self.by_id[maker]
                if not other[best]:
                    del other[best]
            else:
                self.by_id[maker] = (mside, mprice, mqty - amount)
        if qty:
            own = self.buy if side == "B" else self.sell
            own.setdefault(price, deque()).append(oid)
            self.by_id[oid] = (side, price, qty)
        return trades

