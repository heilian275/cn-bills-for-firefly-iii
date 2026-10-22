# Firefly III 交易模型与接口来源

## 交易模型

一笔交易是一个 transaction group，里面有一个或多个 split。账单里的「一单多件」（见 `references/bill-formats.md` 的支付宝第 9 条）就是一个 group 多个 split。每个 split 有：

- `type`：`withdrawal`（资产账户 → expense 账户）、`deposit`（revenue 账户 → 资产账户）、`transfer`（资产账户 → 资产账户）。
- `amount`（字符串）、`date`、`description`、`notes`、`tags`。
- 另有 `category`、`budget`、`external_id`、`currency_code`。

## 版本与接口来源

脚本的防护基线是 6.2.x。勘察输出里的「API 版本」来自 `GET /api/v1/about` 的 `api_version`；实例版本和基线差得多时，先按下面的来源复核接口，再怀疑别的地方。

1. OpenAPI spec（按 release 存档，机器可读）：GitHub 仓库 `firefly-iii/api-docs` 的 `dist/` 目录。列目录用 `https://api.github.com/repos/firefly-iii/api-docs/contents/dist`；直链形如 `https://raw.githubusercontent.com/firefly-iii/api-docs/v6.7.8/dist/firefly-iii-v6.7.8-v1.yaml`。旧版文件名没有 v 前缀，以列目录的结果为准。版本之间的接口差异在 `dist/differences/`。
2. 官方文档站（需要浏览器）：`https://api-docs.firefly-iii.org/`（API 参考）和 `https://docs.firefly-iii.org/`（使用文档）。两个站都在 Cloudflare 后面，纯 HTTP 抓取（curl 之类）会 403。
3. 实例内的源码（和运行版本严格一致）。docker 部署可以直接进容器读，应用根目录通常是 `/var/www/html`。写侧字段和验证规则在 `app/Api/V1/Requests/` 各 FormRequest 的 `rules()`，读侧响应字段在 `app/Transformers/`，端点目录在 `routes/api.php`。行为上的结论也可以从源码里查，比如字段枚举值、约束、去重机制。
4. 实例的运行时信号（没有文档时的兜底）：`OPTIONS` 请求会返回 `Allow` 头；方法打错时错误消息会列出支持的方法；422 验证错误能反馈必填字段。但它不枚举合法值，未知字段会被静默忽略，个别消息还有误导，比如 type 无效时会报账户重名，不能当完整的 schema 用。

字段缺失用 PUT 修时，端点和请求体也从这些来源查。先 GET 这一笔，改完整笔回写。
