# REX Launcher

A native Android home-screen replacement in the REX ecosystem.

## Compatibility target
- Minimum supported Android version: Android 9 (API 28).
- Intended compatibility: Android 9 and newer.
- First physical-device target: Samsung Galaxy A10.
- Physical-device testing is required before claiming support for a specific Android version or manufacturer.

## Current implementation
- Registers as an Android HOME application.
- Retains a normal app-drawer entry for initial setup and debugging.
- Discovers launchable installed apps.
- Displays real app icons and names.
- Provides searchable app list.
- Launches apps when their tiles are tapped.
- Uses an adaptive grid and a dark cyan/purple REX visual foundation.

## Build locally
1. Install Android Studio and JDK 17.
2. Open the `rex-launcher` directory in Android Studio.
3. Install Android SDK Platform 35 and Build-Tools when prompted.
4. Allow Gradle sync to complete.
5. Select **Build > Build Bundle(s) / APK(s) > Build APK(s)**.

Debug APK output: `app/build/outputs/apk/debug/app-debug.apk`

## Install and select as default
1. Install the debug APK on the test phone.
2. Open Android Settings > Apps > Default apps > Home app (wording varies by manufacturer).
3. Select REX Launcher.
4. Test app discovery, search, launch, rotation, Home button behavior, and returning from apps.

## Package visibility
The launcher declares `QUERY_ALL_PACKAGES` because discovering installed launchable apps is core launcher functionality. Distribution through Google Play is subject to Google's package-visibility policy and review.

## Status
First development milestone. Not yet tested on a physical Samsung Galaxy A10.
