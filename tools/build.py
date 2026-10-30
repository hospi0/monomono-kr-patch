# -*- coding: utf-8 -*-
r"""전체 입력 만들기(2026-10-30) → work/build/ (FONT.DAT · ABSOLUTE.BIN · MONOMONO/*.MSG · WARNING.MSG) — 디스크 쓰기는 tools/discbuild.py
  MSG: script.tsv 조각을 번역으로 갈아 끼우고 분기 주소(u16 BE)를 새 오프셋으로. 대상이 조각 안이면 중단. 파일당 ≤ 0x10000
       대사(msg) 3줄 넘으면 쪽 나눔: 3줄마다 «04 00 03(키 대기·창 닫기) + 앞의 16 얼굴 명령» 삽입
  WARNING.MSG: 스크립트 아님 — 조각 자리 그대로, 남으면 끝 0D 앞 전각 공백으로
  ABSOLUTE.BIN: 제자리, 칸 바이트(원문 채움 포함) 안, 남으면 전각 공백 · 정렬 탭 순번(sort_keys) · 오프닝·엔딩 음성 자막 훅(tools/voicesub.py — 파일이 0x8F670 까지 늘어남)
  검사(빌드 실패): 번역 빈 조각 · 표 행 미사용 · 매핑 없는 글자 · 재파싱 분기 어긋남 · 64 KB · 칸 넘침
  python tools/build.py"""
import bisect, csv, os, struct, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import krenc, msgparse

DISC = os.path.join(ROOT, 'work', 'disc')
OUT = os.path.join(ROOT, 'work', 'build')
MAX = 0x10000
LINES = 3
MID = {('TALK.MSG', 0x6014): 21}                               # 분기 3곳이 이 조각 둘째 줄로 들어옴


def table(n):
    return list(csv.DictReader(open(os.path.join(ROOT, 'work', 'text', n), encoding='utf-8'), delimiter='\t', quoting=csv.QUOTE_NONE))


ITEMS, ITEM_N, ITEM_SZ, SORT = 0x30A66, 220, 38, 20
READ = {'ＣＤ': '씨디'}                                       # 번역 안 하는(가나 없는) 이름의 정렬 읽기


def sort_keys(a):
    """아이템 표 +20 = 메뉴 «가» 탭(원래 «あ» 50음순) 순번 1~200 → 한글 이름 가나다순으로 다시 매김(0 = 탭에 안 나옴, 그대로)"""
    ko = {int(r['오프셋'], 16): r['KO'].rstrip('　') for r in table('abs.tsv')}
    its = []
    for k in range(ITEM_N):
        o = ITEMS + k * ITEM_SZ
        if a[o + SORT]:
            nm = ko.get(o) or READ.get(a[o:o + 18].split(b'\0')[0].decode('cp932').rstrip('　'))
            if not nm: raise SystemExit('정렬 탭 아이템 번역 없음 %X' % o)
            its.append((nm, a[o + SORT], o))
    if sorted(i[1] for i in its) != list(range(1, len(its) + 1)): raise SystemExit('정렬 순번이 1~N 이 아님')
    for n, (_, _, o) in enumerate(sorted(its), 1):
        a[o + SORT] = n
    return its


def page(ko, face):
    """3줄 넘는 대사 → [바이트…] 쪽마다"""
    body = ko.split('／'); tail = body.pop() if body and body[-1] == '' else None
    assert tail is not None, ko
    out = bytearray()
    for i in range(0, len(body), LINES):
        if i: out += b'\x04\x00\x03' + face
        out += krenc.encode('／'.join(body[i:i + LINES]) + '／')
    return bytes(out)


def rebuild(b, reps):
    """reps = [(시작, 끝, 새 바이트)] → 분기 주소 고친 새 파일"""
    it = msgparse.parse(b)
    reps = sorted(reps); starts = [r[0] for r in reps]
    deltas = []; d = 0
    for a, e, n in reps:
        d += len(n) - (e - a); deltas.append(d)
    def mp(p):
        i = bisect.bisect_right(starts, p) - 1
        if i < 0: return p
        a, e, n = reps[i]
        if p == a: return p + (deltas[i - 1] if i else 0)
        if p < e: raise SystemExit('분기 대상이 문장 조각 안 @%X' % p)
        return p + deltas[i]
    nb = bytearray(); q = 0
    for a, e, n in reps:
        nb += b[q:a] + n; q = e
    nb += b[q:]
    nb2 = bytearray(nb)
    for s, e, k, v in it:
        if k != 'op': continue
        for ap in v[1]:
            t = struct.unpack_from('>H', b, ap)[0]
            nt = mp(t)
            if nt > 0xFFFF: raise SystemExit('주소 64 KB 넘음')
            struct.pack_into('>H', nb2, mp(ap), nt)
    return bytes(nb2)


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    os.makedirs(os.path.join(OUT, 'MONOMONO'), exist_ok=True)
    open(os.path.join(OUT, 'FONT.DAT'), 'wb').write(krenc.build_font(open(os.path.join(DISC, 'FONT.DAT'), 'rb').read()))
    ko = {r['JP']: r['KO'] for r in table('uniq.tsv')}
    used = set(); by = {}
    for r in table('script.tsv'):
        by.setdefault(r['파일'], []).append((int(r['오프셋'], 16), int(r['바이트']), r['종류'], r['JP']))
    sizes = []; pages = 0
    for nm, rows in by.items():
        sub = 'WARNING.MSG' == nm
        src = os.path.join(DISC, nm) if sub else os.path.join(DISC, 'MONOMONO', nm)
        b = open(src, 'rb').read(); reps = []
        for a, n, kind, jp in rows:
            t = ko.get(jp)
            if not t: raise SystemExit('번역 없음 %s %X %s' % (nm, a, jp))
            used.add(jp)
            if sub:
                e = krenc.encode(t)
                if len(e) > n: raise SystemExit('WARNING 넘침 %d>%d %s' % (len(e), n, t))
                pad = n - len(e)
                reps.append((a, a + n, e[:-1] + b'\x81\x40' * (pad // 2) + e[-1:] + b'\r' * (pad % 2)))   # 홀수면 끝 빈 줄 하나
            elif kind == 'msg' and t.count('／') > LINES:
                assert b[a - 4] == 0x16, (nm, a)
                reps.append((a, a + n, page(t, b[a - 4:a]))); pages += 1
            elif (nm, a) in MID:                                # 조각 안 둘째 줄이 분기 대상 — 줄 단위로 나눠 끼움
                k = MID[(nm, a)]; x, y = t.split('／', 1)
                reps.append((a, a + k, krenc.encode(x + '／'))); reps.append((a + k, a + n, krenc.encode(y)))
            else:
                reps.append((a, a + n, krenc.encode(t)))
        if sub:
            nb = bytearray(b)
            for a, e, x in reps: nb[a:e] = x
            nb = bytes(nb); assert len(nb) == len(b)
            open(os.path.join(OUT, nm), 'wb').write(nb)
            continue
        nb = rebuild(b, reps)
        if len(nb) > MAX: raise SystemExit('크기 %s %X' % (nm, len(nb)))
        bad = msgparse.check(nb, msgparse.parse(nb))
        if bad: raise SystemExit('재파싱 분기 어긋남 %s %s' % (nm, bad[:3]))
        open(os.path.join(OUT, 'MONOMONO', nm), 'wb').write(nb); sizes.append((len(nb), nm))
    miss = [j for j, t in ko.items() if j not in used]
    if miss: raise SystemExit('표 행 미사용 %d %s' % (len(miss), miss[:5]))
    a = bytearray(open(os.path.join(DISC, 'ABSOLUTE.BIN'), 'rb').read())
    for r in table('abs.tsv'):
        o = int(r['오프셋'], 16); n = int(r['바이트']); e = krenc.encode(r['KO'].rstrip('　'))
        if len(e) > n: raise SystemExit('실행 파일 칸 넘침 %s %s' % (r['번호'], r['KO']))
        pad = n - len(e)
        if pad % 2: raise SystemExit('홀수 칸 ' + r['번호'])
        if a[o:o + n].decode('cp932').rstrip('　') != r['JP'].rstrip('　'): raise SystemExit('원문 다름 ' + r['번호'])
        a[o:o + n] = e + b'\x81\x40' * (pad // 2)
    sort_keys(a)
    import voicesub, test_voicesub                                  # 오프닝·엔딩 음성 자막 훅(검산 통과해야 넣음)
    if not test_voicesub.main(): raise SystemExit('음성 자막 훅 검산 실패')
    a = voicesub.patch(bytes(a))[0]
    open(os.path.join(OUT, 'ABSOLUTE.BIN'), 'wb').write(a)
    print('MSG', len(sizes), '최대', hex(max(sizes)[0]), max(sizes)[1], '· 쪽 나눔 대사', pages, '· 실행 파일', len(table('abs.tsv')))
    print('완료 →', OUT)


if __name__ == '__main__':
    main()
