sub init()
    m.registry = CreateObject("roRegistrySection", "SteamLinkRokuBridge")
    m.baseUrl = m.registry.Read("baseUrl")
    if m.baseUrl = invalid or m.baseUrl = "" then m.baseUrl = "http://192.168.1.100:8765"

    m.streamUrl = m.registry.Read("streamUrl")
    if m.streamUrl = invalid or m.streamUrl = "" then m.streamUrl = m.baseUrl + "/stream.m3u8"

    m.isPlaying = false
    m.pendingAction = ""
    m.healthTask = invalid
    m.keyboardDialog = invalid
    m.keyboardTarget = ""

    m.serverLabel = m.top.FindNode("serverLabel")
    m.streamLabel = m.top.FindNode("streamLabel")
    m.statusLabel = m.top.FindNode("statusLabel")
    m.setupGroup = m.top.FindNode("setupGroup")
    m.video = m.top.FindNode("video")
    m.playbackHelp = m.top.FindNode("playbackHelp")

    m.top.FindNode("configureHostButton").ObserveField("buttonSelected", "onConfigureHost")
    m.top.FindNode("configureStreamButton").ObserveField("buttonSelected", "onConfigureStream")
    m.top.FindNode("testButton").ObserveField("buttonSelected", "onTestConnection")
    m.top.FindNode("playButton").ObserveField("buttonSelected", "onPlayStream")
    m.video.ObserveField("state", "onVideoStateChanged")

    renderConfig()
    m.top.FindNode("configureHostButton").SetFocus(true)
end sub

sub renderConfig()
    m.serverLabel.Text = "Servidor: " + m.baseUrl
    m.streamLabel.Text = "Stream HLS: " + m.streamUrl
end sub

sub setStatus(message as String, success as Boolean)
    m.statusLabel.Text = message
    if success then
        m.statusLabel.Color = &h7DFFB2FF
    else
        m.statusLabel.Color = &hFFD166FF
    end if
end sub

sub onConfigureHost()
    openKeyboard("host")
end sub

sub onConfigureStream()
    openKeyboard("stream")
end sub

sub openKeyboard(target as String)
    m.keyboardTarget = target
    m.keyboardDialog = CreateObject("roSGNode", "KeyboardDialog")
    m.keyboardDialog.buttons = ["Salvar", "Cancelar"]
    m.keyboardDialog.optionsDialog = false
    m.keyboardDialog.observeField("buttonSelected", "onKeyboardSelected")

    if target = "host" then
        m.keyboardDialog.title = "Servidor do PC"
        m.keyboardDialog.message = "Digite a URL base, incluindo http:// e a porta. Ex.: http://192.168.1.20:8765"
        m.keyboardDialog.text = m.baseUrl
    else
        m.keyboardDialog.title = "URL do stream HLS"
        m.keyboardDialog.message = "Informe uma URL HLS acessível pela Roku, normalmente terminada em .m3u8."
        m.keyboardDialog.text = m.streamUrl
    end if

    m.top.dialog = m.keyboardDialog
end sub

sub onKeyboardSelected()
    if m.keyboardDialog = invalid then return

    if m.keyboardDialog.buttonSelected = 0 then
        value = Trim(m.keyboardDialog.text)
        if value = "" then
            setStatus("O valor não pode ficar vazio.", false)
        else if m.keyboardTarget = "host" then
            if not isHttpUrl(value) then
                setStatus("URL do servidor inválida. Use http:// ou https://.", false)
            else if Instr(1, value, " ") > 0 then
                setStatus("A URL do servidor não pode conter espaços.", false)
            else
                oldDefaultStream = m.baseUrl + "/stream.m3u8"
                m.baseUrl = removeTrailingSlash(value)
                if m.streamUrl = oldDefaultStream then m.streamUrl = m.baseUrl + "/stream.m3u8"
                m.registry.Write("baseUrl", m.baseUrl)
                m.registry.Flush()
                renderConfig()
                setStatus("Servidor salvo. Valide a conexão antes de reproduzir.", true)
            end if
        else if m.keyboardTarget = "stream" then
            if not isHttpUrl(value) then
                setStatus("URL HLS inválida. Use http:// ou https://.", false)
            else if Instr(1, value, " ") > 0 then
                setStatus("A URL do stream não pode conter espaços.", false)
            else
                m.streamUrl = value
                m.registry.Write("streamUrl", m.streamUrl)
                m.registry.Flush()
                renderConfig()
                setStatus("URL do stream salva.", true)
            end if
        end if
    end if

    m.top.dialog = invalid
    m.keyboardDialog = invalid
    m.top.FindNode("configureHostButton").SetFocus(true)
end sub

function isHttpUrl(value as String) as Boolean
    lowerValue = LCase(value)
    return Left(lowerValue, 7) = "http://" or Left(lowerValue, 8) = "https://"
end function

function removeTrailingSlash(value as String) as String
    result = value
    while Len(result) > 0 and Right(result, 1) = "/"
        result = Left(result, Len(result) - 1)
    end while
    return result
end function

sub onTestConnection()
    m.pendingAction = "test"
    requestHealth()
end sub

sub requestHealth()
    if not isHttpUrl(m.baseUrl) then
        setStatus("Configure primeiro uma URL de servidor válida.", false)
        return
    end if

    if m.healthTask <> invalid then
        setStatus("Uma verificação já está em andamento.", false)
        return
    end if

    setStatus("Validando " + m.baseUrl + "/health ...", true)
    m.healthTask = CreateObject("roSGNode", "HttpRequestTask")
    m.healthTask.url = m.baseUrl + "/health"
    m.healthTask.method = "GET"
    m.healthTask.body = ""
    m.healthTask.ObserveField("response", "onHealthResponse")
    m.top.AppendChild(m.healthTask)
    m.healthTask.Control = "RUN"
end sub

sub onHealthResponse()
    if m.healthTask = invalid then return

    task = m.healthTask
    response = task.response
    succeeded = task.success

    if succeeded and response <> "" then
        parsed = ParseJson(response)
        if parsed = invalid then
            succeeded = false
            setStatus("/health respondeu, mas não retornou JSON válido.", false)
        else if parsed.ok <> true then
            succeeded = false
            setStatus("O servidor respondeu, mas não confirmou {""ok"":true}.", false)
        else
            if parsed.stream <> invalid and parsed.stream <> "" then
                if isHttpUrl(parsed.stream) then
                    m.streamUrl = parsed.stream
                else if Left(parsed.stream, 1) = "/" then
                    m.streamUrl = m.baseUrl + parsed.stream
                end if
                renderConfig()
            end if
        end if
    else
        succeeded = false
        setStatus("Sem resposta em " + m.baseUrl + "/health. Confira IP, porta, firewall e rede.", false)
    end if

    m.top.RemoveChild(task)
    m.healthTask = invalid

    if succeeded then
        if m.pendingAction = "play" then
            startPlayback()
        else
            setStatus("Servidor validado. Endpoint /health respondeu corretamente.", true)
        end if
    end if
    m.pendingAction = ""
end sub

sub onPlayStream()
    m.pendingAction = "play"
    requestHealth()
end sub

sub startPlayback()
    content = CreateObject("roSGNode", "ContentNode")
    content.Url = m.streamUrl
    content.StreamFormat = "hls"
    m.video.Content = content
    m.video.Visible = true
    m.setupGroup.Visible = false
    m.playbackHelp.Visible = true
    m.isPlaying = true
    m.video.Control = "play"
    m.video.SetFocus(true)
    setStatus("Solicitando reprodução do stream HLS...", true)
end sub

sub onVideoStateChanged()
    state = m.video.State
    if state = "error" then
        stopPlayback()
        setStatus("Falha ao reproduzir. Verifique se a URL retorna HLS compatível com Roku.", false)
    else if state = "playing" then
        setStatus("Stream em reprodução. Use BACK para voltar.", true)
    end if
end sub

sub stopPlayback()
    m.video.Control = "stop"
    m.video.Visible = false
    m.playbackHelp.Visible = false
    m.setupGroup.Visible = true
    m.isPlaying = false
    m.top.FindNode("configureHostButton").SetFocus(true)
end sub

sub sendInput(keyName as String, pressed as Boolean)
    ' Best-effort bridge for a companion host server. Roku remotes are not gamepads;
    ' this cannot provide analog sticks, triggers, or native Steam Input.
    task = CreateObject("roSGNode", "HttpRequestTask")
    task.url = m.baseUrl + "/input"
    task.method = "POST"
    pressText = "false"
    if pressed then pressText = "true"
    body = "{" + Chr(34) + "key" + Chr(34) + ":" + Chr(34) + keyName + Chr(34) + "," + Chr(34) + "pressed" + Chr(34) + ":" + pressText + "}"
    task.body = body
    task.ObserveField("state", "onInputTaskState")
    m.top.AppendChild(task)
    task.Control = "RUN"
end sub

sub onInputTaskState(event as Object)
    task = event.GetRoSGNode()
    if task <> invalid and task.State = "stop" then
        m.top.RemoveChild(task)
    end if
end sub

function onKeyEvent(key as String, press as Boolean) as Boolean
    if not press then
        if m.isPlaying and isForwardedKey(key) then
            sendInput(key, false)
            return true
        end if
        return false
    end if

    if m.isPlaying then
        if key = "back" then
            stopPlayback()
            return true
        end if

        if isForwardedKey(key) then
            sendInput(key, true)
            return true
        end if
    end if

    return false
end function

function isForwardedKey(key as String) as Boolean
    return key = "up" or key = "down" or key = "left" or key = "right" or key = "OK" or key = "play" or key = "pause" or key = "rewind" or key = "fastforward"
end function
