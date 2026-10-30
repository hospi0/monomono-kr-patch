# -*- coding: utf-8 -*-
r"""오프닝·엔딩 음성 받아적기 페이지(2026-10-30) — 기계 받아쓰기(위스퍼·kotoba)가 짧은 대사를 못 잡아 하스피가 들으며 적게
  음성 86개를 wav(16 kHz)로 페이지에 넣고, 줄마다 기계 추정·지금 번역·입력 칸 → «결과 복사» = «음성\t들은 말» 줄들
  빨간 줄 = 번역 없음·⚠·보류.  python tools/voice_listen.py → work/check/voice_listen.html"""
import base64, csv, html, os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE); sys.path.insert(0, HERE)
import voice_table as VT

CSS = """:root{--bg:#f6f5f2;--fg:#1d1d1b;--mut:#6b6a66;--card:#fff;--line:#dedbd4;--acc:#b4441c}
@media (prefers-color-scheme:dark){:root{--bg:#1b1a19;--fg:#ece9e3;--mut:#a29e96;--card:#262523;--line:#3a3835;--acc:#e0774f}}
body{margin:0;background:var(--bg);color:var(--fg);font:15px/1.5 system-ui,"Malgun Gothic",sans-serif}
main{max-width:980px;margin:0 auto;padding:16px}h1{font-size:20px;margin:8px 0}p.note{color:var(--mut);margin:4px 0 16px}
.bar{position:sticky;top:0;background:var(--bg);padding:8px 0;border-bottom:1px solid var(--line);display:flex;gap:12px;align-items:center;flex-wrap:wrap;z-index:2}
button{font:inherit;padding:6px 12px;border:1px solid var(--acc);background:var(--acc);color:#fff;border-radius:6px;cursor:pointer}
.row{background:var(--card);border:1px solid var(--line);border-radius:8px;padding:10px 12px;margin:10px 0}
.row.done{opacity:.55}.row.need{border-left:4px solid var(--acc)}
.hd{display:flex;gap:10px;align-items:center;flex-wrap:wrap}.id{font-weight:600;font-family:ui-monospace,Consolas,monospace}
.meta{color:var(--mut);font-size:13px}audio{height:32px;max-width:100%}
.g{display:grid;grid-template-columns:72px 1fr;gap:4px 8px;margin-top:6px;font-size:14px}.g>span{color:var(--mut)}
input.t{font:inherit;width:100%;box-sizing:border-box;padding:5px 8px;border:1px solid var(--line);border-radius:5px;background:var(--bg);color:var(--fg)}
label{font-size:13px;color:var(--mut)}textarea{width:100%;height:140px;box-sizing:border-box;font:12px ui-monospace,Consolas,monospace;background:var(--card);color:var(--fg);border:1px solid var(--line);margin-top:12px}"""

JS = r"""function filt(){const o=document.getElementById('onlyneed').checked;document.querySelectorAll('.row').forEach(r=>{r.style.display=(o&&r.dataset.need==='0')?'none':''})}
function copyOut(){const L=[];document.querySelectorAll('.row').forEach(r=>{const t=r.querySelector('input.t').value.trim(),s=r.querySelector('input.s').checked;if(t||s)L.push(r.dataset.id+'\t'+(s?'(소리만)':t))});
const txt=L.join('\n');document.getElementById('out').value=txt;
navigator.clipboard.writeText(txt).then(()=>{document.getElementById('msg').textContent=L.length+'줄 복사됨'},()=>{document.getElementById('msg').textContent='아래 칸에서 복사해 주세요'})}
document.addEventListener('input',e=>{const r=e.target.closest('.row');if(r){const t=r.querySelector('input.t').value.trim(),s=r.querySelector('input.s').checked;r.classList.toggle('done',!!(t||s))}});"""


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    kt = {r['음성']: r for r in csv.DictReader(open(os.path.join(ROOT, 'work', 'voice', 'voice_ko.tsv'), encoding='utf-8'), delimiter='\t')}
    ap = os.path.join(ROOT, 'work', 'voice', 'asr_kotoba.tsv')
    asr = {r['음성']: r for r in csv.DictReader(open(ap, encoding='utf-8'), delimiter='\t')} if os.path.exists(ap) else {}
    body = []; need_n = 0
    for fn in ('OPENING.MSG', 'ENDING.MSG'):
        for nm, pic, wait, off in VT.voices(fn):
            k = kt.get(nm, {}); note = k.get('비고') or ''; ko = k.get('KO') or ''
            need = nm not in kt or '⚠' in note or ko.startswith('('); need_n += need
            b64 = base64.b64encode(open(os.path.join(ROOT, 'work', 'voice', 'wav', nm + '.wav'), 'rb').read()).decode()
            guess = (asr.get(nm, {}).get('단독') or '—')
            body.append('<div class="row %s" data-id="%s" data-need="%d"><div class="hd"><span class="id">%s</span>'
                        '<span class="meta">%s · 그림 %s · 대기 %.1f초</span><audio controls preload="none" src="data:audio/wav;base64,%s"></audio></div>'
                        '<div class="g"><span>기계 추정</span><div class="meta">%s</div><span>지금 번역</span><div>%s %s</div>'
                        '<span>들은 말</span><input class="t" placeholder="일본어 또는 한국어 뜻">'
                        '<span></span><label><input class="s" type="checkbox"> 소리만(자막 안 넣음)</label></div></div>'
                        % ('need' if need else '', nm, need, nm, fn[:-4], pic, wait or 0, b64, html.escape(guess), html.escape(ko or '—'),
                           '<span class="meta">' + html.escape(note) + '</span>' if note else ''))
    page = ('<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
            '<title>모노모노 음성 받아적기</title><style>' + CSS + '</style></head><body><main><h1>모노모노 오프닝·엔딩 음성 받아적기</h1>'
            '<p class="note">빨간 줄 = 들어 보고 적어 주실 것(%d개). 들리는 일본어를 적거나 뜻만 한국어로 적어도 됩니다. '
            '기합·비명 같은 소리면 «소리만»에 체크. 이미 번역이 있는 줄도 틀렸으면 적어 주세요. 다 하면 «결과 복사» → 대화창에 붙여 주세요.</p>'
            '<div class="bar"><button onclick="copyOut()">결과 복사</button><label><input type="checkbox" id="onlyneed" onchange="filt()"> 적을 것만 보기</label>'
            '<span id="msg" class="meta"></span></div>' % need_n + ''.join(body) +
            '<textarea id="out" placeholder="결과 복사를 누르면 여기에도 나옵니다"></textarea></main><script>' + JS + '</script></body></html>')
    p = os.path.join(ROOT, 'work', 'check', 'voice_listen.html'); os.makedirs(os.path.dirname(p), exist_ok=True)
    open(p, 'w', encoding='utf-8').write(page)
    print('적을 줄 %d / 86 → %s (%d KB)' % (need_n, p, os.path.getsize(p) // 1024))


if __name__ == '__main__':
    main()
