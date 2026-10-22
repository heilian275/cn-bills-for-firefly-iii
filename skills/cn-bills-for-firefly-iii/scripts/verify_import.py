# -*- coding: utf-8 -*-
"""验证：按批次标签（journal 级 tags）核对导入结果：笔数、type 分布、金额合计、external_id 覆盖。
tags 在 journal 级，group 级为空。只读。

用法：
  python verify_import.py --batch "2026-01 账单导入" --start 2026-01-01 --end 2026-01-31 --url ... --token-file ...
"""
import argparse
import json
from collections import defaultdict

import _common


def main():
    ap = argparse.ArgumentParser(description="按批次标签验证导入结果")
    ap.add_argument("--batch", required=True, help="批次标签，如 2026-01 账单导入")
    ap.add_argument("--start", required=True, help="账单起始日 YYYY-MM-DD")
    ap.add_argument("--end", required=True, help="账单结束日 YYYY-MM-DD")
    ap.add_argument("--mapping", help="可选：对照 mapping.json 核对待导入数")
    ap.add_argument("--url", default="http://localhost:8080")
    ap.add_argument("--token-file", help="含 FIREFLY_III_ACCESS_TOKEN=... 的文件路径")
    args = ap.parse_args()

    token = _common.load_token(args.token_file)
    assert token, "未找到 token：请用 --token-file 或设置环境变量 FIREFLY_III_ACCESS_TOKEN"
    ff = _common.Firefly(args.url, token)

    matches = []
    for rows in ff.paged("/api/v1/transactions", {"start": args.start, "end": args.end}):
        for g in rows:
            for j in g["attributes"].get("transactions", []):
                if args.batch in (j.get("tags") or []):
                    matches.append(j)

    print(f"=== Firefly III 中带 '{args.batch}' 标签的交易： {len(matches)} 笔 ===")
    type_c = defaultdict(int)
    exp_by = defaultdict(float)
    inc_by = defaultdict(float)
    trans_total = 0.0
    for j in matches:
        type_c[j["type"]] += 1
        am = float(j["amount"])
        if j["type"] == "withdrawal":
            exp_by[j.get("destination_name") or "?"] += am
        elif j["type"] == "deposit":
            inc_by[j.get("source_name") or "?"] += am
        else:
            trans_total += am
    print("type 分布：", dict(type_c))
    print("\n【支出】各目标账户：")
    for k in sorted(exp_by, key=lambda x: -exp_by[x]):
        print(f"  {k}: ¥{exp_by[k]:.2f}")
    print(f"  支出合计： ¥{sum(exp_by.values()):.2f}")
    print("\n【收入】各来源：", {k: round(v, 2) for k, v in inc_by.items()},
          " 合计 ¥%.2f" % sum(inc_by.values()))
    print(f"【转账】合计： ¥{trans_total:.2f}")
    n_ext = sum(1 for j in matches if j.get("external_id"))
    print(f"\n带 external_id: {n_ext}/{len(matches)}")

    if args.mapping:
        with open(args.mapping, encoding="utf-8") as f:
            items = json.load(f)
        expect = sum(1 for it in items if it.get("操作") == "导入")
        status = "✅ 一致" if len(matches) == expect else "⚠️ 不一致"
        print(f"对照 mapping 待导入 {expect} 笔 vs 实际 {len(matches)} 笔 {status}")


if __name__ == "__main__":
    main()
