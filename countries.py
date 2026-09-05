"""Todos os países do mundo — SKYTICKETservice (sem limites de destino).

Lista com nomes em português, código ISO e continente.
"""

from __future__ import annotations

# (codigo_iso, nome_pt, continente)
PAISES_MUNDO: list[tuple[str, str, str]] = [
    # África
    ("DZ", "Argélia", "África"),
    ("AO", "Angola", "África"),
    ("BJ", "Benim", "África"),
    ("BW", "Botswana", "África"),
    ("BF", "Burquina Faso", "África"),
    ("BI", "Burundi", "África"),
    ("CV", "Cabo Verde", "África"),
    ("CM", "Camarões", "África"),
    ("TD", "Chade", "África"),
    ("KM", "Comores", "África"),
    ("CG", "Congo", "África"),
    ("CD", "Congo (RDC)", "África"),
    ("CI", "Costa do Marfim", "África"),
    ("DJ", "Djibuti", "África"),
    ("EG", "Egipto", "África"),
    ("ER", "Eritreia", "África"),
    ("SZ", "Eswatini", "África"),
    ("ET", "Etiópia", "África"),
    ("GA", "Gabão", "África"),
    ("GM", "Gâmbia", "África"),
    ("GH", "Gana", "África"),
    ("GN", "Guiné", "África"),
    ("GQ", "Guiné Equatorial", "África"),
    ("GW", "Guiné-Bissau", "África"),
    ("LS", "Lesoto", "África"),
    ("LR", "Libéria", "África"),
    ("LY", "Líbia", "África"),
    ("MG", "Madagáscar", "África"),
    ("MW", "Malawi", "África"),
    ("ML", "Mali", "África"),
    ("MA", "Marrocos", "África"),
    ("MU", "Maurícia", "África"),
    ("MR", "Mauritânia", "África"),
    ("MZ", "Moçambique", "África"),
    ("NA", "Namíbia", "África"),
    ("NE", "Níger", "África"),
    ("NG", "Nigéria", "África"),
    ("CF", "República Centro-Africana", "África"),
    ("KE", "Quénia", "África"),
    ("RW", "Ruanda", "África"),
    ("ST", "São Tomé e Príncipe", "África"),
    ("SN", "Senegal", "África"),
    ("SL", "Serra Leoa", "África"),
    ("SC", "Seicheles", "África"),
    ("SO", "Somália", "África"),
    ("ZA", "África do Sul", "África"),
    ("SS", "Sudão do Sul", "África"),
    ("SD", "Sudão", "África"),
    ("TZ", "Tanzânia", "África"),
    ("TG", "Togo", "África"),
    ("TN", "Tunísia", "África"),
    ("UG", "Uganda", "África"),
    ("ZM", "Zâmbia", "África"),
    ("ZW", "Zimbabwe", "África"),
    # Europa
    ("AL", "Albânia", "Europa"),
    ("DE", "Alemanha", "Europa"),
    ("AD", "Andorra", "Europa"),
    ("AT", "Áustria", "Europa"),
    ("BE", "Bélgica", "Europa"),
    ("BY", "Bielorrússia", "Europa"),
    ("BA", "Bósnia e Herzegovina", "Europa"),
    ("BG", "Bulgária", "Europa"),
    ("CY", "Chipre", "Europa"),
    ("HR", "Croácia", "Europa"),
    ("DK", "Dinamarca", "Europa"),
    ("SK", "Eslováquia", "Europa"),
    ("SI", "Eslovénia", "Europa"),
    ("ES", "Espanha", "Europa"),
    ("EE", "Estónia", "Europa"),
    ("FI", "Finlândia", "Europa"),
    ("FR", "França", "Europa"),
    ("GR", "Grécia", "Europa"),
    ("HU", "Hungria", "Europa"),
    ("IE", "Irlanda", "Europa"),
    ("IS", "Islândia", "Europa"),
    ("IT", "Itália", "Europa"),
    ("XK", "Kosovo", "Europa"),
    ("LV", "Letónia", "Europa"),
    ("LI", "Listenstaine", "Europa"),
    ("LT", "Lituânia", "Europa"),
    ("LU", "Luxemburgo", "Europa"),
    ("MK", "Macedónia do Norte", "Europa"),
    ("MT", "Malta", "Europa"),
    ("MD", "Moldávia", "Europa"),
    ("MC", "Mónaco", "Europa"),
    ("ME", "Montenegro", "Europa"),
    ("NO", "Noruega", "Europa"),
    ("NL", "Países Baixos", "Europa"),
    ("PL", "Polónia", "Europa"),
    ("PT", "Portugal", "Europa"),
    ("GB", "Reino Unido", "Europa"),
    ("CZ", "República Checa", "Europa"),
    ("RO", "Roménia", "Europa"),
    ("RU", "Rússia", "Europa"),
    ("SM", "San Marino", "Europa"),
    ("SE", "Suécia", "Europa"),
    ("CH", "Suíça", "Europa"),
    ("RS", "Sérvia", "Europa"),
    ("UA", "Ucrânia", "Europa"),
    ("VA", "Vaticano", "Europa"),
    # Ásia
    ("AF", "Afeganistão", "Ásia"),
    ("SA", "Arábia Saudita", "Ásia"),
    ("AM", "Arménia", "Ásia"),
    ("AZ", "Azerbaijão", "Ásia"),
    ("BH", "Barém", "Ásia"),
    ("BD", "Bangladesh", "Ásia"),
    ("BN", "Brunei", "Ásia"),
    ("BT", "Butão", "Ásia"),
    ("KH", "Camboja", "Ásia"),
    ("KZ", "Cazaquistão", "Ásia"),
    ("CN", "China", "Ásia"),
    ("SG", "Singapura", "Ásia"),
    ("KP", "Coreia do Norte", "Ásia"),
    ("KR", "Coreia do Sul", "Ásia"),
    ("AE", "Emirados Árabes Unidos", "Ásia"),
    ("PH", "Filipinas", "Ásia"),
    ("GE", "Geórgia", "Ásia"),
    ("IN", "Índia", "Ásia"),
    ("ID", "Indonésia", "Ásia"),
    ("IR", "Irão", "Ásia"),
    ("IQ", "Iraque", "Ásia"),
    ("IL", "Israel", "Ásia"),
    ("JP", "Japão", "Ásia"),
    ("YE", "Iémen", "Ásia"),
    ("JO", "Jordânia", "Ásia"),
    ("KW", "Kuwait", "Ásia"),
    ("LA", "Laos", "Ásia"),
    ("LB", "Líbano", "Ásia"),
    ("MY", "Malásia", "Ásia"),
    ("MV", "Maldivas", "Ásia"),
    ("MN", "Mongólia", "Ásia"),
    ("MM", "Mianmar", "Ásia"),
    ("NP", "Nepal", "Ásia"),
    ("OM", "Omã", "Ásia"),
    ("PK", "Paquistão", "Ásia"),
    ("QA", "Catar", "Ásia"),
    ("KG", "Quirguistão", "Ásia"),
    ("SY", "Síria", "Ásia"),
    ("LK", "Sri Lanka", "Ásia"),
    ("TJ", "Tajiquistão", "Ásia"),
    ("TH", "Tailândia", "Ásia"),
    ("TW", "Taiwan", "Ásia"),
    ("TL", "Timor-Leste", "Ásia"),
    ("TM", "Turquemenistão", "Ásia"),
    ("TR", "Turquia", "Ásia"),
    ("UZ", "Usbequistão", "Ásia"),
    ("VN", "Vietname", "Ásia"),
    ("PS", "Palestina", "Ásia"),
    # América
    ("AG", "Antígua e Barbuda", "América"),
    ("AR", "Argentina", "América"),
    ("BS", "Bahamas", "América"),
    ("BB", "Barbados", "América"),
    ("BZ", "Belize", "América"),
    ("BO", "Bolívia", "América"),
    ("BR", "Brasil", "América"),
    ("CA", "Canadá", "América"),
    ("CL", "Chile", "América"),
    ("CO", "Colômbia", "América"),
    ("CR", "Costa Rica", "América"),
    ("CU", "Cuba", "América"),
    ("DM", "Dominica", "América"),
    ("SV", "El Salvador", "América"),
    ("EC", "Equador", "América"),
    ("US", "Estados Unidos", "América"),
    ("GD", "Granada", "América"),
    ("GT", "Guatemala", "América"),
    ("GY", "Guiana", "América"),
    ("HT", "Haiti", "América"),
    ("HN", "Honduras", "América"),
    ("JM", "Jamaica", "América"),
    ("MX", "México", "América"),
    ("NI", "Nicarágua", "América"),
    ("PA", "Panamá", "América"),
    ("PY", "Paraguai", "América"),
    ("PE", "Peru", "América"),
    ("DO", "República Dominicana", "América"),
    ("KN", "São Cristóvão e Neves", "América"),
    ("LC", "Santa Lúcia", "América"),
    ("VC", "São Vicente e Granadinas", "América"),
    ("SR", "Suriname", "América"),
    ("TT", "Trindade e Tobago", "América"),
    ("UY", "Uruguai", "América"),
    ("VE", "Venezuela", "América"),
    # Oceania
    ("AU", "Austrália", "Oceania"),
    ("FJ", "Fiji", "Oceania"),
    ("MH", "Ilhas Marshall", "Oceania"),
    ("SB", "Ilhas Salomão", "Oceania"),
    ("KI", "Kiribati", "Oceania"),
    ("NR", "Nauru", "Oceania"),
    ("NZ", "Nova Zelândia", "Oceania"),
    ("PW", "Palau", "Oceania"),
    ("PG", "Papua-Nova Guiné", "Oceania"),
    ("WS", "Samoa", "Oceania"),
    ("TO", "Tonga", "Oceania"),
    ("TV", "Tuvalu", "Oceania"),
    ("VU", "Vanuatu", "Oceania"),
    ("FM", "Micronésia", "Oceania"),
]


CONTINENTES = ["África", "América", "Ásia", "Europa", "Oceania"]

_PT_BY_CODE: dict[str, str] = {c: n for c, n, _ in PAISES_MUNDO}
_CONT_BY_CODE: dict[str, str] = {c: cont for c, _, cont in PAISES_MUNDO}

_CONTINENT_I18N_KEY = {
    "África": "continent_africa",
    "América": "continent_america",
    "Ásia": "continent_asia",
    "Europa": "continent_europe",
    "Oceania": "continent_oceania",
}

_NAME_INDEX: dict[str, str] | None = None  # lower(name|code) → ISO


def _babel_territory(codigo: str, lang: str) -> str | None:
    try:
        from babel import Locale

        # pt_PT alinha melhor com a nossa lista (ex. Moçambique)
        tag = "pt_PT" if (lang or "pt").startswith("pt") else lang
        loc = Locale.parse(tag)
        name = loc.territories.get((codigo or "").upper())
        return name if name and name != codigo.upper() else None
    except Exception:  # noqa: BLE001
        return None


def localize_continent(continente: str, lang: str = "pt") -> str:
    key = _CONTINENT_I18N_KEY.get(continente)
    if not key:
        return continente
    try:
        from i18n import t

        return t(key, lang)
    except Exception:  # noqa: BLE001
        return continente


def country_display_name(codigo: str, lang: str = "pt") -> str:
    """Nome do país no idioma pedido (ISO → texto)."""
    codigo = (codigo or "").upper().strip()
    if not codigo:
        return ""
    if (lang or "pt").startswith("pt"):
        return _PT_BY_CODE.get(codigo, codigo)
    return _babel_territory(codigo, lang) or _PT_BY_CODE.get(codigo, codigo)


def country_aliases(codigo: str) -> list[str]:
    """Todos os nomes conhecidos (pt/en/fr/es) + código ISO."""
    codigo = (codigo or "").upper().strip()
    names: set[str] = set()
    if codigo in _PT_BY_CODE:
        names.add(_PT_BY_CODE[codigo])
    for lang in ("pt", "en", "fr", "es"):
        n = country_display_name(codigo, lang)
        if n:
            names.add(n)
    names.add(codigo)
    return sorted(names, key=lambda x: x.lower())


def _build_name_index() -> dict[str, str]:
    idx: dict[str, str] = {}
    for codigo in _PT_BY_CODE:
        for alias in country_aliases(codigo):
            idx[alias.strip().lower()] = codigo
        idx[codigo.lower()] = codigo
    return idx


def _name_index() -> dict[str, str]:
    global _NAME_INDEX
    if _NAME_INDEX is None:
        _NAME_INDEX = _build_name_index()
    return _NAME_INDEX


def all_countries(lang: str = "pt") -> list[dict]:
    """Lista de países com nome e continente no idioma da sessão."""
    rows: list[dict] = []
    for c, _n_pt, cont in PAISES_MUNDO:
        nome = country_display_name(c, lang)
        rows.append(
            {
                "codigo": c,
                "nome": nome,
                "continente": localize_continent(cont, lang),
                "aliases": country_aliases(c),
            }
        )
    rows.sort(key=lambda x: (x["nome"] or "").lower())
    return rows


def countries_by_continent(lang: str = "pt") -> dict[str, list[dict]]:
    out: dict[str, list[dict]] = {}
    for row in all_countries(lang):
        out.setdefault(row["continente"], []).append(row)
    return out


def country_names(lang: str = "pt") -> list[str]:
    return [r["nome"] for r in all_countries(lang)]


def find_country(nome: str, lang: str | None = None) -> dict | None:
    """Aceita nome em qualquer idioma (pt/en/fr/es) ou código ISO.

    Devolve ``nome`` no idioma ``lang`` (ou português canónico se lang=None),
    para o formulário e a UI coincidirem com a língua escolhida.
    """
    raw = (nome or "").strip()
    if not raw:
        return None
    codigo = _name_index().get(raw.lower())
    if not codigo:
        return None
    display_lang = lang or "pt"
    cont_pt = _CONT_BY_CODE.get(codigo, "")
    return {
        "codigo": codigo,
        "nome": country_display_name(codigo, display_lang),
        "nome_pt": _PT_BY_CODE.get(codigo, codigo),
        "continente": localize_continent(cont_pt, display_lang),
        "aliases": country_aliases(codigo),
    }


def default_country_name(lang: str = "pt", codigo: str = "MZ") -> str:
    return country_display_name(codigo, lang)
