# JARVIS -> REX integration plan

Status: integration branch created; repository audit in progress. This document is a plan, not a claim that the assistant is already integrated.

## Protected baseline
- Base: feat/rex144-secure-device-foundation
- Keep feat/rex142-continuous-voice, fix/iso-build, master, and existing PRs unchanged.
- All integration work stays on feat/rex145-jarvis-openrouter-integration until reviewed and tested.

## Upstream project findings
- Upstream: https://github.com/adewaskar/jarvis
- Upstream is MIT-licensed.
- UI: React, Vite, Three.js, custom GLSL.
- Voice/UI features include wake-word handling, local VAD, speech synthesis, barge-in, panels, and a WebSocket bridge.
- Its default bridge depends on @anthropic-ai/claude-agent-sdk and Claude Code login.
- Its direct browser backend uses the Anthropic SDK and explicitly enables browser API-key exposure. That mode is unsuitable for a distributable REX OS.
- Upstream requires Node.js >=20 and a real Chrome/Edge browser for its documented microphone path.
- Bundled audio has a separate CREDITS.md and must be reviewed before redistribution.

## Required REX adaptation
1. Preserve the upstream visual experience and attribution; rename visible product identity to REX.
2. Replace Claude Agent SDK / Claude Code with a server-side OpenRouter adapter. Use OpenAI-compatible chat completions or supported tool calling only after validating the selected model's capabilities.
3. Never place OpenRouter credentials in Vite variables, browser bundles, source control, logs, or the ISO. Store credentials per-user in an OS credential store or encrypted local secret store; provide a first-run setup screen.
4. Keep a provider interface so REX can later support other providers and local Ollama without changing the UI.
5. Keep the local bridge bound to loopback by default. Require authenticated sessions, origin checks, input validation, request limits, and explicit user consent for microphone/camera.
6. Do not expose arbitrary shell, filesystem, browser, or phone tools directly to the model. Route actions through REX's permission service and allowlist; require confirmation for sensitive or destructive actions.
7. Integrate with the existing REX OS desktop startup only after health checks and graceful failure behavior are implemented. Assistant failure must never block desktop login or boot.
8. Make startup opt-in on first run until the user completes setup; then allow "start with desktop" to be enabled. Do not open the microphone before explicit permission.
9. Reduce resource usage for the initial target hardware (8 GB RAM, no discrete GPU); keep visual effects and voice components configurable.

## Acceptance gates
- TypeScript typecheck, lint, production frontend build.
- Backend unit tests for provider configuration, OpenRouter request/stream parsing, cancellation, timeouts, error mapping, and secret redaction.
- Integration tests with a mocked OpenRouter endpoint; no real API key in CI.
- Validate that built frontend assets contain no API key or secret-like configured value.
- Verify bridge rejects untrusted origins and unauthenticated clients.
- Verify read-only actions work and sensitive actions require explicit confirmation.
- Build the REX ISO; boot and test in VirtualBox. Confirm desktop auto-start, assistant UI, setup screen, voice permissions, graceful offline behavior, and that the OS remains usable when OpenRouter is unavailable.
- Only call the integration complete after all acceptance gates pass.

## Known risk
A literal copy of upstream is not compatible with the requested OpenRouter setup: its bridge is coupled to Claude Agent SDK and its browser-direct path exposes provider keys. The backend must be replaced, not merely reconfigured.
