import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;
import java.util.Locale;

public final class JavaHarness {
    private record Op(char type, long id, char side, long price, long quantity) {}
    private record Result(long nanos, String digest) {}
    private record Entry(char type, Object value) {}
    private static final long OFFSET = 0xcbf29ce484222325L;
    private static final long PRIME = 0x100000001b3L;

    private static List<Op> parse(String file) throws IOException {
        List<Op> ops = new ArrayList<>();
        for (String line : Files.readAllLines(Path.of(file))) {
            String[] p = line.split(" ");
            if (p.length == 0 || p[0].isEmpty()) continue;
            switch (p[0]) {
                case "A" -> ops.add(new Op('A', Long.parseLong(p[1]), p[2].charAt(0), Long.parseLong(p[3]), Long.parseLong(p[4])));
                case "M" -> ops.add(new Op('M', Long.parseLong(p[1]), '\0', Long.parseLong(p[2]), Long.parseLong(p[3])));
                case "D" -> ops.add(new Op('D', Long.parseLong(p[1]), '\0', 0, 0));
                case "B" -> ops.add(new Op('B', 0, '\0', 0, 0));
                case "S" -> ops.add(new Op('S', 0, '\0', 0, 0));
                default -> throw new IllegalArgumentException("invalid trace");
            }
        }
        return ops;
    }

    private static String trades(char kind, List<OrderBook.Trade> trades) {
        StringBuilder out = new StringBuilder().append(kind).append('|');
        for (int i = 0; i < trades.size(); ++i) {
            if (i != 0) out.append(';');
            var t = trades.get(i);
            out.append(t.makerId()).append(',').append(t.takerId()).append(',').append(t.price()).append(',').append(t.quantity());
        }
        return out.toString();
    }

    private static Entry record(OrderBook book, Op op) {
        return switch (op.type) {
            case 'A' -> new Entry('A', book.add(op.id, op.side, op.price, op.quantity));
            case 'M' -> new Entry('M', book.modify(op.id, op.price, op.quantity));
            case 'D' -> { book.delete(op.id); yield new Entry('D', null); }
            case 'B', 'S' -> new Entry(op.type, op.type == 'B' ? book.getBestBid() : book.getBestAsk());
            default -> throw new IllegalArgumentException("invalid op");
        };
    }

    @SuppressWarnings("unchecked")
    private static String canonical(Entry entry) {
        if (entry.type == 'D') return "D";
        if (entry.type == 'B' || entry.type == 'S') {
            var level = (OrderBook.Level) entry.value;
            return entry.type + "|" + (level == null ? "-" : level.price() + "," + level.quantity());
        }
        return trades(entry.type, (List<OrderBook.Trade>) entry.value);
    }

    private static Result run(List<Op> ops) {
        OrderBook book = new OrderBook();
        Entry[] results = new Entry[ops.size()];
        long start = System.nanoTime();
        for (int i = 0; i < ops.size(); ++i) results[i] = record(book, ops.get(i));
        long elapsed = System.nanoTime() - start;
        long digest = OFFSET;
        for (Entry entry : results) {
            String line = canonical(entry);
            for (int i = 0; i < line.length(); ++i) {
                digest = (digest ^ (byte) line.charAt(i)) * PRIME;
            }
            digest = (digest ^ (byte) '\n') * PRIME;
        }
        return new Result(elapsed, String.format(Locale.ROOT, "%016x", digest));
    }

    public static void main(String[] args) throws Exception {
        if (args.length != 3) throw new IllegalArgumentException("trace warmups runs");
        List<Op> ops = parse(args[0]);
        int warmups = Integer.parseInt(args[1]);
        int runs = Integer.parseInt(args[2]);
        for (int i = 0; i < warmups; ++i) run(ops);
        StringBuilder json = new StringBuilder("{\"digest\":\"");
        String digest = null;
        List<Long> times = new ArrayList<>();
        for (int i = 0; i < runs; ++i) {
            Result result = run(ops);
            if (digest != null && !digest.equals(result.digest)) throw new IllegalStateException("inconsistent digest");
            digest = result.digest;
            times.add(result.nanos);
        }
        json.append(digest).append("\",\"times_ns\":[");
        for (int i = 0; i < times.size(); ++i) {
            if (i != 0) json.append(',');
            json.append(times.get(i));
        }
        System.out.println(json.append("]}") );
    }
}

