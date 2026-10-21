# -*- coding: utf-8 -*-
"""从 mapping.json 生成 HTML 预览页：默认只显示需要关注的项（中低置信和跳过），高置信折叠后可展开；
支持按来源、置信、操作筛选和搜索。置信统计只计导入项，跳过项的置信显示「—」，不参与统计。

用法：
  python build_preview.py --mapping <mapping.json> --out preview.html [--title "2026-01 账单导入预览"]
生成后请按 harness 惯例交付给用户（如自动在浏览器打开）。
"""
import argparse
import json
import sys
from collections import Counter

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass


def esc(x):
    return str(x).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def main():
    ap = argparse.ArgumentParser(description="生成导入预览 HTML")
    ap.add_argument("--mapping", required=True)
    ap.add_argument("--out", required=True, help="输出 html 路径")
    ap.add_argument("--title", default="账单导入预览")
    args = ap.parse_args()

    with open(args.mapping, encoding="utf-8") as f:
        items = json.load(f)

    imp = sum(1 for it in items if it.get("操作") == "导入")
    skip = len(items) - imp
    ch = Counter(it.get("置信", "") for it in items if it.get("操作") == "导入")
    for k in ("高", "中", "低"):
        ch.setdefault(k, 0)
    need = sum(1 for it in items if it.get("操作") == "导入" and it.get("置信") in ("中", "低"))

    rows_html = []
    for it in items:
        op = it.get("操作", "")
        conf = it.get("置信", "")
        confcls = {"高": "c-high", "中": "c-mid", "低": "c-low"}.get(conf, "c-mid")
        opcls = "row-skip" if op == "跳过" else ""
        need_flag = "1" if (op == "跳过" or conf in ("中", "低")) else "0"
        confcell = "—" if op == "跳过" else f'<span class="badge {confcls}">{esc(conf)}</span>'
        mapping = f"{esc(it.get('type',''))}: {esc(it.get('源',''))} → {esc(it.get('目标',''))}"
        if it.get("细分"):
            mapping += f" / {esc(it['细分'])}"
        # autocorrect-disable
        if it.get("用户tag"):
            mapping += f" / #{esc(it['用户tag'])}"
        # autocorrect-enable
        note = it.get("备注") or it.get("理由") or ""
        kw = esc(str(it.get("对方", "")) + " " + str(it.get("商品", ""))).lower()
        rows_html.append(
            f'<tr class="{opcls}" data-conf="{esc(conf)}" data-src="{esc(it.get("来源",""))}" '
            f'data-op="{esc(op)}" data-need="{need_flag}" data-kw="{kw}">'
            f'<td>{esc(it.get("序号",""))}</td><td>{esc(it.get("来源",""))}</td><td>{esc(it.get("日期",""))}</td>'
            f'<td class="l">{esc(it.get("对方",""))}<div class="goods">{esc(it.get("商品",""))}</div></td>'
            f'<td class="amt">{esc(it.get("金额",""))}</td><td>{esc(it.get("收支",""))}</td>'
            f'<td class="l">{mapping}</td><td>{confcell}</td><td>{esc(op)}</td>'
            f'<td class="l note">{esc(note)}</td></tr>')

    html = f"""<!doctype html><html lang="zh"><head><meta charset="utf-8">
<title>{esc(args.title)}</title>
<style>
body{{font-family:-apple-system,"Microsoft YaHei",sans-serif;margin:0;background:#f5f6f8;color:#222}}
.wrap{{max-width:1200px;margin:0 auto;padding:20px}}
h1{{font-size:20px;margin:0 0 4px}}
.sub{{color:#666;margin-bottom:16px;font-size:13px}}
.cards{{display:flex;gap:10px;flex-wrap:wrap;margin-bottom:14px}}
.card{{background:#fff;border-radius:10px;padding:12px 16px;box-shadow:0 1px 3px rgba(0,0,0,.08);min-width:100px}}
.card .n{{font-size:24px;font-weight:700}}
.card .t{{font-size:12px;color:#888}}
.card.imp .n{{color:#1a8a3c}}.card.skip .n{{color:#999}}.card.hi .n{{color:#1a8a3c}}.card.mid .n{{color:#d68a00}}.card.low .n{{color:#d64545}}
.bar{{background:#fff;border-radius:10px;padding:10px 12px;box-shadow:0 1px 3px rgba(0,0,0,.08);margin-bottom:12px;display:flex;gap:6px;flex-wrap:wrap;align-items:center}}
.bar button{{border:1px solid #ddd;background:#fff;padding:6px 12px;border-radius:6px;cursor:pointer;font-size:13px}}
.bar button.on{{background:#2563eb;color:#fff;border-color:#2563eb}}
.bar input{{border:1px solid #ddd;border-radius:6px;padding:6px 10px;font-size:13px;flex:1;min-width:140px}}
table{{width:100%;border-collapse:collapse;background:#fff;border-radius:10px;overflow:hidden;box-shadow:0 1px 3px rgba(0,0,0,.08);font-size:13px}}
th,td{{padding:7px 9px;border-bottom:1px solid #eee;text-align:left;vertical-align:top}}
th{{background:#fafbfc;font-weight:600;color:#555;position:sticky;top:0}}
td.l{{max-width:280px}}.goods{{color:#999;font-size:12px}}.note{{color:#d64545;font-size:12px}}.amt{{white-space:nowrap;font-variant-numeric:tabular-nums}}
tr.row-skip{{background:#f3f3f3;color:#999}}
tr.row-skip td{{text-decoration:line-through}}
.badge{{display:inline-block;padding:2px 8px;border-radius:10px;font-size:11px;font-weight:600}}
.c-high{{background:#e7f6ec;color:#1a8a3c}}.c-mid{{background:#fff4e0;color:#d68a00}}.c-low{{background:#fde8e8;color:#d64545}}
.legend{{font-size:12px;color:#888;margin:8px 0}}
.hidden{{display:none}}
</style></head><body><div class="wrap">
<h1>{esc(args.title)}</h1>
<div class="sub">共 {len(items)} 笔 · 将导入 {imp} / 跳过 {skip} · 审查确认后才写入 Firefly III</div>
<div class="cards">
<div class="card imp"><div class="n">{imp}</div><div class="t">将导入</div></div>
<div class="card skip"><div class="n">{skip}</div><div class="t">跳过</div></div>
<div class="card hi"><div class="n">{ch['高']}</div><div class="t">高置信（导入项）</div></div>
<div class="card mid"><div class="n">{ch['中']}</div><div class="t">中置信</div></div>
<div class="card low"><div class="n">{ch['低']}</div><div class="t">低置信</div></div>
</div>
<div class="legend">🟢高=明确 🟠中=较明确，请扫一眼 🔴低=需用户定 · 置信仅统计导入项，跳过项显示「—」 · 默认只显示「需关注」（中/低 + 跳过）</div>
<div class="bar">
<button class="on" onclick="filt('need',this)">⚠️ 需关注（{need + skip}）</button>
<button onclick="filt('all',this)">显示全部 {len(items)}</button>
<button onclick="filt('low',this)">🔴 低</button>
<button onclick="filt('mid',this)">🟠 中</button>
<button onclick="filt('skip',this)">跳过（{skip}）</button>
<button onclick="filt('zfb',this)">支付宝</button>
<button onclick="filt('wx',this)">微信</button>
<input id="q" placeholder="搜索 对方/商品…" oninput="apply()">
</div>
<table><thead><tr>
<th>#</th><th>来源</th><th>日期</th><th>对方 / 商品</th><th>金额</th><th>收支</th><th>映射（type 源→目标/细分）</th><th>置信</th><th>操作</th><th>备注/理由</th>
</tr></thead><tbody id="tb">
{''.join(rows_html)}
</tbody></table>
<div class="sub" style="margin-top:14px">如要改某笔，告诉 agent「#序号 → 改成…」。</div>
</div>
<script>
let mode='need';
function filt(m,el){{mode=m;document.querySelectorAll('.bar button').forEach(b=>b.classList.remove('on'));el.classList.add('on');apply();}}
function apply(){{
  const q=document.getElementById('q').value.toLowerCase();
  document.querySelectorAll('#tb tr').forEach(tr=>{{
    const conf=tr.dataset.conf,src=tr.dataset.src,op=tr.dataset.op,need=tr.dataset.need,kw=tr.dataset.kw;
    let show=true;
    if(q){{show=kw.includes(q);}}
    if(show){{
      if(mode==='need')show=(need==='1');
      else if(mode==='low')show=(conf==='低');
      else if(mode==='mid')show=(conf==='中');
      else if(mode==='skip')show=(op==='跳过');
      else if(mode==='zfb')show=(src==='支付宝');
      else if(mode==='wx')show=(src==='微信');
      else show=true;
    }}
    tr.classList.toggle('hidden',!show);
  }});
}}
apply();
</script>
</body></html>"""

    with open(args.out, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"已生成预览： {args.out}")
    print(f"导入{imp}（置信 高{ch['高']} 中{ch['中']} 低{ch['低']}） | 跳过{skip} | 需关注（中低 + 跳过）： {need + skip}")
    low_list = [it.get("序号") for it in items if it.get("操作") == "导入" and it.get("置信") in ("中", "低")]
    if low_list:
        print("待用户确认（中低置信且导入）：", low_list)


if __name__ == "__main__":
    main()
