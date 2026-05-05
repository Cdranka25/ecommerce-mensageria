# -*- coding: utf-8 -*-
# ============================================================
#  config/conexao.py  -  Conexão e setup da infraestrutura
# ============================================================
import pika
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.settings import (
    RABBITMQ_HOST, RABBITMQ_PORT, RABBITMQ_USER, RABBITMQ_PASS, RABBITMQ_VHOST,
    EXCHANGE_NAME, EXCHANGE_TYPE,
    FILA_PAGAMENTO, FILA_ESTOQUE, FILA_NOTIFICACAO, FILA_FISCAL, FILA_LOGISTICA,
    ROUTING_KEY_NOVO_PEDIDO,
    DLX_EXCHANGE, DLX_QUEUE,
    MESSAGE_TTL,
)


def criar_conexao() -> pika.BlockingConnection:
    """Cria e retorna uma conexão autenticada com o RabbitMQ."""
    credenciais = pika.PlainCredentials(RABBITMQ_USER, RABBITMQ_PASS)
    parametros = pika.ConnectionParameters(
        host=RABBITMQ_HOST,
        port=RABBITMQ_PORT,
        virtual_host=RABBITMQ_VHOST,
        credentials=credenciais,
        heartbeat=60,                    # Mantém conexão viva
        blocked_connection_timeout=300,  # Timeout se broker travar
    )
    return pika.BlockingConnection(parametros)


def setup_infraestrutura(canal: pika.adapters.blocking_connection.BlockingChannel):
    """
    Declara exchanges, filas e bindings.
    Idempotente: pode ser chamado múltiplas vezes sem erro.
    """

    # ── 1. Dead Letter Exchange e Fila ──────────────────────────────────────
    canal.exchange_declare(
        exchange=DLX_EXCHANGE,
        exchange_type="fanout",
        durable=True,
    )
    canal.queue_declare(
        queue=DLX_QUEUE,
        durable=True,
    )
    canal.queue_bind(queue=DLX_QUEUE, exchange=DLX_EXCHANGE)

    # ── 2. Exchange principal (topic) ────────────────────────────────────────
    canal.exchange_declare(
        exchange=EXCHANGE_NAME,
        exchange_type=EXCHANGE_TYPE,
        durable=True,           # Sobrevive a reinicializações do broker
    )

    # ── 3. Argumentos padrão aplicados a todas as filas ─────────────────────
    args_fila = {
        "x-dead-letter-exchange": DLX_EXCHANGE,  # Redireciona falhas para DLQ
        "x-message-ttl": MESSAGE_TTL,             # Expira mensagem após 1 hora
    }

    # ── 4. Declaração das filas duráveis ────────────────────────────────────
    filas = [
        FILA_PAGAMENTO,
        FILA_ESTOQUE,
        FILA_NOTIFICACAO,
        FILA_FISCAL,
        FILA_LOGISTICA,
    ]
    for nome_fila in filas:
        canal.queue_declare(
            queue=nome_fila,
            durable=True,       # Persiste mesmo se o RabbitMQ reiniciar
            arguments=args_fila,
        )

    # ── 5. Bindings: conecta a exchange às filas via routing key ────────────
    #   "pedidos.#" = qualquer routing key que comece com "pedidos."
    for nome_fila in filas:
        canal.queue_bind(
            queue=nome_fila,
            exchange=EXCHANGE_NAME,
            routing_key=ROUTING_KEY_NOVO_PEDIDO,
        )

    print("[[OK]] Infraestrutura RabbitMQ configurada com sucesso.")
