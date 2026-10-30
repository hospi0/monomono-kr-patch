# -*- coding: utf-8 -*-
r"""MSG 스크립트 파서(2026-10-30, ABSOLUTE.BIN 해석기 역분석)
  주 루프 0x0600A0DA: PC(0x06054964)의 바이트 b — b ≥ 0x80 이면 SJIS 글자를 찍고 2바이트 전진, 아니면 PC++ 후 표 0x0603480C[b] 호출(b = 0x00~0x1F)
  스크립트 적재 0x06054970, 분기 주소 = 파일 오프셋 u16 BE
  피연산자: T = 항 3바이트 [종류][u16 BE](0x06008358) · L = 대입 대상 항 3바이트(0x060083A8)
            E = 수식: T {연산 1 + T} 00 · C = 조건: T 비교1 T {그리고/또는 1 + T 비교1 T} 00
            A = 분기 주소 u16 BE · S = 이름 문자열 …00(0x060082CC) · Z = 글 …00(07 선택지, 글자·제어 바이트)
  python tools/msgparse.py   → 전 파일 해석·검산(명령 경계·분기 대상)"""
import os, sys, glob, struct
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

FMT = {
    0x00: '', 0x01: 'LE', 0x02: 'CA', 0x03: 'A', 0x04: 'A', 0x05: '', 0x06: 'S', 0x07: 'Z', 0x08: '',
    0x09: 'T', 0x0A: '', 0x0B: 'T', 0x0C: 'T', 0x0D: '', 0x0E: 'T', 0x0F: 'TT', 0x10: 'S', 0x11: 'TT',
    0x12: 'T', 0x13: 'TTT', 0x14: 'TTT', 0x15: 'S', 0x16: 'T', 0x17: 'STTTTTTTT', 0x18: 'TTT', 0x19: 'TT',
    0x1A: 'TTTT', 0x1B: 'T', 0x1C: 'TT', 0x1D: 'T', 0x1E: 'T', 0x1F: 'TT',
}


class ParseError(Exception): pass


def parse(b, fmt=FMT):
    """→ [(시작, 끝, 종류, 값)] 종류: 'op'(값=번호, 주소 피연산자 위치 목록) / 'txt'(SJIS 연속)"""
    out = []; i = 0; n = len(b)
    while i < n:
        c = b[i]
        if c >= 0x80:
            s = i
            while i < n and b[i] >= 0x80: i += 2
            out.append((s, i, 'txt', None)); continue
        if c not in fmt: raise ParseError('모르는 명령 %02X @%X' % (c, i))
        s = i; i += 1; addrs = []
        for k in fmt[c]:
            if k in 'TL': i += 3
            elif k == 'A': addrs.append(i); i += 2
            elif k == 'S' or k == 'Z':
                while b[i] != 0:
                    i += 2 if (k == 'Z' and b[i] >= 0x80) else 1
                i += 1
            elif k == 'E':
                i += 3
                while b[i] != 0: i += 4
                i += 1
            elif k == 'C':
                i += 7
                while b[i] != 0: i += 8
                i += 1
            if i > n: raise ParseError('명령 %02X @%X 이 파일 끝을 넘음' % (c, s))
        out.append((s, i, 'op', (c, addrs)))
    return out


def check(b, items):
    starts = {s for s, e, k, v in items}
    bad = []
    for s, e, k, v in items:
        if k != 'op': continue
        for a in v[1]:
            t = struct.unpack_from('>H', b, a)[0]
            if t not in starts: bad.append((s, v[0], t))
    return bad


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    files = sorted(glob.glob(os.path.join(ROOT, 'work', 'disc', 'MONOMONO', '*.MSG')))
    tot = 0; ok = 0
    for f in files:
        b = open(f, 'rb').read()
        try:
            it = parse(b); bad = check(b, it)
            nj = sum(len(v[1]) for s, e, k, v in it if k == 'op')
            tot += 1; ok += not bad
            print('%-12s 명령 %5d 분기 %4d 어긋남 %d %s' % (os.path.basename(f), sum(1 for x in it if x[2] == 'op'), nj, len(bad), bad[:3]))
        except ParseError as e:
            tot += 1; print('%-12s ✗ %s' % (os.path.basename(f), e))
    print('통과 %d/%d' % (ok, tot))


if __name__ == '__main__':
    main()
