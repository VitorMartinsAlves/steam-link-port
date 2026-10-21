# Steam Link Roku Bridge (experimental)

A sideloadable Roku SceneGraph/BrightScript prototype that validates a LAN service, plays an HLS stream, and forwards basic Roku-remote key events to that service.

**Important:** this is not a native Steam Link / Steam Remote Play client. Roku apps use BrightScript and SceneGraph, and this prototype does not implement the Steam Remote Play protocol, its real-time audio/video transport, Steam Input, controller pairing, or low-latency decoding. It will not stream a Steam PC by itself. HLS playback is generally too latent for responsive gaming. This project is a receiver/UI experiment, not a drop-in replacement for Steam Link.

## Build/package

The root of the ZIP must contain `manifest`, `source/`, and `components/`.

```bash
zip -r steam-link-roku.zip manifest source components README.md
```

Upload the ZIP using the Roku Development Application Installer while the device is in developer mode.

## Companion server contract

- `GET /health` — JSON such as `{"ok": true, "stream": "/stream.m3u8"}`.
- `GET /stream.m3u8` — a Roku-compatible HLS playlist and its media segments.
- `POST /input` — accepts JSON such as `{"key":"up","pressed":true}`.

Set the base URL to something like `http://192.168.1.20:8765`. The server must bind to the LAN interface, and the host firewall must allow access. `localhost` on the Roku is the TV itself, not the PC.

No companion service is included because an HLS screen-capture bridge would not reproduce Steam Link's low-latency gameplay or controller support.

## Platform references

- [Roku developer setup / sideloading](https://developer.roku.com/dev/docs/developer-setup)
- [Roku BrightScript and SceneGraph overview](https://developer.roku.com/dev/docs/getting-started)
- [Steam Link supported platforms](https://help.steampowered.com/pt-br/faqs/view/7BE7-BB7D-D904-03AE)
