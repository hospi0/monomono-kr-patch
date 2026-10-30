# -*- coding: utf-8 -*-
r"""음성 SAP(2026-10-30) — 머리 0x800 B: u32 BE 샘플 수 · u32 채널 1 · u32 비트 16 · 80비트 실수 표본율(0x400D AC44.. = 44100), 자료 = 16비트 BE PCM
  python tools/sap.py <이름 …>  → work/voice/wav/<이름>.wav (16 kHz 모노, 받아쓰기용)"""
import os, struct, sys, wave
import numpy as np
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load(name):
    b = open(os.path.join(ROOT, 'work', 'disc', 'MONOMONO', name + '.SAP'), 'rb').read()
    n = struct.unpack_from('>I', b, 0)[0]
    return np.frombuffer(b[0x800:0x800 + n * 2], '>i2').astype(np.float32) / 32768, 44100


def to16k(a, sr):
    t = np.arange(0, len(a) * 16000 // sr) * sr / 16000
    return np.interp(t, np.arange(len(a)), a).astype(np.float32)


if __name__ == '__main__':
    os.makedirs(os.path.join(ROOT, 'work', 'voice', 'wav'), exist_ok=True)
    for nm in sys.argv[1:]:
        a, sr = load(nm); s = (to16k(a, sr) * 32767).astype('<i2')
        w = wave.open(os.path.join(ROOT, 'work', 'voice', 'wav', nm + '.wav'), 'wb'); w.setnchannels(1); w.setsampwidth(2); w.setframerate(16000); w.writeframes(s.tobytes()); w.close()
