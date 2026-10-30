# -*- coding: utf-8 -*-
r"""새턴 Track 1(MODE1/2352) ISO9660 나열·추출(읽기 전용, 2026-10-30)
  python tools/iso.py           → work/filelist.txt
  python tools/iso.py --extract → work/disc/ (전부)"""
import os, sys, struct
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BIN = r'C:\claude\roms\ss\Bouken Katsugeki Monomono (Japan)\Bouken Katsugeki Monomono (Japan) (Track 1).bin'
f = open(BIN, 'rb')


def read(lba, size):
    out = bytearray(); n = (size + 2047) // 2048
    for k in range(n):
        f.seek((lba + k) * 2352 + 16); out += f.read(2048)
    return bytes(out[:size])


def walk():
    pvd = read(16, 2048)
    assert pvd[1:6] == b'CD001'
    out = []

    def rec(lba, size, path):
        data = read(lba, size); i = 0
        while i < len(data):
            ln = data[i]
            if ln == 0: i = (i // 2048 + 1) * 2048; continue
            r = data[i:i + ln]; i += ln
            ext, dl, fl, nl = struct.unpack_from('<I', r, 2)[0], struct.unpack_from('<I', r, 10)[0], r[25], r[32]
            nm = r[33:33 + nl]
            if nl == 1 and nm in (b'\x00', b'\x01'): continue
            full = path + '/' + nm.decode('ascii', 'replace').split(';')[0]
            out.append((full, ext, dl, fl))
            if fl & 2: rec(ext, dl, full)
    rec(struct.unpack_from('<I', pvd, 158)[0], struct.unpack_from('<I', pvd, 166)[0], '')
    return out


def main():
    ents = walk()
    with open(os.path.join(ROOT, 'work', 'filelist.txt'), 'w', encoding='utf-8') as o:
        for full, lba, size, fl in ents:
            o.write('%-40s lba=%7d size=%10d%s\n' % (full, lba, size, ' DIR' if fl & 2 else ''))
    if '--extract' in sys.argv:
        for full, lba, size, fl in ents:
            if fl & 2: continue
            p = os.path.join(ROOT, 'work', 'disc', full.lstrip('/'))
            os.makedirs(os.path.dirname(p), exist_ok=True)
            open(p, 'wb').write(read(lba, size))
    print(len(ents), 'entries')


if __name__ == '__main__':
    main()
