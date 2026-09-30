"""Exercise the pinned transcription code with a tiny randomly initialized model.

This checks runtime/API compatibility, not transcription accuracy or real weights.
"""
import hashlib
import json
import os
from pathlib import Path
import tempfile
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
metadata = json.loads((ROOT / 'scripts/sheetsage2-revision.json').read_text())
with tempfile.TemporaryDirectory(prefix='h3-transcription-runtime-') as directory:
    root = Path(directory)
    source = root / 'SheetSage2'
    source.mkdir()
    os.environ.update(HF_MODULES_CACHE=str(root / 'modules'), HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1')
    for item in metadata['files']:
        name = item['path']
        if '/' in name or not (name.endswith('.py') or name == 'config.json'):
            continue
        url = f"https://huggingface.co/m-a-p/SheetSage2/resolve/{metadata['revision']}/{name}"
        with urllib.request.urlopen(url, timeout=60) as response:
            content = response.read()
        blob = b'blob ' + str(len(content)).encode() + b'\0' + content
        assert hashlib.sha1(blob).hexdigest() == item['oid'], name
        (source / name).write_bytes(content)
    import torch
    from transformers import AutoConfig, AutoModel
    from transformers.dynamic_module_utils import get_cached_module_file
    torch.set_num_threads(2)
    get_cached_module_file(str(source), 'tokenization_sheetsage2.py', local_files_only=True)
    config = AutoConfig.from_pretrained(source, trust_remote_code=True, local_files_only=True)
    config.hidden_size = 32
    config.intermediate_size = 64
    config.num_attention_heads = 4
    config.decoder_layers = 1
    config.weights_format = 'merged'
    config.backbone_config.update(hidden_size=32, intermediate_size=64, num_attention_heads=4,
        num_hidden_layers=1, subsampling_channels=[128, 32, 32], subsampling_depths=[1, 1, 1])
    model = AutoModel.from_config(config, trust_remote_code=True).eval()
    with torch.inference_mode():
        result = model(input_values=torch.randn(1, 24000), decoder_input_ids=torch.tensor([[1]]))
    assert result.logits.shape == (1, 1, config.vocab_size)
    assert torch.isfinite(result.logits).all()
    print('Pinned transcription code forward pass passed:', torch.__version__)
