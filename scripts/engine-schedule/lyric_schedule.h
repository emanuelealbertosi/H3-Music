// H3-Music: section timing control inspired by HOT-Step C6 / YuE2 Studio (MIT).
// The causal prefill stays unchanged. A soft bias gates future lyric rows only
// while semantic tokens are decoded; this does not force individual syllables.
#pragma once
#include "engine/models/yue2/tokenizer_text.h"
#include <algorithm>
#include <cmath>
#include <filesystem>
#include <fstream>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

namespace engine::models::yue2 {
struct Yue2LyricSpan {
    double start_seconds = 0;
    int64_t first_row = 0;
    int64_t end_row = 0;
};

inline std::vector<Yue2LyricSpan> load_lyric_schedule(
    const std::string & path, const std::string & text, const std::string & lyrics,
    const Yue2TextTokenizer & tokenizer) {
    if (path.empty()) return {};
    std::ifstream file(std::filesystem::u8path(path));
    if (!file) throw std::runtime_error("Cannot open H3 lyric schedule");
    const auto tokens = tokenizer.encode(text);
    std::vector<int64_t> ends;
    int64_t offset = 0;
    for (auto token : tokens) {
        offset += static_cast<int64_t>(tokenizer.token_byte_size(token));
        ends.push_back(offset);
    }
    if (offset != static_cast<int64_t>(text.size()) || text.size() < lyrics.size()+1)
        throw std::runtime_error("H3 lyric schedule token byte mapping mismatch");
    const int64_t lyrics_at = static_cast<int64_t>(text.size()-lyrics.size()-1);
    std::vector<Yue2LyricSpan> spans;
    std::string line;
    int64_t previous_end = 0;
    while (std::getline(file, line)) {
        if (line.empty()) continue;
        std::istringstream row(line);
        double seconds;
        int64_t first, last;
        std::string extra;
        if (!(row >> seconds >> first >> last) || row >> extra || !std::isfinite(seconds) ||
            seconds < 0 || seconds > 900 || first < previous_end || last <= first ||
            last > static_cast<int64_t>(lyrics.size()) || spans.size() >= 128 ||
            (!spans.empty() && seconds < spans.back().start_seconds))
            throw std::runtime_error("Invalid H3 lyric schedule row");
        int64_t begin = 0, a = -1, b = -1;
        for (size_t k = 0; k < ends.size(); ++k) {
            if (ends[k] > lyrics_at+first && begin < lyrics_at+last) {
                if (a < 0) a = static_cast<int64_t>(k)+1; // leading EOD
                b = static_cast<int64_t>(k)+2;
            }
            begin = ends[k];
        }
        if (a < 1 || b <= a) throw std::runtime_error("Empty H3 lyric schedule token span");
        spans.push_back({seconds,a,b});
        previous_end = last;
    }
    if (spans.empty()) throw std::runtime_error("Empty H3 lyric schedule");
    return spans;
}

inline std::vector<float> lyric_prefix_bias(
    const std::vector<Yue2LyricSpan> & spans, size_t prefix_size, double seconds) {
    if (spans.empty()) return {};
    std::vector<float> bias(prefix_size,0.0F);
    for (const auto & span : spans) {
        if (span.first_row < 0 || span.end_row > static_cast<int64_t>(prefix_size))
            throw std::runtime_error("H3 lyric schedule exceeds the semantic prefix");
        if (seconds < span.start_seconds)
            std::fill(bias.begin()+span.first_row,bias.begin()+span.end_row,-4.0F);
    }
    return bias;
}
} // namespace engine::models::yue2
