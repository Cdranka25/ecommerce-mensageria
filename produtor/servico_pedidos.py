# -*- coding: utf-8 -*-
#!/usr/bin/env python3
# ============================================================
#  produtor/servico_pedidos.py  -  Produtor de pedido REAL
#
#  Publica UM único pedido com dados fornecidos pelo usuário
#  via argumento JSON na linha de comando.
#
#  Uso:
#      python produtor/servico_pedidos.py '<json_do_pedido>'
#
#  O JSON deve conter os campos:
#      cliente_nome, cliente_email,
#      produto_nome, produto_preco,
#      quantidade, forma_pagamento,
#      endereco_rua, endereco_cidade, endereco_estado, endereco_cep
# ============================================================
import pika
import json
import uuid
import time
import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.conexao import criar_conexao, setup_infraestrutura
from config.settings import EXCHANGE_NAME, ROUTING_KEY_NOVO_PEDIDO


def montar_pedido(dados: dict) -> dict:
    """Constrói o payload de pedido a partir dos dados fornecidos pelo usuário."""
    preco = float(dados.get("produto_preco", 0))
    qtd   = int(dados.get("quantidade", 1))

    return {
        "pedido_id":  str(uuid.uuid4()),
        "timestamp":  datetime.now().isoformat(),
        "cliente": {
            "id":    str(uuid.uuid4())[:8].upper(),
            "nome":  dados.get("cliente_nome", ""),
            "email": dados.get("cliente_email", ""),
        },
        "produto": {
            "id":    f"CUSTOM-{str(uuid.uuid4())[:6].upper()}",
            "nome":  dados.get("produto_nome", ""),
            "preco": preco,
        },
        "quantidade":       qtd,
        "total":            round(preco * qtd, 2),
        "forma_pagamento":  dados.get("forma_pagamento", "pix"),
        "endereco_entrega": {
            "rua":    dados.get("endereco_rua", ""),
            "cidade": dados.get("endereco_cidade", ""),
            "estado": dados.get("endereco_estado", ""),
            "cep":    dados.get("endereco_cep", ""),
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
            delivery_mode=2,
            content_type="application/json",
            message_id=pedido["pedido_id"],
            timestamp=int(time.time()),
        ),
    )
    print(f"\n[>>] Pedido publicado: {pedido['pedido_id']}")
    print(f"    Cliente  : {pedido['cliente']['nome']} <{pedido['cliente']['email']}>")
    print(f"    Produto  : {pedido['produto']['nome']} x{pedido['quantidade']}")
    print(f"    Total    : R$ {pedido['total']:.2f}")
    print(f"    Pagamento: {pedido['forma_pagamento']}")
    print(f"    Endereço : {pedido['endereco_entrega']['rua']}, "
          f"{pedido['endereco_entrega']['cidade']}-{pedido['endereco_entrega']['estado']}")


def main():
    print("=" * 55)
    print("   SERVIÇO DE PEDIDOS  -  E-commerce Mensageria")
    print("=" * 55)

    if len(sys.argv) < 2:
        print("[ERRO] Nenhum dado de pedido fornecido.")
        print("Uso: python produtor/servico_pedidos.py '<json>'")
        sys.exit(1)

    try:
        dados = json.loads(sys.argv[1])
    except json.JSONDecodeError as e:
        print(f"[ERRO] JSON inválido: {e}")
        sys.exit(1)

    pedido  = montar_pedido(dados)
    conexao = criar_conexao()
    canal   = conexao.channel()
    setup_infraestrutura(canal)
    publicar_pedido(canal, pedido)
    conexao.close()
    print("\n[[OK]] Pedido publicado com sucesso. Conexão encerrada.")


if __name__ == "__main__":
    main()
