# <img src="https://www.google.com/s2/favicons?domain=openrouter.ai&sz=32" width="20" valign="middle"> OpenRouter

> Category: **router** · Status: **active**

## Overview

Multi-provider LLM API router. Aggregates hundreds of models behind an OpenAI-compatible API; models with ids ending in ":free" cost $0 per token.

## Current Free Offers

- **OpenRouter Free Models (21 models)** — type `free_tier`, value —, status `active`, confidence `official`
  - 21 models are priced $0 per token, most carrying a ':free' id suffix. Free variants are subject to platform free-usage rate limits; current numbers are rendered dynamically on the limits page, so they are not recorded as fixed values. See https://openrouter.ai/docs/api-reference/limits.
  - Claim: https://openrouter.ai/models?max_price=0
  - Source: https://openrouter.ai/api/v1/models

## Free Models

| Model | Rank | Ctx | Caps | Link |
|---|---|---|---|---|
| Gemma 4 31B | #73 🏆 | 262K | 📝🖼️🎬🛠️👁️🧠 | [↗](https://openrouter.ai/google/gemma-4-31b-it-20260402) |
| Thinking Machines: Inkling | #87 🏆 | 1M | 📝🖼️🔊🛠️👁️🧠 | [↗](https://openrouter.ai/thinkingmachines/inkling-20260715) |
| Qwen3.8 27B | #95 🏆 | 262K | 📝🖼️🎬🛠️👁️🧠 | [↗](https://openrouter.ai/qwen/qwen3.8-27b-20260814) |
| Gemma 4 26B A4B | #96 🏆 | 262K | 📝🖼️🎬🛠️👁️🧠 | [↗](https://openrouter.ai/google/gemma-4-26b-a4b-it-20260403) |
| Nemotron 3 Ultra | #115 🏆 | 1M | 📝🛠️🧠 | [↗](https://openrouter.ai/nvidia/nemotron-3-ultra-550b-a55b-20260604) |
| Thinking Machines: Inkling Small | #148 🏆 | 1M | 📝🖼️🔊🛠️👁️🧠 | [↗](https://openrouter.ai/thinkingmachines/inkling-small-20260730) |
| Nemotron 3 Super | #199 🏆 | 262K | 📝🛠️🧠 | [↗](https://openrouter.ai/nvidia/nemotron-3-super-120b-a12b-20230311) |
| Space Bunny Alpha | #6 🔥 | 1M | 📝🖼️🎬🛠️👁️🧠 | [↗](https://openrouter.ai/stealth/space-bunny-alpha) |
| Ling 3.0 Flash Sante | #47 🔥 | 262K | 📝🛠️🧠 | [↗](https://openrouter.ai/inclusionai/ling-3.0-flash-sante-20260904) |
| Ling 3.0 Flash Fin | #58 🔥 | 262K | 📝🛠️🧠 | [↗](https://openrouter.ai/inclusionai/ling-3.0-flash-fin-20260827) |
| Dots Studio: Dots3-Note Preview | #73 🔥 | 512K | 📝🖼️🛠️👁️🧠 | [↗](https://openrouter.ai/dots-studio/dots-3-note-preview-20260813) |
| LiquidAI: LFM2.5-2.6B | #81 🔥 | 66K | 📝🛠️🧠 | [↗](https://openrouter.ai/liquid/lfm-2.5-2.6b-20260811) |
| Nemotron 3.5 Lightning | #83 🔥 | 1M | 📝🛠️🧠 | [↗](https://openrouter.ai/nvidia/nemotron-3.5-lightning-20260807) |
| Laguna S 2.1 | #97 🔥 | 262K | 📝🛠️🧠 | [↗](https://openrouter.ai/poolside/laguna-s-2.1-20260720) |
| Laguna XS 2.1 | #128 🔥 | 262K | 📝🛠️🧠 | [↗](https://openrouter.ai/poolside/laguna-xs-2.1-20260625) |
| North Mini Code | #135 🔥 | 256K | 📝🛠️🧠 | [↗](https://openrouter.ai/cohere/north-mini-code-20260617) |
| Nemotron 3.5 Content Safety | #143 🔥 | 128K | 📝🖼️👁️🧠 | [↗](https://openrouter.ai/nvidia/nemotron-3.5-content-safety-20260604) |
| Nemotron 3 Nano Omni | #163 🔥 | 256K | 📝🖼️🎬🔊🛠️👁️🧠 | [↗](https://openrouter.ai/nvidia/nemotron-3-nano-omni-30b-a3b-reasoning-20260428) |
| Lyria 3 Pro Preview | #200 🔥 | 1M | 📝🖼️🔊👁️ | [↗](https://openrouter.ai/google/lyria-3-pro-preview-20260330) |
| Lyria 3 Clip Preview | #201 🔥 | 1M | 📝🖼️🔊👁️ | [↗](https://openrouter.ai/google/lyria-3-clip-preview-20260330) |
| Free Models Router | #242 🔥 | 200K | 📝🖼️🛠️👁️🧠 | [↗](https://openrouter.ai/openrouter/free) |

Rank: 🏆 [LMArena](https://llmarena.ai) text-leaderboard rank · 🔥 [OpenRouter](https://openrouter.ai) weekly usage rank · — unranked

*📝 text · 🖼️ image I/O · 👁️ image input (vision) · 🎬 video · 🔊 audio · 🧩 embedding · 🛠️ tools · 🧠 reasoning*

## API

- API base: `https://openrouter.ai/api/v1`
- Compatibility: `openai`

## Context Windows

- Largest free-model context: **1M**
- Free models with published context: 21 of 21

## Rate Limits

_No officially published rate-limit numbers recorded for free usage._

## Requirements

- Account required: yes

## Pros

- 21 free model(s) available
- long-context free models (≥200K)
- free models with tool calling
- free models with reasoning support
- multimodal free models
- high TokenMiner score (89/100, grade A)

## Cons

_No notable drawbacks derived from current data._

## TokenMiner Score

**89/100 — grade A**

| Component | Points | Max |
|---|---|---|
| Free Value | 30 | 30 |
| Model Quality | 20 | 20 |
| Quota & Rate Limit | 8 | 15 |
| Context Window | 10 | 10 |
| API Compatibility | 6 | 10 |
| Ease of Claim | 5 | 5 |
| Platform Reliability | 5 | 5 |
| Transparency | 5 | 5 |

Risk tags: ♾️ Permanent Free Tier

## Recommended For

- Coding
- Reasoning
- Long Context
- Multimodal
- Beginners
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

- Provider: 2026-09-26
- Offer `openrouter-free-models`: 2026-09-26
