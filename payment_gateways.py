"""Gateways de pagamento — Stripe (activo) + Adyen/Worldpay (preparados).

Fluxo cartão (Stripe):
  1) create_card_payment → PaymentIntent (autorização + captura automática)
  2) Cliente confirma no browser (Stripe.js / Payment Element)
  3) confirm_card_payment → verifica status succeeded e devolve resultado

A captura é automática (capture_method=automatic): o valor é capturado
assim que a autorização é bem-sucedida.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

logger = logging.getLogger(__name__)

CONFIG_PATH = Path(__file__).resolve().parent / "payment_config.json"

DEFAULT_PAYMENT_CONFIG: dict[str, Any] = {
    # stripe | adyen | worldpay | none
    "active_card_gateway": "stripe",
    "stripe_secret_key": "",
    "stripe_publishable_key": "",
    "stripe_webhook_secret": "",
    # Adyen (preparado)
    "adyen_api_key": "",
    "adyen_merchant_account": "",
    "adyen_client_key": "",
    "adyen_environment": "test",  # test | live
    # Worldpay (preparado)
    "worldpay_merchant_id": "",
    "worldpay_service_key": "",
    "worldpay_client_key": "",
    "worldpay_environment": "test",
}


@dataclass
class PaymentCreateResult:
    ok: bool
    provider: str
    payment_id: str = ""
    client_secret: str = ""
    publishable_key: str = ""
    redirect_url: str = ""
    message: str = ""
    raw: dict | None = None


@dataclass
class PaymentConfirmResult:
    ok: bool
    provider: str
    payment_id: str = ""
    status: str = ""
    amount: float = 0.0
    currency: str = "USD"
    message: str = ""
    raw: dict | None = None


class CardGateway(Protocol):
    name: str

    def is_configured(self) -> bool: ...

    def create_payment(
        self,
        *,
        amount: float,
        currency: str,
        description: str,
        metadata: dict[str, str],
        customer_email: str = "",
    ) -> PaymentCreateResult: ...

    def confirm_payment(self, payment_id: str) -> PaymentConfirmResult: ...


def load_payment_config() -> dict[str, Any]:
    cfg = dict(DEFAULT_PAYMENT_CONFIG)
    if CONFIG_PATH.exists():
        try:
            data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                cfg.update(data)
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning("payment_config.json: %s", exc)

    env_map = {
        "STRIPE_SECRET_KEY": "stripe_secret_key",
        "STRIPE_PUBLISHABLE_KEY": "stripe_publishable_key",
        "STRIPE_WEBHOOK_SECRET": "stripe_webhook_secret",
        "ADYEN_API_KEY": "adyen_api_key",
        "ADYEN_MERCHANT_ACCOUNT": "adyen_merchant_account",
        "ADYEN_CLIENT_KEY": "adyen_client_key",
        "WORLDPAY_MERCHANT_ID": "worldpay_merchant_id",
        "WORLDPAY_SERVICE_KEY": "worldpay_service_key",
        "WORLDPAY_CLIENT_KEY": "worldpay_client_key",
        "CARD_GATEWAY": "active_card_gateway",
    }
    for env_k, cfg_k in env_map.items():
        val = os.environ.get(env_k, "").strip()
        if val:
            cfg[cfg_k] = val

    active = (cfg.get("active_card_gateway") or "stripe").strip().lower()
    if active not in ("stripe", "adyen", "worldpay", "none"):
        active = "stripe"
    cfg["active_card_gateway"] = active
    return cfg


def save_payment_config(updates: dict[str, Any]) -> dict[str, Any]:
    file_cfg = dict(DEFAULT_PAYMENT_CONFIG)
    if CONFIG_PATH.exists():
        try:
            data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                file_cfg.update(data)
        except (OSError, json.JSONDecodeError):
            pass

    secret_fields = (
        "stripe_secret_key",
        "stripe_webhook_secret",
        "adyen_api_key",
        "worldpay_service_key",
    )
    old_secrets = {k: file_cfg.get(k) or "" for k in secret_fields}
    file_cfg.update(updates)
    for k in secret_fields:
        if k in updates and not (updates.get(k) or "").strip():
            file_cfg[k] = old_secrets[k]

    CONFIG_PATH.write_text(
        json.dumps(file_cfg, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return load_payment_config()


def payment_gateway_status(cfg: dict[str, Any] | None = None) -> tuple[bool, str]:
    cfg = cfg or load_payment_config()
    active = cfg.get("active_card_gateway") or "none"
    gw = get_card_gateway(active, cfg)
    if gw is None or active == "none":
        return False, "Nenhum gateway de cartão activo."
    if not gw.is_configured():
        return (
            False,
            f"Gateway «{active}» seleccionado, mas as chaves ainda não estão configuradas.",
        )
    return True, f"Cartão activo: {active} (autorização + captura automática)."


def _to_minor_units(amount: float, currency: str) -> int:
    """Converte valor para unidades menores (cents)."""
    cur = (currency or "USD").upper()
    # Moedas sem casas decimais (raro no nosso fluxo)
    zero_decimal = {"JPY", "KRW", "VND"}
    if cur in zero_decimal:
        return int(round(float(amount)))
    return int(round(float(amount) * 100))


class StripeGateway:
    name = "stripe"

    def __init__(self, cfg: dict[str, Any]):
        self.cfg = cfg
        self.secret = (cfg.get("stripe_secret_key") or "").strip()
        self.publishable = (cfg.get("stripe_publishable_key") or "").strip()

    def is_configured(self) -> bool:
        return bool(self.secret and self.publishable)

    def create_payment(
        self,
        *,
        amount: float,
        currency: str,
        description: str,
        metadata: dict[str, str],
        customer_email: str = "",
    ) -> PaymentCreateResult:
        if not self.is_configured():
            return PaymentCreateResult(
                ok=False,
                provider=self.name,
                message="Stripe não configurado (secret + publishable key).",
            )
        try:
            import stripe

            stripe.api_key = self.secret
            cur = (currency or "USD").lower()
            intent = stripe.PaymentIntent.create(
                amount=_to_minor_units(amount, cur),
                currency=cur,
                description=(description or "SKYTICKETservice")[:500],
                metadata={k: str(v)[:500] for k, v in (metadata or {}).items()},
                receipt_email=(customer_email or None) or None,
                # Autorização + captura automática após confirmação
                capture_method="automatic",
                confirmation_method="automatic",
                automatic_payment_methods={"enabled": True},
            )
            return PaymentCreateResult(
                ok=True,
                provider=self.name,
                payment_id=intent.id,
                client_secret=intent.client_secret or "",
                publishable_key=self.publishable,
                message="PaymentIntent criado (captura automática).",
                raw={"id": intent.id, "status": intent.status},
            )
        except Exception as exc:  # noqa: BLE001
            logger.exception("Stripe create_payment")
            return PaymentCreateResult(
                ok=False, provider=self.name, message=f"Stripe: {exc}"
            )

    def confirm_payment(self, payment_id: str) -> PaymentConfirmResult:
        if not self.is_configured():
            return PaymentConfirmResult(
                ok=False,
                provider=self.name,
                message="Stripe não configurado.",
            )
        try:
            import stripe

            stripe.api_key = self.secret
            intent = stripe.PaymentIntent.retrieve(payment_id)
            status = intent.status or ""
            # succeeded = autorizado e capturado (capture_method=automatic)
            ok = status == "succeeded"
            amount = float(intent.amount or 0) / 100.0
            currency = (intent.currency or "usd").upper()
            return PaymentConfirmResult(
                ok=ok,
                provider=self.name,
                payment_id=intent.id,
                status=status,
                amount=amount,
                currency=currency,
                message=(
                    "Pagamento autorizado e capturado."
                    if ok
                    else f"Estado Stripe: {status}"
                ),
                raw={"id": intent.id, "status": status},
            )
        except Exception as exc:  # noqa: BLE001
            logger.exception("Stripe confirm_payment")
            return PaymentConfirmResult(
                ok=False, provider=self.name, message=f"Stripe: {exc}"
            )


class AdyenGateway:
    """Stub preparado — activar quando tiver conta Adyen."""

    name = "adyen"

    def __init__(self, cfg: dict[str, Any]):
        self.cfg = cfg

    def is_configured(self) -> bool:
        return bool(
            (self.cfg.get("adyen_api_key") or "").strip()
            and (self.cfg.get("adyen_merchant_account") or "").strip()
            and (self.cfg.get("adyen_client_key") or "").strip()
        )

    def create_payment(self, **kwargs) -> PaymentCreateResult:
        if not self.is_configured():
            return PaymentCreateResult(
                ok=False,
                provider=self.name,
                message=(
                    "Adyen preparado no código, mas ainda sem chaves. "
                    "Configure em Admin → Pagamentos (cartão)."
                ),
            )
        return PaymentCreateResult(
            ok=False,
            provider=self.name,
            message=(
                "Adyen: chaves presentes — falta activar a sessão Checkout/Payments API. "
                "Contacte o desenvolvimento para ligar o endpoint live/test."
            ),
        )

    def confirm_payment(self, payment_id: str) -> PaymentConfirmResult:
        return PaymentConfirmResult(
            ok=False,
            provider=self.name,
            payment_id=payment_id,
            message="Adyen ainda não está ligado à captura automática neste ambiente.",
        )


class WorldpayGateway:
    """Stub preparado — activar quando tiver conta Worldpay."""

    name = "worldpay"

    def __init__(self, cfg: dict[str, Any]):
        self.cfg = cfg

    def is_configured(self) -> bool:
        return bool(
            (self.cfg.get("worldpay_merchant_id") or "").strip()
            and (self.cfg.get("worldpay_service_key") or "").strip()
            and (self.cfg.get("worldpay_client_key") or "").strip()
        )

    def create_payment(self, **kwargs) -> PaymentCreateResult:
        if not self.is_configured():
            return PaymentCreateResult(
                ok=False,
                provider=self.name,
                message=(
                    "Worldpay preparado no código, mas ainda sem chaves. "
                    "Configure em Admin → Pagamentos (cartão)."
                ),
            )
        return PaymentCreateResult(
            ok=False,
            provider=self.name,
            message=(
                "Worldpay: chaves presentes — falta activar a API Payments. "
                "Contacte o desenvolvimento para ligar o endpoint."
            ),
        )

    def confirm_payment(self, payment_id: str) -> PaymentConfirmResult:
        return PaymentConfirmResult(
            ok=False,
            provider=self.name,
            payment_id=payment_id,
            message="Worldpay ainda não está ligado à captura automática neste ambiente.",
        )


def get_card_gateway(
    name: str | None = None, cfg: dict[str, Any] | None = None
) -> CardGateway | None:
    cfg = cfg or load_payment_config()
    name = (name or cfg.get("active_card_gateway") or "stripe").strip().lower()
    if name == "stripe":
        return StripeGateway(cfg)
    if name == "adyen":
        return AdyenGateway(cfg)
    if name == "worldpay":
        return WorldpayGateway(cfg)
    return None
