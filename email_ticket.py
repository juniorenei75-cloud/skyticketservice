"""Confirmação por e-mail e bilhete electrónico (e-ticket).

Dois modos de envio:
1. **brevo** (recomendado se a rede bloquear SMTP) — API HTTPS Brevo/Sendinblue
2. **smtp** — Gmail ou outro servidor SMTP (portas 587/465)

Configuração: Admin → E-mail / SMTP  ou  smtp_config.json  ou  variáveis de ambiente.
"""

from __future__ import annotations

import base64
import json
import logging
import os
import smtplib
import ssl
import urllib.error
import urllib.request
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

_logo_data_uri_cache: str | None = None

DEFAULT_CONFIG: dict[str, Any] = {
    "enabled": True,
    # smtp | brevo  (brevo usa HTTPS — funciona quando a operadora bloqueia SMTP)
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
    file_cfg.update(updates)
    if not (updates.get("password") or "").strip():
        file_cfg["password"] = old_password
    else:
        file_cfg["password"] = str(updates["password"]).replace(" ", "").strip()
    if "brevo_api_key" in updates and not (updates.get("brevo_api_key") or "").strip():
        file_cfg["brevo_api_key"] = old_brevo

    CONFIG_PATH.write_text(
        json.dumps(file_cfg, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return load_smtp_config()


def smtp_is_ready(cfg: dict[str, Any] | None = None) -> tuple[bool, str]:
    """Indica se o envio de e-mail está pronto (SMTP ou Brevo)."""
    cfg = cfg or load_smtp_config()
    if not cfg.get("enabled"):
        return False, "Envio de e-mail desactivado na configuração."

    provider = (cfg.get("provider") or "smtp").lower()
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
    return True, "SMTP configurado (se a rede bloquear a porta 587/465, use o modo Brevo)."


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
            "Solução: no Admin → E-mail, escolha o modo «Brevo (API HTTPS)» "
            "(grátis em app.brevo.com) — usa a porta 443 e costuma funcionar."
        )
    return ""


def _send_via_brevo(
    *,
    to_email: str,
    subject: str,
    text_body: str,
    html_body: str,
    cfg: dict[str, Any],
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


def _send_raw(
    *,
    to_email: str,
    subject: str,
    text_body: str,
    html_body: str,
    cfg: dict[str, Any] | None = None,
) -> tuple[bool, str]:
    cfg = cfg or load_smtp_config()
    ready, reason = smtp_is_ready(cfg)
    if not ready:
        return False, reason
    if not (to_email or "").strip():
        return False, "Destinatário sem e-mail."

    provider = (cfg.get("provider") or "smtp").lower()

    if provider == "brevo":
        return _send_via_brevo(
            to_email=to_email,
            subject=subject,
            text_body=text_body,
            html_body=html_body,
            cfg=cfg,
        )

    ok, msg = _send_via_smtp(
        to_email=to_email,
        subject=subject,
        text_body=text_body,
        html_body=html_body,
        cfg=cfg,
    )
    # Se SMTP falhar por rede e houver chave Brevo, tentar automaticamente
    if not ok and (cfg.get("brevo_api_key") or "").strip() and _connection_blocked_hint(
        Exception(msg)
    ):
        logger.info("SMTP bloqueado — a tentar Brevo automaticamente")
        ok2, msg2 = _send_via_brevo(
            to_email=to_email,
            subject=subject,
            text_body=text_body,
            html_body=html_body,
            cfg=cfg,
        )
        if ok2:
            return True, msg2 + " (SMTP falhou; usado Brevo.)"
        return False, f"{msg} | Fallback Brevo: {msg2}"
    return ok, msg


def send_confirmation_email(
    to_email: str,
    codigo: str,
    html_ticket: str,
    nome: str = "",
) -> tuple[bool, str]:
    """Gera o bilhete localmente e envia por e-mail ao passageiro."""
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

    text = (
        f"Olá {nome or ''},\n\n"
        f"A sua reserva {codigo} foi confirmada com sucesso na SKYTICKETservice.\n\n"
        f"Encontra em baixo o bilhete electrónico (e-ticket) com todos os detalhes.\n"
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
        text_body=text,
        html_body=html_ticket,
        cfg=cfg,
    )
    if ok:
        return True, f"Confirmação e e-ticket enviados para {to_email.strip()}."
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
