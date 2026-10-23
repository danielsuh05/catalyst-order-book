#include "../solutions/cpp/order_book.hpp"
#include <chrono>
#include <cstdint>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

struct Op { char kind; std::int64_t id = 0; char side = 0; std::int64_t price = 0, qty = 0; };
struct Result { std::int64_t nanos; std::string digest; };
struct Entry { char kind; std::vector<Trade> trades; std::optional<Level> level; };

static std::vector<Op> parse(const char* path) {
    std::ifstream in(path);
    if (!in) throw std::runtime_error("trace not found");
    std::vector<Op> ops;
    std::string line;
    while (std::getline(in, line)) {
        if (line.empty()) continue;
        std::istringstream row(line);
        Op op;
        row >> op.kind;
        if (op.kind == 'A') row >> op.id >> op.side >> op.price >> op.qty;
        else if (op.kind == 'M') row >> op.id >> op.price >> op.qty;
        else if (op.kind == 'D') row >> op.id;
        else if (op.kind != 'B' && op.kind != 'S') throw std::runtime_error("invalid trace");
        if (!row) throw std::runtime_error("invalid trace line");
        ops.push_back(op);
    }
    return ops;
}

static std::string trade_line(char kind, const std::vector<Trade>& trades) {
    std::ostringstream out;
    out << kind << '|';
    for (std::size_t i = 0; i < trades.size(); ++i) {
        if (i) out << ';';
        const auto& t = trades[i];
        out << t.maker_id << ',' << t.taker_id << ',' << t.price << ',' << t.quantity;
    }
    return out.str();
}

static Entry record(OrderBook& book, const Op& op) {
    switch (op.kind) {
        case 'A': return {'A', book.add(op.id, op.side, op.price, op.qty), std::nullopt};
        case 'M': return {'M', book.modify(op.id, op.price, op.qty), std::nullopt};
        case 'D': book.remove(op.id); return {'D', {}, std::nullopt};
        case 'B': case 'S': {
            auto level = op.kind == 'B' ? book.getBestBid() : book.getBestAsk();
            return {op.kind, {}, level};
        }
    }
    throw std::runtime_error("invalid op");
}

static std::string canonical(const Entry& entry) {
    if (entry.kind == 'D') return "D";
    if (entry.kind == 'B' || entry.kind == 'S') {
        if (!entry.level) return std::string(1, entry.kind) + "|-";
        return std::string(1, entry.kind) + "|" + std::to_string(entry.level->price) + "," + std::to_string(entry.level->quantity);
    }
    return trade_line(entry.kind, entry.trades);
}

static Result run(const std::vector<Op>& ops) {
    OrderBook book;
    std::vector<Entry> lines;
    lines.reserve(ops.size());
    auto start = std::chrono::steady_clock::now();
    for (const auto& op : ops) lines.push_back(record(book, op));
    auto end = std::chrono::steady_clock::now();
    std::uint64_t hash = 0xcbf29ce484222325ULL;
    for (const auto& entry : lines) {
        const auto line = canonical(entry);
        for (unsigned char byte : line) hash = (hash ^ byte) * 0x100000001b3ULL;
        hash = (hash ^ static_cast<unsigned char>('\n')) * 0x100000001b3ULL;
    }
    std::ostringstream hex;
    hex << std::hex << std::setw(16) << std::setfill('0') << hash;
    return {std::chrono::duration_cast<std::chrono::nanoseconds>(end - start).count(), hex.str()};
}

int main(int argc, char** argv) {
    try {
        if (argc != 4) throw std::runtime_error("trace warmups runs");
        auto ops = parse(argv[1]);
        int warmups = std::stoi(argv[2]);
        int runs = std::stoi(argv[3]);
        for (int i = 0; i < warmups; ++i) run(ops);
        std::string digest;
        std::cout << "{\"digest\":\"";
        std::vector<std::int64_t> times;
        for (int i = 0; i < runs; ++i) {
            auto result = run(ops);
            if (!digest.empty() && digest != result.digest) throw std::runtime_error("inconsistent digest");
            digest = result.digest;
            times.push_back(result.nanos);
        }
        std::cout << digest << "\",\"times_ns\":[";
        for (std::size_t i = 0; i < times.size(); ++i) {
            if (i) std::cout << ',';
            std::cout << times[i];
        }
        std::cout << "]}\n";
    } catch (const std::exception& e) {
        std::cerr << e.what() << '\n';
        return 1;
    }
}

