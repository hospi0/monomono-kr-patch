# -*- coding: utf-8 -*-
r"""대사 추출(2026-10-30) — MONOMONO/*.MSG 27개 + WARNING.MSG 의 SJIS 문장
  문장 = SJIS 글자·0x0D(줄바꿈) 연속, 마지막이 0x0D, 다음 바이트는 SJIS 아님(명령)
  시작 판정: ① 문장 명령 0x16 + 머리 3바이트 뒤(대사·획득 문구, «0D 04 00» 등으로 끝)
             ② 그 밖에 남은 연속(백과사전 설명 «06 00» 뒤, 선택지 «07» 뒤, 경고문) — 앞 바이트가 SJIS 첫 바이트면 검사 목록에
  work/text/script.tsv : 번호 · 파일 · 오프셋 · 바이트수 · 종류 · JP          (출현마다 — 재삽입 기준)
  work/text/uniq.tsv   : 번호 · 출현수 · 첫 위치 · JP · KO                    (같은 원문 한 번)
  my files/tsv/mono_NNN.tsv : 번호 · 위치 · JP · KO — uniq 를 UTF-8 18KB(머리줄 포함) 넘기 전 끊음(하스피 지시)
  JP 표기: 줄바꿈 0x0D → «／»  (원문에 ／ 가 있으면 중단)
  검산: 원본 바이트 = 앞부분 + 문장 바이트 … 로 다시 조립해 파일과 같은지(라운드트립)
  python tools/extract.py"""
import os, sys, glob, collections
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SPLIT = 18 * 1024
SEP = '／'


def lead(c): return 0x81 <= c <= 0x9F or 0xE0 <= c <= 0xEF


def sj(b, i): return i + 1 < len(b) and lead(b[i]) and 0x40 <= b[i + 1] <= 0xFC and b[i + 1] != 0x7F


def run_end(b, i):
    """i 부터 SJIS·0D 연속의 끝(0D 로 끝나야 함) — 아니면 None"""
    j = i; last = None
    while j < len(b):
        if sj(b, j): j += 2
        elif b[j] == 0x0D: j += 1; last = j
        else: break
    return last if last and last > i + 1 else None


def scan(b):
    items = []; cov = bytearray(len(b)); i = 0
    while i < len(b) - 5:                                # ① 문장 명령
        if b[i] == 0x16 and sj(b, i + 4):
            e = run_end(b, i + 4)
            if e and (e >= len(b) or not sj(b, e)):
                items.append((i + 4, e, 'msg')); cov[i:e] = b'\x01' * (e - i); i = e; continue
        i += 1
    i = 0; odd = []
    while i < len(b) - 1:                                # ② 남은 것
        if not cov[i] and sj(b, i):
            e = run_end(b, i)
            if e:
                if i > 0 and lead(b[i - 1]) and not cov[i - 1]: odd.append(i)
                items.append((i, e, 'etc')); cov[i:e] = b'\x01' * (e - i); i = e; continue
            i += 1; continue                                 # 한 바이트씩(앞 명령 바이트와 짝지어 문장 첫 글자를 먹지 않게)
        i += 1
    return sorted(items), odd


def write_split(folder, stem, head, lines):
    os.makedirs(folder, exist_ok=True)
    chunks = []; cur = []; size = len(head.encode('utf-8'))
    for ln in lines:
        n = len(ln.encode('utf-8'))
        if cur and size + n > SPLIT: chunks.append(cur); cur = []; size = len(head.encode('utf-8'))
        cur.append(ln); size += n
    if cur: chunks.append(cur)
    for i, c in enumerate(chunks, 1):
        with open(os.path.join(folder, '%s_%03d.tsv' % (stem, i)), 'w', encoding='utf-8', newline='\n') as w:
            w.write(head + ''.join(c))
    return len(chunks)


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    files = sorted(glob.glob(os.path.join(ROOT, 'work', 'disc', 'MONOMONO', '*.MSG'))) + [os.path.join(ROOT, 'work', 'disc', 'WARNING.MSG')]
    rows = []; uniq = collections.OrderedDict(); odd_all = []
    for f in files:
        nm = os.path.basename(f); b = open(f, 'rb').read()
        items, odd = scan(b); odd_all += [(nm, o) for o in odd]
        re_ = bytearray(); p = 0
        for a, e, kind in items:
            jp = b[a:e].decode('cp932')
            if SEP in jp or '\t' in jp: raise SystemExit('원문에 ／·탭 %s %X' % (nm, a))
            jp = jp.replace('\r', SEP)
            rows.append((nm, a, e - a, kind, jp))
            re_ += b[p:a] + jp.replace(SEP, '\r').encode('cp932'); p = e
            u = uniq.setdefault(jp, [0, '%s@%X' % (nm, a)]); u[0] += 1
        re_ += b[p:]
        if bytes(re_) != b: raise SystemExit('라운드트립 불일치 ' + nm)
    out = os.path.join(ROOT, 'work', 'text'); os.makedirs(out, exist_ok=True)
    with open(os.path.join(out, 'script.tsv'), 'w', encoding='utf-8', newline='\n') as w:
        w.write('번호\t파일\t오프셋\t바이트\t종류\tJP\n')
        for k, (nm, a, n, kind, jp) in enumerate(rows, 1): w.write('%d\t%s\t%X\t%d\t%s\t%s\n' % (k, nm, a, n, kind, jp))
    lines = ['%d\t%s\t%s\t\n' % (k, v[1], jp) for k, (jp, v) in enumerate(uniq.items(), 1)]
    with open(os.path.join(out, 'uniq.tsv'), 'w', encoding='utf-8', newline='\n') as w:
        w.write('번호\t출현수\t첫 위치\tJP\tKO\n')
        for k, (jp, v) in enumerate(uniq.items(), 1): w.write('%d\t%d\t%s\t%s\t\n' % (k, v[0], v[1], jp))
    nf = write_split(os.path.join(ROOT, 'my files', 'tsv'), 'mono', '번호\t위치\tJP\tKO\n', lines)
    c = collections.Counter(r[3] for r in rows)
    print('출현 %d줄(%s) · 고유 %d줄 · 글자 %d · 라운드트립 OK · my files/tsv %d개' % (
        len(rows), dict(c), len(uniq), sum(len(j.replace(SEP, '')) for j in uniq), nf))
    if odd_all: print('⚠️앞 바이트가 SJIS 첫 바이트인 시작(검사 필요):', odd_all)


if __name__ == '__main__':
    main()
