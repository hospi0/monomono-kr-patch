# -*- coding: utf-8 -*-
r"""한글 인코더·글꼴(2026-10-30, 프린세스 퀘스트 tools/krenc.py 에서)
  FONT.DAT = 앞 0x1000 반각 8×16(256자, 16 B) + 16×16 1bpp SJIS 칸 순서 7,806자(칸 번호 = PQ 와 같은 식, 렌더 검산)
  한글 KS X 1001 2,350 → SJIS 889F~ 고정 배정(81~84 행 기호·전각 영숫자·가나는 원본 유지), 자형 갈무리14
  글자는 전부 2바이트(해석기가 바이트 ≥ 0x80 만 글자로 찍음, 반각은 명령) — 공백도 전각 8140
  python tools/krenc.py"""
import os, re, sys, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from bdf import Font

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BDF = r'C:\claude\utils\font\Galmuri-v2.40.3\Galmuri14.bdf'
FONT_BASE = 0x1000


def cell(code):
    hi, lo = code >> 8, code & 0xFF
    hi = hi - 0x81 if hi < 0xA0 else hi - 0xC1
    return hi * 188 + (lo - 0x40 - (1 if lo > 0x7F else 0))


def ks_hangul():
    return [bytes([hi, lo]).decode('euc-kr') for hi in range(0xB0, 0xC9) for lo in range(0xA1, 0xFF)]


def sjis_slots():
    for hi in range(0x88, 0xA0):
        for lo in list(range(0x40, 0x7F)) + list(range(0x80, 0xFD)):
            if hi == 0x88 and lo < 0x9F: continue
            yield (hi << 8) | lo


# 한글식 문장부호 — 값 = (가로, 세로 이동). 반각 폭 그림을 칸 왼쪽에, 여는 괄호는 오른쪽에
PUNCT = {',': (0, -1), '.': (0, 0), '…': (0, 0), '?': (0, 0), '!': (0, 0), '~': (0, 0), ':': (0, 0), ';': (0, 0),
         "'": (0, 0), '"': (0, 0), '(': (10, 0), ')': (0, 0), '-': (0, 0), '·': (0, 0)}
SQUEEZE_PUNCT = ',.!?:;)]}\'"~、。，．！？：；）］｝」』】〉》”’…‥・·～〜♪♥'
_SQ = re.compile('([' + re.escape(SQUEEZE_PUNCT) + '])[ 　](?![ 　])')


def squeeze(t):
    return '／'.join(_SQ.sub(r'\1', p) for p in t.split('／'))


CMAP = {}
for ch, code in zip(ks_hangul() + list(PUNCT), sjis_slots()): CMAP[ch] = code
CMAP[' '] = 0x8140


def code_of(ch):
    if ch in CMAP: return CMAP[ch]
    b = ch.encode('cp932')
    if len(b) != 2 or not (0x81 <= b[0] <= 0x84): raise ValueError('매핑 없는 글자 %r (U+%04X)' % (ch, ord(ch)))
    return (b[0] << 8) | b[1]


def encode(t):
    """번역문 → SJIS 바이트(／ = 0D)"""
    out = bytearray()
    for ch in squeeze(t):
        if ch == '／': out.append(0x0D); continue
        c = code_of(ch); out += bytes([c >> 8, c & 0xFF])
    return bytes(out)


def build_font(orig):
    f = bytearray(orig); fnt = Font(BDF)
    for ch, code in CMAP.items():
        if ch == ' ': continue
        dx, dy = PUNCT.get(ch, (0, 0))
        pts, w = fnt.draw(ch, dx, -3 + dy)
        rows = [0] * 16
        for x, y in pts:
            if not (0 <= x < 16 and 0 <= y < 16): raise SystemExit('글리프가 칸 밖 %s (%d,%d)' % (ch, x, y))
            rows[y] |= 0x8000 >> x
        o = FONT_BASE + cell(code) * 32
        f[o:o + 32] = struct.pack('>16H', *rows)
    assert len(f) == len(orig)
    return bytes(f)
