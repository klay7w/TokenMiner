# TokenMiner v0.1 Specification

This document is the design contract for TokenMiner v0.1. It is kept in the
repository so future contributors (human or bot) know exactly what v0.1 is and
is not. The `README.md` is fully auto-generated; this file is not.

## 0. 项目定位

TokenMiner 是一个可以公开托管在 GitHub 上、通过 GitHub Actions 自动运行的机器人项目。

> 自动发现、验证、整理并评价互联网上合法公开提供的免费 AI 模型、API Token、Credits、Free Tier、注册送额度、学生优惠和限时 Promotion。

v0.1 的第一目标是：建立一个真正可以持续运行、自动更新、数据可追溯的 MVP。

## 1. v0.1 必须回答的问题

用户打开 README 后应可以快速回答：

1. 现在有哪些值得使用的免费 AI API？
2. 哪个平台提供免费 Credits？
3. 哪个平台有永久免费模型？
4. 哪个平台适合 Coding？
5. 哪个平台适合 Reasoning？
6. 哪个平台支持长上下文？
7. 哪个平台需要信用卡？
8. 免费额度什么时候过期？
9. 应该去哪个具体网页领取？
10. 这条优惠最后一次是什么时候验证的？

## 2. v0.1 范围

Tier 1（必须支持，最高优先级）：

* OpenRouter
* TokenRouter（注意：域名是 tokenrouter.com）

Tier 2（首批支持，v0.1 不要求专用 Collector，用 Seed 数据 + Generic Collector）：

* Google AI Studio / Gemini API
* Groq
* Cerebras
* Mistral
* Hugging Face
* NVIDIA

Tier 3（候选 Provider，可收录，不要求 Collector，不阻碍发布）：

* SiliconFlow / DeepInfra / Together AI / Fireworks AI / Requesty /
  Vercel AI Gateway / Cloudflare AI Gateway / Portkey

## 3. v0.1 不做什么

不构建 Web Dashboard / 用户系统 / 数据库服务器（无 PostgreSQL、无 Redis）/
浏览器插件 / 移动 App / 付费功能 / 大规模爬虫；不维护几百个 Provider；
不绕过 Cloudflare / 登录 / Rate Limit；不抓私人 Discord / 泄露 Token；
不自动注册账号 / 领取优惠 / 创建 API Key；不使用多个账号薅额度。

TokenMiner v0.1 = Discovery + Verification + Ranking + GitHub Publishing。

## 4. 技术栈

Python 3.11+，httpx，BeautifulSoup4，PyYAML，Pydantic，pytest，
GitHub Actions。优先 JSON API，其次 httpx + BeautifulSoup 解析静态 HTML，
v0.1 不引入 Playwright。

## 5. Repository 结构

```text
TokenMiner/
├── README.md            (auto-generated)
├── LICENSE              (MIT)
├── CONTRIBUTING.md
├── CHANGELOG.md         (auto-generated)
├── SPEC.md              (this file)
├── pyproject.toml
├── data/
│   ├── providers.yaml   (seed registry, enriched by collectors)
│   ├── offers.json      (auto-generated)
│   ├── models.json      (auto-generated)
│   ├── seeds/
│   │   └── offers.yaml  (hand-verified seed offers)
│   └── history/         (YYYY-MM-DD.json snapshots, only on change)
├── docs/providers/      (auto-generated provider pages)
├── tokenminer/
│   ├── __init__.py
│   ├── __main__.py
│   ├── models/          (provider.py, offer.py, model.py — Pydantic schemas)
│   ├── collectors/      (base.py, openrouter.py, tokenrouter.py, generic.py)
│   ├── validators/offer_validator.py
│   ├── scoring/scorer.py
│   ├── generators/      (readme.py, provider_page.py)
│   └── utils/           (http.py, time.py)
├── scripts/             (update.py, validate.py — thin wrappers)
├── tests/
└── .github/workflows/   (update.yml, test.yml)
```

## 6. 三个核心数据对象

Provider / Offer / Model。不要过度抽象。

## 7. Provider Schema（YAML，data/providers.yaml）

```yaml
id: openrouter
name: OpenRouter
category: router   # router | official | candidate
description: >
  Multi-provider LLM API router.
official_url:
pricing_url:
docs_url:
models_url:
signup_url:
api_base_url:
api_compatibility: [openai]
requires_account: true
status: active      # active | uncertain | unavailable
last_checked:
last_verified:
sources: []
# Tier 2/3 providers additionally carry `collector: generic` + `watch_urls`
# so GenericCollector can do change detection on them.
```

## 8. Offer Schema（JSON）

优惠必须与 Provider 分离。

```json
{
  "id": "example-signup-credit",
  "provider_id": "example",
  "title": "New User Credit",
  "type": "signup_credit",
  "description": "",
  "value": 5,
  "currency": "USD",
  "free_tokens": null,
  "recurring": false,
  "new_users_only": true,
  "requires_payment_method": false,
  "requires_phone": null,
  "requires_student_verification": false,
  "region_limit": null,
  "start_date": null,
  "end_date": null,
  "claim_url": "",
  "source_url": "",
  "status": "active",
  "confidence": "official",
  "first_seen": "",
  "last_checked": "",
  "last_verified": "",
  "stale": false
}
```

`type` 只允许：free_tier / signup_credit / recurring_credit / free_model /
trial / promotion / student / developer_program / unknown。

`confidence` 只允许：official / high / medium / community / unknown。

`status` 只允许：active / uncertain / expired / unavailable。

## 9. Model Schema（JSON）

```json
{
  "provider_id": "openrouter",
  "model_id": "",
  "name": "",
  "developer": "",
  "model_type": ["text"],
  "context_length": null,
  "max_output_tokens": null,
  "input_price": null,
  "output_price": null,
  "free": false,
  "free_variant": null,
  "rate_limit": null,
  "supports_tools": null,
  "supports_vision": null,
  "supports_reasoning": null,
  "model_url": "",
  "source_url": "",
  "last_checked": "",
  "last_verified": ""
}
```

`context_length` 属于核心字段。没有官方可靠信息 → null，禁止通过模型名猜测。

## 10. Source Policy

Never hallucinate deals. 来源优先级：

P0 官方 Pricing / Documentation / API；P1 官方 Blog / GitHub / Announcement；
P2 官方 Social；P3 社区（GitHub Community / Reddit / HN / V2EX / 知乎 / Blog，
只用于 Discovery）。P3 线索必须去官网验证；无法验证 →
confidence=community、status=uncertain。

## 11. URL 必须细分

每个 Provider 尽量提供 Official / Pricing / Models / Docs / Signup / Claim /
Promotion URL。README 按钮直接进入 Claim URL，不是首页。

## 12. OpenRouter Collector

`OpenRouterCollector`：从官方 API 动态获取 Model ID / Name / Developer /
Context Length / Pricing / Free Status / Model URL。重点检测 `:free` 模型。
不得硬编码免费模型列表。

## 13. TokenRouter Collector

`TokenRouterCollector`：从 tokenrouter.com 官方页面收集 Current Models /
Free Models / API Compatibility；Signup Credit 必须有官方 URL 才能记录，
每次运行重新验证，不得永久保存为 Active。

## 14. Generic Collector

`GenericCollector`：对没有专用 Collector 的 Provider 访问预定义 URL、
提取文本、检测关键字（free / free tier / credit / trial / promotion /
promo / student / developer / signup / $5 / $10 / $20 / token）、
和上次 Snapshot 比较、明显变化则 Flag。职责是 Change Detection，
不是完全自动理解网页。

## 15. TokenMiner Score（总分 100）

Free Value 30 / Model Quality 20 / Quota & Rate Limit 15 / Context Window 10 /
API Compatibility 10 / Ease of Claim 5 / Platform Reliability 5 /
Transparency 5。等级 S 90–100 / A 80–89 / B 70–79 / C 60–69 / D <60。
每项由明确规则计算，不使用 AI 随机给分。

## 16. 免费价值评分规则

永久免费高质量模型→高分；每月重置额度→高分；一次性注册送→中等；
7 天 Trial→较低；需绑信用卡→扣分；无法确认额度→降低 Confidence。

## 17. Best For 标签

Best for Coding / Reasoning / Long Context / Speed / Multimodal / Beginners /
Overall Free API。只有证据足够时才赋予。

## 18–23. README 结构（全部自动生成）

1. `# ⛏️ TokenMiner` + 副标题 "Mine free AI models, API credits, tokens and developer deals."
2. `# 🔥 Best Free AI Deals Right Now` 表格：Rank / Provider / Offer /
   Best Model / Context / Free Quota / Payment / Expire / Score / Get
   （Get → Claim URL；只展示 confidence=official/high 的优惠）。
3. `# 🆓 Free Models`：Provider / Model / Type / Context / Rate Limit / API / Link。
4. `# 🎁 Free Credits`：Provider / Credits / Type / Requirement / Expire / Verified / Claim。
5. `# 💻 Best Free Models for Coding`（🥇🥈🥉，声明非正式 Benchmark）。
6. `# 🧠 Best Free Models for Reasoning`（同上）。
7. `# 🕒 Recently Changed`（最近若干项；完整记录进 CHANGELOG.md）。

## 24. Provider Page（docs/providers/<id>.md，固定章节）

Overview / Current Free Offers / Free Models / API / Context Windows /
Rate Limits / Requirements / Pros / Cons / TokenMiner Score / Recommended For /
Links / Sources / Last Verified。

## 25–26. 状态系统与 Stale Detection

所有记录必须有 last_checked；官方确认后才更新 last_verified。
>7 天未成功验证 → 显示 ⚠️ Stale（不自动 Expired）；>30 天 → status=uncertain。

## 27. Change Detection

current_data vs previous_data 生成 Diff：New Provider / New Offer /
Offer Removed / Credits ±、New Free Model / Free Model Removed / Context /
Rate Limit / Pricing / Expiration 变化。

## 28. History

data/history/YYYY-MM-DD.json，只在数据发生变化时保存 Snapshot
（providers + offers + free models）。

## 29. GitHub Actions

update.yml 每天运行：checkout → setup-python → install →
`python -m tokenminer` → pytest → 有变化则创建 Pull Request
（不直接推 main）。PR 标题 `⛏️ TokenMiner Update: YYYY-MM-DD`，
Body 汇总 New offers / Expired offers / New free models / Removed free models。

## 30. CLI

`python -m tokenminer`（等价 `tokenminer update`）、`tokenminer validate`、
`tokenminer generate`。v0.1 不需要更多命令。

## 31. Exit Code

单个 Provider 失败只记 Warning，不中断；仅 Schema invalid / 数据损坏 /
README generator 失败 / 测试失败 才退出非零。

## 32. HTTP 策略

统一 HTTP Client：Timeout / Retry / Backoff / User-Agent / Rate Limit / Cache。
UA：`TokenMiner/0.1 (+https://github.com/tokenminer/TokenMiner)`。
不要高频访问网站。

## 33. Verification（OfferValidator 至少检查）

Claim/Source URL 可访问；免费关键词出现；明显 expired 信息；End Date；
多久没有验证。

## 34. Confidence

official / high / medium / community / unknown。低可信优惠不得进入
Best Free AI Deals Right Now。

## 35. 风险标签（自动生成）

💳 Payment Required / 📱 Phone Verification / 🎓 Student Only /
🌍 Region Restricted / ⏳ Limited Time / 🎁 New Users Only / ♻️ Recurring /
♾️ Permanent Free Tier / ⚠️ Unverified。

## 36–37. Security / Legal

不保存 API Keys / Cookies / Passwords / Tokens；GitHub Actions 基本扫描
不需要任何 Secret。只记录 Provider 主动公开提供的合法优惠；禁止一切绕过、
盗用、批量注册行为。

## 38. Tests

至少覆盖 Provider/Offer/Model schema、Score 计算、Diff 检测、README 生成。
网络 Collector 测试使用 Mock，pytest 不依赖真实互联网。

## 39. Definition of Done

- [ ] `python -m tokenminer` 可以执行
- [ ] OpenRouter Collector 可以运行
- [ ] TokenRouter Collector 可以运行
- [ ] 至少 8 个 Provider 存在基础记录
- [ ] 生成 providers.yaml / offers.json / models.json
- [ ] README 自动生成，包含 Direct Links
- [ ] 模型包含 Context Window；优惠包含 Last Verified
- [ ] 存在 TokenMiner Score 与 Change Detection
- [ ] 自动生成 CHANGELOG
- [ ] GitHub Actions 每日运行
- [ ] Provider 单点失败不中断整体任务
- [ ] pytest 通过

## Philosophy

> Mine deals, verify facts, preserve history.

首先做到：**找到的东西是真的。**
