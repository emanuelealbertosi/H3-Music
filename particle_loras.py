"""Pinned ordinary rank-8 Particle v2 distills, never the nonlinear teachers."""
import array
import hashlib
import json
import math
import struct
import sys
import urllib.request
from pathlib import Path
import model_store

CATALOG = json.loads((Path(__file__).parent/'particle-catalog.json').read_text(encoding='utf-8'))
ADAPTERS = CATALOG['adapters']


def validate(ident):
    if not isinstance(ident, str) or not ident.startswith('particle-') or ident[9:] not in ADAPTERS:
        raise ValueError('Particle LoRA non valido.')
    return ident[9:]


def strength(value=1):
    if isinstance(value, bool):
        raise ValueError('Intensità Particle non valida (0–1).')
    try:
        result = float(value)
    except (ValueError, TypeError):
        raise ValueError('Intensità Particle non valida (0–1).') from None
    if not math.isfinite(result) or not 0 <= result <= 1:
        raise ValueError('Intensità Particle non valida (0–1).')
    return result


def directory(root):
    return model_store.location(root)/'loras/particle-v2-distilled'


def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def installed(root, ident, verify=False):
    key = validate(ident)
    folder = directory(root)/key
    try:
        record = json.loads((folder/'installed.json').read_text(encoding='utf-8'))
        file = folder/'ar.safetensors'
        return (record['revision'] == CATALOG['revision'] and
                record['source_sha256'] == ADAPTERS[key]['sha256'] and
                record['conversion'] == 1 and file.is_file() and
                file.stat().st_size == record['size'] and
                (not verify or digest(file) == record['sha256']))
    except (OSError, ValueError, KeyError, TypeError):
        return False


def status(root):
    return [{'id': 'particle-'+key, 'label': value['label'], 'installed': installed(root, 'particle-'+key)}
            for key, value in ADAPTERS.items()]


def convert(source, target, concept):
    """Rename all 112 attention pairs without rounding; alpha/rank is exactly 1."""
    with Path(source).open('rb') as stream:
        prefix = stream.read(8)
        if len(prefix) != 8:
            raise ValueError('Intestazione Particle incompleta.')
        size = struct.unpack('<Q', prefix)[0]
        if not 0 < size < 2**20:
            raise ValueError('Intestazione Particle non valida.')
        header = json.loads(stream.read(size))
        data = stream.read()
    meta = json.loads(header.get('__metadata__', {}).get('conceptmod', '{}'))
    if (meta.get('ordinary_lora') is not True or meta.get('rank') != 8 or meta.get('alpha') != 8 or
            meta.get('concept') != concept or meta.get('format') != 'conceptmod-yue2-ar-v1'):
        raise ValueError('Servono i Particle v2 distillati standard, non gli slider originali.')
    consumed = set()
    ranges = []

    def tensor(name, shape):
        entry = header[name]
        start, end = entry['data_offsets']
        count = math.prod(shape)
        if (entry['dtype'] != 'F32' or entry['shape'] != shape or
                not 0 <= start < end <= len(data) or end-start != count*4):
            raise ValueError('Tensore Particle non valido: '+name)
        blob = data[start:end]
        values = array.array('f')
        values.frombytes(blob)
        if sys.byteorder != 'little':
            values.byteswap()
        if not all(map(math.isfinite, values)):
            raise ValueError('Valori Particle non finiti.')
        consumed.add(name)
        ranges.append((start, end))
        return blob

    out = {'__metadata__': {'source': CATALOG['repo'], 'revision': CATALOG['revision'],
                            'variant': 'distilled-rank8-v2', 'conversion': 'H3 lossless rename v1'}}
    blobs = []
    offset = 0
    for layer in range(28):
        for projection, width in [('q', 2048), ('k', 1024), ('v', 1024), ('o', 2048)]:
            prefix = f'adapters.model-layers-{layer}-self_attn-{projection}_proj'
            alpha = struct.unpack('<f', tensor(prefix+'.alpha', []))[0]
            if alpha != 8:
                raise ValueError('Alpha Particle inatteso.')
            for suffix, output, shape in [('lora_down.weight', 'lora_A', [8, 2048]),
                                           ('lora_up.weight', 'lora_B', [width, 8])]:
                blob = tensor(prefix+'.'+suffix, shape)
                name = f'layers.{layer}.self_attn.{projection}_proj.{output}'
                out[name] = {'dtype': 'F32', 'shape': shape, 'data_offsets': [offset, offset+len(blob)]}
                blobs.append(blob)
                offset += len(blob)
    if consumed != set(header)-{'__metadata__'}:
        raise ValueError('Tensori Particle non riconosciuti.')
    cursor = 0
    for start, end in sorted(ranges):
        if start != cursor:
            raise ValueError('Intervalli Particle sovrapposti o incompleti.')
        cursor = end
    if cursor != len(data):
        raise ValueError('Dati Particle incompleti.')
    raw = json.dumps(out, separators=(',', ':')).encode()
    raw += b' '*((-len(raw)) % 8)
    staged = Path(target).with_suffix('.partial')
    with staged.open('wb') as stream:
        stream.write(struct.pack('<Q', len(raw)))
        stream.write(raw)
        for blob in blobs:
            stream.write(blob)
    staged.replace(target)


def session_options(root, ident, value=1):
    key = validate(ident)
    scale = strength(value)
    if scale == 0:
        return {}  # Off is the original native path, without loading or merging.
    if not installed(root, ident, True):
        raise ValueError('Installa o ripara Particle '+ADAPTERS[key]['label']+' da Sistema.')
    return {'yue2.ar_lora': str(directory(root)/key/'ar.safetensors'), 'yue2.ar_lora_scale': scale}


def install(root, identifiers=None, progress=lambda **kwargs: None):
    keys = list(ADAPTERS) if identifiers is None else [validate(i) for i in identifiers]
    if not keys or len(keys) != len(set(keys)):
        raise ValueError('Seleziona Particle da installare senza duplicati.')
    with model_store.exclusive(root):
        model_store.check_idle(root)
        for index, key in enumerate(keys):
            if installed(root, 'particle-'+key, True):
                continue
            info = ADAPTERS[key]
            folder = directory(root)/key
            folder.mkdir(parents=True, exist_ok=True)
            raw = folder/'source.safetensors'
            progress(file=info['label'], status='downloading', done=0, total=info['size'], index=index+1, count=len(keys))
            if not raw.exists() or raw.stat().st_size != info['size'] or digest(raw) != info['sha256']:
                pending = raw.with_suffix('.partial')
                url = f"https://huggingface.co/{CATALOG['repo']}/resolve/{CATALOG['revision']}/{info['file']}"
                request = urllib.request.Request(url, headers={'User-Agent': 'H3-Music'})
                with urllib.request.urlopen(request, timeout=90) as response, pending.open('wb') as stream:
                    done = 0
                    while blob := response.read(2**20):
                        stream.write(blob)
                        done += len(blob)
                        progress(file=info['label'], status='downloading', done=done, total=info['size'])
                if pending.stat().st_size != info['size'] or digest(pending) != info['sha256']:
                    raise ValueError('Download Particle non integro: '+key)
                pending.replace(raw)
            progress(file=info['label'], status='converting')
            output = folder/'ar.safetensors'
            convert(raw, output, key)
            record = {'revision': CATALOG['revision'], 'source_sha256': info['sha256'], 'conversion': 1,
                      'size': output.stat().st_size, 'sha256': digest(output)}
            pending = folder/'installed.tmp'
            pending.write_text(json.dumps(record), encoding='utf-8')
            pending.replace(folder/'installed.json')
        progress(status='completed', file='', done=1, total=1)
