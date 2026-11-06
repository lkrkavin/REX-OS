# REX holographic assistant integration

Upstream source: https://github.com/adewaskar/jarvis (MIT; see LICENSE).
The upstream visual interface is adapted and rebranded as REX. The active UI calls
only the same-origin local REX service at 127.0.0.1:8764. The local service uses
REX's existing OpenRouter provider and OS keyring; no API key is shipped to the
browser, Vite bundle, source tree, or ISO.

The upstream Claude Agent SDK bridge and browser-direct Anthropic client are
reference-only and are not imported by the active REX brain module. No Claude
login is required. The local service exposes health and text-generation routes
only; it does not expose shell, filesystem, camera, remote-device, or arbitrary
computer-control tools. Microphone access remains controlled by the user in the
interface. Audio assets remain excluded pending separate rights review.
Preserve upstream MIT notices in derivatives.
