# -*- coding: utf-8 -*-
#!/usr/bin/env python3
# ============================================================
#  consumidores/pagamento.py  -  Consumidor da fila de pagamento
#
#  Processa mensagens de novos pedidos, valida o pagamento
#  e emite ACK (sucesso) ou NACK (falha com retry).
# ============================================================
import pika
import json
import time
import random
import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.conexao import criar_conexao, setup_infraestrutura
from config.settings import FILA_PAGAMENTO, MAX_RETRIES


def validar_pagamento(pedido: dict) -> tuple[bool, str]:
    """
    Simula a validação do pagamento.
    Retorna (aprovado: bool, motivo: str).
    Em produção: integrar com gateway de pagamento (Stripe, PagSeguro, etc.)
    """
    forma = pedido.get("forma_pagamento", "")
    total = pedido.get("total", 0)

    # Simula recusa aleatória (10% de chance) para demonstrar o fluxo de falha
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
    """
    Callback chamado pelo RabbitMQ a cada mensagem recebida.

    Parâmetros:
        canal      - canal RabbitMQ
        method     - metadados de entrega (routing key, delivery tag, etc.)
        properties - propriedades da mensagem (message_id, timestamp, etc.)
        body       - corpo da mensagem em bytes
    """
    try:
        pedido = json.loads(body.decode("utf-8"))
    except json.JSONDecodeError as e:
        # Mensagem corrompida: descarta sem retry (requeue=False >> vai para DLQ)
        print(f"[[ERRO]] Mensagem inválida (JSON corrompido): {e}")
        canal.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
        return

    pedido_id = pedido.get("pedido_id", "N/A")
    cliente   = pedido.get("cliente", {}).get("nome", "N/A")
    total     = pedido.get("total", 0)

    print(f"\n[<<] Mensagem recebida às {datetime.now().strftime('%H:%M:%S')}")
    print(f"    Pedido  : {pedido_id}")
    print(f"    Cliente : {cliente}")
    print(f"    Total   : R$ {total:.2f}")
    print(f"    Pagamento: {pedido.get('forma_pagamento')}")

    # Verifica quantas vezes essa mensagem já foi reentregue
    tentativa = 0
    if properties.headers:
        tentativa = properties.headers.get("x-delivery-count", 0)

    print(f"    Tentativa: {tentativa + 1}/{MAX_RETRIES}")

    # Simula tempo de processamento (integração com gateway)
    time.sleep(1)

    aprovado, motivo = validar_pagamento(pedido)

    if aprovado:
        # ── Sucesso: confirma o processamento ───────────────────────────────
        canal.basic_ack(delivery_tag=method.delivery_tag)
        print(f"    [[OK]] Pagamento APROVADO - {motivo}")

    else:
        # ── Falha: decide entre retry e DLQ ─────────────────────────────────
        print(f"    [[ERRO]] Pagamento RECUSADO - {motivo}")

        if tentativa < MAX_RETRIES - 1:
            # Ainda tem tentativas: recoloca na fila para retry
            print(f"    [[RETRY]] Reenfileirando para nova tentativa...")
            canal.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
        else:
            # Esgotou as tentativas: envia para DLQ sem requeue
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

    # Processa 1 mensagem por vez (fair dispatch)
    # Impede que um worker sobrecarregado receba novas mensagens
    canal.basic_qos(prefetch_count=1)

    canal.basic_consume(
        queue=FILA_PAGAMENTO,
        on_message_callback=processar_mensagem,
        auto_ack=False,   # ACK manual: confirmamos só após processar com sucesso
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
