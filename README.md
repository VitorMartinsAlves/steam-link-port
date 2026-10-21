# Steam Link for Roku — feasibility status

**This repository is not a functional Steam Link client.** The current BrightScript/SceneGraph files are only an HLS receiver/UI experiment. They do not connect to Steam, pair with a Steam host, decode the Steam Remote Play stream, carry game audio, or provide proper controller support.

## Why the Android-style client cannot be produced as a normal Roku sideload

The standard Roku app platform exposes BrightScript and SceneGraph APIs in a sandbox. A working Steam Link client needs the real-time Remote Play client stack, low-latency audio/video decoding and transport, host discovery/pairing, and controller input. Roku's public app environment does not provide a direct way to package and run the existing Android Steam Link app or its native runtime as a sideloaded channel.

Steam Link itself is proprietary software; Valve documents supported apps/platforms such as Android, Samsung TVs, and Raspberry Pi, but does not provide a Roku client or public source code for porting the full client. Sources: [Roku platform architecture](https://developer.roku.com/dev/docs/dev-environment), [Steam Link supported platforms](https://help.steampowered.com/pt-br/faqs/view/7BE7-BB7D-D904-03AE), [Steam Link for Android](https://help.steampowered.com/pt-br/faqs/view/7112-CD02-7B57-59F8).

An HLS screen-capture relay can display a PC image on a Roku, but it is not equivalent to Steam Link: latency, audio synchronization, and input support are inadequate for responsive gameplay. This repo intentionally does not claim otherwise.

## What this repository currently contains

- A SceneGraph settings screen for a base server URL and HLS URL.
- A basic `/health` check.
- HLS playback when an external service supplies a compatible playlist.
- Best-effort posting of Roku remote button events to an external service.

There is no companion service in this repository. The ZIP generated from these files should not be described as a working Steam Link port.

## For actual Steam Remote Play on this TV

Use a device connected through HDMI that supports the Steam Link app (for example, a compatible Android TV device or Raspberry Pi). That lets the client run on a supported platform instead of trying to execute it inside Roku OS.
