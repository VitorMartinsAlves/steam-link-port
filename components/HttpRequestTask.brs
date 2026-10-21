sub init()
    m.top.functionName = "runRequest"
end sub

sub runRequest()
    transfer = CreateObject("roUrlTransfer")
    transfer.SetUrl(m.top.url)
    transfer.SetTimeout(5)

    response = invalid
    if UCase(m.top.method) = "POST" then
        transfer.SetRequest("POST")
        transfer.AddHeader("Content-Type", "application/json")
        response = transfer.PostFromString(m.top.body)
    else
        response = transfer.GetToString()
    end if

    if response = invalid then
        m.top.success = false
        m.top.response = ""
    else
        m.top.success = true
        m.top.response = response
    end if
end sub
