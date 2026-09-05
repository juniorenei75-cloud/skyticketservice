"""Códigos telefónicos internacionais (ITU) por país ISO.

Usado nos contactos de passageiros: qualquer código de país é reconhecido.
"""

from __future__ import annotations

import re

from countries import PAISES_MUNDO, find_country

# ISO 3166-1 alpha-2 → código de chamada (sem +)
DIAL_BY_ISO: dict[str, str] = {
    # África
    "DZ": "213",
    "AO": "244",
    "BJ": "229",
    "BW": "267",
    "BF": "226",
    "BI": "257",
    "CV": "238",
    "CM": "237",
    "TD": "235",
    "KM": "269",
    "CG": "242",
    "CD": "243",
    "CI": "225",
    "DJ": "253",
    "EG": "20",
    "ER": "291",
    "SZ": "268",
    "ET": "251",
    "GA": "241",
    "GM": "220",
    "GH": "233",
    "GN": "224",
    "GQ": "240",
    "GW": "245",
    "LS": "266",
    "LR": "231",
    "LY": "218",
    "MG": "261",
    "MW": "265",
    "ML": "223",
    "MA": "212",
    "MU": "230",
    "MR": "222",
    "MZ": "258",
    "NA": "264",
    "NE": "227",
    "NG": "234",
    "CF": "236",
    "KE": "254",
    "RW": "250",
    "ST": "239",
    "SN": "221",
    "SL": "232",
    "SC": "248",
    "SO": "252",
    "ZA": "27",
    "SS": "211",
    "SD": "249",
    "TZ": "255",
    "TG": "228",
    "TN": "216",
    "UG": "256",
    "ZM": "260",
    "ZW": "263",
    # Europa
    "AL": "355",
    "DE": "49",
    "AD": "376",
    "AT": "43",
    "BE": "32",
    "BY": "375",
    "BA": "387",
    "BG": "359",
    "CY": "357",
    "HR": "385",
    "DK": "45",
    "SK": "421",
    "SI": "386",
    "ES": "34",
    "EE": "372",
    "FI": "358",
    "FR": "33",
    "GR": "30",
    "HU": "36",
    "IE": "353",
    "IS": "354",
    "IT": "39",
    "XK": "383",
    "LV": "371",
    "LI": "423",
    "LT": "370",
    "LU": "352",
    "MK": "389",
    "MT": "356",
    "MD": "373",
    "MC": "377",
    "ME": "382",
    "NO": "47",
    "NL": "31",
    "PL": "48",
    "PT": "351",
    "GB": "44",
    "CZ": "420",
    "RO": "40",
    "RU": "7",
    "SM": "378",
    "SE": "46",
    "CH": "41",
    "RS": "381",
    "UA": "380",
    "VA": "379",
    # Ásia
    "AF": "93",
    "SA": "966",
    "AM": "374",
    "AZ": "994",
    "BH": "973",
    "BD": "880",
    "BN": "673",
    "BT": "975",
    "KH": "855",
    "KZ": "7",
    "CN": "86",
    "SG": "65",
    "KP": "850",
    "KR": "82",
    "AE": "971",
    "PH": "63",
    "GE": "995",
    "IN": "91",
    "ID": "62",
    "IR": "98",
    "IQ": "964",
    "IL": "972",
    "JP": "81",
    "YE": "967",
    "JO": "962",
    "KW": "965",
    "LA": "856",
    "LB": "961",
    "MY": "60",
    "MV": "960",
    "MN": "976",
    "MM": "95",
    "NP": "977",
    "OM": "968",
    "PK": "92",
    "QA": "974",
    "KG": "996",
    "SY": "963",
    "LK": "94",
    "TJ": "992",
    "TH": "66",
    "TW": "886",
    "TL": "670",
    "TM": "993",
    "TR": "90",
    "UZ": "998",
    "VN": "84",
    "PS": "970",
    # América
    "AG": "1",
    "AR": "54",
    "BS": "1",
    "BB": "1",
    "BZ": "501",
    "BO": "591",
    "BR": "55",
    "CA": "1",
    "CL": "56",
    "CO": "57",
    "CR": "506",
    "CU": "53",
    "DM": "1",
    "SV": "503",
    "EC": "593",
    "US": "1",
    "GD": "1",
    "GT": "502",
    "GY": "592",
    "HT": "509",
    "HN": "504",
    "JM": "1",
    "MX": "52",
    "NI": "505",
    "PA": "507",
    "PY": "595",
    "PE": "51",
    "DO": "1",
    "KN": "1",
    "LC": "1",
    "VC": "1",
    "SR": "597",
    "TT": "1",
    "UY": "598",
    "VE": "58",
    # Oceania
    "AU": "61",
    "FJ": "679",
    "MH": "692",
    "SB": "677",
    "KI": "686",
    "NR": "674",
    "NZ": "64",
    "PW": "680",
    "PG": "675",
    "WS": "685",
    "TO": "676",
    "TV": "688",
    "VU": "678",
    "FM": "691",
}


def dial_for_iso(iso: str) -> str:
    return DIAL_BY_ISO.get((iso or "").upper().strip(), "")


def all_phone_countries(lang: str = "pt") -> list[dict]:
    """Lista ordenada: nome, ISO, dial (+xxx) no idioma da sessão."""
    from countries import country_aliases, country_display_name, localize_continent

    out: list[dict] = []
    for iso, _nome_pt, cont in PAISES_MUNDO:
        dial = DIAL_BY_ISO.get(iso, "")
        if not dial:
            continue
        nome = country_display_name(iso, lang)
        out.append(
            {
                "codigo": iso,
                "nome": nome,
                "continente": localize_continent(cont, lang),
                "dial": dial,
                "label": f"{nome} (+{dial})",
                "aliases": country_aliases(iso),
            }
        )
    out.sort(key=lambda x: x["nome"].lower())
    return out


def normalize_phone(
    raw: str, default_iso: str = "MZ", lang: str | None = None
) -> tuple[str, str | None]:
    """Normaliza telefone para E.164 (+código + número).

    Aceita:
      - +258849053340
      - 258 84 905 3340
      - 84 905 3340 (usa default_iso)
    Devolve (e164, mensagem_erro|None).
    """
    try:
        from i18n import t

        def err(key: str) -> str:
            return t(key, lang)
    except Exception:  # noqa: BLE001

        def err(key: str) -> str:
            return key

    s = (raw or "").strip()
    if not s:
        return "", err("err_phone_missing")

    # manter só dígitos e +
    s = re.sub(r"[^\d+]", "", s)
    if s.startswith("00"):
        s = "+" + s[2:]

    digits = re.sub(r"\D", "", s)

    if not digits or len(digits) < 6:
        return "", err("err_phone_short")

    if len(digits) > 15:
        return "", err("err_phone_long")

    international = s.startswith("+") or (raw or "").strip().startswith("00")

    if international:
        # tentar códigos mais longos primeiro (3, depois 2, depois 1)
        matched_dial = ""
        for length in (3, 2, 1):
            prefix = digits[:length]
            if any(d == prefix for d in DIAL_BY_ISO.values()):
                matched_dial = prefix
                break
        if matched_dial and digits.startswith(matched_dial):
            national = digits[len(matched_dial) :].lstrip("0")
            if len(national) < 4:
                return "", err("err_phone_national")
            return f"+{matched_dial}{national}", None
        # + com código não mapeado: aceitar E.164 genérico
        if 8 <= len(digits) <= 15:
            return f"+{digits}", None
        return "", err("err_phone_intl")

    # Número local (sem + / 00): prefixar dial do país por defeito (ex. nacionalidade)
    iso = "MZ"
    if default_iso:
        info = find_country(default_iso)
        if info:
            iso = info["codigo"]
        elif len(default_iso) == 2:
            iso = default_iso.upper()
    dial = dial_for_iso(iso) or "258"
    national = digits.lstrip("0")
    if len(national) < 6:
        return "", err("err_phone_incomplete")
    return f"+{dial}{national}", None


def phone_looks_international(raw: str) -> bool:
    s = re.sub(r"[^\d+]", "", (raw or "").strip())
    return s.startswith("+") or s.startswith("00")
