---
name: cn-bills-for-firefly-iii
description: 把支付宝、微信支付（Alipay / WeChat Pay）导出的 csv/xlsx 账单导入用户自托管的 Firefly III：处理退款配对、复合支付、自充值识别等中国账单特有的情况，按用户已有的账户和分类逐笔归类，写入前由用户确认。用户要导入、同步或整理支付宝、微信账单，或把交易流水记进 Firefly III 时使用。
---

# 支付宝、微信账单导入 Firefly III

这个 skill 把支付宝「交易明细证明」的 csv 和微信「支付账单流水」的 xlsx 逐笔分类，写入用户自托管的 Firefly III。SKILL.md 只放流程、安全门和每一步的指路；细节按提示从 `references/` 读取。

前提是用户已经跑着自己的 Firefly III，并且有一套账户和分类。skill 不替用户建分类，也不预设任何结构。

## 运行依赖

跑脚本之前先确认四件事。能自己检测的就不要问用户：

1. Firefly III 实例和 API token。地址问用户，或者从上下文推断；token 的位置由用户告知，可以是文件或环境变量。用户可以在 Firefly III 的 Options → Profile → OAuth 里生成（Personal Access Tokens 一节）。提醒用户不要把 token 粘贴进对话。
2. 运行环境：`uv`（优先）或 Python 3.9 以上。用 `uv --version` 或 `python3 --version` 检测。
3. openpyxl：只处理微信 xlsx 时需要，纯支付宝 csv 不需要。
4. 网络：用户的 Firefly III 地址要能访问。这一项不用提前测，脚本第一次调用就会暴露问题。

运行环境按这个顺序试，成功就停：

1. `uv run --with openpyxl <script>`。uv 自己管依赖，不污染系统环境。
2. `python3 <script>`（Windows 上通常是 `python`）。需要已经装了 openpyxl（微信 xlsx 必需）；缺了就先 `pip install --user openpyxl` 再试。
3. 两个都不可用就停下，给用户 uv 或 Python 3.9+ 的安装说明。

脚本的共同约定：token 从 `--token-file` 指向的文件或环境变量 `FIREFLY_III_ACCESS_TOKEN` 读取，不接受命令行明文 token；`--url` 默认 `http://localhost:8080`；输出是紧凑文本，方便 agent 直接读。

## 安全须知

模型上下文里的内容会发往 LLM 服务商。模型不在本机运行时，任何进入上下文的账单信息都已经离开本机。开始之前，用户和 agent 都要清楚下面几点。

1. Firefly III 的 API token（PAT）不能进入上下文。不要 cat、Read 或 echo token 文件；脚本会自己从文件或环境变量读。排查认证问题时只打印 token 长度或 HTTP 状态码，不要打印 token 的任何字符片段。
2. 账单内容会进入上下文：商家、金额、时间、订单号、支付账户尾号，模型服务商都能看到；token 不会。第一次使用时要如实告知，用自己的话转述，意思不能削弱，并取得用户明确同意，例如用户回复「同意，开始」。用户没有回复、回答含糊或拒绝时，停在告知这一步，不分析也不导入。在意隐私的用户可以改用本地模型，或者先脱敏再处理，然后重新取得同意。
3. 带凭证的请求只发给用户自己的 Firefly III 实例，通常是 localhost。不要放进任何其他外部调用。
4. PAT 没有细粒度权限。泄漏的后果是别人可以操作记账数据，但不涉及资金账户。如实告知即可，不夸大也不缩小。

## 流程

知情同意 → 定位账单 → 勘察 → 分类 → 预览并取得批准 → 查重 → 导入 → 验证。

写库只发生在预览批准之后。

### 1. 定位账单文件

路径由用户给，或者自己在用户的工作区里找。文件名通常是 `支付宝交易明细*.csv` 和 `微信支付账单流水文件*.xlsx`。

解析前先读 `references/bill-formats.md`，确认平台、编码、表头行号和列名。用户可能按月整理，也可能一次给一批；一批就逐个处理，日期范围看文件名或内容。

### 2. 勘察

```bash
uv run --with openpyxl scripts/gather_reference.py --alipay <csv路径> --wechat <xlsx路径> --url <...> --token-file <...>
```

这条命令一次取回六类信息：

- 连接状态和 API 版本；
- 账单侧各列的取值分布：支付方式、账单分类、收支、状态；
- Firefly III 的账户清单，资产账户带币种；
- 分类清单；
- 最近 3 个月的历史参照：方向 / 账户 / 分类 ← 典型 description；
- 本批账单的逐笔明细。

拿这些信息判断特殊形态、制定映射策略。地址、token 的位置这类环境信息不清楚时问用户；已经确认过的可以按 harness 的习惯存下来复用，存在哪和用户商量。实例版本和脚本基线差得多时，读 `references/firefly-iii.md` 的「版本与接口来源」。

### 3. 分类，生成 mapping

这一步最依赖判断。先读 `references/special-cases.md`，再对照账单明细和 Firefly III 的历史参照，照用户已有的账户、分类和 description 习惯归纳规律。skill 不给分类方法、建议或示例。

- 每笔给 type（`withdrawal` / `deposit` / `transfer` / 跳过）、按用户的实际结构填账户和分类、置信度（高 / 中 / 低）。
- 产出 mapping JSON，格式见 `references/mapping-json.md`。预览和导入脚本都读它。
- 条件性事项不要中途问用户：无效交易跳不跳、退款对是成对跳过还是导入、疑似自充值的源和目标方向。先给最佳处理，置信度标低，备注写清疑点，统一到预览里裁决。

### 4. 预览与批准

```bash
uv run --with openpyxl scripts/build_preview.py --mapping <mapping.json> --out preview.html
```

预览页默认只显示需要关注的项：中低置信和跳过，其余可以展开。脚本只写文件，生成后由你在浏览器打开，或者按 harness 的惯例交给用户。除开头的知情同意，全流程只有这里需要用户裁决，中低置信和条件性事项都在这里处理。用户可以改任何一笔：跳过改成导入、导入改成跳过、换账户、换分类。改动收集起来，更新 mapping。没有明确批准，不进入导入。

### 5. 查重

```bash
uv run scripts/dedup_check.py --mapping <mapping.json> --url <...> --token-file <...>
```

按 external_id 检查 Firefly III 里有没有相同的交易。有重复就停下来处理，0 条重复才继续。external_id 怎么拼，见 `references/bill-formats.md` 的「external_id」。

### 6. 导入

```bash
uv run scripts/import_bills.py import --mapping <mapping.json> --batch <批次标签> --url <...> --token-file <...>
```

逐笔 POST，失败的收集进报告。中途失败可以直接重跑，查重和重复哈希兜底，不会重复写入。`--batch` 是必填参数，惯例是 `YYYY-MM账单`。它会作为 tag 打到本批每一笔交易上，后面的验证、对账、整批定位都靠它；不传会直接报错。脚本还有 dry-run 子命令，能打印请求体自查。

### 7. 验证

```bash
uv run scripts/verify_import.py --mapping <mapping.json> --batch <批次标签> --start <YYYY-MM-DD> --end <YYYY-MM-DD> --url <...> --token-file <...>
```

按批次标签核对笔数、金额合计和 external_id 覆盖。有字段缺失就用 PUT 修：先读这一笔，改完整笔回写。接口和排错来源见 `references/firefly-iii.md`。

## 参考文件

- `references/bill-formats.md`：支付宝和微信的文件布局、编码、表头、列名、平台坑、external_id。
- `references/special-cases.md`：退款对、复合支付、自充值、无效交易、平台分类这些形态。
- `references/mapping-json.md`：mapping JSON 的字段和取值。
- `references/firefly-iii.md`：transaction group/split 模型、API 版本、OpenAPI/文档/源码/运行时信号的查法。

## 红线

- token 不进上下文。账单数据进上下文前，先告知用户并取得明确同意。
- 写生产库前要用户批准；批准只发生在预览这一步。
- 不中途打断用户。无效交易、退款对、特殊形态这类条件性事项，先给最佳处理，集中到预览裁决。
- 分类只用用户已有的结构，不发明账户，也不预设分类。
- 产物里不放真实个人信息，示例一律虚构。
