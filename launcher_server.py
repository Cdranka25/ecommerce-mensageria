# -*- coding: utf-8 -*-
#!/usr/bin/env python3
# ============================================================
#  launcher_server.py  –  Boot da aplicacao web
#
#  Responsabilidade unica: configurar e iniciar o servidor
#  HTTP, servir o dashboard.html e retransmitir eventos via
#  Server-Sent Events (SSE).
#
#  Executar:  python launcher_server.py
#  Acessar:   http://localhost:8080
# ============================================================
import http.server
import json
import threading
import queue
import webbrowser
import os
from urllib.parse import urlparse

from process_manager import ProcessManager

BASE  = os.path.dirname(os.path.abspath(__file__))
PORTA = 8080

_clientes_sse: list[queue.Queue] = []
_lock = threading.Lock()


def _broadcast(evento):
    with _lock:
        mortos = []
        for q in _clientes_sse:
            try:
                q.put_nowait(evento)
            except Exception:
                mortos.append(q)
        for q in mortos:
            _clientes_sse.remove(q)


def _on_log(sid, nome, cor, mensagem, ts):
    _broadcast({"tipo": "log", "id": sid, "nome": nome,
                "cor": cor, "msg": mensagem, "ts": ts})


def _on_status(sid, estado):
    _broadcast({"tipo": "status", "id": sid, "estado": estado})


manager = ProcessManager(on_log=_on_log, on_status=_on_status)


class AppHandler(http.server.BaseHTTPRequestHandler):

    def log_message(self, *args):
        pass

    def do_GET(self):
        rota = urlparse(self.path).path

        if rota in ("/", "/index.html"):
            self._servir_arquivo("dashboard.html", "text/html; charset=utf-8")

        elif rota == "/servicos":
            self._json(manager.servicos())

        elif rota == "/eventos":
            self._sse()

        else:
            caminho = rota.lstrip("/")
            path    = os.path.join(BASE, caminho)

            if os.path.exists(path) and os.path.isfile(path):
                if path.endswith(".css"):
                    ct = "text/css"
                elif path.endswith(".js"):
                    ct = "application/javascript"
                elif path.endswith(".html"):
                    ct = "text/html"
                elif path.endswith(".svg"):
                    ct = "image/svg+xml"
                else:
                    ct = "application/octet-stream"
                self._servir_arquivo(caminho, ct)
            else:
                self.send_error(404)

    def do_POST(self):
        rota = urlparse(self.path).path

        if rota == "/iniciar-consumidores":
            manager.iniciar_consumidores()
            self._json({"ok": True})

        elif rota == "/iniciar-produtor-teste":
            ok, erro = manager.iniciar_produtor_teste()
            self._json({"ok": ok, "erro": erro})

        elif rota == "/iniciar-produtor-manual":
            tamanho = int(self.headers.get("Content-Length", 0))
            corpo   = self.rfile.read(tamanho)
            try:
                dados = json.loads(corpo.decode("utf-8"))
            except json.JSONDecodeError:
                self._json({"ok": False, "erro": "JSON inválido no corpo da requisição."})
                return
            ok, erro = manager.iniciar_produtor_manual(dados)
            self._json({"ok": ok, "erro": erro})

        elif rota == "/parar":
            manager.parar_tudo()
            self._json({"ok": True})

        else:
            self.send_error(404)

    def _sse(self):
        self.send_response(200)
        self.send_header("Content-Type",  "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection",    "keep-alive")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        q = queue.Queue()
        with _lock:
            _clientes_sse.append(q)
        try:
            while True:
                try:
                    evento = q.get(timeout=20)
                    dados  = json.dumps(evento, ensure_ascii=False)
                    self.wfile.write(f"data: {dados}\n\n".encode("utf-8"))
                    self.wfile.flush()
                except queue.Empty:
                    self.wfile.write(b": ping\n\n")
                    self.wfile.flush()
        except Exception:
            pass
        finally:
            with _lock:
                if q in _clientes_sse:
                    _clientes_sse.remove(q)

    def _json(self, dados):
        corpo = json.dumps(dados, ensure_ascii=False).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type",   "application/json")
        self.send_header("Content-Length", str(len(corpo)))
        self.end_headers()
        self.wfile.write(corpo)

    def _servir_arquivo(self, nome, content_type):
        path = os.path.join(BASE, nome)
        with open(path, "rb") as f:
            conteudo = f.read()
        self.send_response(200)
        self.send_header("Content-Type",   content_type)
        self.send_header("Content-Length", str(len(conteudo)))
        self.end_headers()
        self.wfile.write(conteudo)


if __name__ == "__main__":
    servidor = http.server.ThreadingHTTPServer(("localhost", PORTA), AppHandler)
    print(f"[OK] Dashboard rodando em http://localhost:{PORTA}")
    print("[*]  Pressione CTRL+C para encerrar.")
    webbrowser.open(f"http://localhost:{PORTA}")
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        manager.parar_tudo()
        print("\n[!] Servidor encerrado.")
