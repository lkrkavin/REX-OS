# REX OS #155 — Commercial Integration

## Objective
Integrate the existing #143/#144/#145 foundations into a coherent REX OS release candidate, then test the ISO end-to-end. This document is a delivery plan, not a claim that these capabilities are already complete.

## Workstreams and acceptance gates

### 1. AI Core and provider reliability
- Preserve a provider-neutral interface.
- Verify OpenRouter configuration and runtime requests without embedding keys in the image.
- Test provider selection, errors, timeouts, fallback policy and secret redaction.
- Record actual provider integration test evidence.

### 2. Voice and floating assistant
- Verify local Hey Rex wake detection, microphone selection and visible listening/mute state.
- Implement a multi-turn session lifecycle with explicit stop, timeout and cancellation.
- Add interruption/barge-in only where the audio backend can reliably support it; test that speech output stops promptly.
- Test robot autostart and assistant launch in a graphical session.

### 3. Permission-controlled desktop actions
- Use a strict action allowlist and validate every argument.
- Require user confirmation for sensitive operations.
- Reject arbitrary shell commands and unsafe paths.
- Record action outcomes in an audit log.

### 4. Secure device connectivity
- Require authenticated pairing and expiring, revocable credentials.
- Require TLS for non-loopback transport.
- Remove unauthenticated relay paths and placeholder credentials.
- Do not expose arbitrary remote shell access.
- Test permission checks, revocation, expiry and unauthorized requests.

### 5. Companion clients
- Define a stable, versioned pairing/API contract.
- Build and test Android, Windows and macOS clients only where repository toolchains and CI runners support real build validation.
- Do not describe SSH adapters as native companion applications.

### 6. Encrypted synchronisation
- Separate local settings import/export from network sync.
- Encrypt sensitive sync payloads with authenticated encryption and keep keys outside source control.
- Define device trust, revocation, conflict handling and recovery.
- Do not claim cloud sync until a hosted service is deployed and tested.

### 7. REX Omni
- Validate package identifiers and supported package formats.
- Enforce explicit install/uninstall authorization.
- Test progress, failure reporting and rollback/recovery.
- Clearly label unsupported Windows/Android compatibility paths.

### 8. Commercial readiness
- Inventory dependency, upstream code, UI and media licences.
- Define editions and customer-owned API-key handling.
- Design secure update, licensing, account and billing interfaces.
- Do not claim subscriptions, billing or managed cloud are live without operational services.

### 9. Release validation
- Run Python syntax checks and the full test suite.
- Build the ISO and generate checksums.
- Boot in VirtualBox and test login, desktop, robot, networking, AI, voice, desktop permissions, device pairing and Omni.
- Record resource use on the target 8 GB RAM / no-NVIDIA environment.
- Report each feature as planned, implemented, committed, CI-tested, ISO-built, VM-tested or hardware-tested.

## Release rule
A successful GitHub Actions run proves only the checks that ran and the artifact that was produced. It does not prove runtime behaviour. Do not mark #155 complete until required CI and VM acceptance evidence is recorded.
