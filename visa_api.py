"""Integração Sherpa — requisitos de visto e produtos eVisa.

Espelha o padrão de flight_search.py (config JSON + env + funções de consulta).
Sem chave API: devolve resultados vazios e mensagem para configurar.

Auth: header x-api-key
Products: GET {products_host}/v2/products?status=ACTIVE&destination=XXX&currency=USD
Requirements: POST {requirements_host}/v3/trips  Content-Type: application/vnd.api+json
"""

from __future__ import annotations

import json
import logging
import os
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, timedelta
from pathlib import Path
from typing import Any

from countries import find_country

logger = logging.getLogger(__name__)

CONFIG_PATH = Path(__file__).resolve().parent / "visa_api_config.json"

DEFAULT_VISA_API: dict[str, Any] = {
    "sherpa_api_key": "",
    "sherpa_env": "sandbox",  # sandbox | live
    "agency_markup_percent": 5.0,
}

# ISO 3166-1 alpha-2 → alpha-3 (Sherpa usa ISO3)
ISO2_TO_ISO3: dict[str, str] = {
    "AF": "AFG", "AX": "ALA", "AL": "ALB", "DZ": "DZA", "AS": "ASM", "AD": "AND",
    "AO": "AGO", "AI": "AIA", "AQ": "ATA", "AG": "ATG", "AR": "ARG", "AM": "ARM",
    "AW": "ABW", "AU": "AUS", "AT": "AUT", "AZ": "AZE", "BS": "BHS", "BH": "BHR",
    "BD": "BGD", "BB": "BRB", "BY": "BLR", "BE": "BEL", "BZ": "BLZ", "BJ": "BEN",
    "BM": "BMU", "BT": "BTN", "BO": "BOL", "BQ": "BES", "BA": "BIH", "BW": "BWA",
    "BV": "BVT", "BR": "BRA", "IO": "IOT", "BN": "BRN", "BG": "BGR", "BF": "BFA",
    "BI": "BDI", "CV": "CPV", "KH": "KHM", "CM": "CMR", "CA": "CAN", "KY": "CYM",
    "CF": "CAF", "TD": "TCD", "CL": "CHL", "CN": "CHN", "CX": "CXR", "CC": "CCK",
    "CO": "COL", "KM": "COM", "CG": "COG", "CD": "COD", "CK": "COK", "CR": "CRI",
    "CI": "CIV", "HR": "HRV", "CU": "CUB", "CW": "CUW", "CY": "CYP", "CZ": "CZE",
    "DK": "DNK", "DJ": "DJI", "DM": "DMA", "DO": "DOM", "EC": "ECU", "EG": "EGY",
    "SV": "SLV", "GQ": "GNQ", "ER": "ERI", "EE": "EST", "SZ": "SWZ", "ET": "ETH",
    "FK": "FLK", "FO": "FRO", "FJ": "FJI", "FI": "FIN", "FR": "FRA", "GF": "GUF",
    "PF": "PYF", "TF": "ATF", "GA": "GAB", "GM": "GMB", "GE": "GEO", "DE": "DEU",
    "GH": "GHA", "GI": "GIB", "GR": "GRC", "GL": "GRL", "GD": "GRD", "GP": "GLP",
    "GU": "GUM", "GT": "GTM", "GG": "GGY", "GN": "GIN", "GW": "GNB", "GY": "GUY",
    "HT": "HTI", "HM": "HMD", "VA": "VAT", "HN": "HND", "HK": "HKG", "HU": "HUN",
    "IS": "ISL", "IN": "IND", "ID": "IDN", "IR": "IRN", "IQ": "IRQ", "IE": "IRL",
    "IM": "IMN", "IL": "ISR", "IT": "ITA", "JM": "JAM", "JP": "JPN", "JE": "JEY",
    "JO": "JOR", "KZ": "KAZ", "KE": "KEN", "KI": "KIR", "KP": "PRK", "KR": "KOR",
    "KW": "KWT", "KG": "KGZ", "LA": "LAO", "LV": "LVA", "LB": "LBN", "LS": "LSO",
    "LR": "LBR", "LY": "LBY", "LI": "LIE", "LT": "LTU", "LU": "LUX", "MO": "MAC",
    "MG": "MDG", "MW": "MWI", "MY": "MYS", "MV": "MDV", "ML": "MLI", "MT": "MLT",
    "MH": "MHL", "MQ": "MTQ", "MR": "MRT", "MU": "MUS", "YT": "MYT", "MX": "MEX",
    "FM": "FSM", "MD": "MDA", "MC": "MCO", "MN": "MNG", "ME": "MNE", "MS": "MSR",
    "MA": "MAR", "MZ": "MOZ", "MM": "MMR", "NA": "NAM", "NR": "NRU", "NP": "NPL",
    "NL": "NLD", "NC": "NCL", "NZ": "NZL", "NI": "NIC", "NE": "NER", "NG": "NGA",
    "NU": "NIU", "NF": "NFK", "MK": "MKD", "MP": "MNP", "NO": "NOR", "OM": "OMN",
    "PK": "PAK", "PW": "PLW", "PS": "PSE", "PA": "PAN", "PG": "PNG", "PY": "PRY",
    "PE": "PER", "PH": "PHL", "PN": "PCN", "PL": "POL", "PT": "PRT", "PR": "PRI",
    "QA": "QAT", "RE": "REU", "RO": "ROU", "RU": "RUS", "RW": "RWA", "BL": "BLM",
    "SH": "SHN", "KN": "KNA", "LC": "LCA", "MF": "MAF", "PM": "SPM", "VC": "VCT",
    "WS": "WSM", "SM": "SMR", "ST": "STP", "SA": "SAU", "SN": "SEN", "RS": "SRB",
    "SC": "SYC", "SL": "SLE", "SG": "SGP", "SX": "SXM", "SK": "SVK", "SI": "SVN",
    "SB": "SLB", "SO": "SOM", "ZA": "ZAF", "GS": "SGS", "SS": "SSD", "ES": "ESP",
    "LK": "LKA", "SD": "SDN", "SR": "SUR", "SJ": "SJM", "SE": "SWE", "CH": "CHE",
    "SY": "SYR", "TW": "TWN", "TJ": "TJK", "TZ": "TZA", "TH": "THA", "TL": "TLS",
    "TG": "TGO", "TK": "TKL", "TO": "TON", "TT": "TTO", "TN": "TUN", "TR": "TUR",
    "TM": "TKM", "TC": "TCA", "TV": "TUV", "UG": "UGA", "UA": "UKR", "AE": "ARE",
    "GB": "GBR", "US": "USA", "UM": "UMI", "UY": "URY", "UZ": "UZB", "VU": "VUT",
    "VE": "VEN", "VN": "VNM", "VG": "VGB", "VI": "VIR", "WF": "WLF", "EH": "ESH",
    "YE": "YEM", "ZM": "ZMB", "ZW": "ZWE", "XK": "XKX",
}

HOSTS = {
    "sandbox": {
        "products": "https://api-sandbox.joinsherpa.io",
        "requirements": "https://requirements-api.sandbox.joinsherpa.com",
    },
    "live": {
        "products": "https://api.joinsherpa.io",
        "requirements": "https://requirements-api.joinsherpa.com",
    },
}


def load_visa_api_config() -> dict[str, Any]:
    cfg = dict(DEFAULT_VISA_API)
    if CONFIG_PATH.exists():
        try:
            data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                cfg.update(data)
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning("visa_api_config.json: %s", exc)
    env_map = {
        "SHERPA_API_KEY": "sherpa_api_key",
        "SHERPA_ENV": "sherpa_env",
    }
    for env_k, cfg_k in env_map.items():
        val = os.environ.get(env_k, "").strip()
        if val:
            cfg[cfg_k] = val
    cfg["sherpa_env"] = (cfg.get("sherpa_env") or "sandbox").strip().lower()
    if cfg["sherpa_env"] not in ("sandbox", "live"):
        cfg["sherpa_env"] = "sandbox"
    try:
        cfg["agency_markup_percent"] = max(
            0.0, min(100.0, float(cfg.get("agency_markup_percent") or 0))
        )
    except (TypeError, ValueError):
        cfg["agency_markup_percent"] = 5.0
    env_markup = os.environ.get("SHERPA_MARKUP_PERCENT", "").strip()
    if env_markup:
        try:
            cfg["agency_markup_percent"] = max(0.0, min(100.0, float(env_markup)))
        except ValueError:
            pass
    return cfg


def save_visa_api_config(updates: dict[str, Any]) -> dict[str, Any]:
    file_cfg = dict(DEFAULT_VISA_API)
    if CONFIG_PATH.exists():
        try:
            data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                file_cfg.update(data)
        except (OSError, json.JSONDecodeError):
            pass
    old_key = file_cfg.get("sherpa_api_key") or ""
    file_cfg.update(updates)
    # Campo password vazio = manter chave existente
    if "sherpa_api_key" in updates and not (
        updates.get("sherpa_api_key") or ""
    ).strip():
        file_cfg["sherpa_api_key"] = old_key
    env = (file_cfg.get("sherpa_env") or "sandbox").strip().lower()
    file_cfg["sherpa_env"] = env if env in ("sandbox", "live") else "sandbox"
    try:
        file_cfg["agency_markup_percent"] = max(
            0.0, min(100.0, float(file_cfg.get("agency_markup_percent") or 0))
        )
    except (TypeError, ValueError):
        file_cfg["agency_markup_percent"] = 5.0
    CONFIG_PATH.write_text(
        json.dumps(file_cfg, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return load_visa_api_config()


def status_summary(cfg: dict[str, Any] | None = None) -> tuple[bool, str]:
    """Como flight_api_status — (ready, mensagem)."""
    cfg = cfg or load_visa_api_config()
    key = (cfg.get("sherpa_api_key") or "").strip()
    env = cfg.get("sherpa_env") or "sandbox"
    if key:
        return True, f"Sherpa activo ({env}). Requisitos e produtos eVisa disponíveis."
    return (
        False,
        "Sem API Sherpa. Configure a chave em Admin → Vistos API "
        "ou defina a variável SHERPA_API_KEY.",
    )


def apply_agency_markup(
    base_price: float, cfg: dict[str, Any] | None = None
) -> tuple[float, float, float]:
    cfg = cfg or load_visa_api_config()
    try:
        pct = float(cfg.get("agency_markup_percent") or 0)
    except (TypeError, ValueError):
        pct = 0.0
    pct = max(0.0, min(100.0, pct))
    base = float(base_price or 0)
    if base <= 0:
        return 0.0, 0.0, pct
    sell = round(base * (1.0 + pct / 100.0), 2)
    return sell, round(base, 2), pct


def to_iso3(code_or_name: str) -> str | None:
    """Aceita ISO2, ISO3 ou nome de país → ISO3."""
    raw = (code_or_name or "").strip()
    if not raw:
        return None
    up = raw.upper()
    if len(up) == 3 and up.isalpha():
        # Já ISO3, ou ISO2 errado — se estiver no mapa invertido ok
        if up in ISO2_TO_ISO3.values():
            return up
        # Pode ser ISO2 inexistente com 3 letras — tentar find_country
    if len(up) == 2 and up in ISO2_TO_ISO3:
        return ISO2_TO_ISO3[up]
    found = find_country(raw)
    if found:
        iso2 = (found.get("codigo") or "").upper()
        return ISO2_TO_ISO3.get(iso2)
    return None


def _hosts(cfg: dict[str, Any]) -> dict[str, str]:
    env = (cfg.get("sherpa_env") or "sandbox").strip().lower()
    return HOSTS.get(env, HOSTS["sandbox"])


def _http_json(
    method: str,
    url: str,
    api_key: str,
    body: dict | None = None,
    content_type: str = "application/json",
    timeout: int = 25,
) -> tuple[Any | None, str]:
    headers = {
        "x-api-key": api_key,
        "Accept": "application/json",
        "User-Agent": "SKYTICKETservice/1.0",
    }
    data = None
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = content_type
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            if not raw.strip():
                return None, "Resposta vazia da API Sherpa."
            try:
                return json.loads(raw), ""
            except json.JSONDecodeError as exc:
                return None, f"JSON inválido: {exc}"
    except urllib.error.HTTPError as exc:
        detail = ""
        try:
            detail = exc.read().decode("utf-8", errors="replace")[:400]
        except Exception:
            pass
        logger.warning("Sherpa HTTP %s %s: %s %s", method, url, exc.code, detail)
        return None, f"HTTP {exc.code}: {detail or exc.reason}"
    except urllib.error.URLError as exc:
        logger.warning("Sherpa URL error %s: %s", url, exc)
        return None, f"Ligação falhou: {exc.reason}"
    except Exception as exc:  # noqa: BLE001
        logger.exception("Sherpa request failed")
        return None, str(exc)


def check_requirements(
    passport_country_iso3: str,
    destination_iso3: str,
    locale: str = "pt-PT",
    currency: str = "USD",
    departure_date: str | None = None,
    cfg: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Consulta requisitos de visto via POST /v3/trips.

    Devolve dict normalizado: ok, configured, summary, items, raw_error, snippet.
    """
    cfg = cfg or load_visa_api_config()
    key = (cfg.get("sherpa_api_key") or "").strip()
    empty = {
        "ok": False,
        "configured": bool(key),
        "summary": "",
        "items": [],
        "snippet": "",
        "raw_error": "",
        "visa_required": None,
    }
    if not key:
        empty["summary"] = (
            "API Sherpa não configurada. Peça à agência para definir SHERPA_API_KEY "
            "em Admin → Vistos API."
        )
        return empty

    origin = to_iso3(passport_country_iso3) or (passport_country_iso3 or "").upper()
    dest = to_iso3(destination_iso3) or (destination_iso3 or "").upper()
    if len(origin) != 3 or len(dest) != 3:
        empty["configured"] = True
        empty["raw_error"] = "Códigos de país inválidos (precisa ISO3)."
        empty["summary"] = empty["raw_error"]
        return empty

    dep = (departure_date or "").strip()
    if not dep:
        dep = (date.today() + timedelta(days=30)).isoformat()
    loc = (locale or "pt-PT").strip() or "pt-PT"

    payload = {
        "data": {
            "type": "TRIP",
            "attributes": {
                "locale": loc,
                "currency": currency or "USD",
                "traveller": {"passports": [origin]},
                "travelNodes": [
                    {
                        "type": "ORIGIN",
                        "locationCode": origin,
                        "departure": {
                            "date": dep,
                            "time": "12:00",
                            "travelMode": "AIR",
                        },
                    },
                    {
                        "type": "DESTINATION",
                        "locationCode": dest,
                        "arrival": {
                            "date": dep,
                            "time": "18:00",
                            "travelMode": "AIR",
                        },
                    },
                ],
            },
        }
    }
    hosts = _hosts(cfg)
    url = f"{hosts['requirements']}/v3/trips"
    data, err = _http_json(
        "POST",
        url,
        key,
        body=payload,
        content_type="application/vnd.api+json",
    )
    if err or data is None:
        empty["configured"] = True
        empty["raw_error"] = err or "Sem dados"
        empty["summary"] = (
            f"Não foi possível obter requisitos Sherpa ({empty['raw_error']}). "
            "A equipa pode analisar o pedido manualmente."
        )
        return empty

    items, summary, visa_required = _parse_trip_requirements(data)
    snippet_parts = [summary] if summary else []
    for it in items[:8]:
        title = it.get("title") or it.get("type") or ""
        desc = (it.get("description") or "")[:180]
        if title or desc:
            snippet_parts.append(f"- {title}: {desc}".strip(": "))
    snippet = "\n".join(snippet_parts)[:1500]

    return {
        "ok": True,
        "configured": True,
        "summary": summary or "Requisitos obtidos via Sherpa.",
        "items": items,
        "snippet": snippet,
        "raw_error": "",
        "visa_required": visa_required,
    }


def _parse_trip_requirements(data: Any) -> tuple[list[dict], str, bool | None]:
    """Extrai lista legível de procedimentos / requisitos do payload JSON:API."""
    items: list[dict] = []
    visa_required: bool | None = None
    summary_bits: list[str] = []

    included = []
    root = data
    if isinstance(data, dict):
        included = data.get("included") or []
        attrs = ((data.get("data") or {}) if isinstance(data.get("data"), dict) else {})
        if isinstance(attrs, dict):
            a = attrs.get("attributes") or {}
            if isinstance(a, dict) and a.get("headline"):
                summary_bits.append(str(a["headline"]))

    # Procedimentos em included ou data.relationships
    candidates: list[dict] = []
    if isinstance(included, list):
        for node in included:
            if isinstance(node, dict):
                candidates.append(node)
    if isinstance(root, dict) and isinstance(root.get("data"), list):
        for node in root["data"]:
            if isinstance(node, dict):
                candidates.append(node)

    for node in candidates:
        ntype = (node.get("type") or "").upper()
        attrs = node.get("attributes") or {}
        if not isinstance(attrs, dict):
            continue
        # Tipos comuns: PROCEDURE, INFORMATION, RESTRICTION, DOCUMENT
        interesting = ntype in (
            "PROCEDURE",
            "INFORMATION",
            "RESTRICTION",
            "DOCUMENT",
            "GROUP",
        ) or "VISA" in ntype
        title = (
            attrs.get("title")
            or attrs.get("headline")
            or attrs.get("name")
            or attrs.get("description")
            or ntype
        )
        desc = (
            attrs.get("description")
            or attrs.get("longDescription")
            or attrs.get("text")
            or ""
        )
        category = (
            attrs.get("category")
            or attrs.get("documentType")
            or attrs.get("subType")
            or ntype
        )
        if isinstance(category, dict):
            category = category.get("label") or category.get("value") or ""
        enforcements = attrs.get("enforcement") or attrs.get("severity") or ""
        if isinstance(enforcements, dict):
            enforcements = enforcements.get("label") or enforcements.get("value") or ""

        text_blob = f"{title} {desc} {category}".lower()
        if "visa" in text_blob or "visto" in text_blob:
            if any(
                w in text_blob
                for w in ("not required", "não é necessário", "nao e necessario", "visa-free", "exempt")
            ):
                visa_required = False if visa_required is None else visa_required
            elif any(
                w in text_blob
                for w in ("required", "necessário", "necessario", "evisa", "e-visa")
            ):
                visa_required = True

        if interesting or "visa" in text_blob or "visto" in text_blob:
            items.append(
                {
                    "type": ntype,
                    "title": str(title)[:200] if title else ntype,
                    "description": str(desc)[:600] if desc else "",
                    "category": str(category)[:120] if category else "",
                    "enforcement": str(enforcements)[:80] if enforcements else "",
                }
            )

    # Fallback: percorrer dict à procura de titles
    if not items and isinstance(data, dict):
        summary_bits.append("Resposta Sherpa recebida (detalhe estruturado limitado).")

    if visa_required is True:
        summary_bits.insert(0, "Visto provavelmente necessário para este destino.")
    elif visa_required is False:
        summary_bits.insert(0, "Visto pode não ser necessário (confirmar com a agência).")

    # Deduplicar por título
    seen: set[str] = set()
    unique: list[dict] = []
    for it in items:
        key = (it.get("title") or "").strip().lower()
        if key and key in seen:
            continue
        if key:
            seen.add(key)
        unique.append(it)

    summary = " ".join(summary_bits).strip()
    return unique[:20], summary, visa_required


def list_products(
    destination_iso3: str,
    nationality_iso3: str | None = None,
    currency: str = "USD",
    cfg: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Lista produtos eVisa ACTIVE para o destino."""
    cfg = cfg or load_visa_api_config()
    key = (cfg.get("sherpa_api_key") or "").strip()
    empty = {
        "ok": False,
        "configured": bool(key),
        "products": [],
        "raw_error": "",
        "message": "",
    }
    if not key:
        empty["message"] = (
            "Configure a API Sherpa (Admin → Vistos API ou SHERPA_API_KEY) "
            "para ver produtos eVisa com preço."
        )
        return empty

    dest = to_iso3(destination_iso3) or (destination_iso3 or "").upper()
    if len(dest) != 3:
        empty["configured"] = True
        empty["raw_error"] = "Destino inválido (ISO3)."
        empty["message"] = empty["raw_error"]
        return empty

    params: dict[str, str] = {
        "status": "ACTIVE",
        "destination": dest,
        "currency": currency or "USD",
    }
    nat = None
    if nationality_iso3:
        nat = to_iso3(nationality_iso3) or (nationality_iso3 or "").upper()
        if len(nat) == 3:
            params["nationality"] = nat

    hosts = _hosts(cfg)
    qs = urllib.parse.urlencode(params)
    url = f"{hosts['products']}/v2/products?{qs}"
    data, err = _http_json("GET", url, key)
    if err or data is None:
        empty["configured"] = True
        empty["raw_error"] = err or "Sem dados"
        empty["message"] = f"Produtos Sherpa indisponíveis ({empty['raw_error']})."
        return empty

    raw_list: list = []
    if isinstance(data, list):
        raw_list = data
    elif isinstance(data, dict):
        if isinstance(data.get("data"), list):
            raw_list = data["data"]
        elif isinstance(data.get("products"), list):
            raw_list = data["products"]
        elif data.get("productId") or data.get("name"):
            raw_list = [data]

    products = []
    for p in raw_list:
        if not isinstance(p, dict):
            continue
        # JSON:API style
        attrs = p.get("attributes") if isinstance(p.get("attributes"), dict) else p
        pid = (
            attrs.get("productId")
            or p.get("productId")
            or p.get("id")
            or attrs.get("id")
            or ""
        )
        name = attrs.get("name") or attrs.get("shortName") or pid or "Produto"
        desc = attrs.get("description") or ""
        pricing = attrs.get("pricing") or {}
        if not isinstance(pricing, dict):
            pricing = {}
        base = pricing.get("price")
        try:
            base_f = float(base) if base is not None else 0.0
        except (TypeError, ValueError):
            base_f = 0.0
        cur = pricing.get("currency") or currency or "USD"
        sell, base_r, pct = apply_agency_markup(base_f, cfg)
        sub = attrs.get("subType") or {}
        if isinstance(sub, dict):
            sub_label = sub.get("label") or sub.get("value") or ""
        else:
            sub_label = str(sub or "")
        processing = attrs.get("processingTime") or {}
        if isinstance(processing, dict):
            proc_label = processing.get("label") or (
                f"{processing.get('value', '')} {processing.get('unit', '')}".strip()
            )
        else:
            proc_label = str(processing or "")

        # Filtrar por nacionalidade no cliente se a API devolver lista
        elig = attrs.get("eligibleNationalities") or []
        if nat and isinstance(elig, list) and elig:
            codes = []
            for e in elig:
                if isinstance(e, dict):
                    codes.append((e.get("value") or "").upper())
                else:
                    codes.append(str(e).upper())
            if codes and nat not in codes:
                continue

        products.append(
            {
                "product_id": str(pid),
                "name": str(name),
                "description": str(desc)[:400],
                "sub_type": sub_label,
                "price": sell,
                "price_base": base_r,
                "markup_percent": pct,
                "currency": cur,
                "processing_time": proc_label,
                "status": attrs.get("status") or "ACTIVE",
            }
        )

    return {
        "ok": True,
        "configured": True,
        "products": products,
        "raw_error": "",
        "message": (
            f"{len(products)} produto(s) eVisa encontrado(s)."
            if products
            else "Sem produtos eVisa ACTIVE para este destino/nacionalidade."
        ),
    }


def lookup_visa_info(
    passport_country: str,
    destination: str,
    locale: str = "pt-PT",
    currency: str = "USD",
    departure_date: str | None = None,
    cfg: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Conveniência: requisitos + produtos a partir de nomes ou códigos."""
    cfg = cfg or load_visa_api_config()
    ready, status_msg = status_summary(cfg)
    origin3 = to_iso3(passport_country)
    dest3 = to_iso3(destination)
    result = {
        "configured": ready,
        "status_msg": status_msg,
        "origin_iso3": origin3,
        "destination_iso3": dest3,
        "requirements": None,
        "products": None,
    }
    if not ready:
        result["requirements"] = check_requirements(
            passport_country, destination, locale, currency, departure_date, cfg
        )
        result["products"] = list_products(destination, passport_country, currency, cfg)
        return result
    if not origin3 or not dest3:
        result["status_msg"] = (
            "Não foi possível converter país/nacionalidade para código ISO. "
            "Seleccione países da lista."
        )
        result["requirements"] = {
            "ok": False,
            "configured": True,
            "summary": result["status_msg"],
            "items": [],
            "snippet": "",
            "raw_error": "iso3",
            "visa_required": None,
        }
        result["products"] = {
            "ok": False,
            "configured": True,
            "products": [],
            "raw_error": "iso3",
            "message": result["status_msg"],
        }
        return result

    # Preferir en-US se locale inválido / curto
    loc = locale or "pt-PT"
    if loc.lower().startswith("en"):
        loc = "en-US"
    elif loc.lower().startswith("pt"):
        loc = "pt-PT"

    result["requirements"] = check_requirements(
        origin3, dest3, loc, currency, departure_date, cfg
    )
    result["products"] = list_products(dest3, origin3, currency, cfg)
    return result
