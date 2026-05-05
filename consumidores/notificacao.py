# -*- coding: utf-8 -*-
#!/usr/bin/env python3
# ============================================================
#  consumidores/notificacao.py  -  Consumidor de notificação
#
#  Envia e-mail/SMS de confirmação ao cliente após o pedido.
#  Em produção: integrar com SendGrid, AWS SES, Twilio, etc.
# ============================================================
import pika
import json
import time
import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.conexao import criar_conexao, setup_infraestrutura
from config.settings import FILA_NOTIFICACAO


def simular_envio_email(pedido: dict) -> bool:
    """
    Simula o envio de e-mail de confirmação.
    Em produção: usar smtplib ou SDK do SendGrid/AWS SES.
    """
    cliente = pedido.get("cliente", {})
    produto = pedido.get("produto", {})

    print(f"    [[EMAIL]] Enviando e-mail para: {cliente.get('email')}")
    print(f"         Assunto: Pedido {pedido['pedido_id'][:8]}... confirmado!")
    print(f"         Corpo: Olá {cliente.get('nome')}, seu pedido de")
    print(f"                {produto.get('nome')} foi recebido.")
    print(f"                Total: R$ {pedido.get('total', 0):.2f}")
    time.sleep(0.8)
    return True


def processar_mensagem(canal, method, properties, body):
    try:
        pedido = json.loads(body.decode("utf-8"))
    except json.JSONDecodeError as e:
        print(f"[[ERRO]] Mensagem inválida: {e}")
        canal.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
        return

    pedido_id = pedido.get("pedido_id", "N/A")
    print(f"\n[<<] {datetime.now().strftime('%H:%M:%S')} | Notificando pedido: {pedido_id}")

    enviado = simular_envio_email(pedido)

    if enviado:
        canal.basic_ack(delivery_tag=method.delivery_tag)
        print(f"    [[OK]] Notificação ENVIADA com sucesso.")
    else:
        canal.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
        print(f"    [[ERRO]] Falha no envio. Reenfileirando...")


def main():
    print("=" * 55)
    print("   CONSUMIDOR DE NOTIFICAÇÃO  -  E-commerce Mensageria")
    print("=" * 55)

    conexao = criar_conexao()
    canal   = conexao.channel()
    setup_infraestrutura(canal)
    canal.basic_qos(prefetch_count=1)
    canal.basic_consume(
        queue=FILA_NOTIFICACAO,
        on_message_callback=processar_mensagem,
        auto_ack=False,
    )

    print(f"[*] Aguardando mensagens na fila '{FILA_NOTIFICACAO}'...")
    print("[*] Pressione CTRL+C para encerrar.\n")

    try:
        canal.start_consuming()
    except KeyboardInterrupt:
        print("\n[!] Consumidor encerrado.")
        canal.stop_consuming()

    conexao.close()


if __name__ == "__main__":
    main()
