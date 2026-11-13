import json
import struct
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import app
import loras
import particle_loras as particle


def source_file(path, ordinary=True, alpha=8):
    header = {'__metadata__': {'conceptmod': json.dumps({'ordinary_lora': ordinary, 'rank': 8,
              'alpha': 8, 'concept': 'female', 'format': 'conceptmod-yue2-ar-v1'})}}
    blobs = []
    offset = 0
    for layer in range(28):
        for projection, width in [('q', 2048), ('k', 1024), ('v', 1024), ('o', 2048)]:
            prefix = f'adapters.model-layers-{layer}-self_attn-{projection}_proj'
            for suffix, shape, blob in [('alpha', [], struct.pack('<f', alpha)),
                    ('lora_down.weight', [8, 2048], struct.pack('<f', .1234567)*(8*2048)),
                    ('lora_up.weight', [width, 8], struct.pack('<f', -.0376543)*(width*8))]:
                header[prefix+'.'+suffix] = {'dtype': 'F32', 'shape': shape, 'data_offsets': [offset, offset+len(blob)]}
                blobs.append(blob)
                offset += len(blob)
    raw = json.dumps(header).encode()
    path.write_bytes(struct.pack('<Q', len(raw))+raw+b''.join(blobs))


class ParticleTests(unittest.TestCase):
    def test_default_and_cnzn_preserved(self):
        self.assertEqual(app.validate({})['lora'], '')
        self.assertEqual(app.validate({})['particle_strength'], 1)
        self.assertEqual(loras.style_prompt('Italian, pop', 'particle-female'), 'Italian, pop')
        self.assertEqual(loras.style_prompt('pop', 'notte'), 'cnzn, Italian, pop')
        self.assertEqual(particle.session_options(ROOT, 'particle-female', 0), {})
        with patch.object(loras, 'installed', return_value=True):
            self.assertEqual(loras.session_options(ROOT, 'notte', .2)['yue2.ar_lora_scale'], .5)

    def test_selection_and_strength_bounds(self):
        self.assertEqual(len(particle.ADAPTERS), 16)
        self.assertEqual(app.validate({'lora': 'particle-male', 'particle_strength': .5})['particle_strength'], .5)
        for bad in ('particle-../female', 'particle-unknown', 'particle-', [], True):
            with self.assertRaises(ValueError):
                particle.validate(bad)
        for bad in (-.1, 1.1, float('nan'), float('inf'), True, None, 'bad'):
            with self.assertRaises(ValueError):
                app.validate({'particle_strength': bad})

    def test_conversion_preserves_float_bytes_and_all_attention_pairs(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'tests', prefix='tmp-particle-') as temp:
            source, output = Path(temp)/'source', Path(temp)/'adapter.safetensors'
            source_file(source)
            particle.convert(source, output, 'female')
            raw = output.read_bytes()
            length = struct.unpack('<Q', raw[:8])[0]
            header, data = json.loads(raw[8:8+length]), raw[8+length:]
            self.assertEqual(len(header)-1, 224)
            self.assertEqual(header['layers.27.self_attn.v_proj.lora_B']['shape'], [1024, 8])
            for name, entry in header.items():
                if name == '__metadata__':
                    continue
                self.assertEqual(entry['dtype'], 'F32')
                start, end = entry['data_offsets']
                value = .1234567 if name.endswith('lora_A') else -.0376543
                self.assertEqual(data[start:end], struct.pack('<f', value)*((end-start)//4))
            for ordinary, alpha in [(False, 8), (True, 4)]:
                source_file(source, ordinary, alpha)
                with self.assertRaises(ValueError):
                    particle.convert(source, output, 'female')
                self.assertEqual(output.read_bytes(), raw)
            source_file(source)
            with source.open('r+b') as stream:
                stream.truncate(source.stat().st_size-1)
            with self.assertRaises(ValueError):
                particle.convert(source, output, 'female')

    def test_missing_and_corrupt_installation_rejected_and_no_nar(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'tests', prefix='tmp-particle-') as temp:
            root = Path(temp)
            folder = particle.directory(root)/'male'
            folder.mkdir(parents=True)
            self.assertFalse(particle.installed(root, 'particle-male'))
            with self.assertRaisesRegex(ValueError, 'Installa'):
                particle.session_options(root, 'particle-male')
            file = folder/'ar.safetensors'
            file.write_bytes(b'adapter')
            record = {'revision': particle.CATALOG['revision'], 'source_sha256': particle.ADAPTERS['male']['sha256'],
                      'conversion': 1, 'size': 7, 'sha256': particle.digest(file)}
            (folder/'installed.json').write_text(json.dumps(record))
            options = loras.session_options(root, 'particle-male', .5)
            self.assertEqual(options, {'yue2.ar_lora': str(file), 'yue2.ar_lora_scale': .5})
            file.write_bytes(b'corrupt')
            with self.assertRaises(ValueError):
                particle.session_options(root, 'particle-male')

    def test_install_verifies_download_before_conversion(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'tests', prefix='tmp-particle-') as temp:
            import io
            with patch.object(particle.urllib.request, 'urlopen', return_value=io.BytesIO(b'incomplete')), \
                    self.assertRaisesRegex(ValueError, 'non integro'):
                particle.install(Path(temp), ['particle-female'])
            self.assertFalse(particle.installed(Path(temp), 'particle-female'))


if __name__ == '__main__':
    unittest.main()
