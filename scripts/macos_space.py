"""Estimate additional disk space from pinned models, rather than a fixed cutoff."""
import json
from pathlib import Path
import shutil

from scripts.download_models import MODELS, MANIFEST_MODEL
from scripts.transcription_models import matches

RESERVE = 6_000_000_000  # Python, torch, Homebrew downloads and temporary files.


def model_entries(root, quant):
    root = Path(root)
    music = json.loads((root / 'models/manifest.json').read_text(encoding='utf-8-sig'))
    for entry in music:
        if entry['path'] == MANIFEST_MODEL:
            variant = MODELS[quant]
            entry = {'path': variant['path'], 'size': variant['size'], 'lfs': {'oid': variant['lfs']}}
        yield root / 'models/yue2' / entry['path'], entry
    tools = json.loads((root / 'models/tools-manifest.json').read_text(encoding='utf-8'))
    for tool in tools['tools']:
        yield root / 'models/tools' / tool['directory'] / tool['file'], {
            'size': tool['size'], 'lfs': {'oid': tool['sha256']}}
    sheet = json.loads((root / 'scripts/sheetsage2-revision.json').read_text(encoding='utf-8'))
    for entry in sheet['files']:
        if entry['type'] == 'file':
            yield root / 'models/SheetSage2' / entry['path'], entry
    mert = json.loads((root / 'scripts/mert-tree.json').read_text(encoding='utf-8'))
    for entry in mert:
        if entry['type'] == 'file' and entry['path'] in ('config.json', 'configuration_mert2.py', 'modeling_mert2.py', 'model.safetensors', 'LICENSE'):
            yield root / 'models/MERT-v2-FullSong' / entry['path'], entry


def estimate(root, quant):
    # Only verified completed files count as installed. Corrupt files and
    # partial downloads still need space; no dependence on Finder's purgeable total.
    missing = sum(entry['size'] for path, entry in model_entries(root, quant) if not matches(path, entry))
    return {'models': missing, 'required': missing + RESERVE, 'free': shutil.disk_usage(root).free}


def check(root, quant):
    space = estimate(root, quant)
    gb = lambda size: f'{size / 1_000_000_000:.1f}'
    location = str(Path(root).resolve())
    print(f"Spazio su {location}: {gb(space['free'])} GB liberi effettivi; servono circa {gb(space['required'])} GB aggiuntivi per {quant.upper()} e i componenti mancanti.", flush=True)
    if space['free'] < space['required']:
        raise RuntimeError(f"Spazio insufficiente nella cartella {location}: {gb(space['free'])} GB liberi effettivi, circa {gb(space['required'])} GB necessari. Finder può includere spazio eliminabile che il sistema non ha ancora liberato.")
    return space
