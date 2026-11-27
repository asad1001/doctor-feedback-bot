from dashboard.app import app as _dashboard


async def app(scope, receive, send):
    if scope["type"] in ("http", "websocket"):
        path = scope.get("path", "")
        if path == "/api/index" or path.startswith("/api/index/"):
            new = path[len("/api/index"):] or "/"
            scope = dict(scope, path=new, raw_path=new.encode())
    await _dashboard(scope, receive, send)