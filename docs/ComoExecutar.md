## Como Executar o Projeto

### 1. Instalar o Docker

O RabbitMQ será executado em um container Docker.

Acesse o site oficial:
https://www.docker.com/products/docker-desktop/

Baixe o Docker Desktop para o seu sistema operacional e execute o instalador.

Requisitos (Windows):

- Windows 10 ou 11 (64 bits)
- Virtualização ativada na BIOS
- WSL2 (geralmente configurado automaticamente pelo Docker)

Após a instalação, reinicie o computador se necessário.

---

### 2. Verificar instalação do Docker

Abra o terminal (PowerShell, CMD ou terminal do VS Code) e execute:

```bash
docker --version
```

Se aparecer a versão do Docker, está funcionando corretamente.

---

### 3. Subir o RabbitMQ

No terminal, dentro de qualquer pasta, execute:

```bash
docker run -d \
  --name rabbitmq \
  -p 5672:5672 \
  -p 15672:15672 \
  rabbitmq:3-management
```

Esse comando inicia o RabbitMQ com interface web.

---

### 4. Acessar o painel do RabbitMQ

Abra o navegador e acesse:

http://localhost:15672

Login:

- usuário: guest
- senha: guest

---

### 5. Instalar dependências do projeto

No terminal, navegue até a pasta do projeto e execute:

```bash
pip install -r requirements.txt
```

---

### 6. Executar os consumidores

Abra 5 terminais separados e execute um comando em cada:

```bash
# Terminal 1
python consumidores/pagamento.py
```

```bash
# Terminal 2
python consumidores/estoque.py
```

```bash
# Terminal 3
python consumidores/notificacao.py
```

```bash
# Terminal 4
python consumidores/fiscal.py
```

```bash
# Terminal 5
python consumidores/logistica.py
```

Todos devem ficar aguardando mensagens.

---

### 7. Executar o produtor

Abra um sexto terminal e execute:

```bash
python produtor/servico_pedidos.py
```

Esse script irá gerar e enviar pedidos para o RabbitMQ.

---

### 8. Resultado esperado

- Cada consumidor processa os pedidos de forma independente
- As mensagens são distribuídas pelo RabbitMQ
- Os logs aparecem nos terminais

---

### 9. Parar o sistema

Para encerrar:

- Pressione CTRL + C em cada terminal
- Ou pare o container:

```bash
docker stop rabbitmq
```

---

### 10. (Opcional) Executar o dashboard

Se desejar utilizar a interface web:

```bash
python launcher_server.py
```

Acesse:

http://localhost:8080
