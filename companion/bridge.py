#!/usr/bin/env python3
"""Experimental live HLS bridge for a Roku channel on the same LAN.

This is not Steam Remote Play or Moonlight. It captures a local desktop with
FFmpeg, serves HLS to Roku's Video node, and forwards basic Roku remote events
to a virtual Linux gamepad when python-evdev/uinput is available.
"""
from __future__ import annotations

import argparse
import json
import os
import secrets
import shutil
import signal
import subprocess
import sys
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent
PUBLIC = ROOT / "public"
LIVE = PUBLIC / "live"
PLAYLIST = LIVE / "index.m3u8"
TOKEN = secrets.token_urlsafe(24)
ALLOWED_KEYS = {"up", "down", "left", "right", "OK", "play", "pause", "rewind", "fastforward"}


class RemoteInput:
    """Expose Roku remote buttons as a virtual gamepad, with keyboard fallback."""
    def __init__(self) -> None:
        self.device = None
        self.ev = None
        self.pressed_directions: set[str] = set()
        try:
            from evdev import AbsInfo, UInput, ecodes
            caps = {
                ecodes.EV_KEY: [
                    ecodes.BTN_SOUTH, ecodes.BTN_EAST, ecodes.BTN_WEST,
                    ecodes.BTN_NORTH, ecodes.BTN_START, ecodes.BTN_SELECT,
                    ecodes.BTN_DPAD_UP, ecodes.BTN_DPAD_DOWN,
                    ecodes.BTN_DPAD_LEFT, ecodes.BTN_DPAD_RIGHT,
                ],
                ecodes.EV_ABS: [
                    (ecodes.ABS_X, AbsInfo(0, -32768, 32767, 0, 0, 0)),
                    (ecodes.ABS_Y, AbsInfo(0, -32768, 32767, 0, 0, 0)),
                ],
            }
            self.device = UInput(caps, name="Steam Link Roku Remote")
            self.ev = ecodes
            print("[input] Virtual gamepad ready: Steam Link Roku Remote")
        except Exception as exc:
            print(f"[input] Virtual gamepad unavailable ({exc}); trying xdotool keyboard fallback.")
            if not shutil.which("xdotool"):
                print("[input] Install python-evdev and allow access to /dev/uinput, or install xdotool.")

    def handle(self, key: str, pressed: bool) -> tuple[bool, str]:
        if key not in ALLOWED_KEYS:
            return False, "Unsupported remote key"

        if self.device is not None:
            e = self.ev
            btns = {
                "up": e.BTN_DPAD_UP, "down": e.BTN_DPAD_DOWN,
                "left": e.BTN_DPAD_LEFT, "right": e.BTN_DPAD_RIGHT,
                "OK": e.BTN_SOUTH, "play": e.BTN_START,
                "pause": e.BTN_START, "rewind": e.BTN_WEST,
                "fastforward": e.BTN_EAST,
            }
            if key in ("up", "down", "left", "right"):
                if pressed:
                    self.pressed_directions.add(key)
                else:
                    self.pressed_directions.discard(key)
                x = (32767 if "right" in self.pressed_directions else
                     -32768 if "left" in self.pressed_directions else 0)
                y = (32767 if "down" in self.pressed_directions else
                     -32768 if "up" in self.pressed_directions else 0)
                self.device.write(e.EV_ABS, e.ABS_X, x)
                self.device.write(e.EV_ABS, e.ABS_Y, y)
            self.device.write(e.EV_KEY, btns[key], 1 if pressed else 0)
            self.device.syn()
            return True, "virtual gamepad"

        if shutil.which("xdotool"):
            keymap = {
                "up": "Up", "down": "Down", "left": "Left", "right": "Right",
                "OK": "Return", "play": "space", "pause": "space",
                "rewind": "Left", "fastforward": "Right",
            }
            try:
                subprocess.run(
                    ["xdotool", "keydown" if pressed else "keyup", keymap[key]],
                    check=True, timeout=2, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                )
                return True, "keyboard"
            except Exception as exc:
                return False, f"xdotool failed: {exc}"
        return False, "No gamepad or keyboard injector is available"

    def close(self) -> None:
        if self.device is not None:
            try:
                self.device.close()
            except Exception:
                pass


class Handler(SimpleHTTPRequestHandler):
    server_version = "SteamLinkRokuBridge/0.2"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(PUBLIC), **kwargs)

    def _json(self, status: int, data: dict) -> None:
        raw = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path == "/health":
            self._json(200, {
                "ok": True,
                "streamReady": PLAYLIST.exists(),
                "stream": "/live/index.m3u8",
                "token": TOKEN,
                "mode": "experimental-hls-bridge",
                "notice": "Not native Steam Link. HLS latency and remote-input limits apply.",
            })
            return
        if path == "/":
            self._json(200, {"name": "Steam Link Roku Bridge", "health": "/health", "stream": "/live/index.m3u8"})
            return
        return super().do_GET()

    def do_POST(self) -> None:
        if urlparse(self.path).path != "/input":
            self._json(404, {"ok": False, "error": "Unknown endpoint"})
            return
        supplied = self.headers.get("X-Bridge-Token", "")
        if not secrets.compare_digest(supplied, TOKEN):
            self._json(403, {"ok": False, "error": "Invalid session token"})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length <= 0 or length > 4096:
                raise ValueError("Invalid request size")
            payload = json.loads(self.rfile.read(length))
            key = payload.get("key")
            pressed = payload.get("pressed")
            if not isinstance(key, str) or not isinstance(pressed, bool):
                raise ValueError("Expected key:string and pressed:boolean")
        except Exception as exc:
            self._json(400, {"ok": False, "error": str(exc)})
            return
        ok, message = self.server.remote_input.handle(key, pressed)
        self._json(200 if ok else 503, {"ok": ok, "input": message})

    def log_message(self, fmt: str, *args) -> None:
        print("[http] " + (fmt % args))


class BridgeServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True


def capture_args(args: argparse.Namespace) -> tuple[list[str], bool]:
    if sys.platform.startswith("linux"):
        if args.capture == "pipewire":
            video = ["-f", "pipewire", "-framerate", str(args.fps), "-i", "0"]
        else:
            display = args.display or os.environ.get("DISPLAY", ":0.0")
            video = [
                "-f", "x11grab", "-draw_mouse", "1", "-framerate", str(args.fps),
                "-video_size", args.size, "-i", display,
            ]
        audio_device = args.audio_device
        if audio_device == "auto":
            audio_device = None
            if shutil.which("pactl"):
                try:
                    sink = subprocess.check_output(["pactl", "get-default-sink"], text=True, timeout=2).strip()
                    if sink:
                        audio_device = sink + ".monitor"
                except Exception:
                    pass
        if audio_device:
            video += ["-f", "pulse", "-i", audio_device]
        return video, bool(audio_device)

    if sys.platform == "win32":
        return [
            "-f", "gdigrab", "-framerate", str(args.fps),
            "-video_size", args.size, "-i", "desktop",
        ], False

    raise RuntimeError("Automatic desktop capture currently supports Linux and Windows only.")


def start_ffmpeg(args: argparse.Namespace) -> subprocess.Popen:
    LIVE.mkdir(parents=True, exist_ok=True)
    for path in LIVE.glob("*"):
        if path.is_file():
            path.unlink()

    inputs, audio_enabled = capture_args(args)
    command = [args.ffmpeg, "-hide_banner", "-loglevel", "warning", "-nostdin"] + inputs
    command += ["-map", "0:v:0"]
    if audio_enabled:
        command += ["-map", "1:a:0?"]
    command += [
        "-c:v", "libx264", "-preset", "ultrafast", "-tune", "zerolatency",
        "-profile:v", "baseline", "-pix_fmt", "yuv420p",
        "-r", str(args.fps), "-g", str(args.fps), "-keyint_min", str(args.fps),
        "-sc_threshold", "0", "-b:v", args.bitrate, "-maxrate", args.bitrate,
        "-bufsize", "1000k",
    ]
    if audio_enabled:
        command += ["-c:a", "aac", "-b:a", "128k", "-ar", "48000"]
    else:
        command += ["-an"]
    command += [
        "-f", "hls", "-hls_time", "1", "-hls_list_size", "6",
        "-hls_flags", "delete_segments+omit_endlist+independent_segments",
        "-hls_segment_filename", str(LIVE / "segment_%06d.ts"),
        str(PLAYLIST),
    ]
    print("[ffmpeg] " + " ".join(command))
    return subprocess.Popen(command)


def main() -> int:
    parser = argparse.ArgumentParser(description="Experimental PC-to-Roku HLS bridge")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--ffmpeg", default="ffmpeg")
    parser.add_argument("--capture", choices=["x11grab", "pipewire"], default="x11grab")
    parser.add_argument("--display", default=None, help="X11 display, e.g. :0.0")
    parser.add_argument("--size", default="1280x720")
    parser.add_argument("--fps", type=int, choices=[24, 30, 60], default=30)
    parser.add_argument("--bitrate", default="5000k")
    parser.add_argument("--audio-device", default="auto",
                        help="PulseAudio/PipeWire monitor source; 'auto', blank to disable, or exact source name")
    parser.add_argument("--no-audio", action="store_true")
    args = parser.parse_args()
    if args.no_audio:
        args.audio_device = ""
    if not shutil.which(args.ffmpeg):
        print("ERROR: ffmpeg was not found. Install it and rerun.", file=sys.stderr)
        return 2

    PUBLIC.mkdir(parents=True, exist_ok=True)
    remote_input = RemoteInput()
    try:
        process = start_ffmpeg(args)
    except Exception as exc:
        remote_input.close()
        print(f"ERROR: could not start capture: {exc}", file=sys.stderr)
        return 2

    server = BridgeServer((args.host, args.port), Handler)
    server.remote_input = remote_input

    def shutdown(*_):
        threading.Thread(target=server.shutdown, daemon=True).start()

    signal.signal(signal.SIGINT, shutdown)
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, shutdown)

    print("")
    print("Roku bridge: http://<PC-LAN-IP>:%d" % args.port)
    print("Health check: http://<PC-LAN-IP>:%d/health" % args.port)
    print("Stream:      http://<PC-LAN-IP>:%d/live/index.m3u8" % args.port)
    print("Input token is returned to the Roku app by /health.")
    print("IMPORTANT: HLS is higher latency than Steam Link/Moonlight; this is an experiment.")
    print("")
    try:
        server.serve_forever(poll_interval=0.25)
    finally:
        server.server_close()
        remote_input.close()
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=4)
            except subprocess.TimeoutExpired:
                process.kill()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
