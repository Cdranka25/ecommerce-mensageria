# -*- coding: utf-8 -*-
#!/usr/bin/env python3
# ============================================================
#  process_manager.py  –  Gerenciador de processos
#
#  Responsabilidade única: iniciar, parar e monitorar
#  os subprocessos Python de cada serviço.
#  Não contém nenhuma lógica de UI ou servidor HTTP.
# ============================================================
import subprocess
import threading
import sys
import os
from datetime import datetime

BASE = os.path.dirname(os.path.abspath(__file__))

SERVICOS = [
    {"id": "pagamento",   "nome": "Pagamento",   "script": "consumidores/pagamento.py",   "cor": "#22c55e", "icone": "💳", "tipo": "consumidor"},
    {"id": "estoque",     "nome": "Estoque",      "script": "consumidores/estoque.py",     "cor": "#3b82f6", "icone": "📦", "tipo": "consumidor"},
    {"id": "notificacao", "nome": "Notificacao",  "script": "consumidores/notificacao.py", "cor": "#f59e0b", "icone": "📧", "tipo": "consumidor"},
    {"id": "fiscal",      "nome": "Nota Fiscal",  "script": "consumidores/fiscal.py",      "cor": "#a855f7", "icone": "🧾", "tipo": "consumidor"},
    {"id": "logistica",   "nome": "Logistica",    "script": "consumidores/logistica.py",   "cor": "#06b6d4", "icone": "🚚", "tipo": "consumidor"},
    {"id": "pedidos",     "nome": "Pedidos",      "script": "produtor/servico_pedidos.py", "cor": "#ef4444", "icone": "🛒", "tipo": "produtor"},
    {"id": "pedidos_teste", "nome": "Pedidos Teste", "script": "produtor/servico_pedidos_teste.py", "cor": "#f97316", "icone": "🧪", "tipo": "produtor_teste"},
]


class ProcessManager:
    """
    Gerencia o ciclo de vida dos subprocessos do sistema de mensageria.

    Callbacks disponíveis:
        on_log(id, nome, cor, mensagem, timestamp) -> None
        on_status(id, estado) -> None   estado: 'rodando' | 'parado'
    """

    def __init__(self, on_log=None, on_status=None):
        self._processos: dict[str, subprocess.Popen] = {}
        self._iniciados: set[str] = set()
        self._on_log    = on_log    or (lambda *a: None)
        self._on_status = on_status or (lambda *a: None)

    # API pública ──────────────────────────────────────────

    def iniciar_consumidores(self):
        """Inicia todos os serviços do tipo consumidor."""
        for srv in self._consumidores():
            self._iniciar(srv)

    def iniciar_produtor_teste(self) -> tuple[bool, str]:
        """
        Inicia o produtor de teste (5 pedidos aleatórios).
        Retorna (sucesso, mensagem_de_erro).
        """
        if not self._consumidores_ativos():
            return False, "Inicie os consumidores antes de enviar pedidos."
        self._iniciar(self._produtor_teste())
        return True, ""

    def iniciar_produtor_manual(self, dados_pedido: dict) -> tuple[bool, str]:
        """
        Inicia o produtor manual com os dados fornecidos pelo usuário.
        Passa o JSON do pedido como argumento para o script.
        Retorna (sucesso, mensagem_de_erro).
        """
        import json as _json

        if not self._consumidores_ativos():
            return False, "Inicie os consumidores antes de enviar pedidos."

        srv = self._produtor_manual()
        sid = srv["id"]

        if sid in self._processos and self._processos[sid].poll() is None:
            pass

        env = os.environ.copy()
        env["PYTHONUTF8"]       = "1"
        env["PYTHONIOENCODING"] = "utf-8"

        json_pedido = _json.dumps(dados_pedido, ensure_ascii=False)

        proc = subprocess.Popen(
            [sys.executable, "-u", os.path.join(BASE, srv["script"]), json_pedido],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            encoding="utf-8",
            errors="replace",
            cwd=BASE,
            env=env,
        )

        self._processos[sid] = proc
        self._iniciados.add(sid)
        self._on_status(sid, "rodando")

        threading.Thread(
            target=self._ler_stdout,
            args=(proc, srv),
            daemon=True,
        ).start()

        return True, ""

    def parar_tudo(self):
        """Encerra todos os subprocessos em execução."""
        for sid in list(self._processos.keys()):
            self._parar(sid)

    def parar(self, sid: str):
        """Encerra um subprocesso específico pelo seu ID."""
        self._parar(sid)

    def servicos(self) -> list[dict]:
        """Retorna a lista de definições de serviços (para o servidor HTTP expor ao frontend)."""
        return SERVICOS

    def consumidores_iniciados(self) -> bool:
        return self._consumidores_ativos()

    def _iniciar(self, srv: dict):
        sid = srv["id"]
        if sid in self._processos and self._processos[sid].poll() is None:
            return  

        env = os.environ.copy()
        env["PYTHONUTF8"]        = "1"
        env["PYTHONIOENCODING"]  = "utf-8"

        proc = subprocess.Popen(
            [sys.executable, "-u", os.path.join(BASE, srv["script"])],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            encoding="utf-8",
            errors="replace",
            cwd=BASE,
            env=env,
        )

        self._processos[sid] = proc
        self._iniciados.add(sid)
        self._on_status(sid, "rodando")

        threading.Thread(
            target=self._ler_stdout,
            args=(proc, srv),
            daemon=True,
        ).start()

    def _parar(self, sid: str):
        proc = self._processos.pop(sid, None)
        if proc:
            try:
                proc.terminate()
            except Exception:
                pass
        self._on_status(sid, "parado")

    def _ler_stdout(self, proc: subprocess.Popen, srv: dict):
        """Lê linha a linha o stdout do processo e dispara o callback on_log."""
        sid = srv["id"]
        try:
            stdout = proc.stdout
            if stdout is None:
                proc.wait()
                return

            for linha in stdout:
                linha = linha.rstrip()
                if linha:
                    self._on_log(
                        sid,
                        srv["nome"],
                        srv["cor"],
                        linha,
                        datetime.now().strftime("%H:%M:%S"),
                    )
            proc.wait()
        except Exception as e:
            self._on_log(sid, srv["nome"], srv["cor"], f"[ERRO] {e}",
                         datetime.now().strftime("%H:%M:%S"))
        finally:
            self._on_status(sid, "parado")

    def _consumidores(self) -> list[dict]:
        return [s for s in SERVICOS if s["tipo"] == "consumidor"]

    def _consumidores_ativos(self) -> bool:
        ids_consumidores = {s["id"] for s in self._consumidores()}
        return bool(self._iniciados.intersection(ids_consumidores))

    def _produtor_manual(self) -> dict:
        return next(s for s in SERVICOS if s["tipo"] == "produtor")

    def _produtor_teste(self) -> dict:
        return next(s for s in SERVICOS if s["tipo"] == "produtor_teste")
