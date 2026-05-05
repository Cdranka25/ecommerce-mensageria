# E-commerce Mensageria com RabbitMQ
**Trabalho Prático – Sistemas Distribuídos | FURB**

Sistema de pedidos de e-commerce com comunicação assíncrona via RabbitMQ.

---

## Pré-requisitos

- Python 3.10+
- Docker (para o RabbitMQ)

---

## 1. Subir o RabbitMQ com Docker

```bash
docker run -d \
  --name rabbitmq \
  -p 5672:5672 \
  -p 15672:15672 \
  rabbitmq:3-management
```

Interface web: http://localhost:15672  
Login: `guest` | Senha: `guest`

---

## 2. Instalar dependências Python

```bash
pip install -r requirements.txt
```

---

## 3. Executar os consumidores (em terminais separados)

```bash
# Terminal 1 – Pagamento
python consumidores/pagamento.py

# Terminal 2 – Estoque
python consumidores/estoque.py

# Terminal 3 – Notificação
python consumidores/notificacao.py

# Terminal 4 – Nota Fiscal
python consumidores/fiscal.py

# Terminal 5 – Logística
python consumidores/logistica.py
```

---

## 4. Publicar pedidos (produtor)

```bash
# Terminal 6
python produtor/servico_pedidos.py
```

Publica 5 pedidos simulados. Cada consumidor processa em paralelo.

---

## Estrutura do projeto

```
ecommerce-mensageria/
├── config/
│   ├── settings.py       # Parâmetros de conexão e nomes de filas
│   └── conexao.py        # Fábrica de conexão + setup da infraestrutura
├── produtor/
│   └── servico_pedidos.py  # Publica mensagens de novos pedidos
├── consumidores/
│   ├── pagamento.py      # Valida e processa pagamento
│   ├── estoque.py        # Reserva itens no estoque
│   ├── notificacao.py    # Envia e-mail/SMS ao cliente
│   ├── fiscal.py         # Emite nota fiscal
│   └── logistica.py      # Agenda entrega
└── requirements.txt
```

---

## Arquitetura de mensagens

```
Cliente → [HTTP POST] → Serviço de Pedidos (Produtor)
                              ↓
                    Exchange: pedidos_exchange (topic)
                    Routing key: pedidos.novo
                              ↓ (fan-out para todas as filas)
          ┌───────────────────┼───────────────────┐
     q.pagamento        q.estoque           q.notificacao   ...
          ↓                  ↓                    ↓
    Pagamento           Estoque            Notificação       ...
    (consumer)         (consumer)          (consumer)

    Falha após 3 tentativas → Dead Letter Queue (q.dead_letter)
```

---

## Boas práticas implementadas

| Prática | Implementação |
|---|---|
| Persistência | `delivery_mode=2` + filas `durable=True` |
| ACK manual | `auto_ack=False` em todos os consumidores |
| Fair dispatch | `basic_qos(prefetch_count=1)` |
| Dead Letter Queue | `x-dead-letter-exchange` em todas as filas |
| TTL de mensagens | `x-message-ttl = 3.600.000 ms` (1 hora) |
| Retry | NACK com `requeue=True` até `MAX_RETRIES` |
| Formato | JSON UTF-8 com `message_id` único por pedido |
