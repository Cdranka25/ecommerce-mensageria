# -*- coding: utf-8 -*-
#!/usr/bin/env python3
# ============================================================
#  consumidores/logistica.py  -  Consumidor de logística
#
#  Agenda a entrega ao receber um pedido confirmado.
#  Em produção: integrar com Correios, Jadlog, Mercado Envios, etc.
# ============================================================
import pika
import json
import time
import uuid
import random
import sys
import os
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.conexao import criar_conexao, setup_infraestrutura
from config.settings import FILA_LOGISTICA

TRANSPORTADORAS = ["Correios PAC", "Correios SEDEX", "Jadlog", "Mercado Envios"]


def agendar_entrega(pedido: dict) -> dict:
    """Simula o agendamento de entrega com uma transportadora."""
    time.sleep(0.7)
    prazo_dias = random.randint(2, 10)
    previsao   = (datetime.now() + timedelta(days=prazo_dias)).strftime("%d/%m/%Y")

    return {
        "codigo_rastreio":  f"BR{uuid.uuid4().hex[:9].upper()}BR",
        "transportadora":   random.choice(TRANSPORTADORAS),
        "prazo_dias":       prazo_dias,
        "previsao_entrega": previsao,
        "endereco":         pedido.get("endereco_entrega", {}),
    }


def processar_mensagem(canal, method, properties, body):
    try:
        pedido = json.loads(body.decode("utf-8"))
    except json.JSONDecodeError as e:
        print(f"[[ERRO]] Mensagem inválida: {e}")
        canal.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
        return

    pedido_id = pedido.get("pedido_id", "N/A")
    endereco  = pedido.get("endereco_entrega", {})
    print(f"\n[<<] {datetime.now().strftime('%H:%M:%S')} | Agendando entrega: {pedido_id}")
    print(f"    Destino: {endereco.get('rua')}, {endereco.get('cidade')}-{endereco.get('estado')}")

    entrega = agendar_entrega(pedido)

    canal.basic_ack(delivery_tag=method.delivery_tag)
    print(f"    [[OK]] Entrega AGENDADA")
    print(f"         Transportadora: {entrega['transportadora']}")
    print(f"         Rastreio      : {entrega['codigo_rastreio']}")
    print(f"         Previsão      : {entrega['previsao_entrega']} ({entrega['prazo_dias']} dias)")


def main():
    print("=" * 55)
    print("   CONSUMIDOR DE LOGÍSTICA  -  E-commerce Mensageria")
    print("=" * 55)

    conexao = criar_conexao()
    canal   = conexao.channel()
    setup_infraestrutura(canal)
    canal.basic_qos(prefetch_count=1)
    canal.basic_consume(
        queue=FILA_LOGISTICA,
        on_message_callback=processar_mensagem,
        auto_ack=False,
    )

    print(f"[*] Aguardando mensagens na fila '{FILA_LOGISTICA}'...")
    print("[*] Pressione CTRL+C para encerrar.\n")

    try:
        canal.start_consuming()
    except KeyboardInterrupt:
        print("\n[!] Consumidor encerrado.")
        canal.stop_consuming()

    conexao.close()


if __name__ == "__main__":
    main()
