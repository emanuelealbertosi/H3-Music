"""Explicit native GPU smoke test; keeps the user's library and preferences intact."""
import hashlib
import json
from pathlib import Path
import shutil
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import app
import model_store
import resinging


def main():
    target = ROOT/'release-output/resinging-integration'
    target.mkdir(parents=True, exist_ok=True)
    source_id = '275b0ca5fe23473aab5829180bd40065'
    source = ROOT/'data/imports'/source_id
    before = hashlib.sha256((source/'source.mp3').read_bytes()).hexdigest()
    model_store.check_idle(ROOT)
    app.DATA = target/'data'; app.OUT = app.DATA/'outputs'; app.VOCI = app.DATA/'voci'; app.init()
    imported = app.DATA/'imports'/source_id
    if not imported.exists(): shutil.copytree(source, imported)
    app.save_settings(app.DEFAULTS | {'backend': 'cuda', 'model': 'bf16'})
    request = {'title': 'Dragon Ball · nuovo canto sulla base originale', 'style': '',
               'lyrics': '[Verse]\nGoku riparte,\nsi accende il cielo,\ncorre più forte,\nnon ha paura.\n\nVegeta guarda,\nprepara il salto,\nla sfida chiama,\nsi vola ancora.',
               'base_enabled': True, 'base_import_id': source_id, 'base_start': 18.53, 'base_end': 43.47,
               'options': {'num_inference_steps': 48}, 'seed': 831001}
    project = app.project_save({'request': request})
    ident = app.enqueue({'project_id': project['id'], 'request': request})['ids'][0]
    job = app.get_job(ident); folder = app.OUT/ident; folder.mkdir()
    app.db("UPDATE jobs SET status='running' WHERE id=?", (ident,))
    started = time.time()
    with model_store.exclusive(ROOT):
        model_store.check_idle(ROOT)
        try:
            result = resinging.process(app, job, folder)
            app.db("UPDATE jobs SET status='completed',result=?,finished=? WHERE id=?", (app.jdump(result), app.now(), ident))
        except Exception as error:
            app.db("UPDATE jobs SET status='failed',error=? WHERE id=?", (str(error), ident))
            raise
    assert before == hashlib.sha256((source/'source.mp3').read_bytes()).hexdigest()
    assert result['regenerated_vocals'] and not result['cloned']
    assert abs(result['duration']-app.audio_info(folder/'original.wav')['duration']) < .01
    # Preview only the modified section: the full WAV also retains the rest of the song.
    app.run_capture([app.FFMPEG, '-y', '-v', 'error', '-ss', '18.53', '-i', folder/'audio.wav', '-t', '24.94',
                     '-c:a', 'libmp3lame', '-b:a', '320k', target/'preview.mp3'])
    report = {'job_id': ident, 'project_id': project['id'], 'folder': str(folder), 'elapsed_seconds': time.time()-started,
              'source_unchanged': True, 'result': result}
    app.write_json(target/'verified.json', report)
    print(json.dumps(report, ensure_ascii=False), flush=True)


if __name__ == '__main__': main()
