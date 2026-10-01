"""Estimate additional disk space from pinned models, rather than a fixed cutoff."""
import json
from pathlib import Path
import shutil
import model_store

from scripts.download_models import MODELS, MANIFEST_MODEL
from scripts.transcription_models import matches

RESERVE = 6_000_000_000  # Python, torch, Homebrew downloads and temporary files.


def model_entries(root, quant):
    root = Path(root)
    models = model_store.location(root)
    music = json.loads((root / 'models/manifest.json').read_text(encoding='utf-8-sig'))
    for entry in music:
        if entry['path'] == MANIFEST_MODEL:
            selected = ['q8', 'q4'] if quant == 'both' else list(MODELS) if quant == 'all' else [quant]
            for key in selected:
                variant = MODELS[key]
                yield models / 'yue2' / variant['path'], {'size': variant['size'], 'lfs': {'oid': variant['lfs']}}
            continue
        yield models / 'yue2' / entry['path'], entry
    tools = json.loads((root / 'models/tools-manifest.json').read_text(encoding='utf-8'))
    for tool in tools['tools']:
        yield models / 'tools' / tool['directory'] / tool['file'], {
            'size': tool['size'], 'lfs': {'oid': tool['sha256']}}
    sheet = json.loads((root / 'scripts/sheetsage2-revision.json').read_text(encoding='utf-8'))
    for entry in sheet['files']:
        if entry['type'] == 'file':
            yield models / 'SheetSage2' / entry['path'], entry
    mert = json.loads((root / 'scripts/mert-tree.json').read_text(encoding='utf-8'))
    for entry in mert:
        if entry['type'] == 'file' and entry['path'] in ('config.json', 'configuration_mert2.py', 'modeling_mert2.py', 'model.safetensors', 'LICENSE'):
            yield models / 'MERT-v2-FullSong' / entry['path'], entry


def estimate(root, quant):
    # Only verified completed files count as installed. Corrupt files and
    # partial downloads still need space; no dependence on Finder's purgeable total.
    missing = sum(entry['size'] for path, entry in model_entries(root, quant) if not matches(path, entry))
    model_path = model_store.location(root)
    existing = model_path
    while not existing.exists():
        if existing.parent == existing:
            raise ValueError('Il disco della cartella modelli non è disponibile.')
        existing = existing.parent
    separate = not same_volume(root, existing)
    return {'models': missing, 'required': missing + (64 * 1024**2 if separate else RESERVE),
            'free': shutil.disk_usage(existing).free, 'path': str(model_path.resolve()),
            'runtime_required': RESERVE if separate else 0, 'runtime_free': shutil.disk_usage(root).free}


def same_volume(root, models):
    return Path(root).stat().st_dev == Path(models).stat().st_dev


def check(root, quant):
    space = estimate(root, quant)
    gb = lambda size: f'{size / 1_000_000_000:.1f}'
    location = space.get('path', str(Path(root).resolve()))
    print(f"Spazio su {location}: {gb(space['free'])} GB liberi effettivi; servono circa {gb(space['required'])} GB aggiuntivi per {quant.upper()} e i componenti mancanti.", flush=True)
    if space['free'] < space['required']:
        raise RuntimeError(f"Spazio insufficiente nella cartella {location}: {gb(space['free'])} GB liberi effettivi, circa {gb(space['required'])} GB necessari. Finder può includere spazio eliminabile che il sistema non ha ancora liberato.")
    if space.get('runtime_required', 0) > space.get('runtime_free', 0):
        raise RuntimeError(f"Spazio insufficiente per Python e le librerie su {Path(root).resolve()}: servono circa {gb(space['runtime_required'])} GB liberi effettivi.")
    return space
