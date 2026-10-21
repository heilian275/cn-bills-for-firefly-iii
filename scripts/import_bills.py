# -*- coding: utf-8 -*-
"""导入：读取 mapping.json，逐笔 POST 到 Firefly III；dry-run 子命令只打印请求体，不写入。

几个实现上的防护：
- 账户名可能重名，按 asset/expense/revenue 分三个字典查 id（withdrawal 目标=expense，deposit 源=revenue，transfer 两端=asset）
- amount 为两位小数字符串；账户 id 字符串
- 每笔独立 POST；error_if_duplicate_hash 作为最后一道防线
- tags 写 journal 级

用法：
  python import_bills.py dry-run --mapping <mapping.json> --batch "2026-01 账单导入" --url ... --token-file ...
  python import_bills.py import  --mapping <mapping.json> --batch "2026-01 账单导入" ...
"""
import argparse
import json
import sys
import time
import urllib.error

import _common

SRC_TYP = {"withdrawal": "asset", "deposit": "revenue", "transfer": "asset"}
DST_TYP = {"withdrawal": "expense", "deposit": "asset", "transfer": "asset"}


def main():
    ap = argparse.ArgumentParser(description="导入已获预览批准的交易（dry-run 只打印请求体，不写入）")
    ap.add_argument("mode", choices=["dry-run", "import"])
    ap.add_argument("--mapping", required=True)
    ap.add_argument("--batch", required=True, help="批次标签，如 2026-01 账单导入")
    ap.add_argument("--url", default="http://localhost:8080")
    ap.add_argument("--token-file", help="含 FIREFLY_III_ACCESS_TOKEN=... 的文件路径")
    args = ap.parse_args()

    token = _common.load_token(args.token_file)
    assert token, "未找到 token：请用 --token-file 或设置环境变量 FIREFLY_III_ACCESS_TOKEN"
    ff = _common.Firefly(args.url, token)

    # 账户名→id，按类型分三字典（重名坑防护）
    ids = {"asset": {}, "expense": {}, "revenue": {}}
    for t in ids:
        try:
            for rows in ff.paged("/api/v1/accounts", {"type": t}):
                for a in rows:
                    ids[t][a["attributes"]["name"]] = a["id"]
        except urllib.error.HTTPError as e:
            if e.code != 404:
                raise
            # 类型过滤端点对空类型返回 404 而非空列表（6.2.x 实测行为；gather_reference 同处理）。
            # 没有收入账户这类结构不该阻断导入，按空清单继续。
            continue

    with open(args.mapping, encoding="utf-8") as f:
        items = json.load(f)
    to_import = [it for it in items if it.get("操作") == "导入"]
    print(f"模式： {args.mode} | 批次标签： {args.batch} | 待导入 {len(to_import)} 笔")

    def build_req(it):
        tags = [it["来源"]]
        if it.get("账单分类") and it["账单分类"] not in ("/", "", None):
            tags.append(it["账单分类"])
        # autocorrect-disable
        if it.get("用户tag"):
            tags.append(it["用户tag"])  # tag 型细分体系，与 category 型（「细分」）二选一
        # autocorrect-enable
        tags.append(args.batch)
        tx = {"type": it["type"],
              "date": it["日期"] + "T" + (it.get("时间") or "00:00") + ":00",
              "amount": "%.2f" % float(it["金额"]),
              "description": it.get("描述") or it.get("商品") or it.get("对方") or "",
              "tags": tags, "external_id": (it.get("ext") or "").strip()}
        if it.get("细分"):
            tx["category_name"] = it["细分"]
        note = it.get("备注") or it.get("理由")
        if note:
            tx["notes"] = note
        if it.get("币种"):
            tx["currency_code"] = it["币种"]  # 留空则省略靠账户币种继承；账户币种不一致时服务端会静默忽略（6.2.x 实测行为）
        tx["source_id"] = ids[SRC_TYP[it["type"]]][it["源"]]
        tx["destination_id"] = ids[DST_TYP[it["type"]]][it["目标"]]
        return {"error_if_duplicate_hash": True, "transactions": [tx]}

    # 账户名可解析性校验（按各自类型字典；非法 type、空「源/目标」与脏金额在此拦下，避免导入中途裸崩）
    missing = set()
    for it in to_import:
        t = it.get("type")
        if t not in SRC_TYP:
            missing.add(f"#{it.get('序号')}:type 非法 ({t!r}，应为 withdrawal/deposit/transfer)")
            continue
        for k, typ in (("源", SRC_TYP[t]), ("目标", DST_TYP[t])):
            v = it.get(k)
            if not v or not str(v).strip():
                missing.add(f"#{it.get('序号')}:{k}为空")
            elif v not in ids[typ]:
                missing.add(f"{typ}:{v}")
        try:
            float(it["金额"])
        except (TypeError, ValueError, KeyError):
            missing.add(f"#{it.get('序号')}:金额非数字 ({it.get('金额')!r})")
    if missing:
        print("!! 导入前校验未通过（type / 账户名 / 金额），先处理：", missing)
        sys.exit(2)

    if args.mode == "dry-run":
        print("\n--- 抽样请求体（前 3 笔）---")
        for it in to_import[:3]:
            try:
                print(json.dumps(build_req(it), ensure_ascii=False, indent=2))
            except Exception as e:
                print(f"  !! #{it.get('序号')} 构建请求体失败：{e}")
        print("\n（dry-run 完成，未写入。确认请求体无误并获用户正式批准后，再用 import）")
        return

    ok, fail = 0, []
    for i, it in enumerate(to_import, 1):
        try:
            d = ff.post("/api/v1/transactions", build_req(it))
            ok += 1
            if i % 10 == 0:
                print(f"  进度 {i}/{len(to_import)} (last group_id={d.get('data', {}).get('id')})")
        except urllib.error.HTTPError as e:
            err = e.read().decode("utf-8", "replace")[:300]
            fail.append((it.get("序号"), it.get("ext"), e.code, err))
            print(f"  !! #{it.get('序号')} HTTP {e.code}: {err[:120]}")
        except Exception as e:
            fail.append((it.get("序号"), it.get("ext"), "ERR", str(e)))
        time.sleep(0.3)
    print(f"\n=== 导入完成 ===\n成功 {ok}/{len(to_import)} 笔")
    if fail:
        print(f"失败 {len(fail)} 笔（可直接修复 mapping 后重跑，查重与哈希兜底保证幂等）：")
        for sn, ext, code, err in fail:
            print(f"  #{sn} {ext} [{code}] {err[:150]}")
        sys.exit(1)


if __name__ == "__main__":
    main()
