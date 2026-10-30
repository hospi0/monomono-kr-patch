# -*- coding: utf-8 -*-
r"""그림 글자 한글화(2026-10-30) — work/text/gfx.tsv(종류·번호·JP·KO) → work/build/MONOMONO/ (전부 원래 크기 제자리)
  title  TITLE.SP(VDP1 0x10000 적재) 80×24 8bpp 4장 +0x1C00 + k×0x780: 처음부터·이어하기 × (선택 노랑 / 비선택 검정)
         채움 y8~22 줄마다 색(선택 29→16, 비선택 2) · 1px 테두리(선택 3 흰색, 비선택 4 회색)
  win    OBJECT.SP(VDP1 0x56000) +0x120C0 272×48 8bpp «ゲンの勝ち!!»: 채움 y3~45 줄 그라데이션 48↔63 · 2px 테두리 4(흰색)
  name   적 이름판 35개 = BG_BN.MAP(이름당 12×4 셀 u32, 셀 번호 0x552+2k) → BG_BW.CEL(8×8 8bpp 셀, 팔레트 BG_BW.PLT)
         판 바탕 = 35장 화소별 최빈값(같은 판에 먹 글씨) · 먹 = 255 한 색 · 글자 y8~23 주아체(연성체는 16px 에서 ㄱ 획이 떨어져 보임)
         셀은 이름에만 쓰는 칸(판 BG_BW.MAP 와 겹치는 18칸 제외)에 중복 제거해 다시 배치
  panel  BG_BW.MAP(64×28) 판의 오른쪽 이름 «ゲン»·가운데 «対» 문장: 먹 화소 지우고(주변 색 번짐) 다시 씀 — 판에서 한 번만 쓰는 셀만
  icon   CURSOR.SP(VDP1 0x4000) 메뉴 정렬 탭 «あ»(50음순 → 가나다순, 순번은 build.py sort_keys):
         작은 탭 +0x39C0 16×24(바탕 1, 흰 글자 3) · 고른 탭 큰 아이콘 +0x1440 24×24(흰 3 + 테두리 1, 뒤 파란 카드 53~55)
  python tools/gfx_kr.py          → 미리보기 work/check/gfx_*.png(원본|새것)
  python tools/gfx_kr.py --write  → work/build/MONOMONO/ 에 씀(⛔미리보기 승인 전 금지)"""
import csv, os, struct, sys
from collections import Counter
import numpy as np
from PIL import Image, ImageDraw, ImageFont
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
DISC = os.path.join(ROOT, 'work', 'disc', 'MONOMONO')
OUT = os.path.join(ROOT, 'work', 'build', 'MONOMONO')
CHK = os.path.join(ROOT, 'work', 'check')
FONT = r'C:\claude\utils\font'
JUA = FONT + r'\jua\Jua-Regular.ttf'
HAN = FONT + r'\logo\BlackHanSans.ttf'

CEL0 = 0x552                                                   # BG_BW.CEL 첫 셀의 VDP2 셀 번호(256색 → 2씩)
INK = 255


def rd(n):
    return open(os.path.join(DISC, n), 'rb').read()


def texts():
    t = {}
    for r in csv.DictReader(open(os.path.join(ROOT, 'work', 'text', 'gfx.tsv'), encoding='utf-8'), delimiter='\t'):
        t[(r['종류'], r['번호'])] = r['KO']
    return t


def mask(text, ttf, h, maxw, width=None):
    """글자 모양(bool h×w) — '한' 높이를 h 로, 넓으면 가로만 눌러 maxw 안, width 주면 글자 사이를 벌려 그 폭으로"""
    S = 4
    F0 = ImageFont.truetype(ttf, 200)
    rb = F0.getbbox('한')
    F = ImageFont.truetype(ttf, int(200 * h * S / (rb[3] - rb[1])))
    rb = F.getbbox('한')
    ch = []
    for c in text:
        if c == ' ':
            ch.append(None); continue
        b = F.getbbox(c)
        im = Image.new('L', (b[2] - b[0] + 8, h * S + 8 * S), 0)
        ImageDraw.Draw(im).text((4 - b[0], 4 * S - rb[1]), c, font=F, fill=255)
        a = np.asarray(im) > 0
        cols = np.where(a.any(0))[0]
        ch.append(a[4 * S:4 * S + h * S, cols[0]:cols[-1] + 1] if len(cols) else None)
    gap = int(h * S * 0.08); sp = int(h * S * 0.45)
    nat = sum(sp if c is None else c.shape[1] for c in ch) + gap * (len(ch) - 1)
    if width and len(ch) > 1 and nat < width * S:
        gap += (width * S - nat) // (len(ch) - 1)
    W = sum(sp if c is None else c.shape[1] for c in ch) + gap * (len(ch) - 1)
    out = np.zeros((h * S, W), bool); x = 0
    for c in ch:
        if c is None:
            x += sp + gap; continue
        out[:, x:x + c.shape[1]] |= c; x += c.shape[1] + gap
    w = min(maxw, (W + S - 1) // S)
    im = Image.fromarray(out.astype(np.uint8) * 255).resize((w, h), Image.BOX)
    return np.asarray(im) >= 110


def dilate(m, r):
    o = m.copy()
    for dy in range(-r, r + 1):
        for dx in range(-r, r + 1):
            if dx * dx + dy * dy > r * r + r:
                continue
            o |= np.roll(np.roll(m, dy, 0), dx, 1)
    return o


def place(m, H, W, y0, cx=None):
    """m 을 (H,W) 판의 y0 줄, 가운데(cx) 에 놓은 bool"""
    o = np.zeros((H, W), bool)
    x0 = (W - m.shape[1]) // 2 if cx is None else int(round(cx - m.shape[1] / 2))
    o[y0:y0 + m.shape[0], x0:x0 + m.shape[1]] = m
    return o


# ── VDP1 스프라이트(타이틀·승리) ──
TITLE = [(0, 'title', '0', 1), (1, 'title', '1', 1), (2, 'title', '0', 0), (3, 'title', '1', 0)]


def title_sprites(T):
    b = bytearray(rd('TITLE.SP')); out = []
    for k, kind, no, sel in TITLE:
        o = 8 + 0x1C00 + k * 1920
        m = place(mask(T[(kind, no)], JUA, 15, 76), 24, 80, 8)
        ol = dilate(m, 1) & ~m
        a = np.zeros((24, 80), np.uint8)
        for y in range(24):
            a[y][ol[y]] = 3 if sel else 4
            a[y][m[y]] = max(16, min(29, 37 - y)) if sel else 2
        b[o:o + 1920] = a.tobytes(); out.append(a)
    return bytes(b), out


def win_sprite(T):
    b = bytearray(rd('OBJECT.SP')); o = 8 + 0x120C0
    m = place(mask(T[('win', '0')], HAN, 43, 266), 48, 272, 3)
    ol = dilate(m, 2) & ~m
    a = np.zeros((48, 272), np.uint8)
    for y in range(48):
        a[y][ol[y]] = 4
        a[y][m[y]] = max(48, min(63, 46 + y, 93 - y))
    b[o:o + 48 * 272] = a.tobytes()
    return bytes(b), a


def icon_sprites(T):
    b = bytearray(rd('CURSOR.SP')); t = T[('icon', '0')]
    o = 8 + 0x39C0                                              # 작은 탭: 글자 칸 y9~20 x1~14 를 바탕 1 로
    s = np.frombuffer(b[o:o + 384], np.uint8).reshape(24, 16).copy()
    s[9:21, 1:15][np.isin(s[9:21, 1:15], (3, 17))] = 1
    m = place(mask(t, JUA, 12, 12), 24, 16, 9, 7.5)
    s[m] = 3; b[o:o + 384] = s.tobytes()
    o = 8 + 0x1440                                              # 큰 아이콘: 파란 카드 다시 깔고 흰 글자 + 검은 테두리
    g = np.frombuffer(b[o:o + 576], np.uint8).reshape(24, 24)
    a = np.zeros((24, 24), np.uint8)
    for y in range(5, 22):
        for x in range(max(8, 18 - (y - 5)), min(23, 20 + (y - 5)) + 1):
            a[y, x] = g[y, x] if g[y, x] in (53, 54, 55) else 53
    m = place(mask(t, JUA, 17, 19), 24, 24, 2, 9.5)
    a[dilate(m, 1) & ~m] = 1; a[m] = 3
    b[o:o + 576] = a.tobytes()
    return bytes(b), s, a


# ── VDP2 판(이름판·겐·対) ──
def pal():
    return [((v & 31) * 8, ((v >> 5) & 31) * 8, ((v >> 10) & 31) * 8) for v in struct.unpack('>256H', rd('BG_BW.PLT'))]


def cells(c):
    return [np.frombuffer(c[k * 64:k * 64 + 64], np.uint8).reshape(8, 8) for k in range(len(c) // 64)]


def idx(e):
    return ((e & 0x7FFF) - CEL0) // 2


def compose(cl, ents, w):
    h = len(ents) // w
    a = np.zeros((h * 8, w * 8), np.uint8)
    for k, e in enumerate(ents):
        i = idx(e)
        if 0 <= i < len(cl):
            t = cl[i][:, ::-1] if (e >> 30) & 1 else cl[i]
            a[(k // w) * 8:(k // w) * 8 + 8, (k % w) * 8:(k % w) * 8 + 8] = t
    return a


def inpaint(a, hole, P, keep):
    """hole 화소를 주변 색 평균으로 채운 뒤 keep 색(팔레트 번호) 중 가까운 것으로"""
    rgb = np.array(P, float)[a]; known = ~hole.copy(); H, W = a.shape
    while not known.all():
        acc = np.zeros((H, W, 3)); n = np.zeros((H, W))
        for dy, dx in ((0, 1), (0, -1), (1, 0), (-1, 0)):
            k = np.roll(np.roll(known, dy, 0), dx, 1); v = np.roll(np.roll(rgb, dy, 0), dx, 1)
            acc += v * k[..., None]; n += k
        new = ~known & (n > 0)
        rgb[new] = acc[new] / n[new][:, None]; known |= new
    kp = np.array([P[i] for i in keep], float)
    out = a.copy()
    ys, xs = np.where(hole)
    for y, x in zip(ys, xs):
        out[y, x] = keep[int(((kp - rgb[y, x]) ** 2).sum(1).argmin())]
    return out


def is_ink(a, P, box, lim):
    y0, y1, x0, x1 = box
    s = np.array([sum(c) for c in P])[a]
    r = np.array([c[0] - c[2] for c in P])[a]
    m = (s < lim) & (r < 60)                                   # 검정·회색 먹(붉은 테두리·주황 바탕 제외)
    o = np.zeros_like(m); o[y0:y1, x0:x1] = m[y0:y1, x0:x1]
    return o


def ring(a, box, red=22):
    """対 문장 = 빨간 고리(22) 안쪽 — 중심·반지름"""
    y0, y1, x0, x1 = box
    ys, xs = np.where(a[y0:y1, x0:x1] == red)
    cy, cx = (ys.min() + ys.max()) / 2 + y0, (xs.min() + xs.max()) / 2 + x0
    return cy, cx, min(ys.max() - ys.min(), xs.max() - xs.min()) / 2


def names(T, cl, P):
    bn = struct.unpack('>1680I', rd('BG_BN.MAP'))
    orig = [compose(cl, bn[n * 48:n * 48 + 48], 12) for n in range(35)]
    st = np.stack(orig)
    base = np.zeros((32, 96), np.uint8)
    for y in range(32):
        for x in range(96):
            base[y, x] = Counter(st[:, y, x].tolist()).most_common(1)[0][0]
    hole = is_ink(base, P, (6, 26, 0, 96), 430)                # 최빈값에도 남은 먹(«ロ ウ» 자리 등)
    base = inpaint(base, hole, P, sorted(set(base[6:26][~hole[6:26]].tolist())))
    new = []
    for n in range(35):
        t = T[('name', str(n))]; L = len(t.replace(' ', ''))
        width = {2: 52, 3: 66}.get(L) if ' ' not in t else None
        m = place(mask(t, JUA, 16, 88, width), 32, 96, 8)
        a = base.copy(); a[m] = INK; new.append(a)
    return bn, orig, new, base


def panel(T, cl, P, used_by_names, base):
    bw = struct.unpack('>1792I', rd('BG_BW.MAP'))
    a = compose(cl, bw, 64); o = a.copy()
    GEN = (190, 209, 182, 290); TAI = (164, 212, 138, 182)
    for box, key in ((GEN, ('panel', 'gen')), (TAI, ('panel', 'tai'))):
        if key[1] == 'gen':
            ink = is_ink(o, P, box, 430)                       # 양피지 위 회색 번짐까지
            ys, xs = np.where(ink); cx = (xs.min() + xs.max() + 1) / 2
            # 오른쪽 판 = 이름판과 같은 그림 → 깨끗한 이름판 바탕을 맞는 자리에 덮음
            best = min(((np.abs(o[y:y + 32, x:x + 96].astype(int) - base).astype(bool) & ~dilate(ink[y:y + 32, x:x + 96], 1)).sum(), y, x)
                       for y in range(176, 192) for x in range(150, 230))
            _, by, bx = best
            y0, y1, x0, x1 = box
            for yy in range(y0, y1):
                for xx in range(x0, min(x1, bx + 96)):
                    a[yy, xx] = base[yy - by, xx - bx]
            m = mask(T[key], JUA, 16, 90)
            a[place(m, a.shape[0], a.shape[1], by + 8, cx)] = INK
            print('겐 판 바탕 맞춤 y%d x%d 어긋남 %d' % (by, bx, best[0]))
            continue
        else:
            ry, rx, rr = ring(o, box)
            Y, X = np.mgrid[:o.shape[0], :o.shape[1]]
            ink = is_ink(o, P, box, 330) & ((Y - ry) ** 2 + (X - rx) ** 2 < (rr - 1.5) ** 2)
        ys, xs = np.where(ink)
        cy, cx = (ys.min() + ys.max() + 1) / 2, (xs.min() + xs.max() + 1) / 2
        y0, y1, x0, x1 = box
        inside = (Y - ry) ** 2 + (X - rx) ** 2 < (rr - 1.5) ** 2
        keep = sorted(set(o[inside & ~ink].tolist()))             # 원 안 색만
        a = inpaint(a, ink, P, keep)
        if True:
            m = mask(T[key], JUA, int(rr * 1.15), int(rr * 1.7))     # 원 가운데(ㅐ 틈 안 메워지게 폭 여유)
            a[place(m, a.shape[0], a.shape[1], int(round(ry - m.shape[0] / 2)), rx)] = INK
    # 바뀐 칸 → 셀(판에서 한 번만, 이름과 안 겹침)
    use = Counter(idx(e) for e in bw); wr = {}
    for k, e in enumerate(bw):
        ry, rx = (k // 64) * 8, (k % 64) * 8
        if (a[ry:ry + 8, rx:rx + 8] != o[ry:ry + 8, rx:rx + 8]).any():
            i = idx(e)
            assert use[i] == 1 and i not in used_by_names and not (e >> 30) & 1, (k, hex(e))
            wr[i] = a[ry:ry + 8, rx:rx + 8].copy()
    return o, a, wr


def build_cel(T):
    c = rd('BG_BW.CEL'); cl = cells(c); P = pal()
    bn, orig, new, base = names(T, cl, P)
    bw = struct.unpack('>1792I', rd('BG_BW.MAP'))
    N = set(idx(e) for e in bn); Pn = set(idx(e) for e in bw)
    po, pa, wr = panel(T, cl, P, N, base)
    slots = sorted(N - Pn)
    shared = {cl[i].tobytes(): i for i in N & Pn}
    got = dict(shared); nxt = iter(slots); ents = []
    for a in new:
        for k in range(48):
            t = a[(k // 12) * 8:(k // 12) * 8 + 8, (k % 12) * 8:(k % 12) * 8 + 8].tobytes()
            if t not in got:
                got[t] = next(nxt)
            ents.append(CEL0 + 2 * got[t])
    used = len(got) - len(shared)
    nc = bytearray(c)
    for t, i in got.items():
        nc[i * 64:i * 64 + 64] = t
    for i in slots[used:]:                                     # 남는 칸은 판 바탕으로
        nc[i * 64:i * 64 + 64] = new[0][8:16, 0:8].tobytes()
    for i, t in wr.items():
        nc[i * 64:i * 64 + 64] = t.tobytes()
    bnm = struct.pack('>1680I', *ents)
    # 검산: 새 셀로 다시 그리면 그린 그림과 같음
    ncl = cells(bytes(nc))
    for n in range(35):
        assert (compose(ncl, ents[n * 48:n * 48 + 48], 12) == new[n]).all(), n
    assert (compose(ncl, bw, 64) == pa).all()
    print('이름판 셀 %d / 빈 칸 %d, 판 셀 %d 고침' % (used, len(slots), len(wr)))
    return bytes(nc), bnm, orig, new, po, pa, P


# ── 미리보기 ──
def shot(name):
    im = Image.open(os.path.join(ROOT, 'work', 'states', name + '.png')).convert('RGB').crop((26, 0, 1714, 1292))
    return np.asarray(im.resize((320, 224), Image.BOX)).astype(int)


def cram(st, bank):
    cr = open(os.path.join(ROOT, 'work', 'mem', st, 'CRAM.bin'), 'rb').read()
    cr = bytes(x for p in zip(cr[1::2], cr[0::2]) for x in p)
    return [((c & 31) * 8, ((c >> 5) & 31) * 8, ((c >> 10) & 31) * 8) for c in struct.unpack_from('>64H', cr, bank * 2)]


def locate(bg, spr, C):
    op = spr > 0; col = np.array(C)[spr]; H, W = spr.shape; best = None
    for y in range(0, 224 - H + 1):
        for x in range(0, 320 - W + 1):
            d = np.abs(bg[y:y + H, x:x + W][op] - col[op]).mean()
            if best is None or d < best[0]:
                best = (d, y, x)
    return best[1], best[2]


def paste(bg, old, new, C, y, x):
    """old 자리를 좌우 바탕으로 메우고(미리보기용) new 를 얹음"""
    o = bg.copy(); H, W = old.shape
    reg = o[y:y + H, x:x + W]
    for r in range(H):
        ok = np.where(old[r] == 0)[0]
        if len(ok):
            for c in np.where(old[r] > 0)[0]:
                reg[r, c] = reg[r, ok[np.abs(ok - c).argmin()]]
    reg[new > 0] = np.array(C)[new][new > 0]
    return o


def zoom(a, s):
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8)).resize((a.shape[1] * s, a.shape[0] * s), Image.NEAREST)


def side(a, b, s, gap=8):
    A, B = zoom(a, s), zoom(b, s)
    o = Image.new('RGB', (A.width + B.width + gap, max(A.height, B.height)), (40, 40, 40))
    o.paste(A, (0, 0)); o.paste(B, (A.width + gap, 0)); return o


def preview(T, tsp, win, nc):
    os.makedirs(CHK, exist_ok=True)
    # 타이틀
    C = cram('타이틀', 0x400); bg = shot('타이틀'); old = rd('TITLE.SP')
    olds = [np.frombuffer(old[8 + 0x1C00 + k * 1920:][:1920], np.uint8).reshape(24, 80) for k in range(4)]
    y0, x0 = locate(bg, olds[0], C); y1, x1 = locate(bg, olds[3], C)
    nb = paste(paste(bg, olds[0], tsp[0], C, y0, x0), olds[3], tsp[3], C, y1, x1)
    cut = lambda a: a[y0 - 20:y1 + 36, :]
    im = side(cut(bg), cut(nb), 3)
    sp = lambda a: zoom(np.where(a[..., None] > 0, np.array(C)[a], 60), 3)      # 4장 낱장(회색 바탕)
    strip = Image.new('RGB', (im.width, 24 * 3 * 2 + 8), (40, 40, 40))
    for k in range(4):
        strip.paste(sp(olds[k]), (k * 250, 0)); strip.paste(sp(tsp[k]), (k * 250, 24 * 3 + 8))
    o = Image.new('RGB', (im.width, im.height + strip.height + 8), (40, 40, 40)); o.paste(im, (0, 0)); o.paste(strip, (0, im.height + 8))
    o.save(os.path.join(CHK, 'gfx_title.png'))
    # 승리
    C = cram('전투승리', 0x500); bg = shot('전투승리')
    ow = np.frombuffer(rd('OBJECT.SP')[8 + 0x120C0:][:48 * 272], np.uint8).reshape(48, 272)
    y, x = locate(bg, ow, C)
    nb = paste(bg, ow, win, C, y, x)
    o = Image.new('RGB', (320 * 3, 80 * 3 * 2 + 8), (40, 40, 40))
    o.paste(zoom(bg[y - 16:y + 64], 3), (0, 0)); o.paste(zoom(nb[y - 16:y + 64], 3), (0, 80 * 3 + 8))
    o.save(os.path.join(CHK, 'gfx_win.png'))
    # 이름판
    _, _, orig, new, po, pa, P = nc
    Pa = np.array(P)
    cols = 5; cw, chh = 96 * 2 + 6, 32
    o = Image.new('RGB', ((cw + 10) * cols * 2, (chh + 6) * 7 * 2), (40, 40, 40))
    for n in range(35):
        x = (n % cols) * (cw + 10) * 2; y = (n // cols) * (chh + 6) * 2
        o.paste(side(Pa[orig[n]], Pa[new[n]], 2, 12), (x, y))
    o.save(os.path.join(CHK, 'gfx_names.png'))
    r0, r1 = 17 * 8, 28 * 8
    o = Image.new('RGB', (320 * 3, (r1 - r0) * 3 * 2 + 8), (40, 40, 40))
    o.paste(zoom(Pa[po[r0:r1, :320]], 3), (0, 0)); o.paste(zoom(Pa[pa[r0:r1, :320]], 3), (0, (r1 - r0) * 3 + 8))
    o.save(os.path.join(CHK, 'gfx_panel.png'))
    print('미리보기:', ', '.join(os.path.join(CHK, n) for n in ('gfx_title.png', 'gfx_win.png', 'gfx_names.png', 'gfx_panel.png')))


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    T = texts()
    tb, tsp = title_sprites(T)
    ob, win = win_sprite(T)
    nc = build_cel(T)
    cb, si, bi = icon_sprites(T)
    preview(T, tsp, win, nc)
    C = np.array(cram('메뉴', 0x7C0)); old = rd('CURSOR.SP')
    os_ = np.frombuffer(old[8 + 0x39C0:][:384], np.uint8).reshape(24, 16); ob_ = np.frombuffer(old[8 + 0x1440:][:576], np.uint8).reshape(24, 24)
    sh = lambda a: np.where(a[..., None] > 0, C[a], 60)
    o = Image.new('RGB', (24 * 6 * 2 + 16, 24 * 6 * 2 + 16), (40, 40, 40))
    o.paste(zoom(sh(os_), 6), (24, 0)); o.paste(zoom(sh(si), 6), (24 * 6 + 16 + 24, 0))
    o.paste(zoom(sh(ob_), 6), (0, 24 * 6 + 16)); o.paste(zoom(sh(bi), 6), (24 * 6 + 16, 24 * 6 + 16))
    o.save(os.path.join(CHK, 'gfx_icon.png')); print('미리보기:', os.path.join(CHK, 'gfx_icon.png'))
    if '--write' in sys.argv:
        os.makedirs(OUT, exist_ok=True)
        for n, b in (('CURSOR.SP', cb), ('TITLE.SP', tb), ('OBJECT.SP', ob), ('BG_BW.CEL', nc[0]), ('BG_BN.MAP', nc[1])):
            assert len(b) == len(rd(n)), n
            open(os.path.join(OUT, n), 'wb').write(b)
        print('씀:', OUT)


if __name__ == '__main__':
    main()
