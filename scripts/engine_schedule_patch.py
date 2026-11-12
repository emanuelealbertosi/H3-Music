"""Pinned, idempotent audio.cpp extension for score-timed lyric attention."""
from pathlib import Path


def apply(root):
 root=Path(root)
 def edit(name,old,new):
  path=root/name;s=path.read_text(encoding='utf-8')
  if new in s:return
  if s.count(old)!=1:raise RuntimeError('Unexpected schedule patch anchor: '+name+' '+repr(old[:60]))
  path.write_text(s.replace(old,new,1),encoding='utf-8',newline='\n')
 header=Path(__file__).parent/'engine-schedule/lyric_schedule.h'
 (root/'include/engine/models/yue2/lyric_schedule.h').write_bytes(header.read_bytes())
 edit('include/engine/models/yue2/types.h','    bool h3_plan_only = false;',
      '    bool h3_plan_only = false;\n    std::string h3_lyric_schedule_file;')
 edit('src/models/yue2/request.cpp','    out.h3_artifact_dir =',
      '    out.h3_lyric_schedule_file = runtime::find_option(options, {"h3_lyric_schedule_file"}).value_or("");\n    out.h3_artifact_dir =')
 edit('src/models/yue2/session.cpp','    out.request_options = {',
      '    out.request_options = {\n        {"h3_lyric_schedule_file", "path", "Score-timed lyric attention (H3-Music).", false},')
 edit('include/engine/models/yue2/tokenizer_text.h','    std::vector<int32_t> encode(const std::string & text) const;',
      '    std::vector<int32_t> encode(const std::string & text) const;\n    size_t token_byte_size(int32_t token) const;')
 edit('src/models/yue2/tokenizer_text.cpp','}  // namespace engine::models::yue2', '''size_t Yue2TextTokenizer::token_byte_size(int32_t token) const {
    const auto & text = vocab_->id_to_token.at(token).text;
    if (token >= kEodToken) return text.size();
    // Byte-level BPE maps each original byte to one Unicode codepoint.
    size_t bytes = 0;
    for (unsigned char ch : text) if ((ch & 0xc0) != 0x80) ++bytes;
    return bytes;
}

}  // namespace engine::models::yue2''')
 # A generic runtime hook, inactive unless the YuE2 semantic caller supplies it.
 name='include/engine/framework/modules/transformers/qwen_causal_decode_runtime.h'
 edit(name,'    QwenCausalDecodeStepResult decode_token(int32_t token);',
      '    void set_decode_prefix_bias(const std::vector<float> & bias);\n    QwenCausalDecodeStepResult decode_token(int32_t token);')
 name='src/framework/modules/transformers/qwen_causal_decode_runtime.cpp'
 edit(name,'#include <chrono>','#include <chrono>\n#include <cmath>')
 edit(name,'    QwenCausalDecodeStepResult run_decode_step() {', '''public:
    void set_decode_prefix_bias(const std::vector<float> & bias) {
        for (float value : bias) if (!std::isfinite(value) || value > 0)
            throw std::runtime_error("Invalid decode prefix bias");
        decode_prefix_bias_ = bias;
    }
private:
    std::vector<float> decode_prefix_bias_;
    QwenCausalDecodeStepResult run_decode_step() {''')
 edit(name,'''            cache_slot,
            position);
        core::set_backend_threads''','''            cache_slot,
            position);
        if (!decode_prefix_bias_.empty()) {
            if (decode_prefix_bias_.size() > static_cast<size_t>(decode_cache_.valid_steps()))
                throw std::runtime_error("Decode prefix bias exceeds visible cache");
            for (size_t i = 0; i < decode_prefix_bias_.size(); ++i) {
                const float causal = ggml_fp16_to_fp32(decode_attention_mask_values_[i]);
                decode_attention_mask_values_[i] = ggml_fp32_to_fp16(causal+decode_prefix_bias_[i]);
            }
            ggml_backend_tensor_set(decode_attention_mask_, decode_attention_mask_values_.data(),
                                    0, decode_attention_mask_values_.size()*sizeof(ggml_fp16_t));
        }
        core::set_backend_threads''')
 edit(name,'QwenCausalDecodeStepResult QwenCausalDecodeRuntime::decode_token(int32_t token) {',
      'void QwenCausalDecodeRuntime::set_decode_prefix_bias(const std::vector<float> & bias) {\n    impl_->set_decode_prefix_bias(bias);\n}\n\nQwenCausalDecodeStepResult QwenCausalDecodeRuntime::decode_token(int32_t token) {')
 name='include/engine/models/yue2/ar_runtime.h'
 edit(name,'#include "engine/models/yue2/types.h"','#include "engine/models/yue2/types.h"\n#include "engine/models/yue2/lyric_schedule.h"')
 edit(name,'        uint64_t seed);\n\n    std::vector<int32_t> generate_cfg(',
      '        uint64_t seed,\n        const std::vector<Yue2LyricSpan> & schedule = {});\n\n    std::vector<int32_t> generate_cfg(')
 edit(name,'        float guidance_scale,\n        uint64_t seed);',
      '        float guidance_scale,\n        uint64_t seed,\n        const std::vector<Yue2LyricSpan> & schedule = {});')
 name='src/models/yue2/ar_runtime.cpp'
 edit(name,'''        uint64_t seed) {
        if (prefix.empty())''','''        uint64_t seed,
        const std::vector<Yue2LyricSpan> & schedule = {}) {
        if (prefix.empty())''')
 edit(name,'        const auto total_start = Clock::now();\n        engine::debug::timing_log_scalar("yue2.ar.generate.prefix_tokens", prefix.size());',
      '        active_runtime->set_decode_prefix_bias({});\n        const auto total_start = Clock::now();\n        engine::debug::timing_log_scalar("yue2.ar.generate.prefix_tokens", prefix.size());')
 edit(name,'            logits = active_runtime->decode_token(token).logits;',
      '            active_runtime->set_decode_prefix_bias(lyric_prefix_bias(schedule, prefix.size(), emitted.size()/25.0));\n            logits = active_runtime->decode_token(token).logits;')
 edit(name,'''        uint64_t seed) {
        if (guidance_scale == 1.0F) {
            return generate(positive_prefix, window, seed);
        }''','''        uint64_t seed,
        const std::vector<Yue2LyricSpan> & schedule = {}) {
        if (guidance_scale == 1.0F) {
            return generate(positive_prefix, window, seed, schedule);
        }
        if (!schedule.empty()) throw std::runtime_error("Words follow the score requires cfg_scale=1");''')
 edit(name,'''    uint64_t seed) {
    return impl_->generate(prefix, window, seed);
}''','''    uint64_t seed,
    const std::vector<Yue2LyricSpan> & schedule) {
    return impl_->generate(prefix, window, seed, schedule);
}''')
 edit(name,'''    uint64_t seed) {
    return impl_->generate_cfg(positive_prefix, negative_prefix, window, guidance_scale, seed);
}''','''    uint64_t seed,
    const std::vector<Yue2LyricSpan> & schedule) {
    return impl_->generate_cfg(positive_prefix, negative_prefix, window, guidance_scale, seed, schedule);
}''')
 name='src/models/yue2/pipeline.cpp'
 edit(name,'        const auto music_start = Clock::now();', '''        const auto schedule = load_lyric_schedule(request.h3_lyric_schedule_file,
            request_text(request), request.lyrics, tokenizer);
        if (!schedule.empty() && request.abc.empty())
            throw std::runtime_error("Words follow the score requires a supplied ABC score");
        engine::debug::timing_log_scalar("yue2.lyric_schedule.sections", schedule.size());
        const auto music_start = Clock::now();''')
 edit(name,'            request_guidance_scale(request),\n            request.seed);',
      '            request_guidance_scale(request),\n            request.seed, schedule);')
