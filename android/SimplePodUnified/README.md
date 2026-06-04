# SimplePod Unified — Android Client

## Overview
Native Android companion for the SimplePod 20-node asyncio swarm. Provides a floating ChatHead overlay, SMS/MMS conversation analysis, AI reply generation, and real-time swarm monitoring.

## Architecture
| Layer | File | Purpose |
|-------|------|---------|
| **Main Panel** | `MainActivity.kt` | Jetpack Compose navigation hub |
| **Floating Overlay** | `overlay/ChatHeadService.kt` | `SYSTEM_ALERT_WINDOW` bubble, draggable, opens menu |
| **SMS Bridge** | `sms/SMSManager.kt` | Reads threads, counts messages, feeds to LLM |
| **LLM Client** | `llm/LLMClient.kt` | Queries backend `/unified/demo/llm-test`, falls back to Pollinations.AI |
| **Analysis UI** | `ui/AnalysisScreen.kt` | Thread picker → red-flag analysis with sentiment & control scores |
| **Reply UI** | `ui/ReplyGeneratorScreen.kt` | Tone/goal selectors → AI reply suggestions |
| **Swarm UI** | `ui/SwarmStatusScreen.kt` | 5×4 worker grid, auto-refresh every 5s |

## Permissions Required
- `INTERNET` — Backend + Pollinations.AI fallback
- `SYSTEM_ALERT_WINDOW` — Floating ChatHead
- `FOREGROUND_SERVICE` — Keep overlay alive
- `READ_SMS` — Conversation analysis
- `SEND_SMS` — Thread injection (future)

## Backend Connection
Default: `http://10.0.2.2:8000` (Android emulator localhost bridge)

For physical device, change `baseUrl` in `LLMClient.kt` to your PC's LAN IP (e.g., `http://192.168.1.50:8000`).

## Build
```bash
cd android/SimplePodUnified
./gradlew assembleDebug
```

## Install
```bash
adb install app/build/outputs/apk/debug/app-debug.apk
```

## Features from Unified Demo Integrated
- 📊 Phone extraction analysis (contacts, messages, call logs)
- 🤖 LLM-powered conversation analysis (16 red-flag detection)
- 💬 Reply generation with tone/goal selectors
- 🔗 20-worker swarm status monitor
- 🖇 Floating ChatHead overlay (open/close from any screen)
- 🔄 Auto-fallback: Backend → Pollinations.AI (free, no key)
