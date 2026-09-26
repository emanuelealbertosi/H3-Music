from pathlib import Path
r=Path(__file__).resolve().parents[1]/'vendor/audio.cpp'
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
print('Local artifact/plan extension applied')
