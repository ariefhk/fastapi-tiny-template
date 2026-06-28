from fastapi import Request


def request_context(request: Request):
    # ip address
    ip = request.client.host if request.client else None

    # user agent
    ua = request.headers.get("user-agent")

    return {
        "ip": ip,
        "ua": ua,
    }
