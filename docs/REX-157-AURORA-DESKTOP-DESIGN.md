# REX OS Aurora Desktop — Visual Product Direction

Status: design target for REX #157. This document records the intended experience; it is not a claim that every item is implemented or runtime-tested.

## Product direction

Create an original REX desktop that takes cues from the supplied purple macOS-inspired reference: cinematic violet landscape, polished translucent surfaces, compact top status area, rounded windows, a centred application dock and clear desktop widgets. Do not copy Apple logos, proprietary artwork, exact icons, or macOS branding. REX remains a Linux desktop with its own identity.

## Visual system

- **Aurora palette:** deep violet and plum backgrounds; electric lavender as the primary accent; restrained magenta and cyan for secondary highlights and live states.
- **Glass surfaces:** translucent dark-violet panels with subtle borders, soft shadows and readable text. Transparency must degrade gracefully when compositing is unavailable.
- **Typography:** clean system sans-serif, clear hierarchy, compact labels and comfortable scaling.
- **Shape language:** rounded window corners, pill-like controls and consistent spacing. Avoid excessive glow, visual noise or oversized controls.
- **Wallpaper:** original REX mountain/aurora artwork, dark enough behind desktop icons and widgets.
- **Identity:** REX mark and REX terminology only; no Apple logo or copied Finder branding.

## Desktop composition

1. **Top system bar:** REX launcher/menu on the left; workspace and app actions; system tray, network/audio/battery indicators and clock on the right. Preserve Plasma system controls and accessibility.
2. **Workspace:** clean desktop with visible wallpaper, useful shortcuts and optional widgets. Keep icons legible and avoid clutter.
3. **Window experience:** consistent rounded, dark-glass application windows with visible focus, clear title bars, resize/move behavior and keyboard navigation.
4. **Bottom dock:** centred floating dock with REX AI, Omni, Connect, Files, Browser, Terminal and Settings. Use recognizable icons, tooltips, launch feedback and a restrained hover animation. It must not cover maximized-window controls or screen-edge interactions.
5. **Widgets:** clock/date and optional system information. Widgets must be movable, dismissible and non-blocking.
6. **REX assistant:** floating robot remains independently positionable, state-aware and dismissible/quiet-mode capable; it must not obscure essential controls.
7. **File manager:** retain Dolphin and Linux filesystem semantics while presenting a polished REX-branded entry point. Never imply Windows/macOS filesystem compatibility where it does not exist.

## Interaction and accessibility requirements

- Keyboard navigation and visible focus indicators for every dock/menu action.
- Respect desktop scaling, high-DPI displays, reduced motion and available contrast settings.
- Do not rely on color alone for status.
- Avoid persistent overlays that block app windows, task switching or screen edges.
- Provide a low-effects mode for systems with limited graphics resources.
- Keep startup resource use modest for the supported 8 GB RAM class of machines; no mandatory GPU acceleration.
- Preserve native Plasma session controls and a reliable way to reach system settings and a terminal.

## Engineering and release gates

- Keep source UI and ISO-packaged copies synchronized where both exist.
- Add automated tests for layout/config contracts and launch command safety.
- Run syntax checks and the full CI suite after each UI change.
- Build a fresh ISO and verify its checksum/manifest.
- Test clean boot, panel/dock positioning, window focus, keyboard navigation, scaling and assistant coexistence in VirtualBox.
- Do not mark the desktop accepted based on a successful CI run or ISO build alone. VM evidence is required; real-hardware testing remains a separate gate.

## Current implementation note

The repository already contains a Plasma look-and-feel package, a REX desktop hub/dock, a bundled wallpaper and a floating robot autostart entry. The Aurora palette update is an initial visual-system change only. The complete composition and its runtime behavior remain to be implemented and verified.
