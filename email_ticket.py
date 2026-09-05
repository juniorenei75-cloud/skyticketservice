"""Confirmação por e-mail e bilhete electrónico (e-ticket).

Três modos de envio:
1. **sendgrid** — API HTTPS SendGrid (recomendado; porta 443)
2. **brevo** — API HTTPS Brevo/Sendinblue (alternativa HTTPS)
3. **smtp** — Gmail ou outro servidor SMTP (portas 587/465)

Configuração: Admin → E-mail / SMTP  ou  smtp_config.json  ou  variáveis de ambiente.
"""

from __future__ import annotations

import base64
import json
import re
import logging
import os
import smtplib
import ssl
import urllib.error
import urllib.request
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

TICKETS_DIR = Path(__file__).resolve().parent / "tickets"
CONFIG_PATH = Path(__file__).resolve().parent / "smtp_config.json"
LOGO_PATH = Path(__file__).resolve().parent / "static" / "img" / "logo.jpg"
LOGO_FULL_PATH = Path(__file__).resolve().parent / "static" / "img" / "logo-full.jpg"
LOGO_EMAIL_PATH = Path(__file__).resolve().parent / "static" / "img" / "logo-email.png"

_logo_data_uri_cache: str | None = None
_logo_email_data_uri_cache: str | None = None
_AGENCY_WA = "+258 84 905 3340"
_AGENCY_MAIL = "skyticketservicee@gmail.com"


def _html_escape(value: Any) -> str:
    from html import escape

    return escape(str(value if value is not None else ""), quote=True)


DEFAULT_CONFIG: dict[str, Any] = {
    "enabled": True,
    # smtp | brevo | sendgrid  (brevo/sendgrid usam HTTPS — funciona quando a operadora bloqueia SMTP)
    "provider": "smtp",
    "host": "smtp.gmail.com",
    "port": 587,
    "user": "skyticketservicee@gmail.com",
    "password": "",
    "mail_from": "skyticketservicee@gmail.com",
    "from_name": "SKYTICKETservice",
    "use_tls": True,
    "use_ssl": False,
    "bcc_admin": True,
    "admin_email": "skyticketservicee@gmail.com",
    # Brevo (https://app.brevo.com) — chave API
    "brevo_api_key": "",
    # SendGrid (https://app.sendgrid.com) — chave API
    "sendgrid_api_key": "",
    # Gmail Apps Script relay (HTTPS) — envia como a conta Gmail da agência
    "gmail_relay_url": "",
    "gmail_relay_secret": "",
}


def load_smtp_config() -> dict[str, Any]:
    """Carrega config do JSON + sobrepõe com variáveis de ambiente se existirem."""
    cfg = dict(DEFAULT_CONFIG)
    if CONFIG_PATH.exists():
        try:
            data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                cfg.update(data)
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning("Não foi possível ler smtp_config.json: %s", exc)

    env_map = {
        "SMTP_HOST": "host",
        "SMTP_USER": "user",
        "SMTP_PASS": "password",
        "MAIL_FROM": "mail_from",
        "MAIL_FROM_NAME": "from_name",
        "SMTP_ADMIN_EMAIL": "admin_email",
        "BREVO_API_KEY": "brevo_api_key",
        "SENDGRID_API_KEY": "sendgrid_api_key",
        "GMAIL_RELAY_URL": "gmail_relay_url",
        "GMAIL_RELAY_SECRET": "gmail_relay_secret",
        "EMAIL_PROVIDER": "provider",
    }
    for env_k, cfg_k in env_map.items():
        val = os.environ.get(env_k, "").strip()
        if val:
            cfg[cfg_k] = val

    if os.environ.get("SMTP_PORT", "").strip():
        try:
            cfg["port"] = int(os.environ["SMTP_PORT"].strip())
        except ValueError:
            pass
    if os.environ.get("SMTP_ENABLED", "").strip() != "":
        cfg["enabled"] = os.environ.get("SMTP_ENABLED", "1").strip().lower() in (
            "1",
            "true",
            "yes",
            "on",
        )

    try:
        cfg["port"] = int(cfg.get("port") or 587)
    except (TypeError, ValueError):
        cfg["port"] = 587
    cfg["enabled"] = bool(cfg.get("enabled", True))
    cfg["use_tls"] = bool(cfg.get("use_tls", True))
    cfg["use_ssl"] = bool(cfg.get("use_ssl", False))
    cfg["bcc_admin"] = bool(cfg.get("bcc_admin", True))
    cfg["provider"] = (cfg.get("provider") or "smtp").strip().lower()
    # Gmail app passwords: remover espaços
    if cfg.get("password"):
        cfg["password"] = str(cfg["password"]).replace(" ", "").strip()
    return cfg


def save_smtp_config(updates: dict[str, Any]) -> dict[str, Any]:
    file_cfg = dict(DEFAULT_CONFIG)
    if CONFIG_PATH.exists():
        try:
            data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                file_cfg.update(data)
        except (OSError, json.JSONDecodeError):
            pass

    # Password / API key: manter se o formulário enviar vazio
    old_password = file_cfg.get("password") or ""
    old_brevo = file_cfg.get("brevo_api_key") or ""
    old_sendgrid = file_cfg.get("sendgrid_api_key") or ""
    file_cfg.update(updates)
    if not (updates.get("password") or "").strip():
        file_cfg["password"] = old_password
    else:
        file_cfg["password"] = str(updates["password"]).replace(" ", "").strip()
    if "brevo_api_key" in updates and not (updates.get("brevo_api_key") or "").strip():
        file_cfg["brevo_api_key"] = old_brevo
    if "sendgrid_api_key" in updates and not (updates.get("sendgrid_api_key") or "").strip():
        file_cfg["sendgrid_api_key"] = old_sendgrid

    CONFIG_PATH.write_text(
        json.dumps(file_cfg, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return load_smtp_config()


def smtp_is_ready(cfg: dict[str, Any] | None = None) -> tuple[bool, str]:
    """Indica se o envio de e-mail está pronto (SMTP, Brevo ou SendGrid)."""
    cfg = cfg or load_smtp_config()
    if not cfg.get("enabled"):
        return False, "Envio de e-mail desactivado na configuração."

    provider = (cfg.get("provider") or "smtp").lower()
    if provider == "gmail_relay":
        if not (cfg.get("gmail_relay_url") or "").strip():
            return False, "Modo Gmail Relay: falta o URL do Apps Script."
        if not (cfg.get("gmail_relay_secret") or "").strip():
            return False, "Modo Gmail Relay: falta o secret do Apps Script."
        if not (cfg.get("mail_from") or cfg.get("user") or "").strip():
            return False, "Modo Gmail Relay: indique o e-mail remetente (mail_from)."
        return True, "Gmail Relay (Apps Script HTTPS) pronto a enviar."

    if provider == "sendgrid":
        if not (cfg.get("sendgrid_api_key") or "").strip():
            return (
                False,
                "Modo SendGrid: falta a chave API. Crie em app.sendgrid.com → Settings → API Keys.",
            )
        if not (cfg.get("mail_from") or cfg.get("user") or "").strip():
            return False, "Modo SendGrid: indique o e-mail remetente (mail_from)."
        return True, "SendGrid (API HTTPS) pronto a enviar."

    if provider == "brevo":
        if not (cfg.get("brevo_api_key") or "").strip():
            return (
                False,
                "Modo Brevo: falta a chave API. Crie em app.brevo.com → SMTP & API → API keys.",
            )
        if not (cfg.get("mail_from") or cfg.get("user") or "").strip():
            return False, "Modo Brevo: indique o e-mail remetente (mail_from)."
        return True, "Brevo (API HTTPS) pronto a enviar."

    if not (cfg.get("host") or "").strip():
        return False, "Falta o servidor SMTP (host)."
    if not (cfg.get("user") or "").strip():
        return False, "Falta o utilizador SMTP (e-mail da conta)."
    if not (cfg.get("password") or "").strip():
        return (
            False,
            "Falta a palavra-passe SMTP. No Gmail use uma «palavra-passe de aplicação».",
        )
    return True, (
        "SMTP configurado (se a rede bloquear a porta 587/465, "
        "use o modo SendGrid ou Brevo)."
    )


def _format_money(value: float, moeda: str = "USD") -> str:
    try:
        v = float(value)
    except (TypeError, ValueError):
        v = 0
    if moeda == "MZN":
        return f"{v:,.0f} MT".replace(",", " ")
    return f"{moeda} {v:,.2f}"


def logo_data_uri() -> str:
    """Logotipo em data-URI (base64) para e-mail, PDF e impressão offline."""
    global _logo_data_uri_cache
    if _logo_data_uri_cache is not None:
        return _logo_data_uri_cache

    for path in (LOGO_PATH, LOGO_FULL_PATH):
        if path.exists():
            try:
                raw = path.read_bytes()
                # Evitar bilhetes enormes: se > 400KB, preferir logo.jpg
                if path == LOGO_FULL_PATH and len(raw) > 400_000 and LOGO_PATH.exists():
                    raw = LOGO_PATH.read_bytes()
                    path = LOGO_PATH
                mime = "image/jpeg"
                if path.suffix.lower() == ".png":
                    mime = "image/png"
                elif path.suffix.lower() in (".webp",):
                    mime = "image/webp"
                b64 = base64.b64encode(raw).decode("ascii")
                _logo_data_uri_cache = f"data:{mime};base64,{b64}"
                return _logo_data_uri_cache
            except OSError as exc:
                logger.warning("Não foi possível ler o logotipo: %s", exc)

    _logo_data_uri_cache = ""
    return ""



def logo_email_data_uri() -> str:
    """Logotipo pequeno (~8KB) para e-mail — nunca usar logo.jpg completo."""
    global _logo_email_data_uri_cache
    if _logo_email_data_uri_cache is not None:
        return _logo_email_data_uri_cache
    path = LOGO_EMAIL_PATH
    if path.exists():
        try:
            raw = path.read_bytes()
            if len(raw) > 20_000:
                logger.warning("logo-email.png demasiado grande (%s bytes); a ignorar.", len(raw))
            else:
                mime = "image/png" if path.suffix.lower() == ".png" else "image/jpeg"
                b64 = base64.b64encode(raw).decode("ascii")
                _logo_email_data_uri_cache = f"data:{mime};base64,{b64}"
                return _logo_email_data_uri_cache
        except OSError as exc:
            logger.warning("Não foi possível ler logo-email: %s", exc)
    _logo_email_data_uri_cache = ""
    return ""


def _parse_obs_field(obs: str, label: str) -> str:
    """Extrai «Label: valor» de observacoes separadas por |."""
    if not obs or not label:
        return ""
    for part in str(obs).split("|"):
        part = part.strip()
        if part.lower().startswith(label.lower() + ":"):
            return part.split(":", 1)[-1].strip()
    return ""


def build_eticket_html(
    reserva,
    passageiros_txt: str = "",
    pagamento: str = "",
    extras: dict | None = None,
) -> str:
    """HTML do bilhete electrónico — estilo boarding pass (marca bordo)."""
    extras = extras or {}

    def g(key, default="—"):
        try:
            if key in extras and extras.get(key) not in (None, ""):
                return extras[key]
            if isinstance(reserva, dict):
                return reserva.get(key) or default
            return (
                reserva[key]
                if key in reserva.keys() and reserva[key] is not None
                else default
            )
        except Exception:
            return default

    codigo = g("codigo", "—")
    obs = ""
    try:
        if isinstance(reserva, dict):
            obs = reserva.get("observacoes") or ""
        elif hasattr(reserva, "keys") and "observacoes" in reserva.keys():
            obs = reserva["observacoes"] or ""
    except Exception:
        obs = ""

    companhia = g("ticket_companhia", "") if g("ticket_companhia", "") != "—" else ""
    if not companhia:
        companhia = _parse_obs_field(obs, "Companhia") or "SKYTICKETservice"
    flight_no = g("ticket_flight_no", "")
    if not flight_no or flight_no == "—":
        flight_no = _parse_obs_field(obs, "Voo") or ""
    horario = g("ticket_horario", "")
    if not horario or horario == "—":
        horario = _parse_obs_field(obs, "Horário") or "—"
    horario_chegada = g("ticket_horario_chegada", "—")
    duracao = g("ticket_duracao", "")
    if not duracao or duracao == "—":
        duracao = _parse_obs_field(obs, "Duração") or "—"
    classe = g("classe_nome", "")
    if not classe or classe == "—":
        classe = _parse_obs_field(obs, "Classe") or "—"
    if not pagamento:
        pagamento = _parse_obs_field(obs, "Pagamento") or "—"

    o_cid = g("origem_cidade", "")
    o_pais = g("origem_pais", "")
    d_cid = g("destino_cidade", "")
    d_pais = g("destino_pais", "")
    origem = f"{o_cid}, {o_pais}".strip(", ") or "—"
    destino = f"{d_cid}, {d_pais}".strip(", ") or "—"
    o_short = (o_cid or o_pais or "ORG")[:18]
    d_short = (d_cid or d_pais or "DST")[:18]

    total = _format_money(
        g("total", 0) if g("total", 0) != "—" else 0, g("moeda", "USD")
    )
    tipo = "Ida e volta" if g("tipo_viagem") == "ida_volta" else "Só ida"
    logo = logo_data_uri()
    if logo:
        logo_html = (
            f'<img class="logo" src="{logo}" alt="SKYTICKETservice" width="64" height="64">'
        )
        logo_stub = (
            f'<img class="logo-sm" src="{logo}" alt="" width="40" height="40">'
        )
    else:
        logo_html = '<div class="logo-fallback">SK</div>'
        logo_stub = '<div class="logo-fallback sm">SK</div>'

    pax_block = ""
    if passageiros_txt:
        pax_block = f"""
      <div class="section">
        <h3 class="sec-title">Passageiros</h3>
        <div class="pax-list">{passageiros_txt}</div>
      </div>"""

    flight_meta = ""
    if flight_no:
        flight_meta += f'<span class="pill">{flight_no}</span>'
    if classe and classe != "—":
        flight_meta += f'<span class="pill soft">{classe}</span>'
    flight_meta += f'<span class="pill soft">{tipo}</span>'

    chegada_html = ""
    if horario_chegada and horario_chegada != "—":
        chegada_html = f"""
          <div class="time-block arr">
            <span class="time-lbl">Chegada</span>
            <span class="time-val">{horario_chegada}</span>
          </div>"""

    # QR → WhatsApp da agência com dados do bilhete (ler no telemóvel a partir do PC)
    wa_qr_html = ""
    try:
        from notifications import mensagem_nova_reserva, whatsapp_qr_for_admin

        wa_txt = mensagem_nova_reserva(
            codigo=str(codigo),
            nome=str(g("nome")),
            email=str(g("email")),
            telefone=str(g("telefone")),
            tipo=str(g("tipo") if g("tipo") != "—" else "voo"),
            detalhe=f"{origem} → {destino}",
            passageiros=int(g("passageiros", 1) or 1)
            if str(g("passageiros", "1")).isdigit()
            else 1,
            data_viagem=str(g("data_viagem")),
            total=float(g("total", 0) or 0)
            if str(g("total", "0")).replace(".", "", 1).isdigit()
            else 0,
            moeda=str(g("moeda", "USD")),
            pagamento=str(pagamento or ""),
            companhia=str(companhia or ""),
            voo=str(flight_no or ""),
            estado=str(g("status")),
        )
        wa_pack = whatsapp_qr_for_admin(wa_txt)
        if wa_pack.get("qr"):
            wa_qr_html = f"""
    <div class="wa-qr">
      <p class="wa-qr-label">Whatsapp</p>
      <img class="wa-qr-img" src="{wa_pack["qr"]}" alt="Whatsapp" width="180" height="180">
    </div>"""
    except Exception:
        wa_qr_html = ""

    return f"""<!DOCTYPE html>
<html lang="pt">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>E-Ticket {codigo} · SKYTICKETservice</title>
  <style>
    :root {{
      --bordo: #5c0a2c;
      --bordo-2: #8b1538;
      --creme: #f7f5f2;
      --ink: #1a1a1a;
      --muted: #6b6b6b;
      --line: #e8e0dc;
      --gold: #c4a574;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      padding: 28px 14px 48px;
      font-family: "Segoe UI", "Helvetica Neue", Arial, sans-serif;
      background: linear-gradient(180deg, #efe8e4 0%, #f7f5f2 40%, #eee8e4 100%);
      color: var(--ink);
    }}
    .toolbar {{
      max-width: 720px;
      margin: 0 auto 14px;
      display: flex;
      justify-content: flex-end;
      gap: 8px;
    }}
    .toolbar button {{
      border: none;
      background: var(--bordo);
      color: #fff;
      font-weight: 700;
      font-size: 0.9rem;
      padding: 11px 18px;
      cursor: pointer;
      letter-spacing: 0.02em;
    }}
    .toolbar button:hover {{ background: var(--bordo-2); }}
    .ticket {{
      max-width: 720px;
      margin: 0 auto;
      background: #fff;
      border: 1px solid #ddd4ce;
      box-shadow: 0 18px 50px rgba(92, 10, 44, 0.1);
    }}
    .topbar {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      padding: 14px 22px;
      background: var(--bordo);
      color: #fff;
    }}
    .brand {{
      display: flex;
      align-items: center;
      gap: 12px;
      min-width: 0;
    }}
    .logo, .logo-fallback {{
      width: 52px;
      height: 52px;
      object-fit: contain;
      background: #fff;
      padding: 4px;
      flex-shrink: 0;
    }}
    .logo-fallback {{
      display: grid;
      place-items: center;
      font-weight: 800;
      color: var(--bordo);
      font-size: 0.95rem;
    }}
    .logo-fallback.sm {{ width: 36px; height: 36px; font-size: 0.75rem; }}
    .brand-name {{
      font-size: 1.15rem;
      font-weight: 800;
      letter-spacing: 0.01em;
      line-height: 1.1;
    }}
    .brand-name span {{ color: var(--gold); font-weight: 700; }}
    .brand-tag {{
      margin-top: 3px;
      font-size: 0.72rem;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      opacity: 0.88;
    }}
    .et-label {{
      text-align: right;
      font-size: 0.72rem;
      letter-spacing: 0.14em;
      text-transform: uppercase;
      opacity: 0.9;
      line-height: 1.35;
    }}
    .et-label strong {{
      display: block;
      font-size: 1.05rem;
      letter-spacing: 0.06em;
      margin-top: 2px;
    }}
    .boarding {{
      padding: 22px 22px 8px;
      background: #fff;
    }}
    .ref-row {{
      display: flex;
      flex-wrap: wrap;
      justify-content: space-between;
      gap: 10px;
      align-items: flex-end;
      margin-bottom: 18px;
      padding-bottom: 14px;
      border-bottom: 1px solid var(--line);
    }}
    .ref-code {{
      font-size: 1.55rem;
      font-weight: 800;
      letter-spacing: 0.12em;
      color: var(--bordo);
    }}
    .ref-sub {{
      font-size: 0.78rem;
      color: var(--muted);
      margin-top: 2px;
    }}
    .airline-line {{
      text-align: right;
      font-size: 0.95rem;
      font-weight: 700;
      color: var(--ink);
    }}
    .airline-line small {{
      display: block;
      margin-top: 2px;
      font-weight: 600;
      color: var(--muted);
      font-size: 0.78rem;
    }}
    .route {{
      display: grid;
      grid-template-columns: 1fr auto 1fr;
      gap: 10px;
      align-items: center;
      padding: 8px 0 18px;
    }}
    .city {{ min-width: 0; }}
    .city.from {{ text-align: left; }}
    .city.to {{ text-align: right; }}
    .city .name {{
      font-size: 1.35rem;
      font-weight: 800;
      color: var(--bordo);
      line-height: 1.15;
      word-break: break-word;
    }}
    .city .meta {{
      margin-top: 4px;
      font-size: 0.8rem;
      color: var(--muted);
    }}
    .flight-path {{
      text-align: center;
      padding: 0 6px;
      min-width: 110px;
    }}
    .flight-path .plane {{
      font-size: 1.2rem;
      color: var(--bordo);
      margin-bottom: 4px;
    }}
    .flight-path .dash {{
      height: 2px;
      background: linear-gradient(90deg, var(--bordo), var(--gold), var(--bordo));
      margin: 6px 0;
      position: relative;
    }}
    .flight-path .dur {{
      font-size: 0.75rem;
      color: var(--muted);
      font-weight: 600;
    }}
    .pills {{
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
      margin: 0 0 16px;
    }}
    .pill {{
      display: inline-block;
      padding: 4px 10px;
      font-size: 0.72rem;
      font-weight: 700;
      letter-spacing: 0.04em;
      text-transform: uppercase;
      background: var(--bordo);
      color: #fff;
    }}
    .pill.soft {{
      background: #f9f0f4;
      color: var(--bordo);
      border: 1px solid #e8d0da;
    }}
    .times {{
      display: flex;
      flex-wrap: wrap;
      gap: 18px;
      margin-bottom: 8px;
    }}
    .time-block .time-lbl {{
      display: block;
      font-size: 0.7rem;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      color: var(--muted);
      font-weight: 700;
    }}
    .time-block .time-val {{
      font-size: 1.45rem;
      font-weight: 800;
      color: var(--ink);
      letter-spacing: 0.02em;
    }}
    .stub {{
      margin: 8px 22px 0;
      border-top: 2px dashed #d4c8c0;
      position: relative;
    }}
    .stub::before, .stub::after {{
      content: "";
      position: absolute;
      top: -11px;
      width: 20px;
      height: 20px;
      background: #efe8e4;
      border-radius: 50%;
    }}
    .stub::before {{ left: -32px; }}
    .stub::after {{ right: -32px; }}
    .body {{
      padding: 18px 22px 8px;
    }}
    .grid {{
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 0 28px;
    }}
    .field {{
      padding: 10px 0;
      border-bottom: 1px solid var(--line);
    }}
    .field .lbl {{
      display: block;
      font-size: 0.68rem;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      color: var(--muted);
      font-weight: 700;
      margin-bottom: 3px;
    }}
    .field .val {{
      font-size: 0.95rem;
      font-weight: 650;
      color: var(--ink);
      word-break: break-word;
    }}
    .field.full {{ grid-column: 1 / -1; }}
    .section {{
      margin-top: 16px;
      padding-top: 8px;
    }}
    .sec-title {{
      margin: 0 0 8px;
      font-size: 0.72rem;
      letter-spacing: 0.1em;
      text-transform: uppercase;
      color: var(--bordo);
      font-weight: 800;
    }}
    .pax-list {{
      font-size: 0.88rem;
      line-height: 1.55;
      color: #333;
      background: var(--creme);
      border-left: 3px solid var(--bordo);
      padding: 12px 14px;
    }}
    .barcode {{
      margin: 18px 22px 6px;
      text-align: center;
    }}
    .barcode-bars {{
      height: 46px;
      background: repeating-linear-gradient(
        90deg,
        #1a1a1a 0px,
        #1a1a1a 2px,
        transparent 2px,
        transparent 4px,
        #1a1a1a 4px,
        #1a1a1a 5px,
        transparent 5px,
        transparent 8px,
        #1a1a1a 8px,
        #1a1a1a 11px,
        transparent 11px,
        transparent 13px
      );
      margin: 0 auto;
      max-width: 280px;
      opacity: 0.85;
    }}
    .barcode-text {{
      margin-top: 6px;
      font-family: "Consolas", "Courier New", monospace;
      font-size: 0.85rem;
      letter-spacing: 0.18em;
      font-weight: 700;
      color: var(--bordo);
    }}
    .foot {{
      margin-top: 10px;
      padding: 16px 22px 20px;
      background: #faf7f5;
      border-top: 1px solid var(--line);
      display: flex;
      gap: 12px;
      align-items: flex-start;
    }}
    .logo-sm {{
      width: 40px;
      height: 40px;
      object-fit: contain;
      background: #fff;
      border: 1px solid var(--line);
      padding: 2px;
      flex-shrink: 0;
    }}
    .foot-text {{
      font-size: 0.8rem;
      line-height: 1.5;
      color: var(--muted);
    }}
    .foot-text strong {{ color: var(--bordo); }}
    .notice {{
      margin: 14px 22px 0;
      padding: 10px 12px;
      font-size: 0.78rem;
      line-height: 1.45;
      color: #5c0a2c;
      background: #f9f0f4;
      border: 1px solid #e8d0da;
    }}
    .wa-qr {{
      margin: 16px 22px 8px;
      text-align: center;
    }}
    .wa-qr-label {{
      margin: 0 0 8px;
      font-size: 1.05rem;
      font-weight: 800;
      color: #128c7e;
    }}
    .wa-qr-img {{
      width: 180px;
      height: 180px;
      object-fit: contain;
      background: #fff;
      border: 1px solid #e5e0dc;
      padding: 6px;
      display: block;
      margin: 0 auto;
    }}
    @media (max-width: 560px) {{
      .route {{ grid-template-columns: 1fr; text-align: center; }}
      .city.from, .city.to {{ text-align: center; }}
      .grid {{ grid-template-columns: 1fr; }}
      .airline-line, .et-label {{ text-align: left; }}
      .ref-row {{ flex-direction: column; align-items: flex-start; }}
    }}
    @media print {{
      body {{ background: #fff; padding: 0; }}
      .toolbar {{ display: none !important; }}
      .ticket {{
        box-shadow: none;
        border: 1px solid #ccc;
        max-width: 100%;
      }}
      .topbar, .pill, .barcode-bars, .logo, .logo-sm, .logo-fallback {{
        -webkit-print-color-adjust: exact;
        print-color-adjust: exact;
      }}
      .stub::before, .stub::after {{ display: none; }}
    }}
  </style>
</head>
<body>
  <div class="toolbar">
    <button type="button" onclick="window.print()">Imprimir / PDF</button>
  </div>
  <article class="ticket">
    <header class="topbar">
      <div class="brand">
        {logo_html}
        <div>
          <div class="brand-name">SKYTICKET<span>service</span></div>
          <div class="brand-tag">Agência de viagens · Sem limites</div>
        </div>
      </div>
      <div class="et-label">
        Bilhete electrónico
        <strong>E-TICKET</strong>
      </div>
    </header>

    <section class="boarding">
      <div class="ref-row">
        <div>
          <div class="ref-code">{codigo}</div>
          <div class="ref-sub">Código de reserva · Booking reference</div>
        </div>
        <div class="airline-line">
          {companhia}
          <small>Estado: {g('status')}</small>
        </div>
      </div>

      <div class="pills">{flight_meta}</div>

      <div class="route">
        <div class="city from">
          <div class="name">{o_short}</div>
          <div class="meta">{origem}</div>
        </div>
        <div class="flight-path">
          <div class="plane">✈</div>
          <div class="dash"></div>
          <div class="dur">{duracao if duracao != '—' else '—'}</div>
        </div>
        <div class="city to">
          <div class="name">{d_short}</div>
          <div class="meta">{destino}</div>
        </div>
      </div>

      <div class="times">
        <div class="time-block">
          <span class="time-lbl">Partida</span>
          <span class="time-val">{horario if horario != '—' else '—'}</span>
        </div>
        {chegada_html}
        <div class="time-block">
          <span class="time-lbl">Data ida</span>
          <span class="time-val" style="font-size:1.15rem">{g('data_viagem')}</span>
        </div>
        <div class="time-block">
          <span class="time-lbl">Data volta</span>
          <span class="time-val" style="font-size:1.15rem">{g('data_regresso')}</span>
        </div>
      </div>
    </section>

    <div class="stub"></div>

    <section class="body">
      <div class="grid">
        <div class="field">
          <span class="lbl">Passageiro principal</span>
          <span class="val">{g('nome')}</span>
        </div>
        <div class="field">
          <span class="lbl">Contacto</span>
          <span class="val">{g('telefone')}</span>
        </div>
        <div class="field full">
          <span class="lbl">E-mail</span>
          <span class="val">{g('email')}</span>
        </div>
        <div class="field">
          <span class="lbl">Assentos ida</span>
          <span class="val">{g('assentos')}</span>
        </div>
        <div class="field">
          <span class="lbl">Assentos volta</span>
          <span class="val">{g('assentos_volta')}</span>
        </div>
        <div class="field">
          <span class="lbl">N.º passageiros</span>
          <span class="val">{g('passageiros')}</span>
        </div>
        <div class="field">
          <span class="lbl">Total pago</span>
          <span class="val">{total}</span>
        </div>
        <div class="field full">
          <span class="lbl">Pagamento</span>
          <span class="val">{pagamento or '—'}</span>
        </div>
      </div>
      {pax_block}
    </section>

    <div class="notice">
      Apresente este bilhete e documento de viagem no check-in.
      Documento emitido por <strong>SKYTICKETservice</strong> —
      Nampula (Agência Mãe) · Maputo · Beira · Online · 24h.
    </div>

    <div class="barcode">
      <div class="barcode-bars" aria-hidden="true"></div>
      <div class="barcode-text">{codigo}</div>
    </div>

    {wa_qr_html}

    <footer class="foot">
      {logo_stub}
      <div class="foot-text">
        Guarde este e-ticket. Código: <strong>{codigo}</strong><br>
        ✉ skyticketservicee@gmail.com · ☎ +258 84 905 3340 · WhatsApp disponível
      </div>
    </footer>
  </article>
</body>
</html>
"""


def save_eticket(codigo: str, html: str) -> Path:
    TICKETS_DIR.mkdir(parents=True, exist_ok=True)
    path = TICKETS_DIR / f"{codigo}.html"
    path.write_text(html, encoding="utf-8")
    return path


def _connection_blocked_hint(exc: BaseException) -> str:
    msg = str(exc).lower()
    if any(
        x in msg
        for x in (
            "unexpectedly closed",
            "connection reset",
            "timed out",
            "eof",
            "10054",
            "10060",
            "10061",
            "unreachable",
        )
    ):
        return (
            " A sua rede/operadora está a bloquear o SMTP do Gmail (portas 587/465). "
            "Solução: no Admin → E-mail, escolha «SendGrid» ou «Brevo» (API HTTPS) "
            "— usam a porta 443 e costumam funcionar."
        )
    return ""


def _send_via_brevo(
    *,
    to_email: str,
    subject: str,
    text_body: str,
    html_body: str,
    cfg: dict[str, Any],
    attachments: list[dict[str, Any]] | None = None,
) -> tuple[bool, str]:
    api_key = (cfg.get("brevo_api_key") or "").strip()
    if not api_key:
        return False, "Falta a chave API Brevo."

    mail_from = (cfg.get("mail_from") or cfg.get("user") or "").strip()
    from_name = (cfg.get("from_name") or "SKYTICKETservice").strip()
    if not mail_from:
        return False, "Falta o e-mail remetente (mail_from)."

    payload: dict[str, Any] = {
        "sender": {"name": from_name, "email": mail_from},
        "to": [{"email": to_email.strip()}],
        "subject": subject,
        "htmlContent": html_body,
        "textContent": text_body,
        "replyTo": {"email": mail_from, "name": from_name},
    }
    if cfg.get("bcc_admin"):
        admin = (cfg.get("admin_email") or mail_from).strip()
        if admin and admin.lower() != to_email.strip().lower():
            payload["bcc"] = [{"email": admin}]
    if attachments:
        att_out = []
        for att in attachments:
            raw = att.get("content")
            if raw is None:
                continue
            if isinstance(raw, bytes):
                b64 = base64.b64encode(raw).decode("ascii")
            else:
                b64 = str(raw)
            att_out.append(
                {
                    "name": att.get("filename") or "attachment.bin",
                    "content": b64,
                }
            )
        if att_out:
            payload["attachment"] = att_out

    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        "https://api.brevo.com/v3/smtp/email",
        data=data,
        method="POST",
        headers={
            "accept": "application/json",
            "api-key": api_key,
            "content-type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=45) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            logger.info("Brevo OK: %s", body[:200])
        return True, f"E-mail enviado para {to_email.strip()} (via Brevo)."
    except urllib.error.HTTPError as exc:
        err_body = exc.read().decode("utf-8", errors="replace")
        # Remetente não verificado
        if exc.code in (400, 401, 403):
            return (
                False,
                f"Brevo recusou o envio (HTTP {exc.code}): {err_body[:280]}. "
                f"Confirme a API key e que o remetente {mail_from} está verificado em "
                f"Brevo → Senders.",
            )
        return False, f"Brevo HTTP {exc.code}: {err_body[:280]}"
    except Exception as exc:  # noqa: BLE001
        logger.exception("Brevo error")
        return False, f"Falha Brevo: {exc}"



def _send_via_gmail_relay(
    *,
    to_email: str,
    subject: str,
    text_body: str,
    html_body: str,
    cfg: dict[str, Any],
    attachments: list[dict[str, Any]] | None = None,
) -> tuple[bool, str]:
    """Envia via Google Apps Script (GmailApp) — HTTPS, sem SMTP.

    attachments: lista de dicts {filename, content(bytes|str base64), mime_type}.
    Requer Apps Script actualizado (ver gmail_apps_script/Code.gs).
    """
    url = (cfg.get("gmail_relay_url") or "").strip()
    secret = (cfg.get("gmail_relay_secret") or "").strip()
    if not url:
        return False, "Falta gmail_relay_url."
    if not secret:
        return False, "Falta gmail_relay_secret."

    from_name = (cfg.get("from_name") or "SKYTICKETservice").strip()
    payload: dict[str, Any] = {
        "secret": secret,
        "to": to_email.strip(),
        "subject": subject,
        "text": text_body or " ",
        "html": html_body or text_body or " ",
        "fromName": from_name,
    }
    if cfg.get("bcc_admin"):
        admin = (cfg.get("admin_email") or cfg.get("mail_from") or "").strip()
        if admin and admin.lower() != to_email.strip().lower():
            payload["bcc"] = admin
    if attachments:
        att_out = []
        for att in attachments:
            raw = att.get("content")
            if raw is None:
                continue
            if isinstance(raw, bytes):
                b64 = base64.b64encode(raw).decode("ascii")
            else:
                b64 = str(raw)
            att_out.append(
                {
                    "filename": att.get("filename") or "attachment.bin",
                    "mimeType": att.get("mime_type") or att.get("mimeType") or "application/octet-stream",
                    "content": b64,
                }
            )
        if att_out:
            payload["attachments"] = att_out

    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            logger.info("Gmail relay response: %s", body[:300])
        try:
            parsed = json.loads(body) if body.strip() else {}
        except json.JSONDecodeError:
            parsed = {}
        if isinstance(parsed, dict) and parsed.get("ok") is False:
            err = str(parsed.get("error") or body)[:280]
            return False, f"Gmail relay recusou: {err}"
        if isinstance(parsed, dict) and parsed.get("ok") is True:
            return True, f"E-mail enviado para {to_email.strip()} (via Gmail / Apps Script)."
        # Resposta inesperada mas HTTP 200
        if "ok" not in (parsed or {}):
            return True, f"E-mail enviado para {to_email.strip()} (via Gmail / Apps Script)."
        return False, f"Gmail relay resposta inesperada: {body[:280]}"
    except urllib.error.HTTPError as exc:
        err_body = exc.read().decode("utf-8", errors="replace")
        return False, f"Gmail relay HTTP {exc.code}: {err_body[:280]}"
    except Exception as exc:  # noqa: BLE001
        logger.exception("Gmail relay error")
        return False, f"Falha Gmail relay: {exc}"


def _send_via_sendgrid(
    *,
    to_email: str,
    subject: str,
    text_body: str,
    html_body: str,
    cfg: dict[str, Any],
    attachments: list[dict[str, Any]] | None = None,
) -> tuple[bool, str]:
    api_key = (cfg.get("sendgrid_api_key") or "").strip()
    if not api_key:
        return False, "Falta a chave API SendGrid."

    mail_from = (cfg.get("mail_from") or cfg.get("user") or "").strip()
    from_name = (cfg.get("from_name") or "SKYTICKETservice").strip()
    if not mail_from:
        return False, "Falta o e-mail remetente (mail_from)."

    personalization: dict[str, Any] = {
        "to": [{"email": to_email.strip()}],
    }
    if cfg.get("bcc_admin"):
        admin = (cfg.get("admin_email") or mail_from).strip()
        if admin and admin.lower() != to_email.strip().lower():
            personalization["bcc"] = [{"email": admin}]

    payload: dict[str, Any] = {
        "personalizations": [personalization],
        "from": {"email": mail_from, "name": from_name},
        "subject": subject,
        "content": [
            {"type": "text/plain", "value": text_body or " "},
            {"type": "text/html", "value": html_body or text_body or " "},
        ],
        "reply_to": {"email": mail_from, "name": from_name},
    }
    if attachments:
        att_out = []
        for att in attachments:
            raw = att.get("content")
            if raw is None:
                continue
            if isinstance(raw, bytes):
                b64 = base64.b64encode(raw).decode("ascii")
            else:
                b64 = str(raw)
            att_out.append(
                {
                    "content": b64,
                    "type": att.get("mime_type") or att.get("mimeType") or "application/pdf",
                    "filename": att.get("filename") or "attachment.bin",
                    "disposition": "attachment",
                }
            )
        if att_out:
            payload["attachments"] = att_out

    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        "https://api.sendgrid.com/v3/mail/send",
        data=data,
        method="POST",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=45) as resp:
            # SendGrid devolve 202 Accepted sem corpo (ou quase vazio)
            body = resp.read().decode("utf-8", errors="replace")
            logger.info("SendGrid OK (HTTP %s): %s", resp.status, body[:200])
        return True, f"E-mail enviado para {to_email.strip()} (via SendGrid)."
    except urllib.error.HTTPError as exc:
        err_body = exc.read().decode("utf-8", errors="replace")
        if exc.code in (400, 401, 403):
            return (
                False,
                f"SendGrid recusou o envio (HTTP {exc.code}): {err_body[:280]}. "
                f"Confirme a API key e que o remetente {mail_from} está verificado em "
                f"SendGrid → Sender Authentication.",
            )
        return False, f"SendGrid HTTP {exc.code}: {err_body[:280]}"
    except Exception as exc:  # noqa: BLE001
        logger.exception("SendGrid error")
        return False, f"Falha SendGrid: {exc}"


def _smtp_send_once(
    *,
    host: str,
    port: int,
    user: str,
    password: str,
    mail_from: str,
    recipients: list[str],
    raw_message: str,
    use_ssl: bool,
    use_tls: bool,
) -> None:
    timeout = 30
    if use_ssl or port == 465:
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL(host, port, timeout=timeout, context=context) as smtp:
            smtp.ehlo()
            smtp.login(user, password)
            smtp.sendmail(mail_from, recipients, raw_message)
        return

    with smtplib.SMTP(host, port, timeout=timeout) as smtp:
        smtp.ehlo()
        if use_tls or port == 587:
            context = ssl.create_default_context()
            smtp.starttls(context=context)
            smtp.ehlo()
        smtp.login(user, password)
        smtp.sendmail(mail_from, recipients, raw_message)


def _send_via_smtp(
    *,
    to_email: str,
    subject: str,
    text_body: str,
    html_body: str,
    cfg: dict[str, Any],
    attachments: list[dict[str, Any]] | None = None,
) -> tuple[bool, str]:
    host = (cfg.get("host") or "").strip()
    port = int(cfg.get("port") or 587)
    user = (cfg.get("user") or "").strip()
    password = (cfg.get("password") or "").replace(" ", "").strip()
    mail_from = (cfg.get("mail_from") or user).strip()
    from_name = (cfg.get("from_name") or "SKYTICKETservice").strip()

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = formataddr((from_name, mail_from))
    msg["To"] = to_email.strip()
    msg["Reply-To"] = mail_from

    recipients = [to_email.strip()]
    if cfg.get("bcc_admin"):
        admin = (cfg.get("admin_email") or user or "").strip()
        if admin and admin.lower() != to_email.strip().lower():
            msg["Bcc"] = admin
            recipients.append(admin)

    if attachments:
        mixed = MIMEMultipart("mixed")
        for k in ("Subject", "From", "To", "Reply-To", "Bcc"):
            if k in msg:
                mixed[k] = msg[k]
        alt = MIMEMultipart("alternative")
        alt.attach(MIMEText(text_body, "plain", "utf-8"))
        alt.attach(MIMEText(html_body, "html", "utf-8"))
        mixed.attach(alt)
        for att in attachments:
            raw_c = att.get("content")
            if raw_c is None:
                continue
            if isinstance(raw_c, str):
                raw_c = base64.b64decode(raw_c)
            part = MIMEApplication(raw_c, _subtype=(att.get("mime_type") or "application/pdf").split("/")[-1])
            part.add_header(
                "Content-Disposition",
                "attachment",
                filename=att.get("filename") or "attachment.bin",
            )
            mixed.attach(part)
        msg = mixed
    else:
        msg.attach(MIMEText(text_body, "plain", "utf-8"))
        msg.attach(MIMEText(html_body, "html", "utf-8"))
    raw = msg.as_string()

    # Tentar a config pedida e, se falhar por ligação, a alternativa 465/587
    attempts: list[tuple[int, bool, bool]] = []
    use_ssl = bool(cfg.get("use_ssl")) or port == 465
    use_tls = bool(cfg.get("use_tls", True)) and not use_ssl
    attempts.append((port, use_ssl, use_tls))
    if port != 465:
        attempts.append((465, True, False))
    if port != 587:
        attempts.append((587, False, True))

    last_err: BaseException | None = None
    for p, ssl_mode, tls_mode in attempts:
        try:
            _smtp_send_once(
                host=host,
                port=p,
                user=user,
                password=password,
                mail_from=mail_from,
                recipients=recipients,
                raw_message=raw,
                use_ssl=ssl_mode,
                use_tls=tls_mode,
            )
            return True, f"E-mail enviado para {to_email.strip()} (SMTP :{p})."
        except smtplib.SMTPAuthenticationError:
            return (
                False,
                "Falha de autenticação SMTP. No Gmail use a «palavra-passe de aplicação» "
                "(não a palavra-passe normal da conta).",
            )
        except Exception as exc:  # noqa: BLE001
            last_err = exc
            logger.warning("SMTP :%s falhou: %s", p, exc)
            continue

    assert last_err is not None
    hint = _connection_blocked_hint(last_err)
    return False, f"Falha no envio de e-mail: {last_err}.{hint}"


def _brevo_activation_failure(msg: str) -> bool:
    """True se Brevo falhou por conta/remetente ainda não activado."""
    m = (msg or "").lower()
    keys = (
        "activation",
        "not yet activated",
        "sender",
        "unrecognised",
        "unrecognized",
        "not verified",
        "não verificado",
        "http 401",
        "http 403",
    )
    return any(k in m for k in keys)


def _send_raw(
    *,
    to_email: str,
    subject: str,
    text_body: str,
    html_body: str,
    cfg: dict[str, Any] | None = None,
    attachments: list[dict[str, Any]] | None = None,
) -> tuple[bool, str]:
    cfg = cfg or load_smtp_config()
    ready, reason = smtp_is_ready(cfg)
    if not ready:
        return False, reason
    if not (to_email or "").strip():
        return False, "Destinatário sem e-mail."

    provider = (cfg.get("provider") or "smtp").lower()

    if provider == "gmail_relay":
        return _send_via_gmail_relay(
            to_email=to_email,
            subject=subject,
            text_body=text_body,
            html_body=html_body,
            cfg=cfg,
            attachments=attachments,
        )

    # Preferência: SendGrid quando seleccionado
    if provider == "sendgrid":
        return _send_via_sendgrid(
            to_email=to_email,
            subject=subject,
            text_body=text_body,
            html_body=html_body,
            cfg=cfg,
            attachments=attachments,
        )

    if provider == "brevo":
        ok, msg = _send_via_brevo(
            to_email=to_email,
            subject=subject,
            text_body=text_body,
            html_body=html_body,
            cfg=cfg,
            attachments=attachments,
        )
        # Fallback documentado: se Brevo falhar por activação e houver SendGrid
        if (
            not ok
            and _brevo_activation_failure(msg)
            and (cfg.get("sendgrid_api_key") or "").strip()
        ):
            logger.info(
                "Brevo falhou (activação/remetente) — a tentar SendGrid automaticamente"
            )
            ok2, msg2 = _send_via_sendgrid(
                to_email=to_email,
                subject=subject,
                text_body=text_body,
                html_body=html_body,
                cfg=cfg,
                attachments=attachments,
            )
            if ok2:
                return True, msg2 + " (Brevo falhou por activação; usado SendGrid.)"
            return False, (
                f"{msg} | Fallback SendGrid: {msg2}. "
                "Se a conta Brevo ainda não estiver activada, defina provider=sendgrid "
                "no Admin → E-mail."
            )
        if (
            not ok
            and _brevo_activation_failure(msg)
            and (cfg.get("gmail_relay_url") or "").strip()
            and (cfg.get("gmail_relay_secret") or "").strip()
        ):
            logger.info("Brevo falhou — a tentar Gmail Relay automaticamente")
            ok3, msg3 = _send_via_gmail_relay(
                to_email=to_email,
                subject=subject,
                text_body=text_body,
                html_body=html_body,
                cfg=cfg,
                attachments=attachments,
            )
            if ok3:
                return True, msg3 + " (Brevo falhou; usado Gmail Relay.)"

        if not ok and _brevo_activation_failure(msg):
            return False, (
                f"{msg} "
                "Sugestão: se a conta Brevo ainda não estiver activada, use o modo "
                "SendGrid (API HTTPS) em Admin → E-mail."
            )
        return ok, msg

    ok, msg = _send_via_smtp(
        to_email=to_email,
        subject=subject,
        text_body=text_body,
        html_body=html_body,
        cfg=cfg,
    )
    # Se SMTP falhar por rede, tentar HTTPS (SendGrid preferido, depois Brevo)
    if not ok and _connection_blocked_hint(Exception(msg)):
        if (cfg.get("sendgrid_api_key") or "").strip():
            logger.info("SMTP bloqueado — a tentar SendGrid automaticamente")
            ok2, msg2 = _send_via_sendgrid(
                to_email=to_email,
                subject=subject,
                text_body=text_body,
                html_body=html_body,
                cfg=cfg,
                attachments=attachments,
            )
            if ok2:
                return True, msg2 + " (SMTP falhou; usado SendGrid.)"
            msg = f"{msg} | Fallback SendGrid: {msg2}"
        if (cfg.get("brevo_api_key") or "").strip():
            logger.info("SMTP bloqueado — a tentar Brevo automaticamente")
            ok3, msg3 = _send_via_brevo(
                to_email=to_email,
                subject=subject,
                text_body=text_body,
                html_body=html_body,
                cfg=cfg,
                attachments=attachments,
            )
            if ok3:
                return True, msg3 + " (SMTP falhou; usado Brevo.)"
            return False, f"{msg} | Fallback Brevo: {msg3}"
    return ok, msg




def _email_brand_header_html(subtitle: str = "Agência de viagens") -> str:
    """Cabeçalho de marca partilhado (tabelas + estilos inline)."""
    logo = logo_email_data_uri()
    if logo:
        brand_cell = (
            f'<img src="{logo}" alt="SKYTICKETservice" width="96" height="54" '
            f'style="display:block;border:0;outline:none;height:auto;max-width:96px">'
        )
    else:
        brand_cell = (
            '<div style="font-family:Georgia,\'Times New Roman\',serif;font-size:20px;'
            'font-weight:700;letter-spacing:0.04em;color:#ffffff;line-height:1.2">'
            'SKY<span style="color:#e8d5a3">TICKET</span>service</div>'
        )
    sub = _html_escape(subtitle)
    return f"""
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0"
       style="background:#5c0a2c;border-collapse:collapse">
  <tr>
    <td style="padding:18px 22px 14px 22px">
      <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
        <tr>
          <td style="vertical-align:middle;width:110px">{brand_cell}</td>
          <td style="vertical-align:middle;padding-left:14px">
            <div style="font-family:Georgia,'Times New Roman',serif;font-size:18px;
                        font-weight:700;color:#ffffff;letter-spacing:0.03em">
              SKYTICKETservice
            </div>
            <div style="font-family:Segoe UI,Helvetica Neue,Arial,sans-serif;font-size:12px;
                        color:#e8d5a3;margin-top:3px;letter-spacing:0.06em;text-transform:uppercase">
              {sub}
            </div>
          </td>
        </tr>
      </table>
    </td>
  </tr>
  <tr>
    <td style="height:3px;line-height:3px;font-size:0;background-color:#c9a227">&nbsp;</td>
  </tr>
</table>
"""


def _email_brand_footer_html() -> str:
    return f"""
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0"
       style="background:#5c0a2c;border-collapse:collapse">
  <tr>
    <td style="height:3px;line-height:3px;font-size:0;background-color:#c9a227">&nbsp;</td>
  </tr>
  <tr>
    <td style="padding:18px 22px;font-family:Segoe UI,Helvetica Neue,Arial,sans-serif;
               color:#ffffff;font-size:12px;line-height:1.55;text-align:center">
      <strong style="color:#e8d5a3;letter-spacing:0.04em">SKYTICKETservice</strong><br>
      <a href="mailto:{_AGENCY_MAIL}" style="color:#ffffff;text-decoration:underline">{_AGENCY_MAIL}</a>
      &nbsp;·&nbsp;
      <a href="https://wa.me/258849053340" style="color:#e8d5a3;text-decoration:none">WhatsApp {_AGENCY_WA}</a><br>
      <span style="color:#e8d5a3">Nampula · Maputo · Beira · Online · 24h</span>
    </td>
  </tr>
</table>
"""


def _email_shell(inner_html: str, preview_text: str = "") -> str:
    """Envelope 600px email-safe (tabelas + inline)."""
    pre = _html_escape(preview_text) if preview_text else ""
    pre_block = ""
    if pre:
        pre_block = (
            f'<div style="display:none;font-size:1px;line-height:1px;max-height:0;'
            f'max-width:0;opacity:0;overflow:hidden;mso-hide:all">{pre}</div>'
        )
    return f"""<!DOCTYPE html>
<html lang="pt">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta http-equiv="X-UA-Compatible" content="IE=edge">
<title>SKYTICKETservice</title>
</head>
<body style="margin:0;padding:0;background:#f3eee9;-webkit-text-size-adjust:100%;-ms-text-size-adjust:100%">
{pre_block}
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0"
       style="background:#f3eee9;border-collapse:collapse">
  <tr>
    <td align="center" style="padding:24px 12px">
      <table role="presentation" width="600" cellpadding="0" cellspacing="0" border="0"
             style="width:100%;max-width:600px;background:#ffffff;border-collapse:collapse;
                    border:1px solid #e5d9d0">
        <tr><td>{_email_brand_header_html()}</td></tr>
        <tr><td style="padding:0;font-family:Segoe UI,Helvetica Neue,Arial,sans-serif;color:#1a1a1a">
          {inner_html}
        </td></tr>
        <tr><td>{_email_brand_footer_html()}</td></tr>
      </table>
      <div style="font-family:Segoe UI,Arial,sans-serif;font-size:11px;color:#8a7a72;
                  margin-top:14px;text-align:center">
        Mensagem automática da SKYTICKETservice.
      </div>
    </td>
  </tr>
</table>
</body>
</html>
"""


def _reserva_field(reserva, extras: dict | None, key: str, default: str = "—"):
    extras = extras or {}
    try:
        if key in extras and extras.get(key) not in (None, ""):
            return extras[key]
        if isinstance(reserva, dict):
            val = reserva.get(key)
            return default if val in (None, "") else val
        if hasattr(reserva, "keys") and key in reserva.keys() and reserva[key] is not None:
            return reserva[key]
        return default
    except Exception:
        return default


def build_email_eticket_html(
    reserva,
    passageiros_txt: str = "",
    pagamento: str = "",
    extras: dict | None = None,
) -> str:
    """E-ticket leve e polido para EMAIL (tabelas + inline, sem logo grande)."""
    from urllib.parse import quote

    extras = extras or {}

    def g(key, default="—"):
        return _reserva_field(reserva, extras, key, default)

    codigo = str(g("codigo", "—"))
    obs = ""
    try:
        if isinstance(reserva, dict):
            obs = reserva.get("observacoes") or ""
        elif hasattr(reserva, "keys") and "observacoes" in reserva.keys():
            obs = reserva["observacoes"] or ""
    except Exception:
        obs = ""

    companhia = g("ticket_companhia", "") if g("ticket_companhia", "") != "—" else ""
    if not companhia:
        companhia = _parse_obs_field(obs, "Companhia") or "SKYTICKETservice"
    flight_no = g("ticket_flight_no", "")
    if not flight_no or flight_no == "—":
        flight_no = _parse_obs_field(obs, "Voo") or ""
    horario = g("ticket_horario", "")
    if not horario or horario == "—":
        horario = _parse_obs_field(obs, "Horário") or "—"
    horario_chegada = g("ticket_horario_chegada", "—")
    duracao = g("ticket_duracao", "")
    if not duracao or duracao == "—":
        duracao = _parse_obs_field(obs, "Duração") or "—"
    classe = g("classe_nome", "")
    if not classe or classe == "—":
        classe = _parse_obs_field(obs, "Classe") or "—"
    if not pagamento:
        pagamento = _parse_obs_field(obs, "Pagamento") or "—"

    o_cid = str(g("origem_cidade", "") or "")
    o_pais = str(g("origem_pais", "") or "")
    d_cid = str(g("destino_cidade", "") or "")
    d_pais = str(g("destino_pais", "") or "")
    origem = f"{o_cid}, {o_pais}".strip(", ") or "—"
    destino = f"{d_cid}, {d_pais}".strip(", ") or "—"

    total = _format_money(
        g("total", 0) if g("total", 0) != "—" else 0, str(g("moeda", "USD") or "USD")
    )
    tipo = "Ida e volta" if g("tipo_viagem") == "ida_volta" else "Só ida"
    data_viagem = str(g("data_viagem", "—") or "—")
    data_regresso = str(g("data_regresso", "") or "")
    nome = str(g("nome", "") or g("cliente_nome", "") or "")
    status = str(g("status", "confirmada") or "confirmada")

    pax_html = passageiros_txt.strip() if passageiros_txt else _html_escape(nome or "—")

    wa_msg = (
        f"Olá SKYTICKETservice, tenho uma dúvida sobre a reserva {codigo} "
        f"({origem} → {destino})."
    )
    wa_href = f"https://wa.me/258849053340?text={quote(wa_msg)}"

    meta_pills = []
    if flight_no:
        meta_pills.append(_html_escape(str(flight_no)))
    if classe and classe != "—":
        meta_pills.append(_html_escape(str(classe)))
    meta_pills.append(_html_escape(tipo))
    pills = " · ".join(meta_pills)

    chegada_row = ""
    if horario_chegada and horario_chegada != "—":
        chegada_row = f"""
        <tr>
          <td style="padding:8px 0;color:#6b5a55;width:38%;font-size:13px">Chegada</td>
          <td style="padding:8px 0;font-size:15px;font-weight:700;color:#5c0a2c">{_html_escape(horario_chegada)}</td>
        </tr>"""

    regresso_row = ""
    if data_regresso:
        regresso_row = f"""
        <tr>
          <td style="padding:8px 0;color:#6b5a55;width:38%;font-size:13px">Regresso</td>
          <td style="padding:8px 0;font-size:14px;color:#1a1a1a">{_html_escape(data_regresso)}</td>
        </tr>"""

    inner = f"""
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="border-collapse:collapse">
  <tr>
    <td style="padding:22px 22px 8px 22px">
      <div style="font-size:13px;color:#6b5a55;letter-spacing:0.08em;text-transform:uppercase">
        Confirmação de reserva
      </div>
      <div style="font-size:22px;font-weight:700;color:#5c0a2c;margin-top:4px;font-family:Georgia,'Times New Roman',serif">
        O seu e-ticket está pronto
      </div>
      <p style="margin:10px 0 0;font-size:14px;line-height:1.5;color:#333">
        Olá <strong>{_html_escape(nome or "Cliente")}</strong>, a sua reserva foi confirmada.
        Guarde este e-mail e apresente o código no check-in.
      </p>
    </td>
  </tr>

  <tr>
    <td style="padding:8px 22px 18px 22px">
      <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0"
             style="border-collapse:collapse;background:#faf6f2;border:1px solid #e8d5a3">
        <tr>
          <td style="padding:16px 18px;text-align:center">
            <div style="font-size:11px;letter-spacing:0.14em;text-transform:uppercase;color:#c9a227;font-weight:700">
              Código de reserva
            </div>
            <div style="font-size:28px;font-weight:800;letter-spacing:0.12em;color:#5c0a2c;
                        font-family:Consolas,'Courier New',monospace;margin-top:6px">
              {_html_escape(codigo)}
            </div>
            <div style="font-size:12px;color:#6b5a55;margin-top:6px">
              Estado: <strong style="color:#5c0a2c">{_html_escape(status)}</strong>
            </div>
          </td>
        </tr>
      </table>
    </td>
  </tr>

  <tr>
    <td style="padding:0 22px 18px 22px">
      <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0"
             style="border-collapse:collapse;background:#5c0a2c">
        <tr>
          <td width="42%" style="padding:18px 14px;text-align:center;vertical-align:middle">
            <div style="font-size:11px;color:#e8d5a3;letter-spacing:0.1em;text-transform:uppercase">Origem</div>
            <div style="font-size:16px;font-weight:700;color:#ffffff;margin-top:6px;line-height:1.3">
              {_html_escape(origem)}
            </div>
          </td>
          <td width="16%" style="padding:10px 4px;text-align:center;vertical-align:middle;color:#c9a227;font-size:22px">
            &#9992;
          </td>
          <td width="42%" style="padding:18px 14px;text-align:center;vertical-align:middle">
            <div style="font-size:11px;color:#e8d5a3;letter-spacing:0.1em;text-transform:uppercase">Destino</div>
            <div style="font-size:16px;font-weight:700;color:#ffffff;margin-top:6px;line-height:1.3">
              {_html_escape(destino)}
            </div>
          </td>
        </tr>
      </table>
      <div style="font-size:12px;color:#6b5a55;margin-top:8px;text-align:center">{pills}</div>
    </td>
  </tr>

  <tr>
    <td style="padding:0 22px 8px 22px">
      <div style="font-size:12px;letter-spacing:0.1em;text-transform:uppercase;color:#c9a227;font-weight:700;margin-bottom:6px">
        Detalhes do voo
      </div>
      <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0"
             style="border-collapse:collapse;font-family:Segoe UI,Helvetica Neue,Arial,sans-serif">
        <tr>
          <td style="padding:8px 0;color:#6b5a55;width:38%;font-size:13px;border-top:1px solid #eee4dc">Companhia</td>
          <td style="padding:8px 0;font-size:14px;color:#1a1a1a;border-top:1px solid #eee4dc">{_html_escape(companhia)}</td>
        </tr>
        <tr>
          <td style="padding:8px 0;color:#6b5a55;font-size:13px;border-top:1px solid #eee4dc">Data</td>
          <td style="padding:8px 0;font-size:14px;color:#1a1a1a;border-top:1px solid #eee4dc">{_html_escape(data_viagem)}</td>
        </tr>
        {regresso_row}
        <tr>
          <td style="padding:8px 0;color:#6b5a55;font-size:13px;border-top:1px solid #eee4dc">Partida</td>
          <td style="padding:8px 0;font-size:18px;font-weight:700;color:#5c0a2c;border-top:1px solid #eee4dc">{_html_escape(str(horario))}</td>
        </tr>
        {chegada_row}
        <tr>
          <td style="padding:8px 0;color:#6b5a55;font-size:13px;border-top:1px solid #eee4dc">Duração</td>
          <td style="padding:8px 0;font-size:14px;color:#1a1a1a;border-top:1px solid #eee4dc">{_html_escape(str(duracao))}</td>
        </tr>
        <tr>
          <td style="padding:8px 0;color:#6b5a55;font-size:13px;border-top:1px solid #eee4dc">Pagamento</td>
          <td style="padding:8px 0;font-size:14px;color:#1a1a1a;border-top:1px solid #eee4dc">{_html_escape(str(pagamento))}</td>
        </tr>
        <tr>
          <td style="padding:8px 0;color:#6b5a55;font-size:13px;border-top:1px solid #eee4dc">Total</td>
          <td style="padding:8px 0;font-size:18px;font-weight:800;color:#5c0a2c;border-top:1px solid #eee4dc">{_html_escape(total)}</td>
        </tr>
      </table>
    </td>
  </tr>

  <tr>
    <td style="padding:14px 22px 8px 22px">
      <div style="font-size:12px;letter-spacing:0.1em;text-transform:uppercase;color:#c9a227;font-weight:700;margin-bottom:8px">
        Passageiros
      </div>
      <div style="font-size:13px;line-height:1.55;color:#1a1a1a;background:#faf6f2;padding:12px 14px;border:1px solid #eee4dc">
        {pax_html}
      </div>
    </td>
  </tr>

  <tr>
    <td style="padding:20px 22px 26px 22px" align="center">
      <table role="presentation" cellpadding="0" cellspacing="0" border="0" style="border-collapse:collapse;margin:0 auto">
        <tr>
          <td style="background:#c9a227;border-radius:4px">
            <a href="{wa_href}"
               style="display:inline-block;padding:14px 28px;font-family:Segoe UI,Arial,sans-serif;
                      font-size:14px;font-weight:700;color:#5c0a2c;text-decoration:none;
                      letter-spacing:0.03em">
              Falar no WhatsApp
            </a>
          </td>
        </tr>
      </table>
      <div style="font-size:12px;color:#6b5a55;margin-top:12px;line-height:1.45">
        Dúvidas? Escreva-nos em {_html_escape(_AGENCY_MAIL)} ou WhatsApp {_html_escape(_AGENCY_WA)}.
      </div>
    </td>
  </tr>
</table>
"""
    html = _email_shell(
        inner,
        preview_text=f"Reserva {codigo} confirmada · {origem} → {destino} · {total}",
    )
    return _slim_html_for_email(html)



# --- PDF e-ticket (reportlab) — inserted before _slim_html_for_email ---

def _pdf_logo_path() -> Path | None:
    for p in (
        Path(__file__).resolve().parent / "static" / "img" / "logo-official.png",
        Path(__file__).resolve().parent / "static" / "img" / "logo.jpg",
        LOGO_FULL_PATH,
        LOGO_PATH,
    ):
        if p.exists():
            return p
    return None


def build_eticket_pdf(
    reserva,
    passageiros_txt: str = "",
    pagamento: str = "",
    extras: dict | None = None,
) -> bytes:
    """PDF boarding-pass com logo oficial (reportlab)."""
    from io import BytesIO
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.lib.colors import Color, HexColor, white, black
    from reportlab.pdfgen import canvas
    from reportlab.lib.utils import ImageReader
    import re as _re

    extras = extras or {}

    def g(key, default="—"):
        return _reserva_field(reserva, extras, key, default)

    codigo = str(g("codigo", "—"))
    obs = ""
    try:
        if isinstance(reserva, dict):
            obs = reserva.get("observacoes") or ""
        elif hasattr(reserva, "keys") and "observacoes" in reserva.keys():
            obs = reserva["observacoes"] or ""
    except Exception:
        obs = ""

    companhia = g("ticket_companhia", "") if g("ticket_companhia", "") != "—" else ""
    if not companhia:
        companhia = _parse_obs_field(obs, "Companhia") or "SKYTICKETservice"
    flight_no = g("ticket_flight_no", "")
    if not flight_no or flight_no == "—":
        flight_no = _parse_obs_field(obs, "Voo") or "—"
    horario = g("ticket_horario", "")
    if not horario or horario == "—":
        horario = _parse_obs_field(obs, "Horário") or "—"
    horario_chegada = g("ticket_horario_chegada", "—")
    duracao = g("ticket_duracao", "")
    if not duracao or duracao == "—":
        duracao = _parse_obs_field(obs, "Duração") or "—"
    classe = g("classe_nome", "")
    if not classe or classe == "—":
        classe = _parse_obs_field(obs, "Classe") or "—"
    if not pagamento:
        pagamento = _parse_obs_field(obs, "Pagamento") or "—"

    o_cid = str(g("origem_cidade", "") or "")
    o_pais = str(g("origem_pais", "") or "")
    d_cid = str(g("destino_cidade", "") or "")
    d_pais = str(g("destino_pais", "") or "")
    origem = f"{o_cid}, {o_pais}".strip(", ") or "—"
    destino = f"{d_cid}, {d_pais}".strip(", ") or "—"
    total = _format_money(
        g("total", 0) if g("total", 0) != "—" else 0, str(g("moeda", "USD") or "USD")
    )
    tipo = "Ida e volta" if g("tipo_viagem") == "ida_volta" else "Só ida"
    data_viagem = str(g("data_viagem", "—") or "—")
    data_regresso = str(g("data_regresso", "") or "")
    nome = str(g("nome", "") or g("cliente_nome", "") or "—")
    status = str(g("status", "confirmada") or "confirmada")

    pax_plain = _re.sub(r"<[^>]+>", " ", passageiros_txt or "")
    pax_plain = _re.sub(r"\s+", " ", pax_plain).strip() or nome

    bordo = HexColor("#5c0a2c")
    gold = HexColor("#c9a227")
    gold_lt = HexColor("#e8d5a3")
    cream = HexColor("#faf6f2")
    muted = HexColor("#6b5a55")

    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    W, H = A4
    margin = 18 * mm

    # Background
    c.setFillColor(HexColor("#f3eee9"))
    c.rect(0, 0, W, H, fill=1, stroke=0)

    # Card
    card_x, card_y = margin, margin
    card_w, card_h = W - 2 * margin, H - 2 * margin
    c.setFillColor(white)
    c.setStrokeColor(HexColor("#e5d9d0"))
    c.setLineWidth(1)
    c.roundRect(card_x, card_y, card_w, card_h, 6, fill=1, stroke=1)

    # Header bar
    head_h = 32 * mm
    c.setFillColor(bordo)
    c.rect(card_x, card_y + card_h - head_h, card_w, head_h, fill=1, stroke=0)
    # Gold line
    c.setFillColor(gold)
    c.rect(card_x, card_y + card_h - head_h - 2.2 * mm, card_w, 2.2 * mm, fill=1, stroke=0)

    logo_p = _pdf_logo_path()
    if logo_p:
        try:
            img = ImageReader(str(logo_p))
            iw, ih = img.getSize()
            max_w, max_h = 28 * mm, 18 * mm
            scale = min(max_w / iw, max_h / ih)
            lw, lh = iw * scale, ih * scale
            c.drawImage(
                img,
                card_x + 8 * mm,
                card_y + card_h - head_h + (head_h - lh) / 2,
                width=lw,
                height=lh,
                mask="auto",
                preserveAspectRatio=True,
            )
            text_x = card_x + 8 * mm + lw + 6 * mm
        except Exception:
            text_x = card_x + 10 * mm
            logo_p = None
    if not logo_p:
        text_x = card_x + 10 * mm

    c.setFillColor(white)
    c.setFont("Helvetica-Bold", 16)
    c.drawString(text_x, card_y + card_h - 14 * mm, "SKYTICKETservice")
    c.setFillColor(gold_lt)
    c.setFont("Helvetica", 9)
    c.drawString(text_x, card_y + card_h - 20 * mm, "E-TICKET  ·  BOARDING PASS")

    y = card_y + card_h - head_h - 14 * mm

    # Booking code box
    c.setFillColor(cream)
    c.setStrokeColor(gold_lt)
    c.roundRect(card_x + 10 * mm, y - 18 * mm, card_w - 20 * mm, 22 * mm, 4, fill=1, stroke=1)
    c.setFillColor(gold)
    c.setFont("Helvetica-Bold", 8)
    c.drawCentredString(card_x + card_w / 2, y - 2 * mm, "CÓDIGO DE RESERVA")
    c.setFillColor(bordo)
    c.setFont("Courier-Bold", 22)
    c.drawCentredString(card_x + card_w / 2, y - 11 * mm, codigo)
    c.setFillColor(muted)
    c.setFont("Helvetica", 9)
    c.drawCentredString(card_x + card_w / 2, y - 16 * mm, f"Estado: {status}  ·  {tipo}")
    y -= 30 * mm

    # Route bar
    c.setFillColor(bordo)
    c.roundRect(card_x + 10 * mm, y - 22 * mm, card_w - 20 * mm, 26 * mm, 4, fill=1, stroke=0)
    c.setFillColor(gold_lt)
    c.setFont("Helvetica", 8)
    c.drawCentredString(card_x + 10 * mm + (card_w - 20 * mm) * 0.22, y - 2 * mm, "ORIGEM")
    c.drawCentredString(card_x + 10 * mm + (card_w - 20 * mm) * 0.78, y - 2 * mm, "DESTINO")
    c.setFillColor(white)
    c.setFont("Helvetica-Bold", 11)
    # wrap origin/dest if long
    def _fit(txt, max_chars=28):
        t = str(txt)
        return t if len(t) <= max_chars else t[: max_chars - 1] + "…"

    c.drawCentredString(card_x + 10 * mm + (card_w - 20 * mm) * 0.22, y - 10 * mm, _fit(origem))
    c.drawCentredString(card_x + 10 * mm + (card_w - 20 * mm) * 0.78, y - 10 * mm, _fit(destino))
    c.setFillColor(gold)
    c.setFont("Helvetica-Bold", 16)
    c.drawCentredString(card_x + card_w / 2, y - 10 * mm, "✈")
    c.setFillColor(gold_lt)
    c.setFont("Helvetica", 8)
    c.drawCentredString(card_x + card_w / 2, y - 18 * mm, f"{flight_no}  ·  {classe}")
    y -= 36 * mm

    # Details
    c.setFillColor(bordo)
    c.setFont("Helvetica-Bold", 10)
    c.drawString(card_x + 12 * mm, y, "DETALHES DO VOO")
    y -= 8 * mm
    c.setStrokeColor(gold_lt)
    c.setLineWidth(0.6)
    c.line(card_x + 12 * mm, y + 4 * mm, card_x + card_w - 12 * mm, y + 4 * mm)

    rows = [
        ("Companhia", str(companhia)),
        ("Voo", str(flight_no)),
        ("Data", data_viagem),
    ]
    if data_regresso:
        rows.append(("Regresso", data_regresso))
    rows.extend(
        [
            ("Partida", str(horario)),
            ("Chegada", str(horario_chegada)),
            ("Duração", str(duracao)),
            ("Classe", str(classe)),
            ("Pagamento", str(pagamento)),
            ("Total", total),
        ]
    )

    for label, val in rows:
        c.setFillColor(muted)
        c.setFont("Helvetica", 9)
        c.drawString(card_x + 12 * mm, y, label)
        c.setFillColor(black if label != "Total" else bordo)
        c.setFont("Helvetica-Bold" if label in ("Total", "Partida") else "Helvetica", 10 if label == "Total" else 9)
        c.drawRightString(card_x + card_w - 12 * mm, y, str(val)[:48])
        y -= 6.2 * mm

    y -= 4 * mm
    c.setFillColor(bordo)
    c.setFont("Helvetica-Bold", 10)
    c.drawString(card_x + 12 * mm, y, "PASSAGEIROS")
    y -= 6 * mm
    c.setFillColor(cream)
    c.setStrokeColor(HexColor("#eee4dc"))
    box_h = 28 * mm
    c.roundRect(card_x + 10 * mm, y - box_h + 4 * mm, card_w - 20 * mm, box_h, 3, fill=1, stroke=1)
    c.setFillColor(black)
    c.setFont("Helvetica", 9)
    # wrap passenger text
    from reportlab.pdfbase.pdfmetrics import stringWidth

    max_w = card_w - 28 * mm
    words = pax_plain.split()
    lines, cur = [], ""
    for w in words:
        trial = (cur + " " + w).strip()
        if stringWidth(trial, "Helvetica", 9) <= max_w:
            cur = trial
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    ty = y - 2 * mm
    for line in lines[:8]:
        c.drawString(card_x + 14 * mm, ty, line)
        ty -= 4.5 * mm

    # Footer
    c.setFillColor(bordo)
    foot_h = 18 * mm
    c.rect(card_x, card_y, card_w, foot_h, fill=1, stroke=0)
    c.setFillColor(gold)
    c.rect(card_x, card_y + foot_h, card_w, 1.8 * mm, fill=1, stroke=0)
    c.setFillColor(gold_lt)
    c.setFont("Helvetica-Bold", 9)
    c.drawCentredString(card_x + card_w / 2, card_y + 11 * mm, "SKYTICKETservice")
    c.setFillColor(white)
    c.setFont("Helvetica", 8)
    c.drawCentredString(
        card_x + card_w / 2,
        card_y + 6 * mm,
        f"{_AGENCY_MAIL}  ·  WhatsApp {_AGENCY_WA}",
    )
    c.setFillColor(gold_lt)
    c.setFont("Helvetica", 7)
    c.drawCentredString(
        card_x + card_w / 2,
        card_y + 2.5 * mm,
        "Nampula · Maputo · Beira · Online · 24h",
    )

    c.setTitle(f"E-Ticket {codigo} — SKYTICKETservice")
    c.setAuthor("SKYTICKETservice")
    c.showPage()
    c.save()
    return buf.getvalue()


def save_eticket_pdf(codigo: str, pdf_bytes: bytes) -> Path:
    TICKETS_DIR.mkdir(parents=True, exist_ok=True)
    path = TICKETS_DIR / f"{codigo}.pdf"
    path.write_bytes(pdf_bytes)
    return path


def _slim_html_for_email(html: str) -> str:
    """Remove imagens data-URI enormes (logo) para caber no limite do GmailApp."""
    if not html:
        return html
    # Remove <img ... src="data:..."> blocks
    slim = re.sub(
        r'<img\b[^>]*src=["\']data:image/[^"\']+["\'][^>]*/?>',
        '<div style="font-weight:800;color:#5c0a2c;letter-spacing:.08em">SKYTICKETservice</div>',
        html,
        flags=re.I,
    )
    # Safety truncate if still huge
    if len(slim) > 90_000:
        slim = slim[:90_000] + "<p>... (conteúdo truncado para envio por e-mail)</p>"
    return slim


def send_confirmation_email(
    to_email: str,
    codigo: str,
    html_ticket: str,
    nome: str = "",
    reserva=None,
    passageiros_txt: str = "",
    pagamento: str = "",
    extras: dict | None = None,
) -> tuple[bool, str]:
    """Guarda o e-ticket HTML completo e envia versão leve + PDF por e-mail."""
    path = save_eticket(codigo, html_ticket)
    cfg = load_smtp_config()
    ready, reason = smtp_is_ready(cfg)

    if not (to_email or "").strip():
        return False, f"Bilhete guardado em {path.name}. Passageiro sem e-mail."

    if not ready:
        return (
            False,
            f"Bilhete guardado em {path.name}. {reason} "
            f"Configure em Admin → E-mail / SMTP.",
        )

    email_html = ""
    if reserva is not None:
        try:
            email_html = build_email_eticket_html(
                reserva,
                passageiros_txt=passageiros_txt,
                pagamento=pagamento,
                extras=extras,
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("build_email_eticket_html falhou: %s", exc)
            email_html = ""
    if not email_html:
        email_html = _slim_html_for_email(html_ticket)

    attachments: list[dict] = []
    pdf_path = None
    try:
        src = reserva if reserva is not None else {"codigo": codigo, "nome": nome}
        pdf_bytes = build_eticket_pdf(
            src,
            passageiros_txt=passageiros_txt,
            pagamento=pagamento,
            extras=extras,
        )
        pdf_path = save_eticket_pdf(codigo, pdf_bytes)
        attachments.append(
            {
                "filename": f"SKYTICKET-{codigo}.pdf",
                "content": pdf_bytes,
                "mime_type": "application/pdf",
            }
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("PDF e-ticket falhou: %s", exc)

    text_body = (
        f"Olá {nome or ''},\n\n"
        f"A sua reserva {codigo} foi confirmada com sucesso na SKYTICKETservice.\n\n"
        f"Encontra em anexo o bilhete em PDF e, em baixo, o resumo da reserva.\n"
        f"Guarde este e-mail e apresente o código {codigo} no check-in.\n\n"
        f"Qualquer dúvida:\n"
        f"E-mail: skyticketservicee@gmail.com\n"
        f"WhatsApp: +258 84 905 3340\n"
        f"Nampula · Maputo · Beira · Online · 24h\n\n"
        f"Obrigado por viajar connosco.\n"
        f"SKYTICKETservice\n"
    )

    ok, msg = _send_raw(
        to_email=to_email,
        subject=f"SKYTICKETservice — Confirmação e e-ticket {codigo}",
        text_body=text_body,
        html_body=email_html,
        cfg=cfg,
        attachments=attachments or None,
    )
    if ok:
        extra = f" PDF: {pdf_path.name}." if pdf_path else ""
        return True, f"Confirmação e e-ticket enviados para {to_email.strip()}.{extra}"
    return False, f"{msg} Bilhete guardado em {path.name}."


def send_test_email(to_email: str) -> tuple[bool, str]:
    """Envia e-mail de teste com a configuração actual."""
    cfg = load_smtp_config()
    ready, reason = smtp_is_ready(cfg)
    if not ready:
        return False, reason
    dest = (to_email or cfg.get("user") or "").strip()
    if not dest:
        return False, "Indique um e-mail de destino para o teste."

    provider = (cfg.get("provider") or "smtp").upper()
    html = f"""
    <div style="font-family:Segoe UI,Arial,sans-serif;padding:24px;color:#0b1f3a">
      <h2 style="color:#0b1f3a">Teste de e-mail — SKYTICKETservice</h2>
      <p>Se recebeu esta mensagem, o envio de e-mail está a funcionar correctamente.</p>
      <p><strong>Modo:</strong> {provider}<br>
         <strong>Remetente:</strong> {cfg.get('mail_from') or cfg.get('user')}</p>
      <p style="color:#5c6b7a;font-size:.9rem">
        Os e-tickets de reserva serão enviados para o e-mail do passageiro principal.
      </p>
    </div>
    """
    text = (
        "Teste de e-mail — SKYTICKETservice\n\n"
        "Se recebeu esta mensagem, o envio de e-mail está a funcionar.\n"
    )
    return _send_raw(
        to_email=dest,
        subject="SKYTICKETservice — Teste de e-mail",
        text_body=text,
        html_body=html,
        cfg=cfg,
    )

# ---------------------------------------------------------------------------
# Notificações de estado (visto / reserva) — sempre From mail_from da agência
# ---------------------------------------------------------------------------


_STATUS_VISTO_LABELS: dict[str, str] = {
    "pendente": "Pendente",
    "em_analise": "Em análise",
    "contactado": "Contactado",
    "concluido": "Concluído / emitido",
    "cancelado": "Cancelado",
}

_STATUS_RESERVA_LABELS: dict[str, str] = {
    "pendente": "Pendente",
    "confirmada": "Confirmada",
    "cancelada": "Cancelada",
}




def _row_get(row: Any, key: str, default: Any = "") -> Any:
    """Lê chave de dict, sqlite3.Row ou objecto similar."""
    if row is None:
        return default
    try:
        if isinstance(row, dict):
            val = row.get(key, default)
            return default if val is None else val
        if hasattr(row, "keys") and key in row.keys():
            val = row[key]
            return default if val is None else val
        val = getattr(row, key, default)
        return default if val is None else val
    except Exception:
        return default


def _agency_email_footer_html() -> str:
    """Compat: footer de marca (usa o mesmo bloco do envelope de e-mail)."""
    return _email_brand_footer_html()


def _agency_email_footer_text() -> str:
    return (
        f"\n---\n"
        f"SKYTICKETservice\n"
        f"E-mail: {_AGENCY_MAIL}\n"
        f"WhatsApp: {_AGENCY_WA}\n"
        f"Nampula · Maputo · Beira · Online · 24h\n"
    )


def _wrap_status_html(title: str, body_html: str) -> str:
    inner = f"""
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="border-collapse:collapse">
  <tr>
    <td style="padding:22px 22px 8px 22px">
      <div style="font-size:12px;letter-spacing:0.1em;text-transform:uppercase;color:#c9a227;font-weight:700">
        SKYTICKETservice
      </div>
      <h2 style="margin:6px 0 14px;color:#5c0a2c;font-size:20px;font-family:Georgia,'Times New Roman',serif">
        {_html_escape(title)}
      </h2>
      <div style="font-size:14px;line-height:1.55;color:#1a1a1a">{body_html}</div>
    </td>
  </tr>
</table>
"""
    return _email_shell(inner, preview_text=title)


def send_status_email(
    to_email: str,
    subject: str,
    html_body: str,
    text_body: str,
    attachments: list[dict] | None = None,
) -> tuple[bool, str]:
    """Wrapper fino sobre ``_send_raw`` com a configuração da agência (mail_from)."""
    cfg = load_smtp_config()
    return _send_raw(
        to_email=to_email,
        subject=subject,
        text_body=text_body,
        html_body=html_body,
        cfg=cfg,
        attachments=attachments,
    )


def send_visa_notification_email(
    pedido_dict: Any,
    novo_status: str,
) -> tuple[bool, str]:
    """E-mail em português sobre o novo estado do pedido de visto.

    Remetente: sempre ``mail_from`` / from_name SKYTICKETservice.
    """
    to_email = str(_row_get(pedido_dict, "email", "")).strip()
    nome = str(_row_get(pedido_dict, "nome", "")).strip() or "Cliente"
    codigo = str(_row_get(pedido_dict, "codigo", "")).strip() or "—"
    destino = str(_row_get(pedido_dict, "pais_destino", "")).strip() or "—"
    nacionalidade = str(_row_get(pedido_dict, "nacionalidade", "")).strip() or "—"
    status = (novo_status or str(_row_get(pedido_dict, "status", ""))).strip()
    label = _STATUS_VISTO_LABELS.get(status, status.replace("_", " ").title())

    if status == "concluido":
        subject = f"Visto emitido / concluído — {codigo}"
        lead = (
            f"Temos o prazer de informar que o seu pedido de visto "
            f"<strong>{_html_escape(codigo)}</strong> foi "
            f"<strong>concluído / emitido</strong>."
        )
        lead_txt = (
            f"Temos o prazer de informar que o seu pedido de visto {codigo} "
            f"foi concluído / emitido."
        )
    elif status == "cancelado":
        subject = f"Pedido de visto cancelado — {codigo}"
        lead = (
            f"O seu pedido de visto <strong>{_html_escape(codigo)}</strong> "
            f"foi <strong>cancelado</strong>."
        )
        lead_txt = f"O seu pedido de visto {codigo} foi cancelado."
    elif status == "em_analise":
        subject = f"Pedido de visto em análise — {codigo}"
        lead = (
            f"O seu pedido de visto <strong>{_html_escape(codigo)}</strong> "
            f"está agora <strong>em análise</strong> pela nossa equipa."
        )
        lead_txt = (
            f"O seu pedido de visto {codigo} está agora em análise pela nossa equipa."
        )
    elif status == "contactado":
        subject = f"Pedido de visto — contacto da agência — {codigo}"
        lead = (
            f"Actualizámos o estado do pedido <strong>{_html_escape(codigo)}</strong> "
            f"para <strong>contactado</strong>. Em breve (ou já) entraremos em "
            f"contacto consigo pelos dados fornecidos."
        )
        lead_txt = (
            f"Actualizámos o estado do pedido {codigo} para contactado. "
            f"Em breve (ou já) entraremos em contacto consigo."
        )
    elif status == "pendente":
        subject = f"Pedido de visto recebido — {codigo}"
        lead = (
            f"Recebemos o seu pedido de visto "
            f"<strong>{_html_escape(codigo)}</strong>. "
            f"A nossa equipa irá analisá-lo e contactá-lo em breve."
        )
        lead_txt = (
            f"Recebemos o seu pedido de visto {codigo}. "
            f"A nossa equipa irá analisá-lo e contactá-lo em breve."
        )
    else:
        subject = f"Actualização do pedido de visto — {codigo}"
        lead = (
            f"O estado do seu pedido de visto "
            f"<strong>{_html_escape(codigo)}</strong> foi actualizado para "
            f"<strong>{_html_escape(label)}</strong>."
        )
        lead_txt = (
            f"O estado do seu pedido de visto {codigo} foi actualizado para {label}."
        )

    body_html = f"""
      <p>Olá {_html_escape(nome)},</p>
      <p>{lead}</p>
      <table style="width:100%;border-collapse:collapse;margin:18px 0;
                    font-size:.95rem">
        <tr>
          <td style="padding:8px 0;color:#5c6b7a;width:42%">Código</td>
          <td style="padding:8px 0"><strong>{_html_escape(codigo)}</strong></td>
        </tr>
        <tr>
          <td style="padding:8px 0;color:#5c6b7a">Estado</td>
          <td style="padding:8px 0"><strong>{_html_escape(label)}</strong></td>
        </tr>
        <tr>
          <td style="padding:8px 0;color:#5c6b7a">Destino</td>
          <td style="padding:8px 0">{_html_escape(destino)}</td>
        </tr>
        <tr>
          <td style="padding:8px 0;color:#5c6b7a">Nacionalidade</td>
          <td style="padding:8px 0">{_html_escape(nacionalidade)}</td>
        </tr>
      </table>
      <p style="color:#5c6b7a;font-size:.92rem">
        Se tiver dúvidas, responda a este e-mail ou contacte-nos por WhatsApp.
      </p>
    """
    html = _wrap_status_html("SKYTICKETservice — Pedido de visto", body_html)
    text = (
        f"Olá {nome},\n\n"
        f"{lead_txt}\n\n"
        f"Código: {codigo}\n"
        f"Estado: {label}\n"
        f"Destino: {destino}\n"
        f"Nacionalidade: {nacionalidade}\n"
        f"{_agency_email_footer_text()}"
    )
    return send_status_email(to_email, subject, html, text)


def send_reserva_status_email(
    row_dict: Any,
    novo_status: str,
) -> tuple[bool, str]:
    """Notifica o cliente quando a reserva é confirmada ou cancelada.

    Tenta reconstruir o e-ticket HTML se houver dados suficientes (opcional);
    caso contrário envia apenas a mensagem de estado.
    """
    to_email = str(
        _row_get(row_dict, "email", "")
        or _row_get(row_dict, "cliente_email", "")
    ).strip()
    nome = str(
        _row_get(row_dict, "cliente_nome", "")
        or _row_get(row_dict, "nome", "")
    ).strip() or "Cliente"
    codigo = str(_row_get(row_dict, "codigo", "")).strip() or "—"
    status = (novo_status or str(_row_get(row_dict, "status", ""))).strip()
    label = _STATUS_RESERVA_LABELS.get(status, status)
    total = _row_get(row_dict, "total", 0)
    moeda = str(_row_get(row_dict, "moeda", "USD") or "USD")
    total_fmt = _format_money(total, moeda)

    o_cid = str(_row_get(row_dict, "origem_cidade", "") or "")
    o_pais = str(_row_get(row_dict, "origem_pais", "") or "")
    d_cid = str(_row_get(row_dict, "destino_cidade", "") or "")
    d_pais = str(_row_get(row_dict, "destino_pais", "") or "")
    rota = f"{o_cid or o_pais} → {d_cid or d_pais}".strip(" →") or "—"
    data_viagem = str(_row_get(row_dict, "data_viagem", "") or "—")

    ticket_html = ""
    if status == "confirmada":
        try:
            # Reconstruir e-ticket simples a partir da linha (sem passageiros detalhados)
            ticket_html = build_email_eticket_html(
                row_dict if isinstance(row_dict, dict) else dict(row_dict),
                passageiros_txt=_html_escape(nome),
                pagamento="",
                extras={"nome": nome, "email": to_email, "status": status},
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("Não foi possível reconstruir e-ticket: %s", exc)
            ticket_html = ""

    if status == "confirmada":
        subject = f"SKYTICKETservice — Bilhete / reserva confirmada {codigo}"
        lead = (
            f"A sua reserva <strong>{_html_escape(codigo)}</strong> foi "
            f"<strong>confirmada</strong>. O bilhete electrónico (e-ticket) "
            f"segue em baixo quando disponível."
        )
        lead_txt = (
            f"A sua reserva {codigo} foi confirmada. "
            f"Guarde este e-mail e apresente o código {codigo} no check-in."
        )
    elif status == "cancelada":
        subject = f"SKYTICKETservice — Reserva cancelada {codigo}"
        lead = (
            f"Informamos que a reserva <strong>{_html_escape(codigo)}</strong> "
            f"foi <strong>cancelada</strong>."
        )
        lead_txt = f"Informamos que a reserva {codigo} foi cancelada."
    else:
        subject = f"SKYTICKETservice — Actualização da reserva {codigo}"
        lead = (
            f"O estado da reserva <strong>{_html_escape(codigo)}</strong> "
            f"foi actualizado para <strong>{_html_escape(label)}</strong>."
        )
        lead_txt = (
            f"O estado da reserva {codigo} foi actualizado para {label}."
        )

    body_html = f"""
      <p>Olá {_html_escape(nome)},</p>
      <p>{lead}</p>
      <table style="width:100%;border-collapse:collapse;margin:18px 0;
                    font-size:.95rem">
        <tr>
          <td style="padding:8px 0;color:#5c6b7a;width:42%">Código</td>
          <td style="padding:8px 0"><strong>{_html_escape(codigo)}</strong></td>
        </tr>
        <tr>
          <td style="padding:8px 0;color:#5c6b7a">Estado</td>
          <td style="padding:8px 0"><strong>{_html_escape(label)}</strong></td>
        </tr>
        <tr>
          <td style="padding:8px 0;color:#5c6b7a">Rota</td>
          <td style="padding:8px 0">{_html_escape(rota)}</td>
        </tr>
        <tr>
          <td style="padding:8px 0;color:#5c6b7a">Data de viagem</td>
          <td style="padding:8px 0">{_html_escape(data_viagem)}</td>
        </tr>
        <tr>
          <td style="padding:8px 0;color:#5c6b7a">Total</td>
          <td style="padding:8px 0">{_html_escape(total_fmt)}</td>
        </tr>
      </table>
    """
    status_html = _wrap_status_html("SKYTICKETservice — Reserva", body_html)
    html = status_html
    if ticket_html and status == "confirmada":
        html = status_html + "\n" + ticket_html

    text = (
        f"Olá {nome},\n\n"
        f"{lead_txt}\n\n"
        f"Código: {codigo}\n"
        f"Estado: {label}\n"
        f"Rota: {rota}\n"
        f"Data de viagem: {data_viagem}\n"
        f"Total: {total_fmt}\n"
        f"{_agency_email_footer_text()}"
    )
    attachments = None
    if status == "confirmada":
        try:
            pdf_bytes = build_eticket_pdf(
                row_dict if isinstance(row_dict, dict) else dict(row_dict),
                passageiros_txt=_html_escape(nome),
                extras={"nome": nome, "email": to_email, "status": status},
            )
            save_eticket_pdf(codigo, pdf_bytes)
            attachments = [
                {
                    "filename": f"SKYTICKET-{codigo}.pdf",
                    "content": pdf_bytes,
                    "mime_type": "application/pdf",
                }
            ]
        except Exception as exc:  # noqa: BLE001
            logger.warning("PDF status e-ticket falhou: %s", exc)
    return send_status_email(to_email, subject, html, text, attachments=attachments)
