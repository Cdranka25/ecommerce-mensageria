# -*- coding: utf-8 -*-
#!/usr/bin/env python3
# ============================================================
#  produtor/servico_pedidos.py  -  Produtor de mensagens
#
#  Simula o "Serviço de Pedidos" de um e-commerce.
#  Ao receber um novo pedido, publica uma mensagem JSON
#  no RabbitMQ para todos os consumidores interessados.
# ============================================================
import pika
import json
import uuid
import random
import time
import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.conexao import criar_conexao, setup_infraestrutura
from config.settings import EXCHANGE_NAME, ROUTING_KEY_NOVO_PEDIDO


# ── Dados de exemplo para simulação ─────────────────────────
PRODUTOS = [
    {"id": "P001", "nome": "Teclado Mecânico", "preco": 299.90},
    {"id": "P002", "nome": "Monitor 27\"",      "preco": 1499.00},
    {"id": "P003", "nome": "Mouse Gamer",        "preco": 189.90},
    {"id": "P004", "nome": "Headset USB",        "preco": 249.90},
    {"id": "P005", "nome": "Webcam Full HD",     "preco": 349.00},
]

CLIENTES = [
    {"id": "C001", "nome": "Ana Souza",    "email": "ana@email.com"},
    {"id": "C002", "nome": "Bruno Lima",   "email": "bruno@email.com"},
    {"id": "C003", "nome": "Carla Mendes", "email": "carla@email.com"},
]

FORMAS_PAGAMENTO = ["cartao_credito", "pix", "boleto"]


def gerar_pedido() -> dict:
    """Cria um pedido fictício com dados aleatórios."""
    cliente  = random.choice(CLIENTES)
    produto  = random.choice(PRODUTOS)
    qtd      = random.randint(1, 3)
    total    = round(produto["preco"] * qtd, 2)

    return {
        "pedido_id":       str(uuid.uuid4()),
        "timestamp":       datetime.now().isoformat(),
        "cliente":         cliente,
        "produto":         produto,
        "quantidade":      qtd,
        "total":           total,
        "forma_pagamento": random.choice(FORMAS_PAGAMENTO),
        "endereco_entrega": {
            "rua":    "Rua das Flores, 123",
            "cidade": "Blumenau",
            "estado": "SC",
            "cep":    "89000-000",
        },
    }


def publicar_pedido(canal, pedido: dict):
    """Publica a mensagem no RabbitMQ com persistência garantida."""
    mensagem = json.dumps(pedido, ensure_ascii=False, indent=2)

    canal.basic_publish(
        exchange=EXCHANGE_NAME,
        routing_key=ROUTING_KEY_NOVO_PEDIDO,
        body=mensagem.encode("utf-8"),
        properties=pika.BasicProperties(
            delivery_mode=2,               # Mensagem persistente (sobrevive a crash)
            content_type="application/json",
            message_id=pedido["pedido_id"],
            timestamp=int(time.time()),
        ),
    )
    print(f"\n[>>] Pedido publicado: {pedido['pedido_id']}")
    print(f"    Cliente : {pedido['cliente']['nome']}")
    print(f"    Produto : {pedido['produto']['nome']} x{pedido['quantidade']}")
    print(f"    Total   : R$ {pedido['total']:.2f}")
    print(f"    Pagamento: {pedido['forma_pagamento']}")


def main():
    print("=" * 55)
    print("   SERVIÇO DE PEDIDOS  -  E-commerce Mensageria")
    print("=" * 55)

    conexao = criar_conexao()
    canal   = conexao.channel()

    # Garante que toda a infraestrutura existe antes de publicar
    setup_infraestrutura(canal)

    # Publica 5 pedidos com intervalo de 2 segundos entre eles
    total_pedidos = 5
    for i in range(1, total_pedidos + 1):
        print(f"\n── Pedido {i}/{total_pedidos} " + "─" * 30)
        pedido = gerar_pedido()
        publicar_pedido(canal, pedido)
        time.sleep(2)

    conexao.close()
    print(f"\n[[OK]] {total_pedidos} pedidos publicados. Conexão encerrada.")


if __name__ == "__main__":
    main()
