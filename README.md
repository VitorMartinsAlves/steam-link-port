# Steam Link Roku Bridge — protótipo experimental

Este repositório agora inclui um canal Roku sideloadável e um companion para PC. O companion captura o desktop com FFmpeg, publica uma playlist HLS para o player SceneGraph da Roku e envia os comandos do controle remoto do Roku ao PC.

## O que foi implementado

- Validação da conexão do Roku com o PC via endpoint `/health`.
- Reprodução de HLS no player do Roku.
- Captura de desktop por FFmpeg em Linux (X11 ou tentativa via PipeWire) e Windows (captura básica).
- Áudio de saída via monitor PulseAudio/PipeWire no Linux, quando detectado.
- Entrada remota com token de sessão; no Linux tenta criar controle virtual via `python-evdev`/`uinput`, com fallback de teclado via `xdotool`.
- Empacotamento do canal para sideload pela Roku Development Application Installer.

## Limitação importante

**Isto não é o cliente Steam Link nativo e não é equivalente ao Steam Link de verdade.** O Roku OS não executa APK Android ou bibliotecas nativas arbitrárias dentro de um canal sideload e não suporta playback WebRTC. O protocolo de streaming de jogos requer transporte de baixa latência, sockets TCP/UDP e uma cadeia real de decodificação/controle. Esta ponte usa HLS: haverá latência perceptível, e o controle remoto do Roku não substitui um gamepad completo. É uma implementação experimental para visualizar/controlar o desktop, não uma solução garantida para jogos de ação.

Referências técnicas:
- Roku: https://partnersuccess.roku.com/hc/en-us/articles/360060167853-Does-Roku-support-WebRTC-and-Play-WebRTC-streams
- Moonlight FAQ: https://github.com/moonlight-stream/moonlight-docs/wiki/Frequently-Asked-Questions
- Roku SceneGraph Video: https://developer.roku.com/dev/docs/video-player

## Executar no CachyOS / Arch Linux

Instale as dependências:

```bash
sudo pacman -S --needed ffmpeg xdotool python-evdev acl
```

Para gamepad virtual via uinput, carregue o módulo e conceda acesso ao usuário nesta sessão:

```bash
sudo modprobe uinput
sudo setfacl -m "u:$USER:rw" /dev/uinput
```

Em uma sessão X11, rode:

```bash
python companion/bridge.py --capture x11grab --size 1280x720 --fps 30
```

Em Wayland, tente o backend PipeWire se o FFmpeg instalado tiver essa entrada habilitada:

```bash
python companion/bridge.py --capture pipewire --size 1280x720 --fps 30
```

O áudio tenta usar o monitor do sink padrão via pactl. Para desligar o áudio, acrescente `--no-audio`. A captura via PipeWire depende dos recursos do build do FFmpeg e da sessão gráfica.

Descubra o IP local do PC. No canal Roku, configure o servidor como `http://IP-DO-PC:8765`, valide a conexão e selecione reproduzir. PC e TV devem estar na mesma rede local confiável; libere TCP/8765 no firewall se necessário. O token para enviar comandos é entregue ao app pelo endpoint `/health` e só vale enquanto o companion estiver em execução.

## Gerar o ZIP de sideload

Com `zip` instalado:

```bash
bash scripts/package.sh
```

O arquivo será `dist/steam-link-roku.zip`. Ative o modo de desenvolvedor no Roku e envie esse ZIP pelo Development Application Installer. O companion roda separadamente no PC.