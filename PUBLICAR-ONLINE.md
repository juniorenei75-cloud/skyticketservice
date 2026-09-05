# Publicar a SKYTICKETservice na Internet

Objectivo: o site funcionar em **qualquer telemóvel ou PC do mundo**,  
**sem precisar do seu computador ligado**.

---

## O que muda

| Antes (agora) | Depois (online) |
|---------------|-----------------|
| Só no seu PC ou Wi‑Fi de casa | Qualquer rede / dados móveis |
| Precisa de `python app.py` no PC | Corre num servidor 24h |
| Link tipo `192.168.x.x:5000` | Link tipo `https://skyticketservice.onrender.com` |

---

## Método recomendado: Render.com (grátis)

### 1. Conta GitHub (se ainda não tiver)
1. Vá a https://github.com  
2. Crie conta gratuita  
3. Crie um repositório novo, por exemplo: `skyticketservice`  
4. Envie a pasta `Portal-SKYTICKET` para esse repositório  

(Se quiser, peça ajuda no Grok para fazer o `git init` e o push.)

### 2. Conta Render
1. Vá a https://render.com  
2. **Sign Up** com a conta GitHub  
3. **New +** → **Web Service**  
4. Ligue o repositório `skyticketservice`  

### 3. Definições no Render

| Campo | Valor |
|--------|--------|
| **Name** | `skyticketservice` |
| **Region** | a mais próxima (ex.: Frankfurt) |
| **Runtime** | Python |
| **Build Command** | `pip install -r requirements.txt` |
| **Start Command** | `gunicorn app:app --bind 0.0.0.0:$PORT` |
| **Instance** | Free |

**Environment Variables** (Environment):
- `SECRET_KEY` = uma frase longa aleatória (ex.: `sky-ticket-2026-nampula-secreto`)

### 4. Deploy
Clique **Create Web Service** e espere 2–5 minutos.

No fim aparece um link, por exemplo:

```text
https://skyticketservice.onrender.com
```

**Esse link** abre no telemóvel, no PC de um cliente, em qualquer sítio.

### 5. Admin online
```text
https://skyticketservice.onrender.com/admin
```
Login: `admin` / `admin123`  
(Altere a senha assim que estiver em produção.)

---

## Domínio próprio (depois)

Quando comprar **skyticketservice.com**:
1. No Render: Settings → Custom Domain  
2. Adicione `www.skyticketservice.com`  
3. No site onde comprou o domínio, configure o DNS como o Render indicar  

---

## Notas do plano gratuito

- O site pode **“dormir”** após ~15 min sem visitas; a 1.ª abertura demora 30–60 s.  
- No plano free, dados SQLite **podem resetar** se o serviço for recriado. Para negócio sério, mais tarde: base PostgreSQL + plano pago.  
- Para testes e apresentação da agência, o free chega bem.

---

## Alternativas

| Serviço | Notas |
|---------|--------|
| [Railway](https://railway.app) | Fácil, tem crédito grátis |
| [PythonAnywhere](https://www.pythonanywhere.com) | Bom para Flask, free limitado |
| Hostinger / VPS | Pago, mais controlo |

---

## Resumo

1. Código já está preparado (`gunicorn`, `Procfile`, `requirements.txt`).  
2. Publica no **Render** (ou similar).  
3. Partilha o link HTTPS com qualquer pessoa.  
4. O seu PC **não precisa** de estar ligado.

Quando tiver conta GitHub, diga e ajudamos a enviar o código e a ligar ao Render passo a passo.
