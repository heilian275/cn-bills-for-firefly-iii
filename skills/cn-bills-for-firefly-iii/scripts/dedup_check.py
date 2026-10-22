# -*- coding: utf-8 -*-
"""按 external_id 查重：拉取 Firefly III 已有的 external_id，检查 mapping 里准备导入的交易是否已存在。
有重复就退出，不进入导入。只读。token 不打印。

用法：
  python dedup_check.py --mapping <mapping.json> --url http://localhost:8080 --token-file <file>
"""
import argparse
import json
import sys

import _common


def main():
    ap = argparse.ArgumentParser(description="external_id 查重（导入前置硬门）")
    ap.add_argument("--mapping", required=True, help="mapping.json 路径")
    ap.add_argument("--url", default="http://localhost:8080")
    ap.add_argument("--token-file", help="含 FIREFLY_III_ACCESS_TOKEN=... 的文件路径")
    args = ap.parse_args()

    token = _common.load_token(args.token_file)
    assert token, "未找到 token：请用 --token-file 或设置环境变量 FIREFLY_III_ACCESS_TOKEN"
    ff = _common.Firefly(args.url, token)

    existing = set()
    for rows in ff.paged("/api/v1/transactions"):
        for g in rows:
            for j in g.get("attributes", {}).get("transactions", []):
                eid = (j.get("external_id") or "").strip()
                if eid:
                    existing.add(eid)
    print(f"Firefly III 现存带 external_id 的交易： {len(existing)} 条")

    with open(args.mapping, encoding="utf-8") as f:
        items = json.load(f)
    to_import = [it for it in items if it.get("操作") == "导入"]

    dup = []
    for it in to_import:
        eid = (it.get("ext") or "").strip()
        if eid and eid in existing:
            dup.append((it.get("序号"), eid))
    print(f"mapping 待导入 {len(to_import)} 笔中，已存在（重复）： {len(dup)} 笔")
    for sn, e in dup:
        print(f"  #{sn} {e}")
    if not dup:
        print("  ✅ 无重复，可安全导入")
    else:
        print("  ⚠️ 有重复：请先排除重复项再导入（或确认库内旧交易应删除）")
        sys.exit(1)  # 硬门：有重复即失败退出，供链式调用与机器判定


if __name__ == "__main__":
    main()
