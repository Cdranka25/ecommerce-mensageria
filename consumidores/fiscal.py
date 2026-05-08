# -*- coding: utf-8 -*-
#!/usr/bin/env python3
# ============================================================
#  consumidores/fiscal.py  -  Consumidor de nota fiscal
#
#  Gera o documento fiscal (NF-e) ao receber um pedido.
#  Em produção: integrar com SEFAZ via biblioteca nfeio ou similar.
# ============================================================

import pika  # type: ignore[import]
import json
import time
import uuid
import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.conexao import criar_conexao, setup_infraestrutura
from config.settings import FILA_FISCAL


def gerar_nota_fiscal(pedido: dict) -> dict:
    """
    Simula a emissão de uma NF-e.
    Em produção: chamar API da SEFAZ com certificado digital.
    """
    time.sleep(1.2)
    return {
        "nfe_id":      str(uuid.uuid4()),
        "chave_acesso": "".join([str(uuid.uuid4().int)[:44]]),
        "emissao":     datetime.now().isoformat(),
        "pedido_id":   pedido["pedido_id"],
        "valor_total": pedido.get("total", 0),
        "status":      "autorizada",
    }


def processar_mensagem(canal, method, properties, body):
    try:
        pedido = json.loads(body.decode("utf-8"))
    except json.JSONDecodeError as e:
        print(f"[[ERRO]] Mensagem inválida: {e}")
        canal.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
        return

    pedido_id = pedido.get("pedido_id", "N/A")
    print(f"\n[<<] {datetime.now().strftime('%H:%M:%S')} | Emitindo NF-e para pedido: {pedido_id}")
    print(f"    Valor: R$ {pedido.get('total', 0):.2f}")

    nfe = gerar_nota_fiscal(pedido)

    canal.basic_ack(delivery_tag=method.delivery_tag)
    print(f"    [[OK]] NF-e EMITIDA - Chave: {nfe['chave_acesso'][:20]}...")
    print(f"         Status: {nfe['status']}")


def main():
    print("=" * 55)
    print("   CONSUMIDOR FISCAL  -  E-commerce Mensageria")
    print("=" * 55)

    conexao = criar_conexao()
    canal   = conexao.channel()
    setup_infraestrutura(canal)
    canal.basic_qos(prefetch_count=1)
    canal.basic_consume(
        queue=FILA_FISCAL,
        on_message_callback=processar_mensagem,
        auto_ack=False,
    )

    print(f"[*] Aguardando mensagens na fila '{FILA_FISCAL}'...")
    print("[*] Pressione CTRL+C para encerrar.\n")

    try:
        canal.start_consuming()
    except KeyboardInterrupt:
        print("\n[!] Consumidor encerrado.")
        canal.stop_consuming()

    conexao.close()


if __name__ == "__main__":
    main()
