# -*- coding: utf-8 -*-
r"""번역 병합(2026-10-30) — my files/모노모노/*.tsv(하스피 번역, 읽기만) → work/text/uniq.tsv·abs.tsv KO + work/text/merge_report.tsv
  실행: C:\claude\utils\kiwi-venv\Scripts\python.exe tools/merge_ko.py   (백과 줄 이음매 판정에 Kiwi)
  검사·정리:
   - 번호·원문 대조, 토큰 ／「」『』”（） — 어긋나면 중단(줄 수는 다시 접기로 달라질 수 있어 ／ 는 끝 표시만)
   - 이름: 内蔵 = 쿠라조(내장·구라·구라조 통일, か행 ㅋ) · 天狗 = 텐구 · 空手 = 카라테 · 下駄 = 게타
   - 아이템 이름: 실행 파일(9칸 메뉴) 표기가 기준, 백과 제목을 맞춤
   - 부호: ！？～ → ! ? ~ · ‥‥·…… → … · 영숫자 전각(반각 바이트는 해석기에서 명령이라 글자로 못 찍음)
     원문 ”x”·「x」 자리의 "x"·'x' → 원문 토큰으로
   - 대사: 14칸(원문 최장 줄이 더 길면 그 길이) 넘는 줄을 낱말 경계에서 다음 줄로. 3줄 넘으면 빌더가 쪽 나눔
   - 백과: 원문 일본어식 낱말 중간 줄바꿈을 풀고 다시 접음(제목 + 9칸 3줄 + 14칸 3줄)
   - WARNING·ABSOLUTE 는 줄 안 건드림"""
import os, sys, csv, re, glob, collections, shutil
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import trcheck
from kiwipiepy import Kiwi

WIDTH, MAXLINES = 14, 3
LIB_CAPS = [9, 9, 9, 14, 14, 14]
SQ = ',.!?:;)]}\'"~、。，．！？：；）］｝」』】〉》”’…‥・·～〜♪♥'
_SQ = re.compile('([' + re.escape(SQ) + '])[ 　](?![ 　])')
HAND = {   # 번호(대사표): 고친 KO
    '10': '구룡검／거대한 용을 소환해／적을 베는 암살검／아홉 구, 용 룡 자를／써서 ”쿠론”이라 읽는다. 그렇다고／홍콩 쪽 그것과는／관계없다.／',
    '21': '도깨비 방망이／쇠 금 자를 써서／”카나보”라고 읽는／다. 하지만／정확히는 쇠 철 자를 써서 ”카나／보”다. 아니아니／어느 쪽이든 상관없지만.／',
    '46': '프라이팬／오믈렛, 핫케이크,／볶음밥에／칭자오러우쓰.／즐거운 요리에 빠질 수 없는／프라이팬. 부부 싸움／에서도 자주 사용된다.／',
    '65': '철선／만담장의 신 『철벽／정 철분（텟페키테이 테츠분）』의／사인이 든 철선이다. 스승은 조／는 손님을 두들겨 깨우는／데 쓰고 있다고 한다.／',
    '1296': 'Ｌ 또는 Ｒ버튼을 누른 채／리셋 버튼을 누르면 저장／데이터 관리 화면으로／갑니다.／',
    '1298': '새 기록을 저장하려면「３２」／의 빈 용량이 필요합니다.／',
    '1111': '조수「박사님,／　준비됐어요！／',
    '1121': '조수「박사님！ 완성이에요！／',
}
ABS_FIX = {'높은 게다': '높은 게타', '쇠 게다': '쇠 게타', '아이스번 소드': '아이스반 소드'}
HAN0 = 0xAC00
JOINTS = []
SPACE_AT = {'불어|몬스터가', '받아도|통', '후려친다는|이', '마른|대', '케모케모가|겐', '나타나|두', '필수|거대', '않으면|들', '마치|메테오처럼', '예전|미즈타니',
            '시리즈|제１탄,', '시리즈|제２탄,', '시리즈|제３탄,', '시리즈|제４탄,'}


def has_batchim(ch):
    return '가' <= ch <= '힣' and (ord(ch) - HAN0) % 28 != 0


JOSA = [('이', '가'), ('은', '는'), ('을', '를'), ('과', '와'), ('으로', '로'), ('이야', '야'), ('이에요', '예요'), ('이여', '여'), ('아', '야')]


def rename(text, old, new):
    """old → new, 받침 유무가 바뀌면 바로 뒤 조사도"""
    ob, nb = has_batchim(old[-1]), has_batchim(new[-1])
    if ob == nb: return text.replace(old, new)
    pairs = sorted([(a, b) if ob else (b, a) for a, b in JOSA], key=lambda p: -len(p[0]))
    def sub(m):
        rest = m.group(1)
        for a, b in pairs:
            if rest.startswith(a): return new + b + rest[len(a):]
        return new + rest
    return re.sub(re.escape(old) + r'([가-힣]{0,3})', sub, text)


def zen(s):
    return ''.join(chr(ord(c) + 0xFEE0) if ('A' <= c <= 'Z' or 'a' <= c <= 'z' or '0' <= c <= '9') else c for c in s)


def wlen(seg):
    return len(_SQ.sub(r'\1', seg))


def punct(t):
    t = t.replace('！', '!').replace('？', '?').replace('～', '~').replace('〜', '~')
    t = re.sub('‥+', '…', t); t = re.sub('…+', '…', t); t = re.sub(r'\.{3,}', '…', t)
    t = t.replace('Mr.X', 'Ｍｒ．Ｘ').replace('Mr.', 'Ｍｒ．')
    return zen(t)


def quotes(ko, jp):
    """원문 토큰 자리의 반각 따옴표를 원문 토큰으로 — 원문 순서대로"""
    order = re.findall(r'[「”]', jp)
    opens = [t for i, t in enumerate(order)]
    seq = []
    i = 0; st = None
    for c in jp:
        if c == '「': seq.append('「」')
        elif c == '”':
            if st is None: seq.append('””'); st = 1
            else: st = None
    n = 0; out = []; openq = None
    for c in ko:
        if c in '"\'':
            if openq is None:
                if n < len(seq) and not (c == "'" and out and out[-1] in '가나다라마바사아자차카타파하'):
                    openq = (c, seq[n]); out.append(seq[n][0]); n += 1; continue
            elif c == openq[0]:
                out.append(openq[1][1]); openq = None; continue
        out.append(c)
    return ''.join(out)


def rewrap(ko, jp):
    segs = ko.split('／'); tail = segs.pop() if segs[-1] == '' else None
    jmax = max(len(p) for p in jp.split('／'))
    lim = max(WIDTH, jmax)
    indent = '　' if re.search('／　', jp) else ''
    i = 0; ch = False
    while i < len(segs):
        s = segs[i]
        if wlen(s) <= lim: i += 1; continue
        cut = None
        for k in range(len(s) - 1, 0, -1):
            if s[k] == ' ' and wlen(s[:k]) <= lim: cut = k; break
        if cut is None:
            for k in range(len(s) - 1, 0, -1):                     # 부호 뒤도 끊는 자리
                if s[k - 1] in ',.!?…' and wlen(s[:k]) <= lim: cut = k - 1 + 1; break
            if cut is None: return ko, 'cut'
            a, b = s[:cut], s[cut:]
        else:
            a, b = s[:cut], s[cut + 1:]
        segs[i] = a
        b = b.lstrip('　 ')
        if i + 1 < len(segs):
            n = segs[i + 1].lstrip('　')
            pre = segs[i + 1][:len(segs[i + 1]) - len(n)]
            segs[i + 1] = pre + b + ' ' + n
        else:
            segs.append(indent + b)
        ch = True; i += 1
    out = '／'.join(segs) + ('／' if tail is not None else '')
    return out, ('wrap' if ch else '')


def joinjoint(kw, a, b):
    """줄 이음매: 붙일지 띄울지 — Kiwi 점수가 높은 쪽"""
    a, b = a.rstrip(), b.lstrip('　 ')
    if not a or not b: return a + b
    if a[-1] in ',.!?…~」』”:;': return a + ' ' + b
    wa, wb = a.split(' ')[-1], b.split(' ')[0]
    if a[-1] in '(（' or b[0] in ')）': return a + b
    g = wa + wb
    if wa + '|' + wb in SPACE_AT: return a + ' ' + b
    ta, tb = kw.tokenize(wa), kw.tokenize(wb)               # 왼쪽이 이미 조사·어미로 끝난 낱말 + 오른쪽이 제 낱말이면 띄움
    if len(wa) >= 2 and len(wb) >= 2 and ta and tb and ta[-1].tag[0] in 'JE' and tb[0].tag[0] not in 'JE' and not tb[0].tag.startswith('XS'):
        JOINTS.append(('띄움', wa + '|' + wb)); return a + ' ' + b
    # 붙인 꼴의 형태소: 이음매가 형태소 안이거나 바로 뒤가 조사·어미·접미면 한 낱말, 아니면 띄움
    for t in kw.tokenize(g):
        if t.start < len(wa) < t.start + t.len: JOINTS.append(('붙임', wa + '|' + wb)); return a + b
        if t.start == len(wa):
            if t.tag[0] in 'JEX': JOINTS.append(('붙임', wa + '|' + wb)); return a + b
            break
    JOINTS.append(('띄움', wa + '|' + wb))
    return a + ' ' + b


def fold(body, caps):
    lines = []; cur = ''; k = 0
    for w in body.split(' '):
        nxt = cur + ' ' + w if cur else w
        if k >= len(caps): return None
        if wlen(nxt) <= caps[k]: cur = nxt
        else:
            if not cur: return None
            lines.append(cur); k += 1; cur = w
            if k >= len(caps) or wlen(cur) > caps[k]: return None
    lines.append(cur)
    return lines


def lib(kw, ko):
    p = [x for x in ko.split('／')]
    title = p[0]; body = p[1]
    for x in p[2:]:
        if x: body = joinjoint(kw, body, x)
    body = re.sub(' +', ' ', body)
    for caps in (LIB_CAPS, [10, 10, 10, 14, 14, 14]):
        ls = fold(body, caps)
        if ls: return '／'.join([title] + ls) + '／', ''
    ls = fold(body, LIB_CAPS + [14] * 6)                       # ⛔번역 안 깎음 — 7줄 넘으면 쪽 나눔(빌더)
    if ls: return '／'.join([title] + ls) + '／', 'libpage'
    return ko, 'lib'


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    kw = Kiwi()
    a = trcheck.load(trcheck.GOT)
    B = {}                                                     # 대사
    for n in sorted(a):
        if n.startswith('mono_abs'): continue
        for r in a[n][1:]: B[r[0]] = (r[1], r[2], r[3])
    A = {r[0]: (r[1], r[2], r[3], r[4]) for r in a['mono_abs_001.tsv'][1:]}
    cnt = collections.Counter(); rep = []; left = []
    SHORT = dict(ln.rstrip('\n').split('\t') for ln in open(os.path.join(HERE, 'lib_short.tsv'), encoding='utf-8') if ln.strip())
    # 실행 파일 먼저(아이템 이름 기준)
    absko = {}; item = {}
    for n, (w, cap, jp, ko0) in A.items():
        ko = punct(ko0)
        if '内蔵' in jp: ko = ko.replace('구라조', '쿠라조').replace('구라', '쿠라조').replace('내장', '쿠라조')
        ko = ABS_FIX.get(ko, ko)
        if '天狗' in jp: ko = ko.replace('덴구', '텐구')
        if '空手' in jp: ko = ko.replace('가라테', '카라테')
        if len(ko.rstrip('　 ')) > int(cap): left.append((n, w, 'abs 칸', ko))
        ko = ko.replace('덴구', '텐구')
        absko[n] = ko; item[jp.replace('　', '')] = ko.replace('　', ' ').strip()
        if ko != ko0: rep.append(('A' + n, w, jp, ko0, ko))
    out = {}
    for n, (w, jp, ko0) in B.items():
        ko = HAND.get(n, ko0)
        if n in HAND: cnt['손질'] += 1
        ko = punct(ko)
        if '内蔵' in jp:
            ko = rename(rename(rename(ko, '구라조', '쿠라조'), '내장', '쿠라조'), '구라', '쿠라조').replace('쿠라조조', '쿠라조')
        ko = ko.replace('덴구', '텐구')
        ko = ko.replace('가라테', '카라테').replace('게다', '게타') if re.search('空手|下駄', jp) else ko
        ko = quotes(ko, jp)
        if '（' in jp: ko = ko.replace('(', '（').replace(')', '）')
        if w.startswith('LIBRARY'):
            t = jp.split('／')[0]
            if t in item:
                pp = ko.split('／');
                if pp[0] != item[t]: cnt['백과 제목 맞춤'] += 1
                pp[0] = item[t]; ko = '／'.join(pp)
            if n in SHORT:                                     # 하스피 «백과는 적당히 줄여서» — 손으로 줄인 판
                ko = ko.split('／')[0] + '／' + SHORT[n].replace('|', '／') + '／'; why = ''
                for i, x in enumerate(SHORT[n].split('|')):
                    if wlen(x) > (10 if i < 3 else 14): left.append((n, w, '백과 폭 %d줄 %d칸' % (i, wlen(x)), x))
            else:
                ko, why = lib(kw, ko)
            if why == 'lib': left.append((n, w, why, ko))
            else: cnt['백과 다시 접음'] += 1
            if why == 'libpage': cnt['백과 쪽 나눔 필요'] += 1
        elif not w.startswith('WARNING'):
            ko, why = rewrap(ko, jp)
            if why == 'cut': left.append((n, w, 'cut', ko))
            elif why: cnt['줄 다시 나눔'] += 1
            if ko.count('／') > MAXLINES: cnt['쪽 나눔 필요'] += 1
        ko = ko.replace('덴구', '텐구')
        for t in '「」『』”（）':
            if w.startswith('LIBRARY') and n in SHORT: continue   # 줄인 판은 뜻 단위로 다시 씀
            if t in '（）' and n == '47': continue               # 원문 읽기 표기 駆使（くし） — 번역엔 없음
            if jp.count(t) != ko.count(t): left.append((n, w, '토큰 ' + t, ko)); break
        if re.search('[\u3040-\u30fa\u30fc-\u30ff\u4e00-\u9fff]', ko): left.append((n, w, '가나·한자', ko))
        if ko != ko0: rep.append((n, w, jp, ko0, ko)); cnt['바뀐 줄'] += 1
        out[n] = ko
    open(os.path.join(ROOT, 'work', 'text', 'joints.txt'), 'w', encoding='utf-8').write(chr(10).join(a + ' ' + b for a, b in JOINTS))
    print(dict(cnt)); print('남은 문제', len(left), collections.Counter(x[2] for x in left))
    for x in left[:50]: print('  ', x)
    with open(os.path.join(ROOT, 'work', 'text', 'merge_report.tsv'), 'w', encoding='utf-8', newline='\n') as o:
        o.write('번호\t위치\tJP\t받은 KO\t병합 KO\n')
        for x in rep: o.write('\t'.join(x) + '\n')
    if '--write' not in sys.argv: return
    # 표에 쓰기(원본 표는 *_before_merge 로)
    up = os.path.join(ROOT, 'work', 'text', 'uniq.tsv'); ap = os.path.join(ROOT, 'work', 'text', 'abs.tsv')
    for p in (up, ap):
        b = p[:-4] + '_before_merge.tsv'
        if not os.path.exists(b): shutil.copy2(p, b)
    U = open(up[:-4] + '_before_merge.tsv', encoding='utf-8').read().split('\n')
    res = [U[0]]
    for ln in U[1:]:
        if not ln: continue
        c = ln.split('\t'); assert out.get(c[0]) is not None and B[c[0]][1] == c[3], c[:4]
        res.append('\t'.join(c[:4] + [out[c[0]]]))
    open(up, 'w', encoding='utf-8', newline='\n').write('\n'.join(res) + '\n')
    U = open(ap[:-4] + '_before_merge.tsv', encoding='utf-8').read().split('\n')
    res = [U[0] + '\tKO']
    for ln in U[1:]:
        if not ln: continue
        c = ln.split('\t'); assert A[c[0]][2].rstrip('　') == c[3].rstrip('　'), c[:4]
        res.append('\t'.join(c[:4] + [absko[c[0]]]))
    open(ap, 'w', encoding='utf-8', newline='\n').write('\n'.join(res) + '\n')
    print('표 기록 완료')


if __name__ == '__main__':
    main()
