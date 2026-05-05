# -*- coding: utf-8 -*-
# ============================================================
#  config/settings.py  -  Configurações centrais do RabbitMQ
# ============================================================

RABBITMQ_HOST = "localhost"
RABBITMQ_PORT = 5672
RABBITMQ_USER = "guest"
RABBITMQ_PASS = "guest"
RABBITMQ_VHOST = "/"

# Exchange principal (topic)
EXCHANGE_NAME = "pedidos_exchange"
EXCHANGE_TYPE = "topic"

# Routing keys publicadas pelo produtor
ROUTING_KEY_NOVO_PEDIDO = "pedidos.novo"

# Nomes das filas (duráveis)
FILA_PAGAMENTO   = "q.pagamento"
FILA_ESTOQUE     = "q.estoque"
FILA_NOTIFICACAO = "q.notificacao"
FILA_FISCAL      = "q.fiscal"
FILA_LOGISTICA   = "q.logistica"

# Dead Letter Exchange / Queue
DLX_EXCHANGE = "dlx_exchange"
DLX_QUEUE    = "q.dead_letter"

# Retry: máximo de tentativas antes de ir para DLQ
MAX_RETRIES = 3

# TTL das mensagens nas filas (ms) - 1 hora
MESSAGE_TTL = 3_600_000
