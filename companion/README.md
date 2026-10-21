# PC companion

Run the desktop bridge on the Linux gaming PC. It needs FFmpeg; optional Linux input support uses python-evdev plus /dev/uinput, with xdotool as a fallback.

Install on CachyOS / Arch:

```bash
sudo pacman -S --needed ffmpeg xdotool python-evdev acl
sudo modprobe uinput
sudo setfacl -m "u:$USER:rw" /dev/uinput
```

X11 capture:

```bash
python bridge.py --capture x11grab --size 1280x720 --fps 30
```

Wayland capture, if your FFmpeg build includes PipeWire input:

```bash
python bridge.py --capture pipewire --size 1280x720 --fps 30
```

Audio uses the default PulseAudio/PipeWire sink monitor when detectable. Add `--no-audio` to disable it. The app will expose `http://PC-LAN-IP:8765/health` and HLS at `/live/index.m3u8`.

Use only on a trusted LAN. This is an HLS desktop bridge, not a native Steam Link client; HLS adds latency and the Roku remote is not a complete gamepad.