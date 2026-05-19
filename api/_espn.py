import urllib.request
import urllib.error

_HEADERS = {
    "User-Agent": "Mozilla/5.0 CourtsideAnalyticsVercel/1.0",
    "Accept": "application/json",
}


def proxy(handler, url):
    req = urllib.request.Request(url, headers=_HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=12) as r:
            body = r.read()
        status = 200
    except urllib.error.HTTPError as e:
        body = f'{{"error":"{e}"}}'.encode()
        status = e.code
    except Exception as e:
        body = f'{{"error":"{e}"}}'.encode()
        status = 502
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Cache-Control", "public, max-age=45")
    handler.end_headers()
    handler.wfile.write(body)
