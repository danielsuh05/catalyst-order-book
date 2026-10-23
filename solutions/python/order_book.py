"""Participant file. Keep the public API unchanged; replace the internals freely."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Trade:
    maker_id: int
    taker_id: int
    price: int
    quantity: int


@dataclass(frozen=True)
class Level:
    price: int
    quantity: int


class OrderBook:
    def __init__(self) -> None:
        self.orders: dict[int, list] = {}
        self.bids: dict[int, list[int]] = {}
        self.asks: dict[int, list[int]] = {}

    def add(self, order_id: int, side: str, price: int, quantity: int) -> list[Trade]:
        if order_id in self.orders or side not in ("B", "S") or price <= 0 or quantity <= 0:
            raise ValueError("invalid add")
        return self._enter(order_id, side, price, quantity)

    def modify(self, order_id: int, price: int, quantity: int) -> list[Trade]:
        if order_id not in self.orders or price <= 0 or quantity <= 0:
            raise ValueError("invalid modify")
        old = self.orders[order_id]
        if old[1] == price:
            old[2] = quantity
            return []
        side = old[0]
        self.delete(order_id)
        return self._enter(order_id, side, price, quantity)

    def delete(self, order_id: int) -> None:
        if order_id not in self.orders:
            raise ValueError("unknown order")
        side, price, _ = self.orders.pop(order_id)
        levels = self.bids if side == "B" else self.asks
        queue = levels[price]
        queue.remove(order_id)
        if not queue:
            del levels[price]

    def getBestBid(self) -> Level | None:
        return self._best(self.bids, max)

    def getBestAsk(self) -> Level | None:
        return self._best(self.asks, min)

    def _best(self, levels: dict[int, list[int]], choose) -> Level | None:
        if not levels:
            return None
        price = choose(levels)
        return Level(price, sum(self.orders[order_id][2] for order_id in levels[price]))

    def _enter(self, order_id: int, side: str, price: int, quantity: int) -> list[Trade]:
        opposite = self.asks if side == "B" else self.bids
        trades: list[Trade] = []
        while quantity and opposite:
            best = min(opposite) if side == "B" else max(opposite)
            if (side == "B" and best > price) or (side == "S" and best < price):
                break
            queue = opposite[best]
            maker_id = queue[0]
            maker = self.orders[maker_id]
            filled = min(quantity, maker[2])
            trades.append(Trade(maker_id, order_id, best, filled))
            quantity -= filled
            maker[2] -= filled
            if maker[2] == 0:
                queue.pop(0)
                del self.orders[maker_id]
                if not queue:
                    del opposite[best]
        if quantity:
            own = self.bids if side == "B" else self.asks
            own.setdefault(price, []).append(order_id)
            self.orders[order_id] = [side, price, quantity]
        return trades

