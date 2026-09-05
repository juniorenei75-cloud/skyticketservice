"""Notificações WhatsApp para SKYTICKETservice.

Modo actual: link wa.me — abre o WhatsApp com a mensagem pronta
(sem apikey, sem CallMeBot). Ideal para testes e uso simples.
"""

from __future__ import annotations

import json
import logging
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

CONFIG_PATH = Path(__file__).resolve().parent / "whatsapp_config.json"

DEFAULT_CONFIG: dict[str, Any] = {
    "enabled": True,
    "admin_phone": "258849053340",
    "admin_name": "Júnior Jamal",
    # link = só botão/wa.me (sem apikey) | callmebot = envio automático (futuro)
    "provider": "link",
    "callmebot_apikey": "",
    "notify_on_reserva": True,
    "notify_on_contacto": True,
    "notify_on_status_change": True,
}


def load_config() -> dict[str, Any]:
    cfg = dict(DEFAULT_CONFIG)
    if CONFIG_PATH.exists():
        try:
            data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                cfg.update(data)
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning("Não foi possível ler whatsapp_config.json: %s", exc)
    return cfg


def save_config(updates: dict[str, Any]) -> dict[str, Any]:
    cfg = load_config()
    cfg.update(updates)
    CONFIG_PATH.write_text(
        json.dumps(cfg, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return cfg


def _digits(phone: str) -> str:
    return "".join(c for c in (phone or "") if c.isdigit())


def wa_me_link(phone: str, text: str) -> str:
    """Gera link https://wa.me/ com mensagem pré-preenchida."""
    phone_n = _digits(phone)
    q = urllib.parse.quote(text)
    return f"https://wa.me/{phone_n}?text={q}"


def qr_data_uri(content: str, box_size: int = 6, border: int = 2) -> str:
    """QR code em data-URI PNG (para mostrar no PC e ler com o telemóvel).

    Se a biblioteca qrcode não estiver instalada, usa API pública de QR.
    """
    text = (content or "").strip()
    if not text:
        return ""
    try:
        import base64
        import io

        import qrcode

        qr = qrcode.QRCode(
            version=None,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=max(3, min(12, box_size)),
            border=max(1, min(4, border)),
        )
        qr.add_data(text)
        qr.make(fit=True)
        img = qr.make_image(fill_color="#5c0a2c", back_color="white")
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        b64 = base64.b64encode(buf.getvalue()).decode("ascii")
        return f"data:image/png;base64,{b64}"
    except Exception:
        # Fallback online (útil se qrcode/PIL não estiverem instalados)
        q = urllib.parse.quote(text)
        return (
            "https://api.qrserver.com/v1/create-qr-code/"
            f"?size=220x220&margin=10&color=5c0a2c&bgcolor=ffffff&data={q}"
        )


def whatsapp_qr_for_admin(text: str, phone: str | None = None) -> dict[str, str]:
    """Link wa.me + QR para o admin receber os dados do bilhete."""
    cfg = load_config()
    phone_n = _digits(phone or cfg.get("admin_phone") or DEFAULT_CONFIG["admin_phone"])
    link = wa_me_link(phone_n, text)
    return {
        "link": link,
        "phone": phone_n,
        "qr": qr_data_uri(link),
    }


def format_money(value: float, moeda: str = "MZN") -> str:
    try:
        v = float(value)
    except (TypeError, ValueError):
        return f"0 {moeda}"
    if moeda == "MZN":
        return f"{v:,.0f} MT".replace(",", " ")
    return f"{moeda} {v:,.2f}"


def mensagem_nova_reserva(
    *,
    codigo: str,
    nome: str,
    email: str,
    telefone: str,
    tipo: str,
    detalhe: str,
    passageiros: int,
    data_viagem: str | None,
    total: float,
    moeda: str,
    pagamento: str = "",
    companhia: str = "",
    voo: str = "",
    estado: str = "confirmada",
) -> str:
    """Alerta imediato ao admin quando um bilhete/reserva é emitido."""
    linhas = [
        "✈️ *SKYTICKETservice — BILHETE EMITIDO*",
        "",
        f"*Código:* {codigo}",
        f"*Estado:* {estado}",
        f"*Cliente:* {nome}",
        f"*E-mail:* {email}",
        f"*Telefone:* {telefone or '—'}",
        f"*Tipo:* {tipo}",
    ]
    if companhia:
        linhas.append(f"*Companhia:* {companhia}")
    if voo:
        linhas.append(f"*Voo:* {voo}")
    linhas.extend(
        [
            f"*Detalhe:* {detalhe}",
            f"*Passageiros:* {passageiros}",
            f"*Datas:* {data_viagem or 'a definir'}",
            f"*Total:* {format_money(total, moeda) if total else 'Cotação'}",
        ]
    )
    if pagamento:
        linhas.append(f"*Pagamento:* {pagamento}")
    linhas.extend(
        [
            "",
            "⚡ Notificação automática — actue no painel Admin se necessário.",
            "Admin: /admin/reservas",
        ]
    )
    return "\n".join(linhas)


def mensagem_contacto(
    *,
    nome: str,
    email: str,
    telefone: str,
    assunto: str,
    corpo: str,
) -> str:
    return "\n".join(
        [
            "✉️ *SKYTICKETservice — Nova mensagem*",
            "",
            f"*De:* {nome}",
            f"*E-mail:* {email}",
            f"*Telefone:* {telefone or '—'}",
            f"*Assunto:* {assunto or '—'}",
            "",
            corpo,
        ]
    )


def mensagem_status_reserva(
    *,
    codigo: str,
    nome: str,
    status: str,
    total: float,
    moeda: str,
) -> str:
    emoji = {"confirmada": "✅", "cancelada": "❌", "pendente": "⏳"}.get(status, "📋")
    return "\n".join(
        [
            f"{emoji} *SKYTICKETservice — Actualização de reserva*",
            "",
            f"*Código:* {codigo}",
            f"*Cliente:* {nome}",
            f"*Novo estado:* {status}",
            f"*Total:* {format_money(total, moeda)}",
            "",
            "Obrigado por escolher a SKYTICKETservice.",
        ]
    )


def send_callmebot(phone: str, text: str, apikey: str) -> tuple[bool, str]:
    if not apikey:
        return False, "CallMeBot: apikey em falta. Configure em Admin → WhatsApp."
    phone_n = _digits(phone)
    if not phone_n:
        return False, "Número de telefone inválido."
    params = urllib.parse.urlencode(
        {"phone": phone_n, "text": text, "apikey": apikey}
    )
    url = f"https://api.callmebot.com/whatsapp.php?{params}"
    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=20) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            if resp.status == 200:
                return True, body or "Mensagem enviada via CallMeBot."
            return False, f"CallMeBot HTTP {resp.status}: {body}"
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace") if exc.fp else str(exc)
        return False, f"CallMeBot erro HTTP {exc.code}: {body}"
    except Exception as exc:  # noqa: BLE001
        logger.exception("Falha CallMeBot")
        return False, f"Falha de rede: {exc}"


def send_whatsapp_to_admin(text: str) -> dict[str, Any]:
    """Envia ao admin: CallMeBot (automático) ou prepara link wa.me."""
    cfg = load_config()
    phone = cfg.get("admin_phone") or DEFAULT_CONFIG["admin_phone"]
    link = wa_me_link(phone, text)
    result: dict[str, Any] = {
        "ok": True,
        "message": "Link WhatsApp preparado (envio automático não configurado).",
        "link": link,
        "phone": phone,
        "auto_sent": False,
        "configured": False,
    }

    if not cfg.get("enabled", True):
        result["ok"] = False
        result["message"] = "Notificações WhatsApp desactivadas."
        return result

    provider = (cfg.get("provider") or "link").lower()
    apikey = (cfg.get("callmebot_apikey") or "").strip()

    # Preferir envio automático sempre que houver apikey
    if apikey and provider in ("callmebot", "auto", "link"):
        ok, msg = send_callmebot(phone, text, apikey)
        result["ok"] = ok
        result["message"] = msg
        result["auto_sent"] = ok
        result["configured"] = True
        if ok:
            result["message"] = "WhatsApp enviado automaticamente ao administrador."
        return result

    result["message"] = (
        "Sem apikey CallMeBot — configure em Admin → WhatsApp para receber "
        "mensagens automáticas no telemóvel."
    )
    return result


def notify_if_enabled(kind: str, text: str) -> dict[str, Any]:
    """kind: reserva | contacto | status"""
    cfg = load_config()
    flags = {
        "reserva": cfg.get("notify_on_reserva", True),
        "contacto": cfg.get("notify_on_contacto", True),
        "status": cfg.get("notify_on_status_change", True),
    }
    phone = cfg.get("admin_phone") or DEFAULT_CONFIG["admin_phone"]
    if not flags.get(kind, True):
        return {
            "ok": False,
            "message": f"Notificação de «{kind}» desactivada.",
            "link": wa_me_link(phone, text),
            "auto_sent": False,
            "configured": False,
        }
    return send_whatsapp_to_admin(text)
