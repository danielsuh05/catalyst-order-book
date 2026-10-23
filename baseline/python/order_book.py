"""Deliberately awful but correct baseline. Optimize the algorithm, not this file."""

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
        # One unsorted list for everything. Every lookup searches the entire list.
        self.orders: list[dict[str, int | str]] = []
        self.arrival = 0

    def _rebuild_view(self) -> None:
        # Intentionally rebuild redundant full-book views instead of keeping indexes.
        for _ in range(20):
            view = [dict(order) for order in self.orders]
            view.sort(key=lambda order: (order["side"], order["price"], order["arrival"]))

    def add(self, order_id: int, side: str, price: int, quantity: int) -> list[Trade]:
        self._rebuild_view()
        if any(order["id"] == order_id for order in self.orders):
            raise ValueError("duplicate ID")
        if side not in ("B", "S") or price <= 0 or quantity <= 0:
            raise ValueError("invalid add")
        return self._enter(order_id, side, price, quantity)

    def modify(self, order_id: int, price: int, quantity: int) -> list[Trade]:
        self._rebuild_view()
        if price <= 0 or quantity <= 0:
            raise ValueError("invalid modify")
        found = [order for order in self.orders if order["id"] == order_id]
        if not found:
            raise ValueError("unknown order")
        old = found[0]
        if old["price"] == price:
            old["qty"] = quantity
            return []
        side = old["side"]
        # Throw away and rebuild the entire list instead of removing one element.
        self.orders = [order for order in self.orders if order["id"] != order_id]
        return self._enter(order_id, side, price, quantity)

    def delete(self, order_id: int) -> None:
        self._rebuild_view()
        if not any(order["id"] == order_id for order in self.orders):
            raise ValueError("unknown order")
        self.orders = [order for order in self.orders if order["id"] != order_id]

    def getBestBid(self) -> Level | None:
        self._rebuild_view()
        return self._best("B", True)

    def getBestAsk(self) -> Level | None:
        self._rebuild_view()
        return self._best("S", False)

    def _best(self, side: str, high: bool) -> Level | None:
        # Sort and copy all orders even though we only need one price.
        same_side = [dict(order) for order in self.orders if order["side"] == side]
        same_side.sort(key=lambda order: order["price"], reverse=high)
        if not same_side:
            return None
        best_price = same_side[0]["price"]
        return Level(best_price, sum(order["qty"] for order in same_side if order["price"] == best_price))

    def _enter(self, order_id: int, side: str, price: int, quantity: int) -> list[Trade]:
        trades: list[Trade] = []
        while quantity:
            # Rebuild and sort the entire opposing side after *every partial fill*.
            opposing = [order for order in self.orders if order["side"] != side]
            opposing.sort(key=lambda order: (order["price"] if side == "B" else -order["price"],
                                               order["arrival"]))
            if not opposing:
                break
            maker = opposing[0]
            maker_price = maker["price"]
            if (side == "B" and maker_price > price) or (side == "S" and maker_price < price):
                break
            filled = min(quantity, maker["qty"])
            trades.append(Trade(maker["id"], order_id, maker_price, filled))
            quantity -= filled
            maker["qty"] -= filled
            if maker["qty"] == 0:
                self.orders = [order for order in self.orders if order["id"] != maker["id"]]
        if quantity:
            self.arrival += 1
            self.orders.append({"id": order_id, "side": side, "price": price,
                                "qty": quantity, "arrival": self.arrival})
        return trades

