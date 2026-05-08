# -*- coding: utf-8 -*-
#!/usr/bin/env python3
# ============================================================
#  consumidores/pagamento.py  -  Consumidor da fila de pagamento
#
#  Processa mensagens de novos pedidos, valida o pagamento
#  e emite ACK (sucesso) ou NACK (falha com retry).
# ============================================================

import pika   # type: ignore[import]
import json
import time
import random
import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.conexao import criar_conexao, setup_infraestrutura
from config.settings import FILA_PAGAMENTO, MAX_RETRIES

_tentativas: dict[str, int] = {}


def validar_pagamento(pedido: dict) -> tuple[bool, str]:
    """
    Simula a validação do pagamento.
    Retorna (aprovado: bool, motivo: str).
    """
    forma = pedido.get("forma_pagamento", "")
    total = pedido.get("total", 0)

    # Simula recusa aleatória (10% de chance)
    if random.random() < 0.10:
        return False, "Recusado pela operadora (simulação)"

    if forma == "boleto":
        return True, "Boleto gerado - aguardando compensação"

    if forma == "pix":
        return True, "PIX confirmado instantaneamente"

    if forma == "cartao_credito":
        if total > 5000:
            return False, "Limite de crédito insuficiente"
        return True, "Cartão aprovado"

    return False, f"Forma de pagamento desconhecida: {forma}"


def processar_mensagem(canal, method, properties, body):
    try:
        pedido = json.loads(body.decode("utf-8"))
    except json.JSONDecodeError as e:
        print(f"[[ERRO]] Mensagem inválida (JSON corrompido): {e}")
        canal.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
        return

    pedido_id  = pedido.get("pedido_id", "N/A")
    cliente    = pedido.get("cliente", {}).get("nome", "N/A")
    total      = pedido.get("total", 0)
    message_id = properties.message_id or pedido_id

    print(f"\n[<<] Mensagem recebida às {datetime.now().strftime('%H:%M:%S')}")
    print(f"    Pedido  : {pedido_id}")
    print(f"    Cliente : {cliente}")
    print(f"    Total   : R$ {total:.2f}")
    print(f"    Pagamento: {pedido.get('forma_pagamento')}")

    tentativa = _tentativas.get(message_id, 0)
    print(f"    Tentativa: {tentativa + 1}/{MAX_RETRIES}")

    time.sleep(1)

    aprovado, motivo = validar_pagamento(pedido)

    if aprovado:
        _tentativas.pop(message_id, None)
        canal.basic_ack(delivery_tag=method.delivery_tag)
        print(f"    [[OK]] Pagamento APROVADO - {motivo}")
    else:
        print(f"    [[ERRO]] Pagamento RECUSADO - {motivo}")
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
    print("   CONSUMIDOR DE PAGAMENTO  -  E-commerce Mensageria")
    print("=" * 55)
    print(f"[*] Conectando ao RabbitMQ...")

    conexao = criar_conexao()
    canal   = conexao.channel()
    setup_infraestrutura(canal)
    canal.basic_qos(prefetch_count=1)
    canal.basic_consume(
        queue=FILA_PAGAMENTO,
        on_message_callback=processar_mensagem,
        auto_ack=False,
    )

    print(f"[*] Aguardando mensagens na fila '{FILA_PAGAMENTO}'...")
    print("[*] Pressione CTRL+C para encerrar.\n")

    try:
        canal.start_consuming()
    except KeyboardInterrupt:
        print("\n[!] Consumidor encerrado pelo usuário.")
        canal.stop_consuming()

    conexao.close()


if __name__ == "__main__":
    main()
