# -*- coding: utf-8 -*-
r"""받은 번역 검사(2026-10-30, 읽기만) — my files/모노모노/*.tsv ↔ my files/tsv 원본표(번호·원문 대조)
  열: 대사 = 번호·위치·JP·KO / 실행 파일 = 번호·위치·최대글자·JP·KO
  출력: 형식·빈칸·토큰(／ 「」『』 음성·기호)·문장부호·글자 종류·줄 폭 분포·화자별 말투·고유명사 후보
  python tools/trcheck.py"""
import os, sys, csv, re, glob, collections
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
GOT = os.path.join(ROOT, 'my files', '모노모노')
SRC = os.path.join(ROOT, 'my files', 'tsv')


def load(folder):
    out = {}
    for f in sorted(glob.glob(os.path.join(folder, '*.tsv'))):
        n = os.path.basename(f)
        raw = open(f, 'rb').read()
        txt = raw.decode('utf-8-sig')
        rows = list(csv.reader(txt.splitlines(), delimiter='\t', quoting=csv.QUOTE_NONE))
        out[n] = rows
    return out


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    a, b = load(GOT), load(SRC)
    print('받은', sorted(a)); print('원본', sorted(b))
    for n in a:
        print(n, '행', len(a[n]), '머리', a[n][0], '열수', collections.Counter(len(r) for r in a[n]))
    pair = []
    for n in sorted(a):
        if n not in b: print('⛔원본 없음', n); continue
        ra, rb = a[n][1:], b[n][1:]
        if len(ra) != len(rb): print('⛔행 수', n, len(ra), len(rb))
        ja = -2;
        for x, y in zip(ra, rb):
            if x[:-1] != y[:-1]: print('⛔원문 다름', n, x[:3], y[:3])
            pair.append((n, x[0], x[1], x[-2], x[-1]))
    print('전체', len(pair), '빈 번역', sum(1 for p in pair if not p[4].strip()))
    kanaleft = [p for p in pair if re.search('[぀-ヿ一-鿿]', p[4])]
    print('가나·한자 남음', len(kanaleft))
    for p in kanaleft[:40]: print('  ', p[1], p[3][:30], '→', p[4][:40])
    tok = collections.Counter(); bad = []
    for p in pair:
        for t in '／「」『』':
            if p[3].count(t) != p[4].count(t):
                tok[t] += 1; bad.append(p); break
    print('토큰 어긋남', dict(tok), len(bad))
    for p in bad[:60]: print('  ', p[1], p[2], '«%s» → «%s»' % (p[3], p[4]))
    chars = collections.Counter(c for p in pair for c in p[4] if not '가' <= c <= '힣')
    print('한글 밖 글자', chars.most_common(90))
    w = collections.Counter(len(s) for p in pair for s in p[3].split('／'))
    print('원문 줄 칸', sorted(w.items()))
    wk = collections.Counter(len(s) for p in pair for s in p[4].split('／'))
    print('번역 줄 칸', sorted(wk.items()))
    ln = collections.Counter((p[3].count('／'), p[4].count('／')) for p in pair)
    print('줄 수 (원문,번역)', sorted(ln.items()))
    sp = collections.Counter()
    for p in pair:
        m = re.match(r'^([^／「」]{1,12})／?「', p[3])
        if m: sp[m.group(1)] += 1
    print('화자', sp.most_common(60))
    sample = pair[:12] + pair[600:606] + [p for p in pair if p[0].startswith('mono_abs')][:10]
    for p in sample: print(p[2], '«%s» → «%s»' % (p[3], p[4]))


if __name__ == '__main__':
    main()
