# REX OS #155 — Twelve-feature completion and release acceptance

## Purpose and commitment
This is the single delivery tracker for the 12 REX OS capabilities requested for #155. The earlier #155 CI success proved that the existing source passed the configured Python checks and that an ISO artifact was produced. It did not prove that these 12 capabilities were implemented or work at runtime.

Release rule: a feature is not complete merely because a plan exists, code compiles, tests pass, or an ISO builds. Each feature must meet its own acceptance criteria, have automated tests where practical, and be exercised in the built OS. VM-only evidence must be labelled VM-tested, not hardware-tested. Any external service that does not exist must be marked as a blocker, not simulated or described as live.

## Delivery status vocabulary
- Not started — no implementation evidence.
- In progress — code or integration work is underway.
- Implemented — code path exists, but verification is incomplete.
- CI-tested — automated tests passed in GitHub Actions.
- ISO-built — included in a newly built ISO.
- VM-tested — exercised in a clean VirtualBox boot with evidence.
- Hardware-tested — exercised on physical supported hardware.
- Blocked — requires an external service, platform, credentials, hardware, or decision not available in this repository.

Current status at the start of this completion pass: the prior #155 workflow completed successfully and uploaded an ISO. The 12 feature rows below remain unverified until the new implementation and acceptance evidence is attached. Do not carry the old workflow result forward as proof of new changes.

## The 12 required feature deliverables

### 1. Continuous Hey Rex conversation
Deliver: wake-word activation; clear listening/thinking/speaking/muted states; multi-turn conversation without repeating the wake phrase for every turn; explicit stop; timeout; cancellation; safe microphone error handling; interruption/barge-in if the selected audio backend supports reliable cancellation.
Acceptance: test wake, two or more turns, silence timeout, stop command, mute/privacy state, microphone unavailable, speech output cancellation, and no unintended recording after stop. Document unsupported backends rather than faking support.

### 2. Fully permission-controlled desktop control
Deliver: typed action registry and strict allowlist; schema/type/range validation for every argument; no arbitrary shell command pathway; confirmation for sensitive actions; safe path handling; clear user-visible result; audit record that avoids secrets.
Acceptance: allowed actions work; unknown actions, shell metacharacters, path traversal, malformed arguments and unapproved sensitive actions are rejected; tests prove approval is enforced.

### 3. Android phone companion and remote control
Deliver: a real buildable Android companion or a clearly scoped Android client project; authenticated device pairing; device identity; least-privilege remote commands; connection status; revocation; reconnect behaviour; secure transport.
Acceptance: build succeeds on a supported Android toolchain; pair, authorize, perform an allowed action, reject unauthorized action, revoke device, and verify revoked device cannot reconnect. If Android build tooling/signing or a phone is unavailable, mark the corresponding test blocked and provide reproducible steps—do not call a web page or SSH adapter a native app.

### 4. Windows companion app
Deliver: real Windows client with documented supported Windows version, pairing flow, secure transport, permissions, reconnect, and uninstall/revoke path.
Acceptance: reproducible build plus Windows runtime test for pairing, allowed action, denied action, disconnect/reconnect and revocation. If no Windows runner/device is available, CI build and runtime validation must be reported separately.

### 5. macOS companion app
Deliver: real macOS client with documented supported macOS version, pairing flow, secure transport, permissions, reconnect and revoke path. SSH-only support is not a native app.
Acceptance: macOS build and runtime tests for pairing, authorization, allowed/denied action, reconnect and revocation. If Apple tooling/hardware is unavailable, mark hardware/runtime verification blocked.

### 6. Encrypted sync and device/cloud synchronisation
Deliver: distinguish local export/import from network sync; authenticated encryption with a reviewed standard library; key derivation/storage that keeps secrets out of source and logs; device trust and revocation; schema versioning; conflict policy; recovery and deletion semantics.
Acceptance: round-trip encrypted sync; tamper detection; wrong-key rejection; revoked-device rejection; conflict test; secret scan. A hosted sync service, account service and cloud availability are separate blockers until deployed and tested. Do not claim cloud sync from local JSON export.

### 7. Floating REX robot assistant runtime
Deliver: robot UI launches in the logged-in graphical session, stays responsive, has clear state indicators, can be repositioned/minimized/closed, and does not obstruct normal desktop use. Startup must be controllable.
Acceptance: clean VM login shows robot; launch/restart/close works; no duplicate processes; UI recovers from assistant errors; keyboard/accessibility and display scaling are checked.

### 8. OpenRouter integration and live AI response
Deliver: provider-neutral AI Core; OpenRouter base URL/model configuration; user-supplied key stored outside source and ISO; timeout/retry/error handling; provider selection/fallback policy; redaction of secrets in logs and UI.
Acceptance: with a user-supplied test key, make a real request and verify a response; test missing/invalid key, timeout, provider error, fallback and log redaction. Never commit or request the user to paste a private key into GitHub/source.

### 9. Microphone, speech recognition and spoken reply
Deliver: supported input-device selection; permission/privacy indicator; speech-to-text integration; text-to-speech output; clear errors for missing devices/models; language/backend documentation.
Acceptance: record a short test phrase, verify transcription, generate a spoken response, verify mute/stop and device-unavailable behaviour. Keep audio local unless the selected provider's data handling is explicitly disclosed and configured.

### 10. Secure remote access and device authentication
Deliver: authenticated pairing; TLS outside loopback; short-lived/revocable credentials; replay protection; authorization per action; safe relay lifecycle; no placeholder tokens, unauthenticated WebSocket clients, or arbitrary remote shell/OS command execution.
Acceptance: negative tests for missing, invalid, expired and revoked credentials; unauthorized action; replay; non-TLS remote transport; relay disconnect; and permission escalation. Default to loopback/local-only until the secure remote path passes.

### 11. Commercial licensing, editions, subscriptions, billing and REX Cloud
Deliver: licence/dependency inventory; edition feature matrix; secure update and signing design; customer-owned API key model; account/licensing architecture; documented subscription and billing integration boundaries; privacy and support policy.
Acceptance: validate licence inventory and update-signature verification. Actual subscriptions, payment processing, account portal and hosted REX Cloud require deployed production services, secrets, legal/compliance review and operational support. Until those exist, mark them blocked/not live; do not create fake checkout, fake licence validation or claim billing is operational.

### 12. Full ISO and VirtualBox acceptance
Deliver: reproducible clean ISO build; checksums and manifest; artifact retention; bootable VM configuration; test evidence for login, desktop, robot, AI, voice, desktop permissions, network security, pairing, sync and Omni; resource measurements for the target 8 GB RAM/no-NVIDIA PC.
Acceptance: clean VirtualBox boot from the newly built ISO; record VM version, CPU/RAM/disk/display/network settings, test date, logs/screenshots, failures and measured idle/peak RAM. Test recovery/reboot and verify checksum. This does not substitute for physical hardware testing.

## Cross-cutting requirements
- Preserve and reconcile the #143/#144/#145 foundations without silently discarding existing work.
- Review both source copies and the packaged copies under build/config/includes.chroot/opt/rex-os; tests must catch drift between them.
- Add unit/integration/security tests for each feature and wire them into CI.
- Keep credentials out of Git, logs, test fixtures, ISO and artifacts.
- Use least privilege, secure defaults and explicit user consent for remote/device/desktop actions.
- Maintain compatibility and installation documentation, known limitations and recovery steps.
- Do not weaken or delete tests just to make CI green.

## Required evidence table
Update this table as work progresses. Link commits, CI runs, artifacts and VM evidence in the evidence column.

| # | Feature | Implementation status | CI status | ISO status | Runtime status | Evidence / blockers |
|---|---|---|---|---|---|---|
| 1 | Continuous Hey Rex | Not started / unverified | Pending | Pending | Pending | |
| 2 | Desktop control and permissions | Not started / unverified | Pending | Pending | Pending | |
| 3 | Android companion | Not started / unverified | Pending | Pending | Pending | |
| 4 | Windows companion | Not started / unverified | Pending | Pending | Pending | |
| 5 | macOS companion | Not started / unverified | Pending | Pending | Pending | |
| 6 | Encrypted sync | Not started / unverified | Pending | Pending | Pending | |
| 7 | Floating robot runtime | Not started / unverified | Pending | Pending | Pending | |
| 8 | OpenRouter live AI | Not started / unverified | Pending | Pending | Pending | |
| 9 | Microphone/STT/TTS | Not started / unverified | Pending | Pending | Pending | |
| 10 | Secure remote access | Not started / unverified | Pending | Pending | Pending | |
| 11 | Commercial licensing/billing/cloud | Not started / unverified | Pending | Pending | Pending | |
| 12 | ISO + VirtualBox acceptance | Prior ISO build passed; new full acceptance pending | Prior run passed | Prior ISO uploaded | VM test pending | Prior run is not evidence for new code |

## Execution order
1. Audit current source and packaged copies; map each feature to existing modules and identify unsafe/incomplete code.
2. Fix security-critical remote access and desktop-control issues before enabling remote actions.
3. Complete AI provider, voice, microphone and robot integration with tests.
4. Complete pairing protocol and platform clients; clearly separate platform build support from runtime proof.
5. Implement encrypted sync primitives and conflict/revocation handling; deploy hosted cloud only when infrastructure is available.
6. Harden Omni and commercial foundations; mark live services honestly.
7. Run full CI, build a fresh ISO, then complete VirtualBox acceptance and publish the evidence matrix.

## Definition of done
#155 is complete only when every deliverable is either implemented and passes its stated CI + ISO + VM acceptance gates, or explicitly marked blocked with the missing external dependency, with no false claim that the capability is delivered.

A successful CI run or ISO upload alone is never the definition of done.
