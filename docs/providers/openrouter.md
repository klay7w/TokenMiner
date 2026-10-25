# <img src="https://www.google.com/s2/favicons?domain=openrouter.ai&sz=32" width="20" valign="middle"> OpenRouter

> Category: **router** · Status: **active**

## Overview

Multi-provider LLM API router. Aggregates hundreds of models behind an OpenAI-compatible API; models with ids ending in ":free" cost $0 per token.

## Current Free Offers

- **OpenRouter Free Models (20 models)** — type `free_tier`, value —, status `expired`, confidence `official`
  - 20 models are priced $0 per token, most carrying a ':free' id suffix. Free variants are subject to platform free-usage rate limits; current numbers are rendered dynamically on the limits page, so they are not recorded as fixed values. See https://openrouter.ai/docs/api-reference/limits.
  - Claim: https://openrouter.ai/models?max_price=0
  - Source: https://openrouter.ai/api/v1/models

## Free Models

| Model | Rank | Ctx | Caps | Link |
|---|---|---|---|---|
| Gemma 4 31B | #75 🏆 | 262K | 📝🖼️🎬🛠️👁️🧠 | [↗](https://openrouter.ai/google/gemma-4-31b-it-20260402) |
| Thinking Machines: Inkling | #95 🏆 | 1M | 📝🖼️🔊🛠️👁️🧠 | [↗](https://openrouter.ai/thinkingmachines/inkling-20260715) |
| Gemma 4 26B A4B | #100 🏆 | 262K | 📝🖼️🎬🛠️👁️🧠 | [↗](https://openrouter.ai/google/gemma-4-26b-a4b-it-20260403) |
| Nemotron 3 Ultra | #120 🏆 | 1M | 📝🛠️🧠 | [↗](https://openrouter.ai/nvidia/nemotron-3-ultra-550b-a55b-20260604) |
| Thinking Machines: Inkling Small | #153 🏆 | 1M | 📝🖼️🔊🛠️👁️🧠 | [↗](https://openrouter.ai/thinkingmachines/inkling-small-20260730) |
| Nemotron 3 Super | #204 🏆 | 262K | 📝🛠️🧠 | [↗](https://openrouter.ai/nvidia/nemotron-3-super-120b-a12b-20230311) |
| Flint | #2 🔥 | 262K | 📝🛠️🧠 | [↗](https://openrouter.ai/recursive/flint-v1.0-20261021) |
| XingChen: Xing4.0 29B A4B | #6 🔥 | 262K | 📝🛠️🧠 | [↗](https://openrouter.ai/xingchen-agi/xing4.0-29b-a4b-20261015) |
| Nemotron 3.5 Super VL | #13 🔥 | 1M | 📝🖼️🎬🛠️👁️🧠 | [↗](https://openrouter.ai/nvidia/nemotron-3.5-super-vl-20261015) |
| Dots Studio: Dots3-Note Preview | #104 🔥 | 512K | 📝🖼️🛠️👁️🧠 | [↗](https://openrouter.ai/dots-studio/dots-3-note-preview-20260813) |
| LiquidAI: LFM2.5-2.6B | #113 🔥 | 66K | 📝🛠️🧠 | [↗](https://openrouter.ai/liquid/lfm-2.5-2.6b-20260811) |
| Nemotron 3.5 Lightning | #115 🔥 | 1M | 📝🛠️🧠 | [↗](https://openrouter.ai/nvidia/nemotron-3.5-lightning-20260807) |
| Laguna S 2.1 | #129 🔥 | 262K | 📝🛠️🧠 | [↗](https://openrouter.ai/poolside/laguna-s-2.1-20260720) |
| Laguna XS 2.1 | #159 🔥 | 262K | 📝🛠️🧠 | [↗](https://openrouter.ai/poolside/laguna-xs-2.1-20260625) |
| North Mini Code | #166 🔥 | 256K | 📝🛠️🧠 | [↗](https://openrouter.ai/cohere/north-mini-code-20260617) |
| Nemotron 3.5 Content Safety | #174 🔥 | 128K | 📝🖼️👁️🧠 | [↗](https://openrouter.ai/nvidia/nemotron-3.5-content-safety-20260604) |
| Nemotron 3 Nano Omni | #195 🔥 | 256K | 📝🖼️🎬🔊🛠️👁️🧠 | [↗](https://openrouter.ai/nvidia/nemotron-3-nano-omni-30b-a3b-reasoning-20260428) |
| Lyria 3 Pro Preview | #231 🔥 | 1M | 📝🖼️🔊👁️ | [↗](https://openrouter.ai/google/lyria-3-pro-preview-20260330) |
| Lyria 3 Clip Preview | #232 🔥 | 1M | 📝🖼️🔊👁️ | [↗](https://openrouter.ai/google/lyria-3-clip-preview-20260330) |
| Free Models Router | #272 🔥 | 200K | 📝🖼️🛠️👁️🧠 | [↗](https://openrouter.ai/openrouter/free) |

Rank: 🏆 [LMArena](https://llmarena.ai) text-leaderboard rank · 🔥 [OpenRouter](https://openrouter.ai) weekly usage rank · — unranked

*📝 text · 🖼️ image I/O · 👁️ image input (vision) · 🎬 video · 🔊 audio · 🧩 embedding · 🛠️ tools · 🧠 reasoning*

## API

- API base: `https://openrouter.ai/api/v1`
- Compatibility: `openai`

## Context Windows

- Largest free-model context: **1M**
- Free models with published context: 20 of 20

## Rate Limits

_No officially published rate-limit numbers recorded for free usage._

## Requirements

- Account required: yes

## Pros

- 20 free model(s) available
- long-context free models (≥200K)
- free models with tool calling
- free models with reasoning support
- multimodal free models
- high TokenMiner score (80/100, grade A)

## Cons

_No notable drawbacks derived from current data._

## TokenMiner Score

**80/100 — grade A**

| Component | Points | Max |
|---|---|---|
| Free Value | 30 | 30 |
| Model Quality | 20 | 20 |
| Quota & Rate Limit | 8 | 15 |
| Context Window | 10 | 10 |
| API Compatibility | 6 | 10 |
| Ease of Claim | 3 | 5 |
| Platform Reliability | 3 | 5 |
| Transparency | 0 | 5 |

Risk tags: ♾️ Permanent Free Tier

## Recommended For

- Coding
- Reasoning
- Long Context
- Multimodal
- Overall Free API

## Links

- [Official](https://openrouter.ai)
- [Pricing](https://openrouter.ai/models?max_price=0)
- [Docs](https://openrouter.ai/docs)
- [Models](https://openrouter.ai/models)
- [Signup](https://openrouter.ai)

## Sources

- https://openrouter.ai/api/v1/models
- https://openrouter.ai/docs/api-reference/limits

## Last Verified

- Provider: 2026-10-25
- Offer `openrouter-free-models`: 2026-10-20
