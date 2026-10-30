# -*- coding: utf-8 -*-
r"""용어·말투 집계(2026-10-30, 읽기만) — 원문 고유명사별 한글 표기 · 화자별 어미 · 파일별 줄 폭
  python tools/trterm.py > work/text/term_report.txt"""
import os, sys, re, glob, collections
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import trcheck


def rows():
    a = trcheck.load(trcheck.GOT)
    out = []
    for n in sorted(a):
        for x in a[n][1:]: out.append((x[0], x[1], x[-2], x[-1], n))
    return out


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    R = rows()
    # 1) 화자 표기
    sp = collections.defaultdict(collections.Counter)
    for _, w, j, k, _f in R:
        m = re.match(r'^([^／「」]{1,12})「', j); m2 = re.match(r'^([^／「」]{1,14})「', k)
        if m: sp[m.group(1)][m2.group(1) if m2 else '(없음)'] += 1
    print('## 화자'); [print(s, dict(c)) for s, c in sorted(sp.items(), key=lambda x: -sum(x[1].values()))]
    # 2) 원문 가타카나·한자 낱말 ↔ 번역 표기(같은 줄 번역에서 가장 자주 함께 나온 2~6자 낱말)
    jw = collections.Counter(); rowsw = collections.defaultdict(list)
    for r in R:
        for t in set(re.findall(r'[ァ-ヴー]{2,}|[一-龠々]{2,}', r[2].replace('／', ''))):
            jw[t] += 1; rowsw[t].append(r)
    print('## 낱말')
    allk = collections.Counter(w for r in R for w in set(re.findall(r'[가-힣]{2,}', r[3])))
    for t, n in jw.most_common(400):
        if n < 3: break
        cnt = collections.Counter()
        for r in rowsw[t]:
            for w in set(re.findall(r'[가-힣]{2,}', r[3].replace('／', ' '))):
                cnt[w] += 1
        top = [(w, c) for w, c in cnt.most_common(40) if c >= max(2, n * 0.15)]
        top.sort(key=lambda x: -(x[1] ** 2 / allk[x[0]]))
        print(t, n, top[:6])
    # 3) 화자별 어미
    print('## 말투')
    end = collections.defaultdict(collections.Counter)
    ex = collections.defaultdict(dict)
    for _, w, j, k, _f in R:
        m2 = re.match(r'^([^／「」]{1,14})「', k)
        if not m2: continue
        s = m2.group(1)
        t = k[len(s) + 1:].replace('／', ' ').replace('　', ' ')
        for sent in re.split(r'(?<=[.!?！？…‥~～])\s*', t):
            sent = re.sub(r'[.!?！？…‥~～」\s]+$', '', sent)
            if len(sent) < 2: continue
            e = '요' if sent.endswith(('요', '죠', '까요')) else '니다' if sent.endswith(('니다', '니까')) else '반말'
            end[s][e] += 1
            if e != '반말': ex[s].setdefault(e, []).append(sent[-14:])
            else: ex[s].setdefault(e, []).append(sent[-14:])
    for s, c in sorted(end.items(), key=lambda x: -sum(x[1].values())):
        if sum(c.values()) < 5: continue
        print(s, dict(c), {k: v[:4] for k, v in ex[s].items() if c[k] <= sum(c.values()) * 0.35})
    # 4) 파일별 줄 폭
    print('## 폭')
    w = collections.defaultdict(collections.Counter); wk = collections.defaultdict(collections.Counter)
    for _, loc, j, k, _f in R:
        f = loc.split('@')[0].split(':')[0]
        for s in j.split('／'):
            if s: w[f][len(s)] += 1
        for s in k.split('／'):
            if s: wk[f][len(s)] += 1
    for f in sorted(w): print(f, '원', max(w[f]), sorted(w[f].items())[-3:], '역', max(wk[f]), sorted(wk[f].items())[-3:])


if __name__ == '__main__':
    main()
