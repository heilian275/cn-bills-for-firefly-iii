# cn-bills-for-firefly-iii

English | [简体中文](README.zh-CN.md)

[![skills.sh installs](https://skills.sh/b/heilian275/cn-bills-for-firefly-iii)](https://skills.sh/heilian275/cn-bills-for-firefly-iii)

Takes the CSV and XLSX statements exported by Alipay and WeChat Pay, classifies every transaction, and imports them into your self-hosted [Firefly III](https://firefly-iii.org/). Refund pairs, split payments, and self-top-up detection — cases that are common in Chinese statements — are handled separately. Categorization follows the accounts and categories you already have, and you see a preview before anything is written.

The skill comes out of two months of real imports. Parsing the statements is only the first step; most of the effort goes into format details, matching refunds and split payments, and the judgement calls before writing to the ledger.

## Layout

The skill itself lives in `skills/cn-bills-for-firefly-iii/`, so a skills CLI copies only those files and not the repository around them.

- `skills/cn-bills-for-firefly-iii/SKILL.md`: the entry point. The workflow, the safety gates, and what to do at each step.
- `skills/cn-bills-for-firefly-iii/references/`: details loaded on demand. `bill-formats.md` covers the Alipay and WeChat file layouts and their pitfalls, `special-cases.md` covers refunds, split payments, and self-top-ups, `mapping-json.md` defines the classification output, and `firefly-iii.md` covers the transaction model and how to look up the API.
- `skills/cn-bills-for-firefly-iii/scripts/`: inspection, preview, duplicate check, import, and verification.
- `.claude-plugin/`, `README.md`, `LICENSE`: repository packaging; not part of the skill.

## Installation

Skills CLI (works with Claude Code, Codex, ZCode, and other agent harnesses):

```bash
npx skills add heilian275/cn-bills-for-firefly-iii --global
```

As a Claude Code plugin:

```text
/plugin marketplace add heilian275/cn-bills-for-firefly-iii
/plugin install cn-bills-for-firefly-iii@cn-bills-for-firefly-iii
```

Manual install: clone or download this repository, then copy the `skills/cn-bills-for-firefly-iii` directory into your agent's skills directory (for example `~/.claude/skills/` or `~/.zcode/skills/`).

## Usage

Tell your agent "import this Alipay statement into my Firefly III" and give it the file path. Each import roughly goes like this:

1. The scripts read the token from the file or environment variable you point them at, then fetch the statement characteristics plus the accounts, categories, and recent transactions from your instance;
2. the agent classifies every transaction against that information. The skill ships no classification rules; it follows the structure you already have;
3. the preview lists mid- and low-confidence items together with skipped transactions. Nothing is written until you have edited and approved it; after the import, the result is verified by batch tag.

Conditional cases such as voided transactions and refund pairs do not interrupt you mid-flow. The agent picks the best treatment, notes the doubt, and leaves the decision to the preview.

Prerequisites: you already run Firefly III and have a set of accounts and categories. The skill does not create categories for you and does not assume any structure.

## Privacy and safety

Statement contents (merchant, amount, time, order number, last digits of the payment account) enter the AI context, where the model provider can see them. The skill tells you this before it starts and only begins after you explicitly agree. If that matters to you, use a local model or anonymize the statements first.

The Firefly III API token never enters the AI context. Every script reads it from the file or environment variable you specify, and debugging output is limited to the token length or HTTP status codes.

Nothing is written without your approval; there is no other write path.

The skill collects and uploads nothing; its scripts only talk to the Firefly III instance you specify. Statement content does enter the AI context, as described in the first paragraph of this section.

Provided as is (MIT). Review the preview before importing, and back up your Firefly III data regularly.

## Version history

<details>
<summary>Show version history</summary>

- 0.1.0: first public release. Passed four layers of testing (structure checks, behavior matrix, regression, cross-harness smoke) and was verified end to end on both Claude Code and ZCode.

</details>

## License

MIT
