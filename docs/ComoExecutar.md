## Como Executar o Projeto (VS Code)

### 1. Instalar o Docker

O RabbitMQ será executado em um container Docker.

Acesse o site oficial:
https://www.docker.com/products/docker-desktop/

Baixe e instale o Docker Desktop. Reinicie o computador se necessário.

---

### 2. Verificar instalação do Docker

Abra o **VS Code**.

Abra o terminal:

```
Terminal → Novo Terminal
```

Execute:

```bash
docker --version
```

Se aparecer a versão, está funcionando.

---

### 3. Subir o RabbitMQ

No terminal do VS Code, execute:

```bash
docker run -d --name rabbitmq -p 5672:5672 -p 15672:15672 rabbitmq:3-management
```

---

### 4. Acessar o painel do RabbitMQ

Abra no navegador:

http://localhost:15672

Login:

* usuário: guest
* senha: guest

---

### 5. Instalar dependências

No terminal do VS Code, dentro da pasta do projeto:

```bash
pip install pika
```

---

### 6. Executar o dashboard (modo manual)

No terminal:

```bash
python launcher_server.py
```

Abra:

http://localhost:8080

