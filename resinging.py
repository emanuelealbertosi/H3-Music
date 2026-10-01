"""New lyrics and singing on the separated original accompaniment."""
import hashlib
import json
import math
import statistics
import execution
import platform_runtime
import transcription
import cloning
import mixing

MAX_SECONDS = 150


def validate_fields(req):
    enabled = req.get('base_enabled', False)
    if not isinstance(enabled, bool):
        raise ValueError('Scelta della base originale non valida.')
    source = req.get('base_import_id', '')
    if not isinstance(source, str) or len(source) > 200:
        raise ValueError('Canzone originale non valida.')
    result = {'base_enabled': enabled, 'base_import_id': source}
    for key in ('base_start', 'base_end'):
        value = req.get(key, 0)
        if isinstance(value, bool):
            raise ValueError('Intervallo della base originale non valido.')
        try:
            value = float(value)
        except (ValueError, TypeError):
            raise ValueError('Intervallo della base originale non valido.')
        if not math.isfinite(value) or value < 0:
            raise ValueError('Intervallo della base originale non valido.')
        result[key] = value
    return result


def preflight(app, req):
    if not app.ready()['ready']:
        raise ValueError('Completa i modelli musicali prima di usare la base originale.')
    cloning.preflight(app, req.get('clone_voice', ''), instrumental=not req.get('clone_enabled'))
    if not transcription.status(app.ROOT, app.settings()['backend'])['ready']:
        raise ValueError('Completa la trascrizione in Sistema per usare la base originale.')
    source, meta = transcription.source(app.DATA, req['base_import_id'])
    start, end = req['base_start'], req['base_end'] or meta['duration']
    if not 0 <= start < end <= meta['duration'] + .05 or end - start < 3:
        raise ValueError('Scegli un tratto di almeno 3 secondi entro la canzone originale.')
    if end - start > MAX_SECONDS + .05:
        raise ValueError(f'Il nuovo canto può coprire fino a {MAX_SECONDS} secondi per volta. Scegli inizio e fine del tratto.')
    if not req['lyrics'].strip():
        raise ValueError('Scrivi il testo da cantare sulla base originale.')
    return source, meta, start, end


def read_notes(path):
    result = []
    for line in path.read_text(encoding='utf-8').splitlines():
        if not line.strip():
            continue
        fields = line.split()
        if len(fields) != 3:
            raise ValueError('Note vocali non valide.')
        start, end, pitch = map(float, fields)
        if not all(math.isfinite(v) for v in (start, end, pitch)) or not 0 <= start < end or not 0 <= pitch <= 127 or pitch != int(pitch):
            raise ValueError('Note vocali non valide.')
        result.append((start, end, int(pitch)))
    if len(result) > 2000 or any(b[0] < a[0] for a, b in zip(result, result[1:])):
        raise ValueError('Sequenza vocale troppo complessa o non ordinata.')
    return result


def alignment(original, generated):
    """Match note sequences, then accept only a stable constant vocal delay."""
    n, m = len(original), len(generated)
    if min(n, m) < 6:
        raise ValueError('Non sono state riconosciute abbastanza note cantate per allineare la voce.')
    guess = generated[0][0] - original[0][0]
    previous = list(map(float, range(m + 1)))
    directions = bytearray(n * m)
    for i in range(1, n + 1):
        current = [float(i)] + [0.0] * m
        for j in range(1, m + 1):
            same = original[i-1][2] == generated[j-1][2]
            error = abs(original[i-1][0] + guess - generated[j-1][0])
            choices = (previous[j-1] + (0 if same else 1.5) + min(.3, error * .1), previous[j] + 1, current[j-1] + 1)
            k = min(range(3), key=lambda k: choices[k])
            current[j] = choices[k]; directions[(i-1)*m+j-1] = k
        previous = current
    i, j = n, m; matched = []
    while i or j:
        k = directions[(i-1)*m+j-1] if i and j else (1 if i else 2)
        if k == 0:
            if original[i-1][2] == generated[j-1][2]:
                matched.append((original[i-1], generated[j-1]))
            i -= 1; j -= 1
        elif k == 1: i -= 1
        else: j -= 1
    if len(matched) / max(n, m) < .7:
        raise ValueError('Il nuovo canto si discosta troppo dalla melodia originale. Prova un testo con una metrica più simile.')
    delay = statistics.median(g[0] - o[0] for o, g in matched)
    errors = sorted(abs(g[0] - o[0] - delay) for o, g in matched)
    p90 = errors[min(len(errors)-1, math.ceil(.9*len(errors))-1)]
    if abs(delay) > 2.5 or p90 > .2 or max(errors) > .65:
        raise ValueError('Il nuovo canto cambia ritmo rispetto alla base. Il mix è stato fermato per non spostare la musica: prova un testo più vicino alla metrica originale.')
    return {'original_notes': n, 'generated_notes': m, 'matching_notes': len(matched), 'vocal_delay_seconds': delay,
            'median_onset_error_seconds': statistics.median(errors), 'p90_onset_error_seconds': p90,
            'max_onset_error_seconds': max(errors), 'method': 'SheetSage2 note recognition; constant delay only'}


def process(app, job, d):
    req = job['request']; source, meta, start, end = preflight(app, req)
    app.check_cancel(job['id']); s = app.settings()
    app.write_json(d/'request.json', req); app.write_json(d/'source.json', meta)
    def run(args, label, pct):
        app.check_cancel(job['id'])
        app.run_job_process(job, d, list(map(str, args)), append=True, phase=(label, pct))
        app.check_cancel(job['id'])
    def ff(args, label, pct):
        run([app.FFMPEG, '-y', '-v', 'error', '-nostdin', '-protocol_whitelist', 'file,pipe', *args], label, pct)
    def separate(audio, folder, label, pct):
        folder.mkdir(exist_ok=True)
        ff(['-i', audio, '-ar', '44100', '-ac', '2', folder/'input.wav'], label, pct)
        run([app.ENGINE, '--task', 'sep', '--family', 'htdemucs', '--model', app.separation_model(), '--backend', s['backend'],
             '--threads', s['threads'], '--audio', folder/'input.wav', '--out-dir', folder, '--log', '--metrics'], label, pct)
        if not all((folder/(name+'.wav')).is_file() for name in ('vocals', 'drums', 'bass', 'other')):
            raise RuntimeError('Separazione incompleta: il nuovo canto non è stato rimixato.')
    def transcribe(audio, folder, duration, label, pct):
        folder.mkdir(exist_ok=True)
        app.write_json(folder/'request.json', {'start': 0, 'end': duration, 'melody_only': False})
        run([execution.transcription_python(app.ROOT, s['backend']), '-u', app.ROOT/'scripts/transcribe_worker.py', '--input', audio,
             '--output', folder, '--root', app.ROOT, '--backend', platform_runtime.transcription_backend(s['backend']), '--threads', s['threads']], label, pct)
        return read_notes(folder/'melody_vocal.lab')
    original = d/'original.wav'
    ff(['-i', source, '-ar', '48000', '-ac', '2', '-c:a', 'pcm_s24le', original], 'Preparazione della canzone originale', 3)
    whole_duration = app.audio_info(original)['duration']; end = min(end, whole_duration)
    duration = end - start
    if duration < 3: raise ValueError('Il tratto selezionato non contiene abbastanza audio.')
    stems = d/'stems'; separate(original, stems, 'Separazione della base originale', 10)
    excerpt = d/'source-excerpt.wav'
    ff(['-ss', start, '-i', original, '-t', duration, '-ar', '48000', '-ac', '2', excerpt], 'Preparazione del tratto cantato', 20)
    score_dir = d/'source-score'
    original_notes = transcribe(excerpt, score_dir, duration, 'Lettura della melodia originale', 25)
    if len(original_notes) < 6: raise ValueError('Il tratto scelto non contiene abbastanza canto riconoscibile.')
    score = app.read_abc(score_dir/'score.abc')
    if not score.strip(): raise RuntimeError('La melodia originale non ha prodotto uno spartito utilizzabile.')
    (d/'score.abc').write_text(score, encoding='utf-8', newline='\n')
    generated = d/'generated'; generated.mkdir(exist_ok=True)
    style = req['style'] or 'Italian, clear solo lead singing, steady tempo, follow the supplied score exactly, no extra intro, no backing vocals'
    options = dict(req['options']); options.setdefault('num_inference_steps', 48)
    generation_req = req | {'style': style, 'abc': score, 'cot': 'full', 'base_enabled': False, 'clone_enabled': False, 'options': options}
    run(app.command_for({'kind': 'generate', 'request': generation_req}, generated), 'Generazione del nuovo canto', 45)
    flags = json.loads((generated/'generation_flags.json').read_text(encoding='utf-8')) if (generated/'generation_flags.json').exists() else {}
    if flags.get('audio_truncated') or flags.get('abc_truncated'):
        raise ValueError('Il nuovo canto è stato troncato dal limite token. Scegli un tratto più breve o aumenta il limite nelle opzioni avanzate.')
    generated_duration = app.audio_info(generated/'audio.wav')['duration']
    generated_notes = transcribe(generated/'audio.wav', d/'generated-score', generated_duration, 'Controllo dei tempi del nuovo canto', 65)
    report = alignment(original_notes, generated_notes)
    report.update({'start': start, 'end': end, 'original_duration': duration, 'generated_duration': generated_duration})
    app.write_json(d/'alignment.json', report)
    fresh_stems = d/'generated-stems'; separate(generated/'audio.wav', fresh_stems, 'Estrazione del nuovo canto', 75)
    delay = report['vocal_delay_seconds']; aligned = d/'new-singing.wav'
    filters = f'atrim=start={max(0,delay):.8f},asetpts=PTS-STARTPTS'
    if delay < 0: filters += f',adelay={round(-delay*48000)}S:all=1'
    filters += f',apad,atrim=duration={duration:.8f}'
    ff(['-i', fresh_stems/'vocals.wav', '-af', filters, '-ar', '48000', '-ac', '2', '-c:a', 'pcm_s24le', aligned], 'Allineamento del nuovo canto', 82)
    fresh_voice = aligned
    if req.get('clone_enabled'):
        reference = d/'reference.wav'
        ff(['-i', app.voice_sample(req['clone_voice']), '-ar', '44100', '-ac', '1', reference], 'Preparazione della tua voce', 85)
        converted = d/'converted-singing.wav'
        cloning.convert_voice(app, job, d, aligned, reference, converted, s)
        if abs(app.audio_info(converted)['duration']-duration) > .25:
            raise RuntimeError('La conversione ha cambiato la durata del canto: il mix è stato fermato.')
        fresh_voice = converted
    # Match the replacement section itself: the retained vocals elsewhere in
    # the song must not hide a quiet new voice from the full-song loudness check.
    if req['mix']['automatic']:
        reference_excerpt = d/'reference-singing.wav'
        ff(['-ss', start, '-i', stems/'vocals.wav', '-t', duration, '-ar', '48000', '-ac', '2', reference_excerpt], 'Bilanciamento del tratto cantato', 88)
        measure = lambda path: mixing.measure(app, path, d, lambda args: run(args, 'Bilanciamento del tratto cantato', 88))
        gain = mixing.matching_gain(measure(reference_excerpt), measure(fresh_voice))
        balanced = d/'balanced-singing.wav'
        ff(['-i', fresh_voice, '-af', f'volume={gain:.8f}dB,apad,atrim=duration={duration:.8f}', '-ar', '48000', '-ac', '2', '-c:a', 'pcm_s24le', balanced], 'Bilanciamento del tratto cantato', 88)
        fresh_voice = balanced
        report['excerpt_voice_gain_db'] = gain
        app.write_json(d/'alignment.json', report)
    # Preserve the original singing outside the selected range and every instrumental sample timing.
    parts = []
    if start > 0: parts.append(('original', 0, start))
    parts.append(('new', 0, duration))
    if whole_duration-end > .0001: parts.append(('original', end, whole_duration))
    filters = []
    for i, (which, a, b) in enumerate(parts):
        index = 0 if which == 'original' else 1
        filters.append(f'[{index}:a]atrim=start={a:.8f}:end={b:.8f},asetpts=PTS-STARTPTS,aformat=sample_rates=48000:channel_layouts=stereo,apad,atrim=duration={b-a:.8f}[p{i}]')
    filters.append(''.join(f'[p{i}]' for i in range(len(parts))) + f'concat=n={len(parts)}:v=0:a=1[out]')
    ff(['-i', stems/'vocals.wav', '-i', fresh_voice, '-filter_complex', ';'.join(filters), '-map', '[out]', '-ar', '48000', '-ac', '2', '-c:a', 'pcm_s24le', d/'voce.wav'], 'Inserimento sulla base originale', 90)
    final = app.mix_voice(job, d, d/'voce.wav', source=stems, runner=lambda args: run(args, 'Bilanciamento del nuovo canto', 95))
    result = app.audio_info(final) | {'regenerated_vocals': True, 'original_preserved': True, 'source_kind': 'import', 'import_id': req['base_import_id'],
                                    'base_start': start, 'base_end': end, 'alignment': report, 'cloned': req.get('clone_enabled', False)}
    if req.get('clone_enabled'): result.update({'voice': req['clone_voice'], 'voice_steps': req['voice_steps']})
    def digest(path):
        with path.open('rb') as stream: return hashlib.file_digest(stream, 'sha256').hexdigest()
    app.write_json(d/'manifest.json', {'result': result, 'sha256': {name: digest(d/name) for name in ('audio.wav', 'original.wav', 'voce.wav', 'score.abc', 'alignment.json')}})
    return result
