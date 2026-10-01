from pathlib import Path
import argparse
p=argparse.ArgumentParser();p.add_argument('--source',type=Path,default=Path(__file__).resolve().parents[1]/'vendor/audio.cpp');r=p.parse_args().source
def edit(name,old,new):
 p=r/name; s=p.read_text(encoding='utf-8')
 if new in s: return
 assert old in s, name
 p.write_text(s.replace(old,new,1),encoding='utf-8')
edit('include/engine/models/yue2/types.h','struct Yue2Request {','struct Yue2Request {\n    std::string h3_artifact_dir;\n    bool h3_plan_only = false;')
edit('src/models/yue2/request.cpp','    if (const auto cot = runtime::find_option(options, {"cot"})) {','    out.h3_artifact_dir = runtime::find_option(options, {"h3_artifact_dir"}).value_or("");\n    out.h3_plan_only = runtime::find_option(options, {"h3_plan_only"}).value_or("false") == "true";\n    if (const auto cot = runtime::find_option(options, {"cot"})) {')
edit('src/models/yue2/pipeline.cpp','#include <utility>','#include <utility>\n#include <fstream>\n#include <filesystem>')
edit('src/models/yue2/pipeline.cpp','        const auto negative_start = Clock::now();','        if (request.h3_plan_only) return out;\n        const auto negative_start = Clock::now();')
edit('src/models/yue2/pipeline.cpp','        auto semantic = generate_semantic(request, std::move(planned));','''        auto semantic = generate_semantic(request, std::move(planned));
        if (!request.h3_artifact_dir.empty()) {
            const std::filesystem::path dir(request.h3_artifact_dir);
            std::filesystem::create_directories(dir);
            auto save_ids = [&dir](const char *name, const std::vector<int32_t> &ids) {
                std::ofstream file(dir / name, std::ios::binary);
                file.write(reinterpret_cast<const char *>(ids.data()), ids.size() * sizeof(int32_t));
                if (!file) throw std::runtime_error("H3-Music artifact write failed");
            };
            save_ids("abc_tokens.i32", semantic.plan.abc_ids);
            save_ids("semantic_tokens.i32", semantic.tokens);
            std::ofstream(dir / "generation_flags.json") << "{\\"abc_truncated\\":"
                << (semantic.plan.truncated ? "true" : "false") << ",\\"audio_truncated\\":"
                << (semantic.truncated ? "true" : "false") << "}";
        }
        if (request.h3_plan_only) return runtime::AudioBuffer{48000, 2, {}};''')
edit('src/models/yue2/pipeline.cpp','        auto latents = synthesize_latents(semantic, request.generation, request.nar_noise, request.seed);','''        auto latents = synthesize_latents(semantic, request.generation, request.nar_noise, request.seed);
        if (!request.h3_artifact_dir.empty()) {
            std::ofstream file(std::filesystem::path(request.h3_artifact_dir) / "latents.f32", std::ios::binary);
            file.write(reinterpret_cast<const char *>(latents.data()), latents.size() * sizeof(float));
            if (!file) throw std::runtime_error("H3-Music latent write failed");
        }''')
patches=Path(__file__).resolve().parent/'engine-lora'
for src,dest in [('lora_tensor_source.h','include/engine/framework/assets/lora_tensor_source.h'),('lora_tensor_source.cpp','src/framework/assets/lora_tensor_source.cpp'),('lora.cpp','src/models/yue2/lora.cpp')]:
 (r/dest).write_bytes((patches/src).read_bytes())
edit('CMakeLists.txt','    src/framework/assets/tensor_source.cpp','    src/framework/assets/tensor_source.cpp\n    src/framework/assets/lora_tensor_source.cpp')
edit('CMakeLists.txt','        src/models/yue2/assets.cpp','        src/models/yue2/assets.cpp\n        src/models/yue2/lora.cpp')
edit('include/engine/models/yue2/assets.h','std::shared_ptr<const Yue2Assets> load_yue2_assets', '''std::shared_ptr<const assets::TensorSource> make_yue2_lora_source(
    std::shared_ptr<const assets::TensorSource> base,
    const std::filesystem::path & adapter_path, float scale, int64_t layer_count,
    const std::filesystem::path & nar_adapter_path, float nar_scale);

std::shared_ptr<const Yue2Assets> load_yue2_assets''')
edit('src/models/yue2/session.cpp','    validate_component_anchors(*selected);', '''    validate_component_anchors(*selected);
    auto ar_adapter = std::filesystem::u8path(runtime::find_option(options, {"yue2.ar_lora"}).value_or(""));
    auto nar_adapter = std::filesystem::u8path(runtime::find_option(options, {"yue2.nar_lora"}).value_or(""));
    if (!ar_adapter.empty() || !nar_adapter.empty()) {
        if (!ar_adapter.empty() && ar_adapter.is_relative()) ar_adapter = base->model_root / ar_adapter;
        if (!nar_adapter.empty() && nar_adapter.is_relative()) nar_adapter = base->model_root / nar_adapter;
        selected->model_weights = make_yue2_lora_source(selected->model_weights, ar_adapter,
            runtime::parse_finite_float_option(options, {"yue2.ar_lora_scale"}).value_or(1.0F),
            selected->config.model.layers, nar_adapter,
            runtime::parse_finite_float_option(options, {"yue2.nar_lora_scale"}).value_or(1.0F));
    }''')
edit('src/models/yue2/session.cpp','    out.session_options = {', '''    out.session_options = {
        {"yue2.ar_lora", "path", "Optional unfused AR LoRA safetensors.", false},
        {"yue2.nar_lora", "path", "Optional unfused NAR LoRA safetensors.", false},
        {"yue2.ar_lora_scale", "float", "AR LoRA strength.", false, "1"},
        {"yue2.nar_lora_scale", "float", "NAR LoRA strength.", false, "1"},''')
print('Local artifact/plan extension and optional AR/NAR LoRA support applied')
