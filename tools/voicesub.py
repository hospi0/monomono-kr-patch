# -*- coding: utf-8 -*-
r"""오프닝·엔딩 음성 자막 훅(2026-10-30, 에너미 제로 tools/subhook.py·subdata.py 를 옮김 — 같은 SGL)
  ■ 게임(ABSOLUTE.BIN, 램 0x06004000, BSS 0x06037610~0x0608CA08 — 진입점 0x06004058 이 지움, 힙 0x060B0000+0x40000)
    · 스크립트 명령 표 0x0603480C: 10(음성 «_A1_001»…) 처리 0x06008A98 — 들어올 때 PC 변수(0x06054964)가 이름 문자열을 가리킴
    · SGL VBlank-OUT 처리기 0x0602D742(등록 리터럴 0x0602D954) 가 VDP1 명령을 «간접 DMA 표»(포인터 0x06034508 → 0x060F0000)로 보냄
      항목 12 B {0x1E, VDP1 쓸 곳, 읽을 곳(마지막 = 비트 31, END 견본 0x06032C02)}
    · SGL VDP2 레지스터 사본 0x060FFCC0 — BGON(+0x20) 오프닝 그림 화면 = 0x0001(타이틀 0x1C · 필드·전투 0x1E)
  ■ 훅: 명령 표 10 칸 → vwrap(이름이 자막 표에 있으면 cur = 번호·프레임 0, 없으면 cur = −1) → 원래 처리
        등록 리터럴 → vbo: sub(프레임 +1 · BGON == 1 일 때만 쪽 찾아 그림·DMA 표 끝 END 앞에 우리 스프라이트) → 원래 처리기
        마지막 쪽 끝을 지나면 cur = −1
  ■ 그림: VDP1 VRAM 0x78000(320×40 4비트, 색 참조표 뒤) — 스테이트 7장 모두 «빈 END 명령만» 있는 0x76000~0x7A000 구역(SP 적재 끝 최대 0x72780)
      스프라이트 PMOD 0x0088 · 지역 좌표(화면 가운데 원점) · 색 1 띠(검정) · 2 글자(흰) · 3 그림자. SPCTL 0x23(RGB 섞임)·PRISA S0 = 2 > NBG0 1
  ■ 자리: BLOCK 0x06090000(BSS 끝 0x0608CA08 와 힙 0x060B0000 사이 — 스테이트 7장 모두 0, 실행 파일 리터럴 참조 없음) → ABSOLUTE.BIN 을 0 으로 늘려 붙임
  ■ 자료: work/voice/voice.tsv(tools/voice_table.py) KO 있는 줄 — 쪽 = 두 줄(폭 ≤ 300 px), 끝 = 스크립트 대기(대기초) − 0.1초,
      여러 쪽이면 음성 길이 안에서 글자 수 비율(마지막 쪽은 대기 끝까지)
  python tools/voicesub.py   → 검산(흉내기로 전 쪽 그림을 파이썬 기준과 대조) + 미리보기 work/check/vsub_*.png"""
import csv, os, re, struct, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE); sys.path.insert(0, HERE)
from sh2asm import A

BIN_BASE = 0x06004000
BLOCK = 0x06090000; BLOCK_END = 0x060B0000
VAR = BLOCK + 0x10                                  # 0 cur · 4 frame · 8 shown
SPR = BLOCK + 0x40; ENDC = BLOCK + 0x60
CODE = BLOCK + 0x80
PCVAR = 0x06054964
CMD10_AT = 0x0603480C + 4 * 0x10; CMD10 = 0x06008A98
DMA_PTR = 0x06034508
VBO_ORIG = 0x0602D742; VBO_LIT = 0x0602D954
BGON_SH = 0x060FFCC0 + 0x20
W_, H_ = 320, 40; ROWB = W_ // 2; BMPSZ = ROWB * H_
TEXO = 0x78000; LUTO = TEXO + BMPSZ
TEX = 0x25C00000 + TEXO; LUT = 0x25C00000 + LUTO
GROWS = 14
FONT_B = 2 * GROWS
XA, YA = -160, 112 - H_ - 6
COLORS = (0x0000, 0x8000, 0xFFFF, 0x8000)          # 0 투명 · 1 띠 · 2 글자 · 3 그림자
GALMURI = r'C:\claude\utils\font\Galmuri-v2.40.3\Galmuri11.bdf'
NANUM = r'C:\claude\utils\font\nanum-gothic\NanumGothicBold.ttf'
MAXW = 300; FPS = 60
LY = (4, 21)
PUNCT_SP = re.compile(r'([,.!?:;)\]}\'"~、。，．！？：；）］｝」』】〉》”’…‥・·～〜♪♥]) (?! )')    # 문장부호 뒤 공백 1칸 지움(전 프로젝트 규칙)


class S(A):
    """A + 중간 리터럴 풀(ltorg) — 마리카 subhook.S"""
    def __init__(s, base): super().__init__(base); s.pools = []; s.cur = []
    def ld(s, rn, val): s.fix.append((len(s.c), 'lit', (rn, val, len(s.pools)))); s.c.append(0); s.cur.append(val)
    def ltorg(s):
        if (s.base + 2 * len(s.c)) % 4: s.c.append(0x0009)
        vals = list(dict.fromkeys(s.cur)); s.pools.append((len(s.c), vals)); s.c.extend([0, 0] * len(vals)); s.cur = []
    def build(s):
        if s.cur: s.ltorg()
        def val(v): return s.lab[v] if isinstance(v, str) else v
        for k, (at, vals) in enumerate(s.pools):
            for j, v in enumerate(vals):
                x = val(v) & 0xFFFFFFFF; s.c[at + 2 * j] = x >> 16; s.c[at + 2 * j + 1] = x & 0xFFFF
        for i, op, a in s.fix:
            pc = s.base + 2 * i
            if op == 'lit':
                rn, v, pk = a; at, vals = s.pools[pk]
                la = s.base + 2 * at + 4 * vals.index(v)
                d = la - ((pc & ~3) + 4); assert d >= 0 and d % 4 == 0 and d // 4 < 256, (hex(pc), d); s.c[i] = 0xD000 | (rn << 8) | d // 4
            else:
                d = (s.lab[a] - (pc + 4)) // 2
                if op in ('bra', 'bsr'): assert -2048 <= d < 2048; s.c[i] = (0xA000 if op == 'bra' else 0xB000) | (d & 0xFFF)
                else: assert -128 <= d < 128, (op, a, d); s.c[i] = {'bt': 0x8900, 'bf': 0x8B00, 'bts': 0x8D00, 'bfs': 0x8F00}[op] | (d & 0xFF)
        return b''.join(struct.pack('>H', x) for x in s.c)

    def mov(s, m, n): s.w(0x6003 | n << 8 | m << 4)
    def movi(s, i, n): s.w(0xE000 | n << 8 | (i & 0xFF))
    def addi(s, i, n): s.w(0x7000 | n << 8 | (i & 0xFF))
    def add(s, m, n): s.w(0x300C | n << 8 | m << 4)
    def sub(s, m, n): s.w(0x3008 | n << 8 | m << 4)
    def ldb(s, m, n): s.w(0x6000 | n << 8 | m << 4)          # mov.b @Rm,Rn
    def ldw(s, m, n): s.w(0x6001 | n << 8 | m << 4)          # mov.w @Rm,Rn
    def ldl(s, m, n): s.w(0x6002 | n << 8 | m << 4)
    def ldwp(s, m, n): s.w(0x6005 | n << 8 | m << 4)         # mov.w @Rm+,Rn
    def stb(s, m, n): s.w(0x2000 | n << 8 | m << 4)          # mov.b Rm,@Rn
    def stw(s, m, n): s.w(0x2001 | n << 8 | m << 4)
    def stl(s, m, n): s.w(0x2002 | n << 8 | m << 4)
    def ldld(s, d, m, n): assert d % 4 == 0 and d < 64; s.w(0x5000 | n << 8 | m << 4 | d // 4)     # mov.l @(d,Rm),Rn
    def stld(s, m, d, n): assert d % 4 == 0 and d < 64; s.w(0x1000 | n << 8 | m << 4 | d // 4)     # mov.l Rm,@(d,Rn)
    def ldwd(s, d, m): assert d % 2 == 0 and d < 32; s.w(0x8500 | m << 4 | d // 2)                # mov.w @(d,Rm),R0 (부호 확장)
    def extub(s, m, n): s.w(0x600C | n << 8 | m << 4)
    def extuw(s, m, n): s.w(0x600D | n << 8 | m << 4)
    def cmpeq(s, m, n): s.w(0x3000 | n << 8 | m << 4)        # T = Rn == Rm
    def cmphs(s, m, n): s.w(0x3002 | n << 8 | m << 4)        # T = Rn >= Rm (부호 없음)
    def cmphi(s, m, n): s.w(0x3006 | n << 8 | m << 4)        # T = Rn > Rm (부호 없음)
    def cmpgt(s, m, n): s.w(0x3007 | n << 8 | m << 4)        # T = Rn > Rm (부호)
    def cmpge(s, m, n): s.w(0x3003 | n << 8 | m << 4)        # T = Rn >= Rm (부호)
    def cmppz(s, n): s.w(0x4011 | n << 8)                    # T = Rn >= 0
    def tst(s, m, n): s.w(0x2008 | n << 8 | m << 4)
    def or_(s, m, n): s.w(0x200B | n << 8 | m << 4)
    def andi(s, i): s.w(0xC900 | i)
    def tsti(s, i): s.w(0xC800 | i)
    def cmpeqi(s, i): s.w(0x8800 | (i & 0xFF))
    def shll(s, n): s.w(0x4000 | n << 8)
    def shlr(s, n): s.w(0x4001 | n << 8)
    def shll2(s, n): s.w(0x4008 | n << 8)
    def shlr2(s, n): s.w(0x4009 | n << 8)
    def shll16(s, n): s.w(0x4028 | n << 8)
    def dt(s, n): s.w(0x4010 | n << 8)
    def push(s, n): s.w(0x2F06 | n << 4)
    def pop(s, n): s.w(0x60F6 | n << 8)
    def pushpr(s): s.w(0x4F22)
    def poppr(s): s.w(0x4F26)
    def jsr(s, m): s.w(0x400B | m << 8)
    def jmp(s, m): s.w(0x402B | m << 8)
    def rts(s): s.w(0x000B)
    def nop(s): s.w(0x0009)



def code(lay):
    a = S(CODE)
    # ── vwrap: PC 변수 → 이름 문자열, 자막 표(8 B 칸) 와 대조 — r4~r8 보존(원래 처리에 그대로)
    a.L('vwrap')
    for n in (4, 5, 6, 7, 8): a.push(n)
    a.ld(1, PCVAR); a.ldl(1, 1)
    a.ld(2, lay['NAMES']); a.ld(3, lay['NNAME']); a.movi(0, 4)
    a.L('nl'); a.tst(3, 3); a.br('bt', 'notf')
    a.mov(1, 5); a.mov(2, 6); a.movi(8, 7)
    a.L('cl'); a.ldb(5, 0); a.ldb(6, 8); a.cmpeq(8, 0); a.br('bf', 'mism')
    a.tst(0, 0); a.br('bt', 'hit')                                                         # 둘 다 NUL → 같음
    a.addi(1, 5); a.addi(1, 6); a.dt(7); a.br('bf', 'cl')
    a.L('hit'); a.ld(1, VAR); a.stld(4, 0, 1); a.movi(0, 0); a.stld(0, 4, 1); a.stld(0, 8, 1); a.br('bra', 'vout'); a.nop()
    a.L('mism'); a.addi(8, 2); a.addi(1, 4); a.addi(-1, 3); a.br('bra', 'nl'); a.nop()
    a.L('notf'); a.ld(1, VAR); a.movi(-1, 0); a.stld(0, 0, 1); a.movi(0, 0); a.stld(0, 8, 1)
    a.L('vout')
    for n in (8, 7, 6, 5, 4): a.pop(n)
    a.ld(0, CMD10); a.jmp(0); a.nop()
    # ── vbo: sub → 원래 처리기
    a.L('vbo'); a.pushpr(); a.br('bsr', 'sub'); a.nop(); a.ld(0, VBO_ORIG); a.jsr(0); a.nop(); a.poppr(); a.rts(); a.nop()
    a.ltorg()
    # ── sub
    a.L('sub'); a.ld(6, VAR)
    a.ldld(0, 6, 7); a.cmppz(7); a.br('bf', 'ret')
    a.ldld(4, 6, 3); a.addi(1, 3); a.stld(3, 4, 6)                                       # r3 = 프레임
    a.ld(1, lay['IDX']); a.mov(7, 0); a.shll2(0); a.add(1, 0); a.ldl(0, 1)
    a.tst(1, 1); a.br('bt', 'kill')
    a.ldwp(1, 5); a.extuw(5, 5)                                                           # r5 = 쪽 수, r1 = 첫 쪽
    a.L('pl'); a.tst(5, 5); a.br('bt', 'kill')
    a.ldwd(2, 1); a.cmpge(0, 3); a.br('bf', 'ret')                                       # 프레임 < 시작 → 쪽 사이(안 그림)
    a.ldwd(4, 1); a.cmpgt(3, 0); a.br('bt', 'found')                                     # 끝 > 프레임 → 이 쪽
    a.ldwd(0, 1); a.extuw(0, 0); a.add(0, 1); a.addi(-1, 5); a.br('bra', 'pl'); a.nop()
    a.L('found'); a.ld(2, BGON_SH); a.ldw(2, 0); a.extuw(0, 0); a.cmpeqi(1); a.br('bf', 'ret')   # 그림 화면(NBG0 만)일 때만
    a.ldld(8, 6, 0); a.cmpeq(1, 0); a.br('bt', 'patch')
    a.stld(1, 8, 6)
    a.pushpr(); a.mov(1, 4); a.br('bsr', 'render'); a.nop(); a.poppr()
    a.ld(1, lay['COMP']); a.ld(2, TEX); a.ld(5, BMPSZ // 4)
    a.L('cp'); a.ldl(1, 0); a.stl(0, 2); a.addi(4, 1); a.addi(4, 2); a.dt(5); a.br('bf', 'cp')
    a.ld(2, LUT)
    for c in COLORS:
        a.ld(0, c); a.stw(0, 2); a.addi(2, 2)
    # DMA 표 끝 항목 → 우리 스프라이트 + END 덧붙임
    a.L('patch'); a.ld(1, DMA_PTR); a.ldl(1, 1); a.ld(5, 4000)
    a.L('dl'); a.ldld(8, 1, 0); a.cmppz(0); a.br('bf', 'dend'); a.addi(12, 1); a.dt(5); a.br('bf', 'dl'); a.rts(); a.nop()
    a.L('dend'); a.ld(2, ENDC | 0x80000000); a.cmpeq(2, 0); a.br('bt', 'ret')
    a.ld(0, SPR); a.stld(0, 8, 1)
    a.ldld(0, 1, 0); a.stld(0, 12, 1)
    a.ldld(4, 1, 0); a.addi(32, 0); a.stld(0, 16, 1)
    a.stld(2, 20, 1)
    a.L('ret'); a.rts(); a.nop()
    a.L('kill'); a.movi(-1, 0); a.stld(0, 0, 6); a.movi(0, 0); a.stld(0, 8, 6); a.rts(); a.nop()
    a.ltorg()

    # ── render(r4 = 쪽) → COMP: r8~r14 보존
    a.L('render')
    for n in (8, 9, 10, 11, 12, 13, 14): a.push(n)
    a.pushpr()
    a.mov(4, 14)
    a.ld(1, lay['COMP']); a.ld(2, BMPSZ // 4); a.movi(0, 0)
    a.L('rc'); a.stl(0, 1); a.addi(4, 1); a.dt(2); a.br('bf', 'rc')
    # 띠: 행 by0..by1−1, 바이트 열 bx0..bx1−1 = 0x11
    a.ldwd(8, 14); a.extuw(0, 8); a.ldwd(10, 14); a.extuw(0, 9); a.ldwd(12, 14); a.extuw(0, 10); a.ldwd(14, 14); a.extuw(0, 11)
    a.mov(10, 1); a.shll2(1); a.shll2(1); a.shll(1); a.mov(1, 0); a.shll2(0); a.add(1, 0)   # by0×160
    a.ld(12, lay['COMP']); a.add(0, 12)
    a.mov(11, 13); a.sub(10, 13); a.ld(3, 0x11)
    a.L('brow'); a.mov(12, 1); a.add(8, 1); a.mov(9, 2); a.sub(8, 2)
    a.L('bcol'); a.stb(3, 1); a.addi(1, 1); a.dt(2); a.br('bf', 'bcol')
    a.ld(0, ROWB); a.add(0, 12); a.dt(13); a.br('bf', 'brow')
    # 줄들 — 스택 [줄 y, 남은 줄]
    a.ldwd(6, 14); a.extuw(0, 0); a.push(0)
    a.mov(14, 12); a.addi(16, 12)
    a.L('ln'); a.ldl(15, 0); a.tst(0, 0); a.br('bt', 'rdone'); a.addi(-1, 0); a.stl(0, 15)
    a.ldwp(12, 8); a.extuw(8, 8)                                                          # x0
    a.ldwp(12, 0); a.extuw(0, 0); a.push(0)                                               # 줄 y
    a.ldwp(12, 13); a.extuw(13, 13)                                                       # 글자 수
    a.tst(13, 13); a.br('bt', 'lend')
    a.L('gl'); a.ldw(12, 0); a.extuw(0, 0)
    a.mov(0, 1); a.shll2(1); a.shll2(0); a.shll2(0); a.shll(0); a.sub(1, 0)               # 번호×28
    a.ld(10, lay['FONT']); a.add(0, 10)
    a.ldl(15, 9); a.movi(GROWS, 11)
    a.L('grow'); a.ldwp(10, 14); a.extuw(14, 14); a.tst(14, 14); a.br('bt', 'gnext')
    a.shll16(14); a.mov(8, 4)
    a.L('gcol'); a.shll(14); a.br('bf', 'gskip')
    a.mov(4, 0); a.push(0); a.addi(1, 4); a.mov(9, 5); a.addi(1, 5); a.movi(3, 6); a.movi(1, 7); a.br('bsr', 'pix'); a.nop()
    a.pop(4); a.mov(9, 5); a.movi(2, 6); a.movi(0, 7); a.br('bsr', 'pix'); a.nop()
    a.L('gskip'); a.addi(1, 4); a.tst(14, 14); a.br('bf', 'gcol')
    a.L('gnext'); a.addi(1, 9); a.dt(11); a.br('bf', 'grow')
    a.ldw(12, 0); a.extuw(0, 0); a.ld(1, lay['ADV']); a.add(0, 1); a.ldb(1, 0); a.extub(0, 0); a.add(0, 8)
    a.addi(2, 12); a.dt(13); a.br('bf', 'gl')
    a.L('lend'); a.pop(0); a.br('bra', 'ln'); a.nop()
    a.L('rdone'); a.pop(0); a.poppr()
    for n in (14, 13, 12, 11, 10, 9, 8): a.pop(n)
    a.rts(); a.nop()
    a.ltorg()
    # ── pix(r4 = x, r5 = y, r6 = 색, r7 = 1 이면 띠(1) 위에만) — r0~r3 씀
    a.L('pix'); a.ld(0, W_); a.cmphs(0, 4); a.br('bt', 'pret'); a.movi(H_, 0); a.cmphs(0, 5); a.br('bt', 'pret')
    a.mov(5, 1); a.shll2(1); a.shll2(1); a.shll(1); a.mov(1, 0); a.shll2(0); a.add(1, 0)
    a.mov(4, 1); a.shlr(1); a.add(1, 0); a.ld(2, lay['COMP']); a.add(0, 2)
    a.ldb(2, 1); a.extub(1, 1); a.mov(4, 0); a.tsti(1); a.br('bf', 'podd')
    a.mov(1, 3); a.shlr2(3); a.shlr2(3)
    a.tst(7, 7); a.br('bt', 'pe1'); a.movi(1, 0); a.cmpeq(0, 3); a.br('bf', 'pret')
    a.L('pe1'); a.mov(1, 0); a.andi(0x0F); a.mov(6, 3); a.shll2(3); a.shll2(3); a.or_(3, 0); a.stb(0, 2); a.rts(); a.nop()
    a.L('podd'); a.mov(1, 0); a.andi(0x0F); a.mov(0, 3)
    a.tst(7, 7); a.br('bt', 'po1'); a.movi(1, 0); a.cmpeq(0, 3); a.br('bf', 'pret')
    a.L('po1'); a.mov(1, 0); a.andi(0xF0); a.or_(6, 0); a.stb(0, 2)
    a.L('pret'); a.rts(); a.nop()
    return a


def layout(nfont, pages_len, nname):
    tmp = {'IDX': 0x0A0B0C00, 'COMP': 0x0A0B0D00, 'FONT': 0x0A0B0E00, 'ADV': 0x0A0B0F00, 'NAMES': 0x0A0B1000, 'NNAME': nname}
    n0 = len(code(tmp).build())
    lay = {'NNAME': nname}; p = (CODE + n0 + 15) & ~15
    lay['IDX'] = p; p += 4 * nname
    lay['NAMES'] = p; p += 8 * nname
    lay['PAGES'] = p; p += (pages_len + 3) & ~3
    lay['COMP'] = p; p += BMPSZ
    lay['FONT'] = p; p += FONT_B * nfont
    lay['ADV'] = p; p += nfont
    lay['END'] = (p + 15) & ~15
    a = code(lay); c = a.build(); assert len(c) == n0
    return lay, a, c


def block(font_bits, advs, names, lists):
    """names: 음성 이름(번호 순), lists: {번호: 쪽 목록 바이트}"""
    body = b''; offs = {}
    for k in sorted(lists):
        offs[k] = len(body); body += lists[k] + (b'\0\0' if len(lists[k]) & 2 else b'')
    lay, a, c = layout(len(advs), len(body), len(names))
    blk = bytearray(lay['END'] - BLOCK)
    blk[0:4] = b'MMV1'
    struct.pack_into('>3I', blk, VAR - BLOCK, 0xFFFFFFFF, 0, 0)
    blk[SPR - BLOCK:SPR - BLOCK + 32] = struct.pack('>16H', 0x0000, 0, 0x0088, LUTO >> 3, TEXO >> 3, (W_ // 8) << 8 | H_, XA & 0xFFFF, YA & 0xFFFF, *[0] * 8)
    blk[ENDC - BLOCK:ENDC - BLOCK + 32] = struct.pack('>16H', 0x8000, *[0] * 15)
    blk[CODE - BLOCK:CODE - BLOCK + len(c)] = c
    for k, o in offs.items():
        struct.pack_into('>I', blk, lay['IDX'] - BLOCK + 4 * k, lay['PAGES'] + o)
    for k, nm in enumerate(names):
        e = nm.encode('latin1'); assert len(e) < 8; blk[lay['NAMES'] - BLOCK + 8 * k:lay['NAMES'] - BLOCK + 8 * k + len(e)] = e
    blk[lay['PAGES'] - BLOCK:lay['PAGES'] - BLOCK + len(body)] = body
    f = lay['FONT'] - BLOCK
    for i, g in enumerate(font_bits): blk[f + FONT_B * i:f + FONT_B * (i + 1)] = g
    blk[lay['ADV'] - BLOCK:lay['ADV'] - BLOCK + len(advs)] = bytes(advs)
    assert lay['END'] <= BLOCK_END, ('블록이 힙 0x060B0000 을 넘음', hex(lay['END']))
    return bytes(blk), a.lab, lay


def patch(a0, data=None):
    """ABSOLUTE.BIN(번역 빌드 결과) → 훅 넣은 바이트"""
    data = data or build_data()
    idx, bits, advs, names, lists, pages_all = data
    blk, lab, lay = block(bits, advs, names, lists)
    s = bytearray(a0)
    assert len(s) == 210436, 'ABSOLUTE.BIN 크기가 원본과 다름'
    assert struct.unpack_from('>I', s, CMD10_AT - BIN_BASE)[0] == CMD10; struct.pack_into('>I', s, CMD10_AT - BIN_BASE, lab['vwrap'])
    assert struct.unpack_from('>I', s, VBO_LIT - BIN_BASE)[0] == VBO_ORIG; struct.pack_into('>I', s, VBO_LIT - BIN_BASE, lab['vbo'])
    s += bytes(BLOCK - BIN_BASE - len(s)); s += blk
    return bytes(s), lab, lay


# ───────── 자료 ─────────
def build_font(chars):
    """갈무리11 비트맵(한글 잉크 윗선 = 0행) — 없는 글자만 나눔고딕 1비트 (에너미 제로 subdata 그대로)"""
    import bdf
    from PIL import Image, ImageDraw, ImageFont
    import numpy as np
    g = bdf.Font(GALMURI)
    ys = [y for c in '가각힣맑앙' for x, y in g.draw(c)[0]]
    top, bot = min(ys), max(ys); off = -top + max(0, (GROWS - (bot - top + 1)) // 2)
    order = sorted(chars); idx = {c: i for i, c in enumerate(order)}
    bits, advs, miss = [], [], []
    for c in order:
        rows = [0] * GROWS
        if ord(c) in g.g:
            pts, w = g.draw(c)
            for x, y in pts:
                yy = y + off
                if 0 <= yy < GROWS and 0 <= x < 16: rows[yy] |= 0x8000 >> x
            adv = 4 if c == ' ' else max(1, min(16, w))
        else:
            fb = ImageFont.truetype(NANUM, 56); im = Image.new('L', (64, 64), 0)
            ImageDraw.Draw(im).text((0, -fb.getbbox('가')[1]), c, font=fb, fill=255)
            cov = np.array(im.resize((16, 16), Image.BOX), float) / 255
            for y in range(GROWS):
                rows[y] = sum(0x8000 >> x for x in range(16) if cov[y, x] > 0.45)
            adv = max(1, min(16, int(round(ImageFont.truetype(NANUM, 14).getlength(c))))); miss.append(c)
        bits.append(b''.join(struct.pack('>H', r) for r in rows)); advs.append(adv)
    if miss: print('  갈무리11 에 없는 글자(나눔으로):', ''.join(miss))
    return idx, bits, advs


def wrap(t, W, maxw):
    out = []; cur = ''
    for w in t.split(' '):
        cand = (cur + ' ' + w) if cur else w
        if W(cand) <= maxw: cur = cand
        else:
            assert cur, ('낱말 하나가 폭 넘침', w); out.append(cur); cur = w
    if cur: out.append(cur)
    return out


def rows():
    out = []
    for r in csv.DictReader(open(os.path.join(ROOT, 'work', 'voice', 'voice.tsv'), encoding='utf-8'), delimiter='\t'):
        ko = r['KO'].strip()
        if not ko or ko.startswith('('): continue                                       # 번역 보류 줄은 뺌
        ko = PUNCT_SP.sub(r'\1', ko)
        assert not re.search(r'[぀-ヿ一-鿿]', ko), ('가나·한자 남음', r['음성'], ko)
        out.append((r['음성'], ko, float(r['길이']), float(r['대기초'])))
    return out


def build_data():
    rs = rows()
    chars = set(''.join(ko for _, ko, _, _ in rs)) | {' '}
    idx, bits, advs = build_font(chars)
    W = lambda s: sum(advs[idx[c]] for c in s)
    names = []; lists = {}; pages_all = {}
    for n, (nm, ko, ln, wait) in enumerate(rs):
        names.append(nm)
        ls = wrap(ko, W, MAXW)
        grp = [ls[k:k + 2] for k in range(0, len(ls), 2)]
        end = wait - 0.1; tot = sum(len(''.join(g)) for g in grp); t = 0.0; pages = []
        for k, g in enumerate(grp):
            b = end if k == len(grp) - 1 else t + ln * len(''.join(g)) / tot
            pages.append((int(t * FPS), max(int(b * FPS), int(t * FPS) + 1), g)); t = b
        body = struct.pack('>H', len(pages)); pp = []
        for f0, f1, g in pages:
            ys = LY if len(g) == 2 else LY[1:]
            lines = []
            for l, y in zip(g, ys):
                w = W(l); lines.append(((W_ - w) // 2, y, [idx[c] for c in l], w))
            x0 = min(l[0] for l in lines); x1 = max(l[0] + l[3] for l in lines)
            bx0 = max(0, x0 - 6) >> 1; bx1 = (min(W_, x1 + 6) + 1) >> 1
            by0 = ys[0] - 3; by1 = min(H_ - 1, ys[-1] + GROWS + 3)
            pb = struct.pack('>7H', f0, f1, len(lines), bx0, bx1, by0, by1)
            for x, y, gl, w in lines:
                pb += struct.pack('>3H', x, y, len(gl)) + b''.join(struct.pack('>H', k) for k in gl)
            pb = struct.pack('>H', 2 + len(pb)) + pb
            body += pb; pp.append((f0, f1, bx0, bx1, by0, by1, [(x, y, gl) for x, y, gl, w in lines]))
        lists[n] = body; pages_all[n] = pp
    return idx, bits, advs, names, lists, pages_all


def ref_render(page, font_bits, advs):
    """render 와 같은 셈(검산용) — page = (시작, 끝, bx0, bx1, by0, by1, [(x0, y, [글자])]) → BMPSZ B"""
    f0, f1, bx0, bx1, by0, by1, lines = page
    px = [[0] * W_ for _ in range(H_)]
    for y in range(by0, by1):
        for b in range(bx0, bx1): px[y][2 * b] = px[y][2 * b + 1] = 1
    for x, ly, gl in lines:
        for g in gl:
            bits = font_bits[g]
            for r in range(GROWS):
                v = bits[2 * r] << 8 | bits[2 * r + 1]
                for c in range(16):
                    if v & (0x8000 >> c):
                        xx, yy = x + c, ly + r
                        if xx + 1 < W_ and yy + 1 < H_ and px[yy + 1][xx + 1] == 1: px[yy + 1][xx + 1] = 3
                        if xx < W_ and yy < H_: px[yy][xx] = 2
            x += advs[g]
    return bytes(px[y][x] << 4 | px[y][x + 1] for y in range(H_) for x in range(0, W_, 2))
