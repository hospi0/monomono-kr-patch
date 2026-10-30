# -*- coding: utf-8 -*-
r"""오프닝·엔딩 음성 받아쓰기(2026-10-30, 프린세스 퀘스트 tools/asr_movie.py 꼴) — work/voice/wav/*.wav(tools/sap.py)
  → work/voice/asr.tsv (voice·start·end·no_speech·JP·words)   ★VAD 끔(짧은 외침 버려짐 방지)
  C:\claude\utils\whisper-venv\Scripts\python.exe tools/asr_voice.py"""
import glob, os, sys, wave
import numpy as np
from faster_whisper import WhisperModel
sys.stdout.reconfigure(encoding='utf-8')
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HINT = 'ゲン、トーベー、博士、村長、ヘンダー、内蔵、ユキ、助手、モノモノ、ケモケモ、影忍、ブショウ、とり丸、イノジジ、キャプテン、鬼公子、天狗、大入道。'
m = WhisperModel('large-v3', device='cuda', compute_type='float16')
out = open(os.path.join(ROOT, 'work', 'voice', 'asr.tsv'), 'w', encoding='utf-8')
out.write('voice\tstart\tend\tno_speech\tJP\twords\n')
for p in sorted(glob.glob(os.path.join(ROOT, 'work', 'voice', 'wav', '*.wav'))):
    w = wave.open(p); a = np.frombuffer(w.readframes(w.getnframes()), '<i2').astype(np.float32) / 32768
    nm = os.path.basename(p)[:-4]
    segs, _ = m.transcribe(a, language='ja', vad_filter=False, word_timestamps=True, initial_prompt=HINT, condition_on_previous_text=False)
    for s in segs:
        ws = ' '.join('%.2f:%s' % (x.start, x.word) for x in s.words)
        out.write('%s\t%.2f\t%.2f\t%.2f\t%s\t%s\n' % (nm, s.start, s.end, s.no_speech_prob, s.text.strip(), ws))
        print(nm, '%.2f-%.2f' % (s.start, s.end), s.text.strip())
out.close()
