# SKYTICKETservice — Sistema de Agência de Viagens

Sistema web completo para gestão de agência de viagens e turismo:

- **Site público** — pacotes, voos, hotéis, reservas e contacto  
- **Painel admin** — dashboard, CRUD, gestão de reservas e mensagens  

Stack: **Python · Flask · SQLite · HTML/CSS**

---

## Como executar

### 1. Requisitos
- Python 3.10+ instalado

### 2. Instalar dependências

Abra o terminal na pasta `sistema` e execute:

```bash
pip install -r requirements.txt
```

### 3. Iniciar o servidor

```bash
python app.py
```

### 4. Abrir no navegador

| Área | URL |
|------|-----|
| Site | http://127.0.0.1:5000 |
| Admin | http://127.0.0.1:5000/admin |

**Login admin (demo):**
- Utilizador: `admin`
- Senha: `admin123`

**Contactos da agência (site):**
- Responsável: Júnior Jamal
- Telefone / WhatsApp: +258 84 905 3340
- E-mail: skyticketservicee@gmail.com
- Locais: Nampula (Agência Mãe), Maputo, Beira e online
- Horário: 24h / 7 dias

---

## Pesquisa de voos (Fase 2)

Na fase de opções o sistema mostra **dezenas de bilhetes**, ordenados do **mais barato ao mais caro**, com várias companhias, horários e escalas.

### Tarifas em tempo real (Amadeus — opcional)

Para ligar ao GDS Amadeus (tarifas reais de 400+ companhias):

1. Crie conta em [developers.amadeus.com](https://developers.amadeus.com/)
2. Crie uma app Self-Service e copie **API Key** e **API Secret**
3. Defina variáveis de ambiente antes de arrancar o servidor:

```bash
# Windows PowerShell
$env:AMADEUS_CLIENT_ID="a_sua_key"
$env:AMADEUS_CLIENT_SECRET="o_seu_secret"
$env:AMADEUS_ENV="test"   # ou production

python app.py
```

Sem estas chaves, o portal usa o **mercado multi-companhia** (muitas ofertas modeladas por rota/data/classe), sempre ordenadas por preço.

---

## E-mail / SMTP (confirmação e e-ticket)

Após o pagamento, o sistema gera o bilhete electrónico e envia-o para o **e-mail do passageiro principal**.

### Opção A — Painel Admin (mais fácil)

1. Entre em `/admin` → **E-mail / SMTP**
2. Preencha a conta (ex.: `skyticketservicee@gmail.com`)
3. No Gmail: active **2FA** e crie uma [**palavra-passe de aplicação**](https://myaccount.google.com/apppasswords)
4. Cole a app password, guarde e envie um **e-mail de teste**

### Opção B — Variáveis de ambiente

```bash
# Windows PowerShell
$env:SMTP_HOST="smtp.gmail.com"
$env:SMTP_PORT="587"
$env:SMTP_USER="skyticketservicee@gmail.com"
$env:SMTP_PASS="xxxx xxxx xxxx xxxx"   # app password do Gmail
$env:MAIL_FROM="skyticketservicee@gmail.com"
$env:SMTP_ENABLED="1"

python app.py
```

Configuração também em `smtp_config.json` (não partilhe este ficheiro com a password).

### E-mails automáticos ao cliente (From agência)

O remetente é sempre `mail_from` / **SKYTICKETservice** (`skyticketservicee@gmail.com` por omissão):

| Evento | E-mail |
|--------|--------|
| Novo pedido de visto | «Pedido de visto recebido» |
| Admin altera estado do visto | Notificação do novo estado (incl. concluído / cancelado) |
| Admin confirma ou cancela reserva | Confirmação / cancelamento (e-ticket se possível) |
| Booking flow (pagamento) | Confirmação + e-ticket (já existente) |

Se `smtp_config.json` tiver a **password vazia**, o envio falha sem crash — o admin vê um aviso (flash).  
Configure em **Admin → E-mail** uma [Gmail App Password](https://myaccount.google.com/apppasswords) para `skyticketservicee@gmail.com` (conta com 2FA).

---

## Funcionalidades

### Público
- Fluxo de reserva em 6 fases (pesquisa → bilhetes → passageiros → assentos → confirmação → pagamento)
- Dezenas de opções de voo por pesquisa (barato → caro)
- Listagem e detalhe de pacotes turísticos
- Busca de voos por origem/destino
- Hotéis parceiros
- Formulário de reserva com código de confirmação
- Contacto (mensagens guardadas no sistema)
- Página institucional

### Admin
- Dashboard com estatísticas
- CRUD de pacotes e voos
- Lista de clientes
- Gestão de estado das reservas (pendente / confirmada / cancelada)
- Mensagens de contacto

---

## Estrutura

```
sistema/
├── app.py              # Aplicação Flask
├── database.py         # SQLite + dados demo
├── requirements.txt
├── skyticket.db        # Criado no 1º arranque
├── static/
│   ├── css/style.css
│   └── js/app.js
└── templates/
    ├── ...             # Site público
    └── admin/          # Painel
```

---

## Notas

- A base de dados SQLite (`skyticket.db`) é criada automaticamente com dados de exemplo (Moçambique + destinos internacionais).
- Em produção, altere `app.secret_key` em `app.py` e a senha do admin.
- Preços e rotas são demonstrativos (sem integração com GDS/APIs de companhias).

---

© SKYTICKETservice — Agência de Viagens e Turismo
