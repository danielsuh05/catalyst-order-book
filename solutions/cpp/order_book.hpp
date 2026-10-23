#pragma once

#include <algorithm>
#include <cstdint>
#include <iterator>
#include <map>
#include <optional>
#include <stdexcept>
#include <unordered_map>
#include <vector>

// Participant file. Keep the public API and result types unchanged.
struct Trade {
    std::int64_t maker_id, taker_id, price, quantity;
};
struct Level {
    std::int64_t price, quantity;
};

class OrderBook {
    struct Order { char side; std::int64_t price, quantity; };
    std::unordered_map<std::int64_t, Order> orders_;
    std::map<std::int64_t, std::vector<std::int64_t>> bids_, asks_;

    std::vector<Trade> enter(std::int64_t id, char side, std::int64_t price, std::int64_t quantity) {
        auto& other = side == 'B' ? asks_ : bids_;
        std::vector<Trade> trades;
        while (quantity > 0 && !other.empty()) {
            auto it = side == 'B' ? other.begin() : std::prev(other.end());
            const auto best = it->first;
            if ((side == 'B' && best > price) || (side == 'S' && best < price)) break;
            const auto maker_id = it->second.front();
            auto& maker = orders_.at(maker_id);
            const auto filled = std::min(quantity, maker.quantity);
            trades.push_back({maker_id, id, best, filled});
            quantity -= filled;
            maker.quantity -= filled;
            if (maker.quantity == 0) {
                it->second.erase(it->second.begin());
                orders_.erase(maker_id);
                if (it->second.empty()) other.erase(it);
            }
        }
        if (quantity > 0) {
            (side == 'B' ? bids_ : asks_)[price].push_back(id);
            orders_.emplace(id, Order{side, price, quantity});
        }
        return trades;
    }

    std::optional<Level> best(const std::map<std::int64_t, std::vector<std::int64_t>>& levels,
                              bool high) const {
        if (levels.empty()) return std::nullopt;
        auto it = high ? std::prev(levels.end()) : levels.begin();
        std::int64_t total = 0;
        for (auto id : it->second) total += orders_.at(id).quantity;
        return Level{it->first, total};
    }

public:
    std::vector<Trade> add(std::int64_t id, char side, std::int64_t price, std::int64_t quantity) {
        if (orders_.count(id) || (side != 'B' && side != 'S') || price <= 0 || quantity <= 0)
            throw std::invalid_argument("invalid add");
        return enter(id, side, price, quantity);
    }
    std::vector<Trade> modify(std::int64_t id, std::int64_t price, std::int64_t quantity) {
        auto it = orders_.find(id);
        if (it == orders_.end() || price <= 0 || quantity <= 0)
            throw std::invalid_argument("invalid modify");
        if (it->second.price == price) {
            it->second.quantity = quantity;
            return {};
        }
        char side = it->second.side;
        remove(id);
        return enter(id, side, price, quantity);
    }
    void remove(std::int64_t id) {
        auto it = orders_.find(id);
        if (it == orders_.end()) throw std::invalid_argument("unknown order");
        auto& levels = it->second.side == 'B' ? bids_ : asks_;
        auto level = levels.find(it->second.price);
        auto& queue = level->second;
        queue.erase(std::find(queue.begin(), queue.end(), id));
        if (queue.empty()) levels.erase(level);
        orders_.erase(it);
    }
    // C++ reserves "delete" as a keyword; remove is its equivalent.
    std::optional<Level> getBestBid() const { return best(bids_, true); }
    std::optional<Level> getBestAsk() const { return best(asks_, false); }
};

