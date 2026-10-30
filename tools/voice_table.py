# -*- coding: utf-8 -*-
r"""오프닝·엔딩 음성 자막 번역표(2026-10-30) — OPENING/ENDING.MSG 의 음성 명령(10 «_A1_001»)마다 앞 그림(15 «OP00»)·다음 대기(01 변수7 = 프레임)
  + work/voice/asr_best.tsv(받아쓰기) → work/voice/voice.tsv, my files/tsv/mono_voice_001.tsv(번호·음성·그림·대기초·길이·JP·KO·비고)
  python tools/voice_table.py"""
import csv, os, struct, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import msgparse


def voices(fn):
    b = open(os.path.join(ROOT, 'work', 'disc', 'MONOMONO', fn), 'rb').read()
    pic = ''; out = []
    for s, e, k, v in msgparse.parse(b):
        if k != 'op': continue
        c = b[s]
        if c == 0x15: pic = b[s + 1:e - 1].decode('latin1')
        elif c == 0x10: out.append([b[s + 1:e - 1].decode('latin1'), pic, None, s])
        elif c == 0x01 and b[s + 1:s + 4] == b'\x01\x00\x07' and out and out[-1][2] is None:
            out[-1][2] = struct.unpack_from('>H', b, s + 5)[0] / 60      # 변수7 = 대기 프레임(첫 항 상수)
    return out


NONVERBAL = {'ふっ', 'ふぅ', 'え', 'はっ', 'うん'}


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    asr = {r['음성']: r for r in csv.DictReader(open(os.path.join(ROOT, 'work', 'voice', 'asr_best.tsv'), encoding='utf-8'), delimiter='\t')}
    kp = os.path.join(ROOT, 'work', 'voice', 'voice_ko.tsv')       # 번역(음성 키) — 받아쓰기 고친 원문 추정·KO·비고
    kt = {r['음성']: r for r in csv.DictReader(open(kp, encoding='utf-8'), delimiter='	')} if os.path.exists(kp) else {}
    rows = []; n = 0; drop = 0
    for fn in ('OPENING.MSG', 'ENDING.MSG'):
        for nm, pic, wait, off in voices(fn):
            a = asr.get(nm, {}); jp = a.get('JP', '')
            if nm not in kt and (not jp or jp.rstrip('。!?！？、') in NONVERBAL or 'トーベー、博士、モノモノ' in jp):   # 뒤 = 힌트 문구 환각 · 번역(voice_ko)에 있으면 받아쓰기와 상관없이 넣음          # 하스피: 비언어로 추정되는 짧은 줄은 뺀다
                drop += 1; continue
            n += 1
            k = kt.get(nm, {})
            rows.append([n, nm, fn.split('.')[0] + ':' + pic, '%.1f' % wait if wait else '', a.get('길이', ''), k.get('JP(고친 원문 추정)') or jp, k.get('KO', ''), k.get('비고', '') or a.get('비고', '')])
    hd = ['번호', '음성', '그림', '대기초', '길이', 'JP', 'KO', '비고']
    for p in (os.path.join(ROOT, 'work', 'voice', 'voice.tsv'), os.path.join(ROOT, 'my files', 'tsv', 'mono_voice_001.tsv')):
        with open(p, 'w', encoding='utf-8', newline='') as f:
            w = csv.writer(f, delimiter='\t', lineterminator='\n'); w.writerow(hd); w.writerows(rows)
    print(len(rows), '줄 (뺀 비언어', drop, ') →', p)


if __name__ == '__main__':
    main()
