# -*- coding: utf-8 -*-
r"""실행 파일(ABSOLUTE.BIN, 적재 0x06004000) 문자열 추출(2026-10-30)
  문자열 = SJIS(+전각 공백 채움) 연속, NUL 로 끝남 — 고정 폭 칸(아이템 이름 18 B·상점 대사 26/28 B·저장 메시지 24/34 B 등)
  찾기: SJIS 연속 6 B 이상이 NUL 로 끝남, 또는 4 B 이상이 NUL 앞뒤 — 코드·표 조각은 SKIP 으로 뺌, 주소 리터럴과 짝지어 어긋난 시작은 FIX
  예산 = 원문 바이트(채움 공백 포함) — 제자리 덮어쓰기 기준(전각 글자 수 = 바이트/2)
  work/text/abs.tsv : 번호 · 오프셋 · 바이트 · JP
  my files/tsv/mono_abs_001.tsv : 번호 · 위치 · 최대글자 · JP · KO (하스피 지시 — 18KB 단위)
  python tools/extract_abs.py"""
import os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from extract import write_split

SKIP = {0x13B19, 0x239E1, 0x28FC0, 0x29E46, 0x24D79}          # 코드·데이터가 우연히 SJIS 로 읽힌 것
FIX = {0x923A: 0x923C}                               # 앞 주소 리터럴(0x0602989A) 끝 바이트와 짝지어 어긋남 → «所持金»


def lead(c): return 0x81 <= c <= 0x9F or 0xE0 <= c <= 0xEF


def scan(b):
    def sj(i): return i + 1 < len(b) and lead(b[i]) and 0x40 <= b[i + 1] <= 0xFC and b[i + 1] != 0x7F
    out = []; i = 0
    while i < len(b) - 1:
        if sj(i):
            s = i
            while i < len(b) - 1 and sj(i): i += 2
            n = i - s; nul = i < len(b) and b[i] == 0
            if nul and (n >= 6 or (n >= 4 and (s == 0 or b[s - 1] == 0 or s % 2 == 0))):
                s2 = FIX.get(s, s)
                if s2 not in SKIP:
                    try: t = b[s2:i].decode('cp932')
                    except UnicodeDecodeError: continue          # IBM 확장 등 — 글이 아님
                    if any('぀' <= c <= 'ヿ' or '一' <= c <= '鿿' for c in t): out.append((s2, i, t))
        else: i += 1
    return out


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    b = open(os.path.join(ROOT, 'work', 'disc', 'ABSOLUTE.BIN'), 'rb').read()
    items = scan(b)
    with open(os.path.join(ROOT, 'work', 'text', 'abs.tsv'), 'w', encoding='utf-8', newline='\n') as w:
        w.write('번호\t오프셋\t바이트\tJP\n')
        for k, (s, e, t) in enumerate(items, 1): w.write('%d\t%X\t%d\t%s\n' % (k, s, e - s, t))
    lines = ['%d\tABSOLUTE.BIN@%X\t%d\t%s\t\n' % (k, s, (e - s) // 2, t.rstrip('　')) for k, (s, e, t) in enumerate(items, 1)]
    nf = write_split(os.path.join(ROOT, 'my files', 'tsv'), 'mono_abs', '번호\t위치\t최대글자\tJP\tKO\n', lines)
    print('문자열 %d개 · 글자 %d · my files/tsv/mono_abs %d개' % (len(items), sum(len(t.rstrip('　')) for _, _, t in items), nf))


if __name__ == '__main__':
    main()
