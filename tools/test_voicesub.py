# -*- coding: utf-8 -*-
"""오프닝·엔딩 음성 자막 훅 검산(2026-10-30, 에너미 제로 test_sub.py 꼴) — 패치 ABSOLUTE.BIN 을 흉내기 램에 올려
   ① 명령 표 10 칸·VBO 등록 ② vwrap: PC 가 «_A1_001» → cur 0·프레임 0·원래 처리 호출 / 표에 없는 이름 → cur −1
   ③ 프레임마다 vbo(게임 DMA 표 흉내): 쪽 그림 = ref_render · 색 · 표 끝 덧붙임 · 끝 지나면 cur −1 (전 음성)
   ④ 표 안 새로 짠 프레임 → 두 번 안 붙임 ⑤ BGON ≠ 1(그림 화면 아님) → 안 붙임 ⑥ 미리보기 work/check/vsub_*.png
   python tools/test_voicesub.py"""
import os, struct, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE); sys.path.insert(0, HERE)
import sh2sim as S, voicesub as H

DMA_TBL = 0x060F0000
SYS_END = 0x06032C02
NAMEBUF = 0x06054970


def game_table(m, n=2):
    m.w32(H.DMA_PTR, DMA_TBL)
    for k in range(n):
        p = DMA_TBL + 12 * k
        m.w32(p, 0x1E); m.w32(p + 4, 0x25C00060 + 0x20 * k)
        m.w32(p + 8, (0x8000_0000 | SYS_END) if k == n - 1 else 0x0602D5A0)
    for k in range(n, n + 3):
        for j in (0, 4, 8): m.w32(DMA_TBL + 12 * k + j, 0xAAAAAAAA)


def save_png(tex, path):
    from PIL import Image
    col = {0: (40, 60, 80), 1: (0, 0, 0), 2: (255, 255, 255), 3: (0, 0, 0)}
    im = Image.new('RGB', (H.W_, H.H_))
    for y in range(H.H_):
        for x in range(0, H.W_, 2):
            b = tex[y * H.ROWB + x // 2]; im.putpixel((x, y), col[b >> 4]); im.putpixel((x + 1, y), col[b & 15])
    im.resize((H.W_ * 3, H.H_ * 3), Image.NEAREST).save(path)


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    data = H.build_data(); idx, bits, advs, names, lists, pages_all = data
    a0 = open(os.path.join(ROOT, 'work', 'disc', 'ABSOLUTE.BIN'), 'rb').read()
    s, lab, lay = H.patch(a0, data)
    m = S.Mem(); ram = m.add(0x06000000, 0x100000); m.add(0x05C00000, 0x80000)
    ram[0x4000:0x4000 + len(s)] = s
    ok = True
    c0 = m.r32(H.CMD10_AT) == lab['vwrap'] and m.r32(H.VBO_LIT) == lab['vbo']
    print('① 명령 표 10 칸·VBO 등록', c0); ok &= c0
    os.makedirs(os.path.join(ROOT, 'work', 'check'), exist_ok=True)
    called = []

    def vw(nm):
        for i, ch in enumerate(nm.encode('latin1') + b'\0\x05'): m.w8(NAMEBUF + i, ch)
        m.w32(H.PCVAR, NAMEBUF)
        S.run(m, lab['vwrap'], regs=[0, 0, 0, 0, 0x1111, 0x2222, 0x3333, 0x4444, 0x5555], calls={H.CMD10: lambda r, mm: called.append((r[4], r[5], r[6], r[7], r[8]))})

    def frame(rebuild=True, bgon=1):
        m.w16(H.BGON_SH, bgon)
        if rebuild: game_table(m)
        S.run(m, lab['vbo'], calls={H.VBO_ORIG: lambda r, mm: None})

    end_e = DMA_TBL + 12 * 1

    def patched():
        return m.r32(end_e + 8) == H.SPR and m.r32(end_e + 12 + 8) == (H.ENDC | 0x80000000) and m.r32(end_e + 12 + 4) == 0x25C00080 + 0x20 and m.r32(end_e + 12) == 0x1E

    # ② 이름 대조
    vw(names[0])
    c1 = called == [(0x1111, 0x2222, 0x3333, 0x4444, 0x5555)] and m.r32(H.VAR) == 0 and m.r32(H.VAR + 4) == 0
    print('② vwrap %s → cur 0·프레임 0·원래 처리(r4~r8 보존)' % names[0], c1); ok &= c1
    vw('_B1_001')
    c1b = m.r32(H.VAR) == 0xFFFFFFFF
    print('   표에 없는 음성(_B1_001) → cur −1', c1b); ok &= c1b
    # ③ 전 음성
    bad_all = 0
    for no, nm in enumerate(names):
        vw(nm)
        if m.r32(H.VAR) != no: print('  ✗ 번호', nm); bad_all += 1; continue
        pages = pages_all[no]; seen = []; bad = 0
        for f in range(pages[-1][1] + 3):
            frame()
            fr = S.s32(m.r32(H.VAR + 4))
            cur = next((k for k, p in enumerate(pages) if p[0] <= fr < p[1]), None)
            if cur is None:
                if patched(): bad += 1
                continue
            if not patched(): bad += 1
            if not seen or seen[-1] != cur:
                seen.append(cur)
                tex = bytes(m.r8(H.TEX + i) for i in range(H.BMPSZ)); ref = H.ref_render(pages[cur], bits, advs)
                lut = [m.r16(H.LUT + 2 * i) for i in range(4)]
                if tex != ref or lut != list(H.COLORS): print('  ✗ %s 쪽 %d 그림/색 다름' % (nm, cur)); bad += 1
                save_png(tex, os.path.join(ROOT, 'work', 'check', 'vsub_%s_%d.png' % (nm, cur)))
        if bad or len(seen) != len(pages) or m.r32(H.VAR) != 0xFFFFFFFF:
            print('  ✗ %s 쪽 %d/%d 오류 %d cur %08X' % (nm, len(seen), len(pages), bad, m.r32(H.VAR))); bad_all += 1
    c3 = bad_all == 0
    print('③ 음성 %d개 전 쪽 그림 일치·표 덧붙임·끝나면 cur −1' % len(names), c3); ok &= c3
    # ④ 표 안 새로 짠 프레임
    vw(names[1]); frame(); frame(rebuild=False)
    c4 = m.r32(DMA_TBL + 12 * 2 + 8) == (H.ENDC | 0x80000000) and m.r32(DMA_TBL + 12 * 3) == 0xAAAAAAAA
    print('④ 표 안 새로 짠 프레임 → 두 번 안 붙임', c4); ok &= c4
    # ⑤ 그림 화면 아님
    frame(bgon=0x1E)
    c5 = m.r32(end_e + 8) == (0x80000000 | SYS_END)
    print('⑤ BGON 0x1E(필드) → 안 붙임', c5); ok &= c5
    print('★전체', '통과' if ok else '실패')
    return ok


if __name__ == '__main__':
    sys.exit(0 if main() else 1)
