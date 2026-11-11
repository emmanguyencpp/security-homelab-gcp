import http.server
import socket
import threading

import pytest

import reconkit


@pytest.fixture()
def web_server():
    class H(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.send_header("X-Frame-Options", "DENY")
            self.send_header("X-Powered-By", "Express")
            self.end_headers()
            self.wfile.write(b"ok")

        do_HEAD = do_GET

        def log_message(self, *a):
            pass

    srv = http.server.HTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield srv.server_address[1]
    srv.shutdown()


def test_parse_ports():
    assert reconkit.parse_ports("22,80,8000-8002") == [22, 80, 8000, 8001, 8002]
    assert reconkit.parse_ports("top") == reconkit.TOP_PORTS
    with pytest.raises(ValueError):
        reconkit.parse_ports("70000")


def test_lab_address_guard():
    assert reconkit.is_lab_address("10.10.0.20")
    assert reconkit.is_lab_address("127.0.0.1")
    assert not reconkit.is_lab_address("8.8.8.8")
    with pytest.raises(SystemExit):
        reconkit.check_authorized("8.8.8.8", authorized=False)


def test_scan_finds_open_port(web_server):
    # tìm thêm 1 cổng chắc chắn đóng
    s = socket.socket(); s.bind(("127.0.0.1", 0)); closed = s.getsockname()[1]; s.close()
    res = reconkit.scan("127.0.0.1", [web_server, closed], timeout=0.5, workers=4)
    assert [r.port for r in res] == [web_server]
    assert "HTTP" in res[0].banner


def test_header_audit(web_server):
    rep = reconkit.audit_headers(f"http://127.0.0.1:{web_server}/", timeout=3)
    assert rep.status == 200
    assert "X-Frame-Options" in rep.present
    assert "Content-Security-Policy" in rep.missing
    assert rep.leaks["X-Powered-By"] == "Express"
    assert rep.score == round(100 / 6)
