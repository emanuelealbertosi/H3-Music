# Optional YuE2 LoRA backport

These three source files originate from audio.cpp commit
`542bb4ea2a18273e96b3237e5f1f6941df148d9f` by ShugoAI LLC,
under Apache-2.0 (see LICENSE). H3-Music keeps its existing pinned engine
`13c4192a28d6a212f075c4cbefc5e4983e6ed52a` and applies this isolated,
optional feature through `scripts/patch_engine.py`.

Local change: retain uploaded tensor bytes using the pinned engine's
five-argument conversion API plus `ggml_backend_tensor_get`.
Without adapter paths, the original tensor source is used unchanged.
