"""Pesquisa de bilhetes aéreos — APENAS dados reais.

Sistema de produção (SKYTICKETservice), não demonstração.

Fontes permitidas no site do cliente:
1. Duffel Flights API — ofertas reais por companhia (recomendado para começar)
2. Amadeus Flight Offers (GDS) — se configurado
3. Kiwi Tequila — se configurado
4. Catálogo da agência (BD) e cotação — geridos no Admin com dados reais

NÃO se inventam preços nem horários de companhias.
Se não houver API nem catálogo: lista vazia + cotação pela agência.
"""

from __future__ import annotations

import hashlib
import json
import logging
import math
import os
import random
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any

from countries import find_country

logger = logging.getLogger(__name__)

CONFIG_PATH = Path(__file__).resolve().parent / "flight_api_config.json"
_TOKEN_CACHE: dict[str, Any] = {"amadeus": None, "amadeus_exp": 0.0}

DEFAULT_FLIGHT_API: dict[str, Any] = {
    # Duffel — principal para começar (token test_ ou live_)
    "duffel_access_token": "",
    "amadeus_client_id": "",
    "amadeus_client_secret": "",
    "amadeus_env": "test",
    "tequila_api_key": "",
    "prefer_live_only": True,
    "allow_simulated_market": False,
    "max_live_results": 80,
    # Margem da agência sobre o preço do fornecedor (Duffel/Amadeus/Kiwi)
    # Ex.: 5 → cliente paga preço_API × 1,05
    "agency_markup_percent": 5.0,
}


def load_flight_api_config() -> dict[str, Any]:
    cfg = dict(DEFAULT_FLIGHT_API)
    if CONFIG_PATH.exists():
        try:
            data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                cfg.update(data)
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning("flight_api_config.json: %s", exc)
    env_map = {
        "DUFFEL_ACCESS_TOKEN": "duffel_access_token",
        "DUFFEL_TOKEN": "duffel_access_token",
        "AMADEUS_CLIENT_ID": "amadeus_client_id",
        "AMADEUS_CLIENT_SECRET": "amadeus_client_secret",
        "AMADEUS_ENV": "amadeus_env",
        "TEQUILA_API_KEY": "tequila_api_key",
        "KIWI_API_KEY": "tequila_api_key",
    }
    for env_k, cfg_k in env_map.items():
        val = os.environ.get(env_k, "").strip()
        if val:
            cfg[cfg_k] = val
    if os.environ.get("FLIGHT_LIVE_ONLY", "").strip() != "":
        cfg["prefer_live_only"] = os.environ.get(
            "FLIGHT_LIVE_ONLY", "1"
        ).strip().lower() in ("1", "true", "yes", "on")
    cfg["amadeus_env"] = (cfg.get("amadeus_env") or "test").strip().lower()
    cfg["prefer_live_only"] = bool(cfg.get("prefer_live_only", True))
    try:
        cfg["max_live_results"] = max(
            10, min(250, int(cfg.get("max_live_results") or 80))
        )
    except (TypeError, ValueError):
        cfg["max_live_results"] = 80
    try:
        cfg["agency_markup_percent"] = max(
            0.0, min(100.0, float(cfg.get("agency_markup_percent") or 0))
        )
    except (TypeError, ValueError):
        cfg["agency_markup_percent"] = 5.0
    env_markup = os.environ.get("AGENCY_MARKUP_PERCENT", "").strip()
    if env_markup:
        try:
            cfg["agency_markup_percent"] = max(0.0, min(100.0, float(env_markup)))
        except ValueError:
            pass
    return cfg


def apply_agency_markup(
    base_price: float, cfg: dict[str, Any] | None = None
) -> tuple[float, float, float]:
    """Aplica margem da agência.

    Devolve (preco_venda, preco_base, percentagem).
    """
    cfg = cfg or load_flight_api_config()
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


def with_agency_price(offer: dict, cfg: dict[str, Any] | None = None) -> dict:
    """Copia oferta live com preço de venda (base + margem)."""
    cfg = cfg or load_flight_api_config()
    out = dict(offer)
    base = float(out.get("preco") or 0)
    sell, base_r, pct = apply_agency_markup(base, cfg)
    out["preco_base"] = base_r
    out["preco"] = sell
    out["markup_percent"] = pct
    out["markup_amount"] = round(max(0.0, sell - base_r), 2)
    return out


def save_flight_api_config(updates: dict[str, Any]) -> dict[str, Any]:
    file_cfg = dict(DEFAULT_FLIGHT_API)
    if CONFIG_PATH.exists():
        try:
            data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                file_cfg.update(data)
        except (OSError, json.JSONDecodeError):
            pass
    old_secret = file_cfg.get("amadeus_client_secret") or ""
    old_tequila = file_cfg.get("tequila_api_key") or ""
    old_duffel = file_cfg.get("duffel_access_token") or ""
    file_cfg.update(updates)
    if "amadeus_client_secret" in updates and not (
        updates.get("amadeus_client_secret") or ""
    ).strip():
        file_cfg["amadeus_client_secret"] = old_secret
    if "tequila_api_key" in updates and not (
        updates.get("tequila_api_key") or ""
    ).strip():
        file_cfg["tequila_api_key"] = old_tequila
    if "duffel_access_token" in updates and not (
        updates.get("duffel_access_token") or ""
    ).strip():
        file_cfg["duffel_access_token"] = old_duffel
    CONFIG_PATH.write_text(
        json.dumps(file_cfg, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    _TOKEN_CACHE["amadeus"] = None
    _TOKEN_CACHE["amadeus_exp"] = 0.0
    return load_flight_api_config()


def flight_api_status(cfg: dict[str, Any] | None = None) -> tuple[bool, str]:
    cfg = cfg or load_flight_api_config()
    parts = []
    duffel = (cfg.get("duffel_access_token") or "").strip()
    if duffel:
        mode = "test" if "test" in duffel else ("live" if "live" in duffel else "token")
        parts.append(f"Duffel ({mode})")
    amadeus = bool(
        (cfg.get("amadeus_client_id") or "").strip()
        and (cfg.get("amadeus_client_secret") or "").strip()
    )
    tequila = bool((cfg.get("tequila_api_key") or "").strip())
    if amadeus:
        parts.append(f"Amadeus ({cfg.get('amadeus_env') or 'test'})")
    if tequila:
        parts.append("Kiwi Tequila")
    if parts:
        return True, "Tempo real activo: " + " + ".join(parts)
    return (
        False,
        "Sem API de voos. Configure Duffel (recomendado) em Admin → Voos tempo real.",
    )


# ---------------------------------------------------------------------------
# IATA aproximado por cidade (capital / hub principal)
# ---------------------------------------------------------------------------
CITY_IATA: dict[str, str] = {
    # Moçambique / região
    "maputo": "MPM",
    "nampula": "APL",
    "beira": "BEW",
    "pemba": "POL",
    "quelimane": "UEL",
    "tete": "TET",
    "inhambane": "INH",
    "chimoio": "VPY",
    "xai-xai": "VJB",
    "lichinga": "VXC",
    "nacala": "MNC",
    "vilanculos": "VNX",
    "johannesburg": "JNB",
    "cidade do cabo": "CPT",
    "durban": "DUR",
    "pretória": "PRY",
    "port elizabeth": "PLZ",
    "bloemfontein": "BFN",
    "luanda": "LAD",
    "nairobi": "NBO",
    "mombaça": "MBA",
    "adis abeba": "ADD",
    "cairo": "CAI",
    "casablanca": "CMN",
    "lagos": "LOS",
    "abuja": "ABV",
    "dakar": "DSS",
    "accra": "ACC",
    "acra": "ACC",
    "dar es salaam": "DAR",
    "zanzibar": "ZNZ",
    "kigali": "KGL",
    "kampala": "EBB",
    "entebbe": "EBB",
    "lusaka": "LUN",
    "harare": "HRE",
    "gaborone": "GBE",
    "windhoek": "WDH",
    "mauritius": "MRU",
    "port louis": "MRU",
    "antananarivo": "TNR",
    "mahé": "SEZ",
    "victoria": "SEZ",
    # Europa
    "lisboa": "LIS",
    "porto": "OPO",
    "funchal": "FNC",
    "faro": "FAO",
    "madrid": "MAD",
    "barcelona": "BCN",
    "paris": "CDG",
    "londres": "LHR",
    "london": "LHR",
    "frankfurt": "FRA",
    "munique": "MUC",
    "berlim": "BER",
    "amesterdão": "AMS",
    "amsterdam": "AMS",
    "roma": "FCO",
    "milão": "MXP",
    "istambul": "IST",
    "viena": "VIE",
    "zurique": "ZRH",
    "bruxelas": "BRU",
    "copenhaga": "CPH",
    "estocolmo": "ARN",
    "oslo": "OSL",
    "helsínquia": "HEL",
    "varsóvia": "WAW",
    "praga": "PRG",
    "atenas": "ATH",
    "dublin": "DUB",
    "manchester": "MAN",
    # Médio Oriente / Ásia
    "dubai": "DXB",
    "abu dhabi": "AUH",
    "doha": "DOH",
    "riade": "RUH",
    "jeddah": "JED",
    "tel aviv": "TLV",
    "mumbai": "BOM",
    "nova deli": "DEL",
    "delhi": "DEL",
    "bangalore": "BLR",
    "banguecoque": "BKK",
    "bangkok": "BKK",
    "singapura": "SIN",
    "kuala lumpur": "KUL",
    "jacarta": "CGK",
    "manila": "MNL",
    "hong kong": "HKG",
    "pequim": "PEK",
    "xangai": "PVG",
    "tóquio": "NRT",
    "osaka": "KIX",
    "seul": "ICN",
    "taipei": "TPE",
    "sydney": "SYD",
    "melbourne": "MEL",
    "auckland": "AKL",
    # Américas
    "nova iorque": "JFK",
    "new york": "JFK",
    "los angeles": "LAX",
    "miami": "MIA",
    "chicago": "ORD",
    "toronto": "YYZ",
    "vancouver": "YVR",
    "são paulo": "GRU",
    "rio de janeiro": "GIG",
    "brasília": "BSB",
    "buenos aires": "EZE",
    "santiago": "SCL",
    "lima": "LIM",
    "bogotá": "BOG",
    "cidade do méxico": "MEX",
    "cancún": "CUN",
    "havana": "HAV",
}

# Companias reais + hubs típicos (IATA de hub)
AIRLINES: list[tuple[str, str, str]] = [
    ("LAM Mozambique Airlines", "TM", "MPM"),
    ("TAP Air Portugal", "TP", "LIS"),
    ("Emirates", "EK", "DXB"),
    ("Qatar Airways", "QR", "DOH"),
    ("Ethiopian Airlines", "ET", "ADD"),
    ("Kenya Airways", "KQ", "NBO"),
    ("Turkish Airlines", "TK", "IST"),
    ("Air France", "AF", "CDG"),
    ("KLM", "KL", "AMS"),
    ("British Airways", "BA", "LHR"),
    ("Lufthansa", "LH", "FRA"),
    ("Iberia", "IB", "MAD"),
    ("Swiss International", "LX", "ZRH"),
    ("EgyptAir", "MS", "CAI"),
    ("Royal Air Maroc", "AT", "CMN"),
    ("South African Airways", "SA", "JNB"),
    ("Airlink", "4Z", "JNB"),
    ("TAAG Angola Airlines", "DT", "LAD"),
    ("RwandAir", "WB", "KGL"),
    ("Air China", "CA", "PEK"),
    ("China Eastern", "MU", "PVG"),
    ("Cathay Pacific", "CX", "HKG"),
    ("Singapore Airlines", "SQ", "SIN"),
    ("Qantas", "QF", "SYD"),
    ("Japan Airlines", "JL", "NRT"),
    ("ANA", "NH", "NRT"),
    ("Delta Air Lines", "DL", "ATL"),
    ("United Airlines", "UA", "ORD"),
    ("American Airlines", "AA", "DFW"),
    ("LATAM", "LA", "GRU"),
    ("Air Canada", "AC", "YYZ"),
    ("Etihad Airways", "EY", "AUH"),
    ("Saudia", "SV", "RUH"),
    ("Oman Air", "WY", "MCT"),
    ("Air India", "AI", "DEL"),
    ("IndiGo", "6E", "DEL"),
    ("Ryanair", "FR", "DUB"),
    ("easyJet", "U2", "LGW"),
    ("Wizz Air", "W6", "BUD"),
    ("Pegasus Airlines", "PC", "SAW"),
    ("Air Arabia", "G9", "SHJ"),
    ("Flydubai", "FZ", "DXB"),
    ("Condor", "DE", "FRA"),
    ("Brussels Airlines", "SN", "BRU"),
    ("Austrian Airlines", "OS", "VIE"),
    ("SAS", "SK", "ARN"),
    ("Finnair", "AY", "HEL"),
    ("LOT Polish", "LO", "WAW"),
    ("Aegean Airlines", "A3", "ATH"),
    ("Copa Airlines", "CM", "PTY"),
    ("Avianca", "AV", "BOG"),
    ("GOL", "G3", "GRU"),
    ("Azul", "AD", "VCP"),
]

HUBS_AFRICA = ["JNB", "ADD", "NBO", "CAI", "CMN", "LOS", "MPM"]
HUBS_EU = ["LIS", "CDG", "FRA", "AMS", "LHR", "MAD", "IST"]
HUBS_ME = ["DXB", "DOH", "AUH", "IST"]
HUBS_ASIA = ["SIN", "BKK", "HKG", "NRT", "ICN", "DEL"]
HUBS_AM = ["GRU", "JFK", "MIA", "EZE", "BOG"]


def _norm(s: str) -> str:
    return (s or "").strip().lower()


def resolve_iata(city: str, country: str = "") -> str | None:
    """Resolve código IATA a partir da cidade (e país como fallback)."""
    c = _norm(city)
    if not c:
        return None
    if c in CITY_IATA:
        return CITY_IATA[c]
    # correspondência parcial
    for key, code in CITY_IATA.items():
        if key in c or c in key:
            return code
    # fallback: 3 letras do nome da cidade (apenas se não houver melhor)
    info = find_country(country)
    if info:
        # aeroporto genérico por país — códigos de capital comuns
        capital_guess = {
            "MZ": "MPM",
            "PT": "LIS",
            "ZA": "JNB",
            "AE": "DXB",
            "FR": "CDG",
            "GB": "LHR",
            "US": "JFK",
            "BR": "GRU",
            "CN": "PEK",
            "IN": "DEL",
            "TR": "IST",
            "KE": "NBO",
            "ET": "ADD",
            "EG": "CAI",
            "QA": "DOH",
            "AO": "LAD",
            "NG": "LOS",
            "MA": "CMN",
            "ES": "MAD",
            "DE": "FRA",
            "NL": "AMS",
            "IT": "FCO",
            "JP": "NRT",
            "AU": "SYD",
            "CA": "YYZ",
            "MX": "MEX",
            "AR": "EZE",
            "CL": "SCL",
            "PE": "LIM",
            "CO": "BOG",
            "SA": "RUH",
            "SG": "SIN",
            "TH": "BKK",
            "HK": "HKG",
            "KR": "ICN",
        }
        return capital_guess.get(info["codigo"])
    return None


def _seed_int(*parts: Any) -> int:
    raw = "|".join(str(p) for p in parts)
    return int(hashlib.md5(raw.encode("utf-8")).hexdigest()[:8], 16)


def _approx_distance_km(o_iata: str, d_iata: str) -> float:
    """Distância aproximada entre hubs (haversine leve com coords típicas)."""
    # coordenadas aproximadas de hubs (lat, lon)
    coords = {
        "MPM": (-25.92, 32.57),
        "APL": (-15.11, 39.28),
        "BEW": (-19.80, 34.91),
        "JNB": (-26.14, 28.25),
        "CPT": (-33.97, 18.60),
        "LAD": (-8.86, 13.23),
        "NBO": (-1.32, 36.93),
        "ADD": (8.98, 38.80),
        "CAI": (30.12, 31.41),
        "CMN": (33.37, -7.59),
        "LOS": (6.58, 3.32),
        "LIS": (38.77, -9.13),
        "OPO": (41.25, -8.68),
        "MAD": (40.47, -3.56),
        "CDG": (49.01, 2.55),
        "LHR": (51.47, -0.46),
        "FRA": (50.04, 8.56),
        "AMS": (52.31, 4.77),
        "FCO": (41.80, 12.25),
        "IST": (41.28, 28.75),
        "DXB": (25.25, 55.36),
        "DOH": (25.27, 51.61),
        "AUH": (24.43, 54.65),
        "BOM": (19.09, 72.87),
        "DEL": (28.56, 77.10),
        "BKK": (13.69, 100.75),
        "SIN": (1.36, 103.99),
        "HKG": (22.31, 113.91),
        "PEK": (40.08, 116.58),
        "PVG": (31.14, 121.81),
        "NRT": (35.77, 140.39),
        "ICN": (37.46, 126.44),
        "SYD": (-33.95, 151.18),
        "JFK": (40.64, -73.78),
        "LAX": (33.94, -118.41),
        "MIA": (25.80, -80.29),
        "ORD": (41.98, -87.90),
        "YYZ": (43.68, -79.63),
        "GRU": (-23.43, -46.47),
        "GIG": (-22.81, -43.25),
        "EZE": (-34.82, -58.54),
        "SCL": (-33.39, -70.79),
        "LIM": (-12.02, -77.11),
        "BOG": (4.70, -74.15),
        "MEX": (19.44, -99.07),
        "ATL": (33.64, -84.43),
        "DFW": (32.90, -97.04),
        "MCT": (23.59, 58.28),
        "RUH": (24.96, 46.70),
        "JED": (21.68, 39.16),
        "TLV": (32.01, 34.89),
        "DAR": (-6.88, 39.20),
        "ZNZ": (-6.22, 39.22),
        "KGL": (-1.97, 30.14),
        "EBB": (0.04, 32.44),
        "LUN": (-15.33, 28.45),
        "HRE": (-17.93, 31.09),
        "DSS": (14.67, -17.07),
        "ACC": (5.61, -0.17),
        "VIE": (48.11, 16.57),
        "ZRH": (47.46, 8.55),
        "BRU": (50.90, 4.48),
        "CPH": (55.62, 12.65),
        "ARN": (59.65, 17.92),
        "HEL": (60.32, 24.96),
        "WAW": (52.17, 20.97),
        "PRG": (50.10, 14.26),
        "ATH": (37.94, 23.94),
        "DUB": (53.42, -6.27),
        "MAN": (53.35, -2.27),
        "MUC": (48.35, 11.79),
        "BER": (52.37, 13.50),
        "KUL": (2.75, 101.71),
        "CGK": (-6.13, 106.66),
        "MNL": (14.51, 121.02),
        "TPE": (25.08, 121.23),
        "MEL": (-37.67, 144.84),
        "AKL": (-37.01, 174.79),
        "YVR": (49.19, -123.18),
        "BSB": (-15.87, -47.92),
        "CUN": (21.04, -86.87),
        "HAV": (22.99, -82.41),
        "PTY": (9.07, -79.38),
        "VCP": (-23.01, -47.13),
        "SAW": (40.90, 29.31),
        "SHJ": (25.33, 55.52),
        "LGW": (51.15, -0.19),
        "BUD": (47.44, 19.26),
        "POL": (-12.99, 40.52),
        "TET": (-16.10, 33.64),
    }
    a = coords.get(o_iata.upper())
    b = coords.get(d_iata.upper())
    if not a or not b:
        # distância média continental genérica
        return 4500.0
    lat1, lon1 = map(math.radians, a)
    lat2, lon2 = map(math.radians, b)
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    h = (
        math.sin(dlat / 2) ** 2
        + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    )
    return 6371 * 2 * math.asin(math.sqrt(min(1.0, h)))


def _duration_str(hours: float) -> str:
    h = int(hours)
    m = int(round((hours - h) * 60))
    if m >= 60:
        h += 1
        m = 0
    return f"{h}h {m:02d}m"


def _cabin_multiplier(classe_id: str) -> float:
    c = (classe_id or "economica").lower()
    if c in ("primeira", "first"):
        return 3.4
    if c in ("executiva", "business"):
        return 2.15
    return 1.0


def airline_name_from_code(code: str, fallback: str = "") -> str:
    c = (code or "").upper().strip()
    for name, ac, _hub in AIRLINES:
        if ac == c:
            return name
    try:
        for name, ac, _hub in PREMIUM_AIRLINE_POOL + BUDGET_AIRLINE_POOL:
            if ac == c:
                return name
    except NameError:
        pass
    return fallback or c or "Companhia"


def _amadeus_host(cfg: dict[str, Any] | None = None) -> str:
    cfg = cfg or load_flight_api_config()
    env = (cfg.get("amadeus_env") or "test").strip().lower()
    return (
        "https://api.amadeus.com"
        if env == "production"
        else "https://test.api.amadeus.com"
    )


def _amadeus_token(cfg: dict[str, Any] | None = None) -> str | None:
    cfg = cfg or load_flight_api_config()
    cid = (cfg.get("amadeus_client_id") or "").strip()
    secret = (cfg.get("amadeus_client_secret") or "").strip()
    if not cid or not secret:
        return None
    now = time.time()
    if _TOKEN_CACHE.get("amadeus") and now < float(_TOKEN_CACHE.get("amadeus_exp") or 0):
        return _TOKEN_CACHE["amadeus"]

    host = _amadeus_host(cfg)
    data = urllib.parse.urlencode(
        {
            "grant_type": "client_credentials",
            "client_id": cid,
            "client_secret": secret,
        }
    ).encode()
    req = urllib.request.Request(
        f"{host}/v1/security/oauth2/token",
        data=data,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            body = json.loads(resp.read().decode())
            token = body.get("access_token")
            expires = int(body.get("expires_in") or 1700)
            if token:
                _TOKEN_CACHE["amadeus"] = token
                _TOKEN_CACHE["amadeus_exp"] = now + max(60, expires - 60)
            return token
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, KeyError) as exc:
        logger.warning("Amadeus token falhou: %s", exc)
        return None


def _brand_color(code: str) -> str:
    hue = (sum(ord(c) for c in (code or "XX")) * 37) % 360
    return f"hsl({hue}, 55%, 32%)"


def _normalize_offer(
    *,
    uid: str,
    origin: str,
    destination: str,
    companhia: str,
    airline_code: str,
    flight_no: str,
    dep_time: str,
    arr_time: str,
    dur: str,
    stops: int,
    unit: float,
    currency: str,
    travel_class: str,
    fonte: str,
    round_trip: bool,
    via: str = "",
    seats_left: int | None = None,
    detalhes_extra: str = "",
) -> dict:
    stops_lbl = "Directo" if stops == 0 else f"{stops} escala(s)"
    code = (airline_code or "").upper()
    name = airline_name_from_code(code, companhia)
    label = f"{origin} ⇄ {destination}" if round_trip else f"{origin} → {destination}"
    det = (
        f"Tempo real · {name} · Voo {flight_no or code} · {stops_lbl}"
        f"{' · via ' + via if via else ''} · Chegada {arr_time}"
    )
    if detalhes_extra:
        det = f"{det} · {detalhes_extra}"
    return {
        "uid": uid,
        "id": 0,
        "kind": "voo",
        "tipo": "tempo_real",
        "origem": origin,
        "destino": destination,
        "origem_iata": origin,
        "destino_iata": destination,
        "companhia": name,
        "airline_code": code,
        "logo_url": airline_logo_url(code, 64),
        "logo_urls": airline_logo_urls(code),
        "classe": travel_class,
        "duracao": dur,
        "horario": dep_time,
        "horario_chegada": arr_time,
        "preco": unit,
        "moeda": currency,
        "label": label,
        "detalhes": det,
        "fonte": fonte,
        "stops": stops,
        "stops_label": stops_lbl,
        "flight_no": flight_no or code,
        "brand_color": _brand_color(code),
        "bagagem": "Conforme tarifa da companhia",
        "bagagem_cabine": "1× cabine",
        "trip_label": "Ida e volta" if round_trip else "Só ida",
        "via": via,
        "seats_left": seats_left,
        "live": True,
    }


def search_duffel(
    origin: str,
    destination: str,
    departure_date: str,
    return_date: str | None,
    adults: int,
    children: int,
    travel_class: str,
    max_results: int = 50,
    cfg: dict[str, Any] | None = None,
) -> list[dict]:
    """Duffel Flights API — ofertas reais por companhia aérea.

    Docs: https://duffel.com/docs/api/offer-requests/create-offer-request
    Token: app.duffel.com → Developers → Access tokens (duffel_test_… ou duffel_live_…)
    """
    cfg = cfg or load_flight_api_config()
    token = (cfg.get("duffel_access_token") or "").strip()
    if not token:
        return []

    cabin_map = {
        "economica": "economy",
        "executiva": "business",
        "primeira": "first",
    }
    cabin = cabin_map.get((travel_class or "economica").lower(), "economy")

    slices: list[dict[str, str]] = [
        {
            "origin": origin,
            "destination": destination,
            "departure_date": departure_date[:10],
        }
    ]
    if return_date:
        slices.append(
            {
                "origin": destination,
                "destination": origin,
                "departure_date": return_date[:10],
            }
        )

    passengers: list[dict[str, Any]] = []
    for _ in range(max(1, min(9, adults))):
        passengers.append({"type": "adult"})
    # Crianças: Duffel prefere idade (ex. 8) em vez de type child em alguns fluxos
    for _ in range(max(0, min(8, children))):
        passengers.append({"age": 8})

    body = {
        "data": {
            "slices": slices,
            "passengers": passengers,
            "cabin_class": cabin,
        }
    }

    # return_offers=true devolve ofertas já na resposta do offer_request
    url = (
        "https://api.duffel.com/air/offer_requests"
        "?return_offers=true&supplier_timeout=15000"
    )
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        method="POST",
        headers={
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Duffel-Version": "v2",
            "Authorization": f"Bearer {token}",
            "Accept-Encoding": "gzip",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=45) as resp:
            raw = resp.read()
            # gzip opcional
            if resp.headers.get("Content-Encoding") == "gzip":
                import gzip

                raw = gzip.decompress(raw)
            payload = json.loads(raw.decode("utf-8"))
    except urllib.error.HTTPError as exc:
        try:
            err_body = exc.read().decode("utf-8", errors="replace")[:400]
        except Exception:
            err_body = str(exc)
        logger.warning("Duffel HTTP %s: %s", exc.code, err_body)
        return []
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError) as exc:
        logger.warning("Duffel search falhou: %s", exc)
        return []

    data_obj = payload.get("data") or {}
    offers = data_obj.get("offers") or []
    pax = max(1, adults + children)
    out: list[dict] = []

    for i, offer in enumerate(offers[: max(1, min(200, max_results))]):
        try:
            total = float(offer.get("total_amount") or 0)
            if total <= 0:
                continue
            currency = (offer.get("total_currency") or "USD").upper()
            unit = round(total / pax, 2) if pax else total

            owner = offer.get("owner") or {}
            carrier_code = (
                owner.get("iata_code") or owner.get("iata_airline_code") or ""
            ).upper()
            companhia = owner.get("name") or airline_name_from_code(
                carrier_code, carrier_code
            )

            offer_slices = offer.get("slices") or []
            if not offer_slices:
                continue
            segs0 = offer_slices[0].get("segments") or []
            if not segs0:
                continue
            first = segs0[0]
            last = segs0[-1]

            def _iata(node: dict, key: str = "iata_code") -> str:
                if not isinstance(node, dict):
                    return ""
                # origin/destination podem ser objectos com iata_code
                return (node.get(key) or node.get("iata_code") or "") or ""

            o_from = first.get("origin") or {}
            o_to = last.get("destination") or {}
            dep_at = first.get("departing_at") or ""
            arr_at = last.get("arriving_at") or ""
            dep_time = dep_at[11:16] if len(dep_at) >= 16 else "—"
            arr_time = arr_at[11:16] if len(arr_at) >= 16 else "—"

            mkt = first.get("marketing_carrier") or {}
            if not carrier_code:
                carrier_code = (mkt.get("iata_code") or "").upper()
                if not companhia or companhia == carrier_code:
                    companhia = mkt.get("name") or airline_name_from_code(
                        carrier_code, carrier_code
                    )
            flight_n = str(
                first.get("marketing_carrier_flight_number")
                or first.get("operating_carrier_flight_number")
                or ""
            )
            flight_no = f"{carrier_code}{flight_n}" if carrier_code else flight_n

            stops = max(0, len(segs0) - 1)
            via = ", ".join(
                _iata(s.get("destination") or {})
                for s in segs0[:-1]
                if _iata(s.get("destination") or {})
            )
            for sl in offer_slices[1:]:
                segs = sl.get("segments") or []
                stops += max(0, len(segs) - 1)

            dur = _parse_iso_duration(
                offer_slices[0].get("duration") or first.get("duration") or "PT0H"
            )
            aircraft = ""
            ac = first.get("aircraft") or {}
            if isinstance(ac, dict):
                aircraft = ac.get("name") or ac.get("iata_code") or ""

            segs_detail = []
            for s in segs0:
                mc = s.get("marketing_carrier") or {}
                sc = (mc.get("iata_code") or carrier_code or "").upper()
                sn = str(
                    s.get("marketing_carrier_flight_number")
                    or s.get("operating_carrier_flight_number")
                    or ""
                )
                segs_detail.append(
                    {
                        "voo": f"{sc}{sn}",
                        "de": _iata(s.get("origin") or {}),
                        "para": _iata(s.get("destination") or {}),
                        "partida": (s.get("departing_at") or "")[11:16] or "—",
                        "chegada": (s.get("arriving_at") or "")[11:16] or "—",
                        "companhia": mc.get("name")
                        or airline_name_from_code(sc, sc),
                    }
                )

            offer_id = offer.get("id") or i
            row = _normalize_offer(
                uid=f"duffel-{offer_id}",
                origin=origin,
                destination=destination,
                companhia=companhia,
                airline_code=carrier_code,
                flight_no=flight_no,
                dep_time=dep_time,
                arr_time=arr_time,
                dur=dur,
                stops=stops,
                unit=unit,
                currency=currency,
                travel_class=travel_class,
                fonte="duffel",
                round_trip=bool(return_date) or len(offer_slices) > 1,
                via=via,
                seats_left=None,
                detalhes_extra=aircraft or "",
            )
            if aircraft:
                row["aircraft"] = aircraft
            row["segments"] = segs_detail
            row["duffel_offer_id"] = offer_id
            row["origem_iata"] = _iata(o_from) or origin
            row["destino_iata"] = _iata(o_to) or destination
            # bagagem se existir na oferta
            try:
                bags = offer.get("passengers") or []
                if bags and isinstance(bags[0], dict):
                    baggages = bags[0].get("baggages") or []
                    if baggages:
                        row["bagagem"] = ", ".join(
                            f"{b.get('quantity', 1)}× {b.get('type', 'bag')}"
                            for b in baggages
                            if isinstance(b, dict)
                        )
            except (TypeError, KeyError, IndexError):
                pass
            out.append(row)
        except (TypeError, ValueError, KeyError) as exc:
            logger.debug("Duffel offer skip: %s", exc)
            continue
    return out


def search_amadeus(
    origin: str,
    destination: str,
    departure_date: str,
    return_date: str | None,
    adults: int,
    children: int,
    travel_class: str,
    max_results: int = 50,
    cfg: dict[str, Any] | None = None,
) -> list[dict]:
    """Amadeus Flight Offers — tarifas GDS em tempo real por companhia."""
    cfg = cfg or load_flight_api_config()
    token = _amadeus_token(cfg)
    if not token:
        return []

    cabin_map = {
        "economica": "ECONOMY",
        "executiva": "BUSINESS",
        "primeira": "FIRST",
    }
    params: dict[str, Any] = {
        "originLocationCode": origin,
        "destinationLocationCode": destination,
        "departureDate": departure_date,
        "adults": max(1, min(9, adults)),
        "max": max(1, min(250, max_results)),
        "currencyCode": "USD",
        "travelClass": cabin_map.get((travel_class or "economica").lower(), "ECONOMY"),
        "nonStop": "false",
    }
    if children and children > 0:
        params["children"] = min(8, children)
    if return_date:
        params["returnDate"] = return_date

    qs = urllib.parse.urlencode(params)
    url = f"{_amadeus_host(cfg)}/v2/shopping/flight-offers?{qs}"
    req = urllib.request.Request(
        url,
        headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
        method="GET",
    )
    try:
        with urllib.request.urlopen(req, timeout=25) as resp:
            payload = json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        logger.warning("Amadeus search HTTP %s", exc.code)
        return []
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        logger.warning("Amadeus search falhou: %s", exc)
        return []

    dicts = payload.get("dictionaries") or {}
    carriers = dicts.get("carriers") or {}
    aircraft_dict = dicts.get("aircraft") or {}

    out: list[dict] = []
    for i, offer in enumerate(payload.get("data") or []):
        try:
            price_info = offer.get("price") or {}
            total = float(price_info.get("grandTotal") or price_info.get("total") or 0)
            currency = price_info.get("currency") or "USD"
            itineraries = offer.get("itineraries") or []
            if not itineraries:
                continue
            segs0 = itineraries[0].get("segments") or []
            if not segs0:
                continue
            first = segs0[0]
            last = segs0[-1]
            dep = (first.get("departure") or {}).get("at", "")
            arr = (last.get("arrival") or {}).get("at", "")
            dep_time = dep[11:16] if len(dep) >= 16 else "—"
            arr_time = arr[11:16] if len(arr) >= 16 else "—"
            # Companhia operadora / marketing do primeiro segmento
            carrier_code = (
                first.get("carrierCode")
                or first.get("operating", {}).get("carrierCode")
                or ""
            )
            flight_n = str(first.get("number") or "")
            flight_no = f"{carrier_code}{flight_n}" if carrier_code else flight_n
            companhia = carriers.get(carrier_code) or airline_name_from_code(
                carrier_code, carrier_code
            )
            stops = max(0, len(segs0) - 1)
            via_codes = []
            for s in segs0[:-1]:
                a = (s.get("arrival") or {}).get("iataCode")
                if a:
                    via_codes.append(a)
            for it in itineraries[1:]:
                segs = it.get("segments") or []
                stops += max(0, len(segs) - 1)
            via = ", ".join(via_codes[:3])
            dur = _parse_iso_duration(itineraries[0].get("duration") or "PT0H")
            pax = max(1, adults + children)
            unit = round(total / pax, 2) if pax else total
            ac_code = (first.get("aircraft") or {}).get("code") or ""
            ac_name = aircraft_dict.get(ac_code, ac_code)
            seats = None
            try:
                seats = int(
                    (offer.get("numberOfBookableSeats") or 0) or 0
                ) or None
            except (TypeError, ValueError):
                seats = None
            offer_id = offer.get("id") or i
            row = _normalize_offer(
                uid=f"amadeus-{offer_id}-{i}",
                origin=origin,
                destination=destination,
                companhia=companhia,
                airline_code=carrier_code,
                flight_no=flight_no,
                dep_time=dep_time,
                arr_time=arr_time,
                dur=dur,
                stops=stops,
                unit=unit,
                currency=currency,
                travel_class=travel_class,
                fonte="amadeus",
                round_trip=bool(return_date) or len(itineraries) > 1,
                via=via,
                seats_left=seats,
                detalhes_extra=ac_name or "",
            )
            if ac_name:
                row["aircraft"] = ac_name
            # segmentos para «Mostrar detalhes»
            segs_detail = []
            for s in segs0:
                sc = s.get("carrierCode") or carrier_code
                sn = s.get("number") or ""
                segs_detail.append(
                    {
                        "voo": f"{sc}{sn}",
                        "de": (s.get("departure") or {}).get("iataCode"),
                        "para": (s.get("arrival") or {}).get("iataCode"),
                        "partida": ((s.get("departure") or {}).get("at") or "")[11:16],
                        "chegada": ((s.get("arrival") or {}).get("at") or "")[11:16],
                        "companhia": carriers.get(sc) or airline_name_from_code(sc, sc),
                    }
                )
            row["segments"] = segs_detail
            out.append(row)
        except (TypeError, ValueError, KeyError) as exc:
            logger.debug("Amadeus offer skip: %s", exc)
            continue
    return out


def search_kiwi_tequila(
    origin: str,
    destination: str,
    departure_date: str,
    return_date: str | None,
    adults: int,
    children: int,
    travel_class: str,
    max_results: int = 50,
    cfg: dict[str, Any] | None = None,
) -> list[dict]:
    """Kiwi Tequila — ofertas multi-companhia em tempo real."""
    cfg = cfg or load_flight_api_config()
    key = (cfg.get("tequila_api_key") or "").strip()
    if not key:
        return []

    # date format DD/MM/YYYY
    def _dmy(iso: str) -> str:
        try:
            d = datetime.strptime(iso[:10], "%Y-%m-%d")
            return d.strftime("%d/%m/%Y")
        except ValueError:
            return iso

    cabin_map = {
        "economica": "M",
        "executiva": "C",
        "primeira": "F",
    }
    params: dict[str, Any] = {
        "fly_from": origin,
        "fly_to": destination,
        "date_from": _dmy(departure_date),
        "date_to": _dmy(departure_date),
        "adults": max(1, min(9, adults)),
        "children": max(0, min(8, children)),
        "curr": "USD",
        "limit": max(1, min(200, max_results)),
        "sort": "price",
        "max_stopovers": 3,
        "vehicle_type": "aircraft",
        "selected_cabins": cabin_map.get(
            (travel_class or "economica").lower(), "M"
        ),
    }
    if return_date:
        params["return_from"] = _dmy(return_date)
        params["return_to"] = _dmy(return_date)
        params["flight_type"] = "round"
    else:
        params["flight_type"] = "oneway"

    qs = urllib.parse.urlencode(params)
    url = f"https://api.tequila.kiwi.com/v2/search?{qs}"
    req = urllib.request.Request(
        url,
        headers={"apikey": key, "Accept": "application/json"},
        method="GET",
    )
    try:
        with urllib.request.urlopen(req, timeout=25) as resp:
            payload = json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        logger.warning("Kiwi Tequila HTTP %s", exc.code)
        return []
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        logger.warning("Kiwi Tequila falhou: %s", exc)
        return []

    out: list[dict] = []
    pax = max(1, adults + children)
    for i, offer in enumerate(payload.get("data") or []):
        try:
            price = float(offer.get("price") or 0)
            if price <= 0:
                continue
            unit = round(price / pax, 2) if pax else price
            route = offer.get("route") or []
            outbound = [r for r in route if not r.get("return")]
            if not outbound:
                outbound = route
            if not outbound:
                continue
            first = outbound[0]
            last = outbound[-1]
            airline_codes = offer.get("airlines") or []
            carrier_code = (
                (airline_codes[0] if airline_codes else None)
                or first.get("airline")
                or first.get("operating_carrier")
                or ""
            )
            carrier_code = str(carrier_code).upper()
            flight_no = f"{carrier_code}{first.get('flight_no') or ''}"
            dep_time = "—"
            arr_time = "—"
            dtime = first.get("local_departure") or first.get("utc_departure") or ""
            atime = last.get("local_arrival") or last.get("utc_arrival") or ""
            if len(str(dtime)) >= 16:
                dep_time = str(dtime)[11:16]
            if len(str(atime)) >= 16:
                arr_time = str(atime)[11:16]
            stops = max(0, len(outbound) - 1)
            via = ", ".join(
                str(r.get("flyTo") or "")
                for r in outbound[:-1]
                if r.get("flyTo")
            )
            # duração em segundos
            dur_s = int(offer.get("duration", {}).get("departure") or 0)
            if not dur_s and offer.get("fly_duration"):
                # e.g. "12h 30m"
                dur = str(offer.get("fly_duration"))
            else:
                h, m = divmod(max(0, dur_s) // 60, 60)
                dur = f"{h}h {m:02d}m"
            segs_detail = []
            for r in outbound:
                ac = str(r.get("airline") or carrier_code).upper()
                segs_detail.append(
                    {
                        "voo": f"{ac}{r.get('flight_no') or ''}",
                        "de": r.get("flyFrom"),
                        "para": r.get("flyTo"),
                        "partida": (str(r.get("local_departure") or "")[11:16] or "—"),
                        "chegada": (str(r.get("local_arrival") or "")[11:16] or "—"),
                        "companhia": airline_name_from_code(ac, ac),
                    }
                )
            row = _normalize_offer(
                uid=f"kiwi-{offer.get('id') or i}",
                origin=origin,
                destination=destination,
                companhia=airline_name_from_code(carrier_code, carrier_code),
                airline_code=carrier_code,
                flight_no=flight_no,
                dep_time=dep_time,
                arr_time=arr_time,
                dur=dur,
                stops=stops,
                unit=unit,
                currency="USD",
                travel_class=travel_class,
                fonte="kiwi",
                round_trip=bool(return_date),
                via=via,
                seats_left=offer.get("availability", {}).get("seats")
                if isinstance(offer.get("availability"), dict)
                else None,
            )
            row["segments"] = segs_detail
            out.append(row)
        except (TypeError, ValueError, KeyError) as exc:
            logger.debug("Kiwi offer skip: %s", exc)
            continue
    return out


def _parse_iso_duration(iso: str) -> str:
    # PT12H45M or PT5H
    iso = (iso or "").replace("PT", "")
    h = m = 0
    if "H" in iso:
        parts = iso.split("H")
        try:
            h = int(parts[0] or 0)
        except ValueError:
            h = 0
        iso = parts[1] if len(parts) > 1 else ""
    if "M" in iso:
        try:
            m = int(iso.replace("M", "") or 0)
        except ValueError:
            m = 0
    return f"{h}h {m:02d}m"


# Companhias premium — sempre disponíveis no modo «melhores»
PREMIUM_AIRLINE_POOL: list[tuple[str, str, str]] = [
    ("Emirates", "EK", "DXB"),
    ("Qatar Airways", "QR", "DOH"),
    ("Ethiopian Airlines", "ET", "ADD"),
    ("TAP Air Portugal", "TP", "LIS"),
    ("Turkish Airlines", "TK", "IST"),
    ("Etihad Airways", "EY", "AUH"),
    ("Lufthansa", "LH", "FRA"),
    ("British Airways", "BA", "LHR"),
    ("Air France", "AF", "CDG"),
    ("KLM", "KL", "AMS"),
    ("Swiss International", "LX", "ZRH"),
    ("Singapore Airlines", "SQ", "SIN"),
    ("Kenya Airways", "KQ", "NBO"),
    ("EgyptAir", "MS", "CAI"),
    ("South African Airways", "SA", "JNB"),
    ("Qatar Airways", "QR", "DOH"),  # reforço
    ("Emirates", "EK", "DXB"),
    ("Ethiopian Airlines", "ET", "ADD"),
]

# Companhias económicas / low-cost — modo «baratos»
BUDGET_AIRLINE_POOL: list[tuple[str, str, str]] = [
    ("Ryanair", "FR", "DUB"),
    ("easyJet", "U2", "LGW"),
    ("Wizz Air", "W6", "BUD"),
    ("Pegasus Airlines", "PC", "SAW"),
    ("Air Arabia", "G9", "SHJ"),
    ("Flydubai", "FZ", "DXB"),
    ("IndiGo", "6E", "DEL"),
    ("GOL", "G3", "GRU"),
    ("Azul", "AD", "VCP"),
    ("Airlink", "4Z", "JNB"),
    ("LAM Mozambique Airlines", "TM", "MPM"),
    ("TAAG Angola Airlines", "DT", "LAD"),
    ("RwandAir", "WB", "KGL"),
    ("Condor", "DE", "FRA"),
    ("Pegasus Airlines", "PC", "SAW"),
    ("Air Arabia", "G9", "SHJ"),
    ("Flydubai", "FZ", "DXB"),
    ("easyJet", "U2", "LGW"),
]

PREMIUM_CODES_SET = {c for _, c, _ in PREMIUM_AIRLINE_POOL}
BUDGET_CODES_SET = {c for _, c, _ in BUDGET_AIRLINE_POOL}


# Logos locais (SVG/PNG oficiais ou Google Flights) em static/img/airlines/
_AIRLINES_LOGO_DIR = Path(__file__).resolve().parent / "static" / "img" / "airlines"


def _local_airline_logo_path(code: str) -> Path | None:
    c = (code or "").upper().strip()
    if not c:
        return None
    # PNG primeiro (mais fiável no <img>); SVG como alternativa
    for ext in (".png", ".svg", ".jpg", ".webp"):
        p = _AIRLINES_LOGO_DIR / f"{c}{ext}"
        if p.is_file() and p.stat().st_size > 100:
            return p
    return None


def airline_logo_url(code: str, size: int = 64) -> str:
    """URL do logotipo da companhia (IATA).

    Prioridade:
    1. Ficheiro local em static/img/airlines/{CODE}.svg|png  (logos correctos)
    2. Google Flights CDN
    3. Kiwi / avs.io
    """
    c = (code or "").upper().strip()
    if not c or len(c) > 3:
        return ""
    local = _local_airline_logo_path(c)
    if local:
        # caminho estático servido pelo Flask
        return f"/static/img/airlines/{local.name}"
    return f"https://www.gstatic.com/flights/airline_logos/70px/{c}.png"


def airline_logo_urls(code: str) -> list[str]:
    """Lista de URLs de logo (primária + fallbacks) para o bilhete."""
    c = (code or "").upper().strip()
    if not c or len(c) > 3:
        return []
    urls: list[str] = []
    local = _local_airline_logo_path(c)
    if local:
        urls.append(f"/static/img/airlines/{local.name}")
    # Google Flights — logos de marca usados no Google
    urls.append(f"https://www.gstatic.com/flights/airline_logos/70px/{c}.png")
    urls.append(f"https://images.kiwi.com/airlines/64/{c}.png")
    urls.append(f"https://pics.avs.io/200/200/{c}.png")
    # dedupe mantendo ordem
    seen: set[str] = set()
    out: list[str] = []
    for u in urls:
        if u not in seen:
            seen.add(u)
            out.append(u)
    return out


def generate_market_offers(
    origem_cidade: str,
    origem_pais: str,
    destino_cidade: str,
    destino_pais: str,
    data_ida: str,
    data_volta: str | None,
    classe_id: str,
    classe_nome: str,
    round_trip: bool,
    n: int = 36,
    mode: str = "",
) -> list[dict]:
    """Gera ofertas multi-companhia realistas conforme o modo escolhido.

    mode:
      - baratos  → só low-cost / económicas, preços baixos
      - melhores → só premium (Emirates, Qatar, Ethiopian, …)
      - ''       → mistura (compatibilidade)
    """
    o_iata = resolve_iata(origem_cidade, origem_pais) or "XXX"
    d_iata = resolve_iata(destino_cidade, destino_pais) or "YYY"
    dist = _approx_distance_km(o_iata, d_iata)
    cabin_m = _cabin_multiplier(classe_id)
    rt_m = 1.75 if round_trip else 1.0
    mode = (mode or "").strip().lower()

    # base USD por km — modo altera o patamar de preço
    if mode == "baratos":
        base_per_km = 0.055
        n = max(n, 28)
    elif mode == "melhores":
        base_per_km = 0.12
        n = max(n, 24)
    else:
        base_per_km = 0.085
    base = max(85.0, dist * base_per_km) * cabin_m * rt_m

    # sazonalidade / dia da semana
    try:
        dt = datetime.strptime(data_ida, "%Y-%m-%d")
        dow = dt.weekday()  # 0=seg
        season = 1.12 if dow in (4, 5, 6) else 1.0
        month = dt.month
        if month in (7, 8, 12):
            season *= 1.18
        elif month in (1, 2):
            season *= 0.92
    except ValueError:
        season = 1.0
        dow = 0

    seed = _seed_int(
        origem_cidade,
        destino_cidade,
        data_ida,
        data_volta or "",
        classe_id,
        round_trip,
        mode or "all",
    )
    rng = random.Random(seed)

    # Pool de companhias conforme a escolha do utilizador (realista)
    if mode == "melhores":
        # Garantir Emirates, Qatar e Ethiopian no topo da lista
        core = [
            ("Emirates", "EK", "DXB"),
            ("Qatar Airways", "QR", "DOH"),
            ("Ethiopian Airlines", "ET", "ADD"),
        ]
        rest = [a for a in PREMIUM_AIRLINE_POOL if a[1] not in ("EK", "QR", "ET")]
        rng.shuffle(rest)
        pool = core + rest
        while len(pool) < n:
            pool.extend(PREMIUM_AIRLINE_POOL)
        pool = pool[:n]
    elif mode == "baratos":
        pool = list(BUDGET_AIRLINE_POOL)
        rng.shuffle(pool)
        while len(pool) < n:
            pool.extend(BUDGET_AIRLINE_POOL)
        pool = pool[:n]
    else:
        airlines = list(AIRLINES)
        rng.shuffle(airlines)
        preferred = []
        others = []
        for name, code, hub in airlines:
            if hub in (o_iata, d_iata) or abs(hash(hub) % 7) == 0:
                preferred.append((name, code, hub))
            else:
                others.append((name, code, hub))
        pool = (preferred + others)[: max(n, 40)]
        while len(pool) < n:
            pool.extend(AIRLINES)
        pool = pool[:n]

    # horários de partida comuns
    dep_slots = [
        "05:40",
        "06:15",
        "07:00",
        "07:45",
        "08:30",
        "09:10",
        "10:00",
        "11:20",
        "12:05",
        "13:40",
        "14:15",
        "15:30",
        "16:45",
        "17:20",
        "18:00",
        "19:10",
        "20:30",
        "21:45",
        "22:55",
        "23:40",
    ]

    # escales: 0, 1, 2
    stop_options = [0, 0, 0, 1, 1, 1, 1, 2, 2]

    # hubs de ligação
    connect_hubs = HUBS_AFRICA + HUBS_EU + HUBS_ME + HUBS_ASIA + HUBS_AM

    offers: list[dict] = []
    for i in range(n):
        name, code, hub = pool[i % len(pool)]
        stops = stop_options[i % len(stop_options)]
        # low-cost / premium conforme modo (realista)
        low_cost = code in BUDGET_CODES_SET or code in (
            "FR",
            "U2",
            "W6",
            "PC",
            "G9",
            "FZ",
            "6E",
            "G3",
            "AD",
        )
        if mode == "baratos":
            low_cost = True
            brand_m = 0.62 + (i % 6) * 0.035  # faixa económica
            stop_m = 1.0 - stops * 0.10
            jitter = 0.72 + (rng.random() * 0.28)
            scarcity = 1.0
        elif mode == "melhores":
            low_cost = False
            # Emirates / Qatar / Ethiopian ligeiramente distintos
            if code == "EK":
                brand_m = 1.35 + (i % 4) * 0.04
            elif code == "QR":
                brand_m = 1.28 + (i % 4) * 0.04
            elif code == "ET":
                brand_m = 1.05 + (i % 4) * 0.03
            else:
                brand_m = 1.15 + (i % 5) * 0.05
            stop_m = 1.0 - stops * 0.04  # premium: menos desconto por escala
            jitter = 0.92 + (rng.random() * 0.22)
            scarcity = 1.0 + (0.08 if rng.random() < 0.2 else 0.0)
        else:
            brand_m = 0.72 if low_cost else (1.05 + (i % 5) * 0.04)
            stop_m = 1.0 - stops * 0.08
            jitter = 0.78 + (rng.random() * 0.55)
            scarcity = 1.0 + (0.15 if rng.random() < 0.18 else 0.0)

        price = round(base * season * brand_m * stop_m * jitter * scarcity, 2)
        # arredondar para .99 de mercado
        min_price = 39.0 if mode == "baratos" else (120.0 if mode == "melhores" else 49.0)
        price = max(min_price, math.floor(price) + 0.99)

        # duração de voo ~ dist/800 + escalas
        cruise = dist / (780 if stops == 0 else 720)
        lay = stops * (1.2 + rng.random() * 2.5)
        hours = max(0.9, cruise + lay)
        dur = _duration_str(hours)

        horario = dep_slots[(i * 3 + seed % 7) % len(dep_slots)]
        flight_no = f"{code}{100 + (seed + i * 17) % 890}"

        # chegada estimada a partir da partida + duração
        try:
            dh, dm = map(int, horario.split(":"))
            total_m = dh * 60 + dm + int(hours * 60)
            arr_h, arr_m = (total_m // 60) % 24, total_m % 60
            horario_chegada = f"{arr_h:02d}:{arr_m:02d}"
            # dia seguinte se passou da meia-noite
            next_day = total_m >= 24 * 60
        except ValueError:
            horario_chegada = "—"
            next_day = False

        via_code = ""
        if stops == 0:
            route_note = f"Voo directo {o_iata}–{d_iata}"
            stops_lbl = "Directo"
        else:
            via_code = connect_hubs[(seed + i * 5) % len(connect_hubs)]
            if via_code in (o_iata, d_iata):
                via_code = connect_hubs[(seed + i * 5 + 3) % len(connect_hubs)]
            route_note = f"{stops} escala(s) via {via_code}"
            stops_lbl = f"{stops} escala(s)"

        seats_left = 2 + (seed + i * 3) % 12
        bag = "1× 23 kg" if not low_cost else "Bagagem paga"
        bag_cabin = "1× 8 kg" if low_cost else "1× 10 kg"
        rt_note = "Ida e volta" if round_trip else "Só ida"
        aircrafts = ["A320", "A321", "A330", "A350", "B737", "B777", "B787", "E190"]
        aircraft = aircrafts[(seed + i) % len(aircrafts)]
        # cores de marca conhecidas (postura profissional)
        brand_colors = {
            "EK": "#D71921",
            "QR": "#5C0A2C",
            "ET": "#006633",
            "TP": "#00ADEF",
            "TK": "#C70A0C",
            "EY": "#BD8B13",
            "LH": "#05164D",
            "BA": "#075AAA",
            "AF": "#002157",
            "KL": "#00A1DE",
            "FR": "#073590",
            "U2": "#FF6600",
            "FZ": "#EE1C25",
            "G9": "#FF6600",
        }
        hue = (sum(ord(c) for c in code) * 37) % 360
        brand_color = brand_colors.get(code, f"hsl({hue}, 55%, 32%)")

        label = f"{origem_cidade} → {destino_cidade}"
        if round_trip:
            label = f"{origem_cidade} ⇄ {destino_cidade}"

        offers.append(
            {
                "uid": f"mkt-{seed:x}-{i}",
                "id": 0,
                "kind": "voo",
                "tipo": "mercado",
                "origem": f"{origem_cidade}, {origem_pais}",
                "destino": f"{destino_cidade}, {destino_pais}",
                "origem_iata": o_iata,
                "destino_iata": d_iata,
                "origem_cidade": origem_cidade,
                "destino_cidade": destino_cidade,
                "companhia": name,
                "airline_code": code,
                "logo_url": airline_logo_url(code, 64),
                "logo_urls": airline_logo_urls(code),
                "classe": classe_nome,
                "duracao": dur,
                "horario": horario,
                "horario_chegada": horario_chegada,
                "next_day": next_day,
                "preco": price,
                "moeda": "USD",
                "label": label,
                "detalhes": (
                    f"{flight_no} · {route_note} · {bag} · "
                    f"{seats_left} lugares · {stops_lbl} · {rt_note}"
                ),
                "fonte": "mercado",
                "stops": stops,
                "stops_label": stops_lbl,
                "via": via_code,
                "flight_no": flight_no,
                "seats_left": seats_left,
                "bagagem": bag,
                "bagagem_cabine": bag_cabin,
                "aircraft": aircraft,
                "brand_color": brand_color,
                "trip_label": rt_note,
                "low_cost": low_cost,
            }
        )

    offers.sort(key=lambda x: (x["preco"] if x["preco"] > 0 else 1e12, x["horario"]))
    return offers


def _dedupe_offers(offers: list[dict]) -> list[dict]:
    seen: set[tuple] = set()
    out: list[dict] = []
    for t in offers:
        key = (
            (t.get("airline_code") or t.get("companhia") or "").upper(),
            t.get("flight_no") or "",
            t.get("horario") or "",
            t.get("horario_chegada") or "",
            round(float(t.get("preco") or 0), 0),
        )
        if key in seen:
            continue
        seen.add(key)
        out.append(t)
    return out


def _filter_by_mode(offers: list[dict], mode: str) -> list[dict]:
    """Filtra tempo real conforme preferência baratos / melhores."""
    mode = (mode or "").strip().lower()
    if not mode or not offers:
        return offers
    premium_codes = {a[1] for a in PREMIUM_AIRLINE_POOL}
    budget_codes = {a[1] for a in BUDGET_AIRLINE_POOL} | {
        "FR",
        "U2",
        "W6",
        "PC",
        "G9",
        "FZ",
        "6E",
        "TO",
        "VY",
        "NK",
        "F9",
    }
    if mode == "melhores":
        pref = [
            t
            for t in offers
            if (t.get("airline_code") or "").upper() in premium_codes
            or not t.get("low_cost")
        ]
        # se filtrar demasiado, manter top por companhia premium + caras
        if len(pref) >= 5:
            return pref
        return sorted(
            offers,
            key=lambda x: (
                0 if (x.get("airline_code") or "").upper() in premium_codes else 1,
                -(float(x.get("preco") or 0)),
            ),
        )
    if mode == "baratos":
        # preferir low-cost e preços baixos (já ordenados)
        cheap = [
            t
            for t in offers
            if (t.get("airline_code") or "").upper() in budget_codes
            or t.get("low_cost")
            or float(t.get("preco") or 0) > 0
        ]
        return cheap or offers
    return offers


def search_flights(booking: dict) -> tuple[list[dict], str]:
    """Pesquisa completa. Devolve (lista ordenada por preço, fonte_label).

    fonte_label: 'amadeus' | 'kiwi' | 'live' | 'mercado'
    Com API activa e resultados: só tempo real (por companhia aérea).
    """
    cfg = load_flight_api_config()
    origem_cidade = booking.get("origem_cidade") or ""
    origem_pais = booking.get("origem_pais") or ""
    destino_cidade = booking.get("destino_cidade") or ""
    destino_pais = booking.get("destino_pais") or ""
    data_ida = booking.get("data_viagem") or ""
    data_volta = booking.get("data_regresso") or ""
    round_trip = (booking.get("tipo_viagem") or "ida_volta") == "ida_volta"
    classe_id = booking.get("classe") or "economica"
    classe_nome = booking.get("classe_nome") or "Económica"
    adults = int(booking.get("n_adultos") or 1)
    children = int(booking.get("n_criancas") or 0)
    mode = (booking.get("ticket_mode") or "").strip().lower()
    max_live = int(cfg.get("max_live_results") or 80)

    o_iata = resolve_iata(origem_cidade, origem_pais)
    d_iata = resolve_iata(destino_cidade, destino_pais)

    live: list[dict] = []
    sources_hit: list[str] = []

    if o_iata and d_iata and data_ida:
        # 1) Duffel — principal (ofertas reais por companhia)
        duffel = search_duffel(
            o_iata,
            d_iata,
            data_ida,
            data_volta if round_trip else None,
            adults,
            children,
            classe_id,
            max_results=max_live,
            cfg=cfg,
        )
        if duffel:
            sources_hit.append("duffel")
            live.extend(duffel)

        # 2) Amadeus GDS — se configurado
        amadeus = search_amadeus(
            o_iata,
            d_iata,
            data_ida,
            data_volta if round_trip else None,
            adults,
            children,
            classe_id,
            max_results=max_live,
            cfg=cfg,
        )
        if amadeus:
            sources_hit.append("amadeus")
            live.extend(amadeus)

        # 3) Kiwi Tequila — se configurado
        kiwi = search_kiwi_tequila(
            o_iata,
            d_iata,
            data_ida,
            data_volta if round_trip else None,
            adults,
            children,
            classe_id,
            max_results=max_live,
            cfg=cfg,
        )
        if kiwi:
            sources_hit.append("kiwi")
            live.extend(kiwi)

    for t in live:
        t["classe"] = classe_nome
        t["live"] = True
        t["tipo"] = "tempo_real"

    live = _dedupe_offers(live)
    live = _filter_by_mode(live, mode)
    live.sort(
        key=lambda x: (
            float(x["preco"]) if float(x.get("preco") or 0) > 0 else 1e12,
            x.get("horario") or "",
            x.get("companhia") or "",
        )
    )

    if live:
        # Margem da agência sobre o preço do fornecedor (ex. Duffel)
        live = [with_agency_price(t, cfg) for t in live[:max_live]]
        if len(sources_hit) > 1:
            return live, "live"
        return live, sources_hit[0] if sources_hit else "live"

    # Sem inventar bilhetes: vazio. O fluxo de reserva acrescenta catálogo + cotação.
    ready, _msg = flight_api_status(cfg)
    if not ready:
        return [], "sem_api"
    if not o_iata or not d_iata:
        return [], "sem_iata"
    if not data_ida:
        return [], "sem_data"
    return [], "sem_resultados"
