# -*- coding: utf-8 -*-
#!/usr/bin/env python3
# ============================================================
#  consumidores/estoque.py  -  Consumidor da fila de estoque
#
#  Reserva/baixa os itens do estoque ao receber um pedido.
# ============================================================

import pika  # type: ignore[import]
import json
import time
import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.conexao import criar_conexao, setup_infraestrutura
from config.settings import FILA_ESTOQUE, MAX_RETRIES

# Estoque simulado em memória
ESTOQUE = {
    "P001": 50,
    "P002": 10,
    "P003": 100,
    "P004": 30,
    "P005": 15,
}


_tentativas: dict[str, int] = {}


def reservar_estoque(pedido: dict) -> tuple[bool, str]:
    """
    Verifica disponibilidade e reserva os itens.

    Produtos com ID iniciado em 'CUSTOM-' são pedidos manuais criados
    pelo usuário — tratados como disponíveis, sem controle de saldo.
    """
    produto_id = pedido.get("produto", {}).get("id", "")
    quantidade = pedido.get("quantidade", 1)

    if produto_id.startswith("CUSTOM-"):
        return True, f"Produto manual reservado ({quantidade} unidade(s)) — sem controle de saldo"

    if produto_id not in ESTOQUE:
        return False, f"Produto {produto_id} não encontrado no catálogo"

    disponivel = ESTOQUE[produto_id]
    if disponivel < quantidade:
        return False, f"Estoque insuficiente: {disponivel} disponível, {quantidade} solicitado"

    ESTOQUE[produto_id] -= quantidade
    return True, f"Reservados {quantidade} unidade(s). Saldo atual: {ESTOQUE[produto_id]}"


def processar_mensagem(canal, method, properties, body):
    try:
        pedido = json.loads(body.decode("utf-8"))
    except json.JSONDecodeError as e:
        print(f"[[ERRO]] Mensagem inválida: {e}")
        canal.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
        return

    pedido_id  = pedido.get("pedido_id", "N/A")
    produto    = pedido.get("produto", {})
    qtd        = pedido.get("quantidade", 1)
    message_id = properties.message_id or pedido_id

    print(f"\n[<<] {datetime.now().strftime('%H:%M:%S')} | Pedido: {pedido_id}")
    print(f"    Produto: {produto.get('nome')} (ID: {produto.get('id')}) x{qtd}")


    tentativa = _tentativas.get(message_id, 0)
    print(f"    Tentativa: {tentativa + 1}/{MAX_RETRIES}")

    time.sleep(0.5)

    reservado, motivo = reservar_estoque(pedido)

    if reservado:
        _tentativas.pop(message_id, None)
        canal.basic_ack(delivery_tag=method.delivery_tag)
        print(f"    [[OK]] Estoque RESERVADO - {motivo}")
    else:
        print(f"    [[ERRO]] Falha no estoque - {motivo}")
        if tentativa < MAX_RETRIES - 1:
            _tentativas[message_id] = tentativa + 1
            print(f"    [[RETRY]] Reenfileirando para nova tentativa...")
            canal.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
        else:
            _tentativas.pop(message_id, None)
            print(f"    [[DLQ]] Máximo de tentativas atingido. Enviando para DLQ.")
            canal.basic_nack(delivery_tag=method.delivery_tag, requeue=False)


def main():
    print("=" * 55)
    print("   CONSUMIDOR DE ESTOQUE  -  E-commerce Mensageria")
    print("=" * 55)

    conexao = criar_conexao()
    canal   = conexao.channel()
    setup_infraestrutura(canal)
    canal.basic_qos(prefetch_count=1)
    canal.basic_consume(
        queue=FILA_ESTOQUE,
        on_message_callback=processar_mensagem,
        auto_ack=False,
    )

    print(f"[*] Aguardando mensagens na fila '{FILA_ESTOQUE}'...")
    print("[*] Pressione CTRL+C para encerrar.\n")

    try:
        canal.start_consuming()
    except KeyboardInterrupt:
        print("\n[!] Consumidor encerrado.")
        canal.stop_consuming()

    conexao.close()


if __name__ == "__main__":
    main()
