import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.TreeMap;

/** Participant file. Keep these public methods and records unchanged. */
public final class OrderBook {
    public record Trade(long makerId, long takerId, long price, long quantity) {}
    public record Level(long price, long quantity) {}
    private static final class Order {
        final long id;
        final char side;
        long price;
        long quantity;
        Order(long id, char side, long price, long quantity) {
            this.id = id; this.side = side; this.price = price; this.quantity = quantity;
        }
    }
    private final Map<Long, Order> orders = new HashMap<>();
    private final TreeMap<Long, List<Long>> bids = new TreeMap<>();
    private final TreeMap<Long, List<Long>> asks = new TreeMap<>();

    public List<Trade> add(long id, char side, long price, long quantity) {
        if (orders.containsKey(id) || (side != 'B' && side != 'S') || price <= 0 || quantity <= 0)
            throw new IllegalArgumentException("invalid add");
        return enter(id, side, price, quantity);
    }

    public List<Trade> modify(long id, long price, long quantity) {
        Order old = orders.get(id);
        if (old == null || price <= 0 || quantity <= 0)
            throw new IllegalArgumentException("invalid modify");
        if (old.price == price) {
            old.quantity = quantity;
            return List.of();
        }
        char side = old.side;
        delete(id);
        return enter(id, side, price, quantity);
    }

    public void delete(long id) {
        Order old = orders.remove(id);
        if (old == null) throw new IllegalArgumentException("unknown order");
        TreeMap<Long, List<Long>> levels = old.side == 'B' ? bids : asks;
        List<Long> queue = levels.get(old.price);
        queue.remove(Long.valueOf(id));
        if (queue.isEmpty()) levels.remove(old.price);
    }

    public Level getBestBid() { return best(bids, true); }
    public Level getBestAsk() { return best(asks, false); }

    private Level best(TreeMap<Long, List<Long>> levels, boolean high) {
        if (levels.isEmpty()) return null;
        long price = high ? levels.lastKey() : levels.firstKey();
        long total = 0;
        for (long id : levels.get(price)) total += orders.get(id).quantity;
        return new Level(price, total);
    }

    private List<Trade> enter(long id, char side, long price, long quantity) {
        TreeMap<Long, List<Long>> other = side == 'B' ? asks : bids;
        List<Trade> trades = new ArrayList<>();
        while (quantity > 0 && !other.isEmpty()) {
            long best = side == 'B' ? other.firstKey() : other.lastKey();
            if ((side == 'B' && best > price) || (side == 'S' && best < price)) break;
            List<Long> queue = other.get(best);
            long makerId = queue.get(0);
            Order maker = orders.get(makerId);
            long filled = Math.min(quantity, maker.quantity);
            trades.add(new Trade(makerId, id, best, filled));
            quantity -= filled;
            maker.quantity -= filled;
            if (maker.quantity == 0) {
                queue.remove(0);
                orders.remove(makerId);
                if (queue.isEmpty()) other.remove(best);
            }
        }
        if (quantity > 0) {
            (side == 'B' ? bids : asks).computeIfAbsent(price, ignored -> new ArrayList<>()).add(id);
            orders.put(id, new Order(id, side, price, quantity));
        }
        return trades;
    }
}

