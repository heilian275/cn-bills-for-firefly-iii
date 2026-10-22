# cn-bills-for-firefly-iii

[English](README.md) | 简体中文

[![skills.sh installs](https://skills.sh/b/heilian275/cn-bills-for-firefly-iii)](https://skills.sh/heilian275/cn-bills-for-firefly-iii)

把支付宝、微信支付（Alipay / WeChat Pay）导出的 csv/xlsx 账单逐笔分类，导入你自托管的 [Firefly III](https://firefly-iii.org/)。退款配对、复合支付、自充值识别这些中国账单里常见的情况会单独处理；分类照你已有的账户和分类来；写入前给你看预览。

这个 skill 来自两个月的实际导入。账单解析只是第一步，真正花时间的是格式细节、退款和复合支付的对应关系，以及写库前的判断。

## 目录

skill 本体在 `skills/cn-bills-for-firefly-iii/`，skills CLI 只拷这一层，不会把仓库里的其他文件一起装进 skills 目录。

- `skills/cn-bills-for-firefly-iii/SKILL.md`：入口，放流程、安全门和每一步该做什么。
- `skills/cn-bills-for-firefly-iii/references/`：按需读取的细节。`bill-formats.md` 是支付宝和微信的格式与坑，`special-cases.md` 是退款、复合支付、自充值这些形态，`mapping-json.md` 是分类产物的字段约定，`firefly-iii.md` 是交易模型和接口查法。
- `skills/cn-bills-for-firefly-iii/scripts/`：勘察、预览、查重、导入、验证。
- `.claude-plugin/`、`README.md`、`LICENSE`：仓库打包用，不属于 skill 本体。

## 安装

Skills CLI（支持 Claude Code、Codex、ZCode 等 agent harness）：

```bash
npx skills add heilian275/cn-bills-for-firefly-iii --global
```

Claude Code 插件方式：

```text
/plugin marketplace add heilian275/cn-bills-for-firefly-iii
/plugin install cn-bills-for-firefly-iii@cn-bills-for-firefly-iii
```

手动安装：克隆或下载本仓库，把 `skills/cn-bills-for-firefly-iii` 这个目录拷进你的 agent 的 skills 目录（如 `~/.claude/skills/`、`~/.zcode/skills/`）。

## 使用

对 agent 说「把这份支付宝账单导入我的 Firefly III」并给出文件路径。每次导入大致是：

1. 脚本从你指定的文件或环境变量读 token，取回账单特征和你实例里的账户、分类、近期交易；
2. agent 对照这些信息逐笔分类。skill 不内置分类规则，照你已有的结构来；
3. 预览页列出中低置信和跳过的交易，你改完并批准后才写库；写入后按批次标签验证。

无效交易、退款对这类条件性事项不会中途打断你。agent 先给最佳处理并标注疑点，统一在预览页裁决。

前提是你已经跑着自己的 Firefly III，并且有一套账户和分类。skill 不替你建分类，也不预设任何结构。

## 安全须知

账单内容（商家、金额、时间、订单号、支付账户尾号）会进入 AI 上下文，模型服务商可以看到。skill 会在开始前告知，并取得你的明确同意后才开始。在意隐私可以改用本地模型，或先做脱敏预处理。

Firefly III API token 不进入 AI 上下文。所有脚本从你指定的文件或环境变量读，调试输出只有 token 长度或 HTTP 状态码。

写入前必须经你批准；除此之外没有别的写库入口。

本 skill 不收集、不上传任何数据；脚本只与你指定的 Firefly III 实例通信。账单内容会进入 AI 上下文，这一点见本节第一段。

按现状提供（MIT）。导入前核对预览，Firefly III 数据请定期备份。

## 版本历史

<details>
<summary>显示版本记录</summary>

- 0.1.0：首个公开版本。四层测试（结构校验 / 行为矩阵 / 回归 / 跨 harness 冒烟）通过；在 Claude Code 与 ZCode 双 harness 实测完成。

</details>

## License

MIT
