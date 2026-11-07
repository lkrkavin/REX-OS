# REX OS #156 — Unified 12-feature completion and release plan

## Purpose
#156 consolidates the 12 capabilities previously tracked under #155 into one release scope. The goal is a reliable, secure, testable REX OS release—not a checklist marked complete because code exists.

## Status definitions
- **Not started:** no implementation evidence.
- **In progress:** implementation or integration is underway.
- **Implemented:** code path exists; runtime acceptance is still outstanding.
- **CI-tested:** focused automated tests passed in CI.
- **ISO-built:** included in a fresh ISO generated from this exact commit.
- **VM-tested:** exercised in a clean VirtualBox boot with recorded evidence.
- **Platform-tested:** exercised on the actual supported Android, Windows, or macOS target.
- **Blocked:** requires unavailable hardware, service, credentials, signing, or user action.

A feature is complete only when its applicable implementation, security, automated-test, and runtime acceptance criteria pass. CI and ISO build success are not substitutes for runtime tests. Never describe a hosted service as live unless deployed and tested.

## The 12 feature workstreams

### 1. Continuous Hey Rex conversation
Implement wake-word activation, multi-turn session lifecycle, listening/thinking/speaking/muted states, stop, timeout, cancellation, privacy-safe microphone handling, and interruption where the audio backend supports it. Test multi-turn dialogue, timeout, stop, mute, microphone denial/unavailability, speech cancellation and restart.

### 2. Permission-controlled desktop control
Use a typed action registry, strict allowlist, argument schema validation, path validation, approval for sensitive operations, visible results and privacy-safe audit logs. Reject unknown actions, arbitrary shell, malformed input, path traversal and unapproved sensitive actions.

### 3. Android companion and remote control
Deliver a genuine buildable Android client with secure pairing, device identity, least-privilege actions, revocation, reconnect and secure transport. Build and test on supported Android tooling and a device/emulator. Do not call a web view or SSH bridge a native companion.

### 4. Windows companion
Deliver a genuine Windows client with documented supported versions, pairing, permissions, secure transport, reconnect and revocation. Build and runtime-test on Windows; report CI-only evidence separately.

### 5. macOS companion
Deliver a genuine macOS client with documented supported versions, pairing, permissions, secure transport, reconnect and revocation. SSH-only access is not a native client. Apple tooling/hardware is required for full platform acceptance.

### 6. Encrypted synchronisation
Separate local import/export from network synchronisation. Use authenticated encryption, safe key derivation/storage, device trust/revocation, schema versions, conflict handling, recovery and deletion semantics. Test round trips, wrong keys, tampering, revoked devices and conflicts. Hosted cloud sync requires a real deployed service.

### 7. Floating REX robot
Integrate the assistant overlay into the logged-in desktop session with startup controls, positioning, visibility, accessibility, graceful failure and resource-aware behavior. Verify in a clean VM, including restart/login behavior.

### 8. OpenRouter AI integration
Verify provider selection, model configuration, authenticated request, response rendering, timeout, rate-limit and network error handling, safe fallback, and API-key secrecy. Never commit keys or expose them in logs/UI. A real response test requires a user-supplied key and network access.

### 9. Microphone, speech recognition and spoken reply
Test device discovery, permission denial, recognition, TTS, language/configuration, mute, stop, device disconnect and error recovery. CI mocks do not count as microphone hardware testing.

### 10. Secure remote access and device authentication
Require authenticated pairing, encrypted transport, scoped authorization, replay protection, rate limiting, expiration and revocation. Fail closed. No unauthenticated WebSocket clients, placeholder relay credentials, arbitrary shell, or remote destructive action without explicit local approval.

### 11. Commercial readiness
Complete licence/dependency inventory, edition boundaries, secure configuration and key handling, update verification and documented support policy. Billing, subscriptions, accounts, hosted REX Cloud and licensing enforcement are not complete until real services are deployed and end-to-end tested. No fake checkout or placeholder cloud claims.

### 12. REX Omni
Implement package/source validation, install/launch/update/remove flows, permission boundaries, progress, logs, rollback/recovery and compatibility disclosures. Test safe local packages and rejected malformed/untrusted packages. Windows/Android compatibility layers must be described accurately.

## Release gates
1. Review and reconcile the existing #143/#144/#145/#155 foundations before replacing or duplicating them.
2. Fix the known #155 CI import failure: the latest run failed importing `services.rex_remote_server` because `psutil` was not installed in the Python test environment. Declare dependencies in the project's actual dependency manifest and ensure the ISO runtime installs them too; do not add a CI-only workaround.
3. Add focused tests for each feature and security boundary.
4. Run compile/static checks and the full test suite.
5. Build a fresh ISO from the exact release candidate commit; generate SHA-256/SHA-512 and manifest.
6. Boot the ISO in a clean VirtualBox VM; test login, desktop, robot, AI, voice, desktop permissions, remote pairing, sync, Omni, networking, shutdown/restart and resource usage.
7. Run platform tests on Android, Windows and macOS for each native companion.
8. Record all evidence and blockers. Do not close #156 or declare a complete release while any required acceptance gate is unverified.

## Initial status
All 12 workstreams are **not yet accepted** at the start of #156. This plan is a scope and gate definition, not proof of implementation. Update each workstream only with linked commits, tests, build artifacts and runtime evidence.
