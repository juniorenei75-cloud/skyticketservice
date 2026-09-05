"""Fluxo sequencial de reserva — 6 fases (especificação SKYTICKETservice).

1. Pesquisa — destino (autocomplete 197 países), datas ida/volta, adultos/crianças,
   classe → Pesquisar
2. Bilhetes e pacotes com preços, horários e companhias
3. Identificação completa de todos os passageiros
4. Escolha de assentos (conforme classe)
5. Confirmação de todos os dados
6. Pagamento e confirmação final
"""

from __future__ import annotations

from flask import (
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

from cities import canonical_city, is_valid_city
from countries import default_country_name, find_country
from database import get_db
from flight_search import search_flights
from i18n import class_label, normalize_lang, pay_label, t
from phone_codes import normalize_phone
from notifications import (
    load_config as load_whatsapp_config,
    mensagem_nova_reserva,
    notify_if_enabled,
    wa_me_link,
    whatsapp_qr_for_admin,
)
from payment_gateways import (
    get_card_gateway,
    load_payment_config,
    payment_gateway_status,
)


def _lang() -> str:
    return normalize_lang(session.get("lang"))

BOOKING_STEPS = [
    {"n": 1, "key": "pesquisa", "title": "Pesquisa", "short": "Destino e critérios"},
    {"n": 2, "key": "bilhetes", "title": "Bilhetes", "short": "Opções e preços"},
    {"n": 3, "key": "passageiros", "title": "Passageiros", "short": "Identificação"},
    {"n": 4, "key": "assentos", "title": "Assentos", "short": "Lugares no avião"},
    {"n": 5, "key": "confirmacao", "title": "Confirmação", "short": "Rever tudo"},
    {"n": 6, "key": "pagamento", "title": "Pagamento", "short": "Pagar e confirmar"},
]

# Rótulos amigáveis ↔ valor interno (mapeia ao catálogo)
CLASSES_META = [
    {"id": "economica", "db": "Económica"},
    {"id": "executiva", "db": "Business"},
    {"id": "primeira", "db": "First"},
]

# Métodos de pagamento (locais MZ + internacionais)
PAGAMENTOS_META = [
    {
        "id": "mpesa",
        "logo": "mpesa.svg",
        "group": "mz",
        "logos_extra": [],
    },
    {
        "id": "emola",
        "logo": "emola.svg",
        "group": "mz",
        "logos_extra": [],
    },
    {
        "id": "cartao",
        "logo": "card.svg",
        "group": "intl",
        "logos_extra": ["visa.svg", "mastercard.svg"],
    },
    {
        "id": "paypal",
        "logo": "paypal.svg",
        "group": "intl",
        "logos_extra": [],
    },
    {
        "id": "transferencia",
        "logo": "transfer.svg",
        "group": "bank",
        "logos_extra": [],
    },
    {
        "id": "multibanco",
        "logo": "multibanco.svg",
        "group": "bank",
        "logos_extra": [],
    },
    {
        "id": "agencia",
        "logo": "agency.svg",
        "group": "agency",
        "logos_extra": [],
    },
]
PAGAMENTOS_IDS = [p["id"] for p in PAGAMENTOS_META]
# Compatibilidade com reservas antigas (crédito/débito → cartão)
PAGAMENTOS_ALIASES = {
    "credito": "cartao",
    "debito": "cartao",
}


def _classes(lang: str | None = None):
    return [
        {"id": c["id"], "nome": class_label(c["id"], lang), "db": c["db"]}
        for c in CLASSES_META
    ]


def _pagamentos(lang: str | None = None):
    out = []
    for meta in PAGAMENTOS_META:
        nome, desc = pay_label(meta["id"], lang)
        out.append(
            {
                "id": meta["id"],
                "nome": nome,
                "desc": desc,
                "logo": meta["logo"],
                "logos_extra": meta.get("logos_extra") or [],
                "group": meta.get("group") or "",
            }
        )
    return out


def _empty_booking() -> dict:
    return {
        "origem_pais": "",
        "origem_cidade": "",
        "destino_pais": "",
        "destino_cidade": "",
        "tipo_viagem": "ida_volta",  # ida | ida_volta — datas ida e volta na UI
        "data_viagem": "",
        "data_regresso": "",
        "n_adultos": 1,
        "n_criancas": 0,
        "n_passageiros": 1,
        "classe": "economica",
        "classe_nome": "Económica",
        "item_id": None,
        "item_kind": "voo",  # voo | pacote | cotacao
        "ticket_label": "",
        "ticket_companhia": "",
        "ticket_preco": 0,
        "ticket_moeda": "USD",
        "ticket_duracao": "",
        "ticket_horario": "",
        "ticket_detalhes": "",
        "ticket_tipo": "catalogo",
        "assentos": [],
        "assentos_volta": [],
        "passageiros": [],
        "observacoes": "",
        "pagamento_metodo": "",
        "pesquisa_feita": False,
        # baratos | melhores — escolhido após a pesquisa, antes dos resultados
        "ticket_mode": "",
    }

# Companhias premium (filtro «melhores companhias») — nomes completos (match seguro)
PREMIUM_AIRLINES = (
    "emirates",
    "qatar airways",
    "ethiopian airlines",
    "tap air portugal",
    "turkish airlines",
    "lufthansa",
    "british airways",
    "air france",
    "klm",
    "swiss international",
    "singapore airlines",
    "etihad airways",
    "qantas",
    "japan airlines",
    "cathay pacific",
    "delta air lines",
    "united airlines",
    "american airlines",
    "south african airways",
    "kenya airways",
    "egyptair",
    "royal air maroc",
    "iberia",
    "austrian airlines",
    "brussels airlines",
    "finair",
    "air canada",
    "latam",
)
PREMIUM_CODES = {
    "EK",
    "QR",
    "ET",
    "TP",
    "TK",
    "LH",
    "BA",
    "AF",
    "KL",
    "LX",
    "SQ",
    "EY",
    "QF",
    "JL",
    "NH",
    "CX",
    "DL",
    "UA",
    "AA",
    "SA",
    "KQ",
    "MS",
    "AT",
    "IB",
    "OS",
    "SN",
    "AY",
    "AC",
    "LA",
}


# Incrementar quando mudar defaults de formulário (força sessão limpa)
BOOKING_FORM_VERSION = 2


def _get_booking() -> dict:
    if session.get("booking_form_version") != BOOKING_FORM_VERSION:
        b = _empty_booking()
        session["booking"] = b
        session["booking_form_version"] = BOOKING_FORM_VERSION
        session.modified = True
        return b
    b = session.get("booking")
    if not isinstance(b, dict):
        b = _empty_booking()
        session["booking"] = b
    base = _empty_booking()
    for k, v in base.items():
        if k not in b:
            b[k] = v
    return b


def _save_booking(b: dict) -> None:
    session["booking"] = b
    session.modified = True


def _is_round_trip(booking: dict) -> bool:
    return (booking.get("tipo_viagem") or "ida_volta") == "ida_volta"


def _n_pax(booking: dict) -> int:
    try:
        a = max(0, int(booking.get("n_adultos") or 0))
        c = max(0, int(booking.get("n_criancas") or 0))
    except (TypeError, ValueError):
        a, c = 1, 0
    return max(1, a + c)


def _route_label(booking: dict) -> str:
    o = f"{booking.get('origem_cidade') or ''}, {booking.get('origem_pais') or ''}".strip(
        ", "
    )
    d = f"{booking.get('destino_cidade') or ''}, {booking.get('destino_pais') or ''}".strip(
        ", "
    )
    return f"{o} → {d}"


def _classe_db(classe_id: str) -> str:
    for c in CLASSES_META:
        if c["id"] == classe_id:
            return c["db"]
    return "Económica"


def _classe_nome(classe_id: str, lang: str | None = None) -> str:
    return class_label(classe_id, lang)


def _seat_layout(seed: int, n_rows: int = 10, classe_id: str = "economica"):
    """Mapa de assentos; classes superiores usam menos filas / mais espaço."""
    if classe_id == "primeira":
        n_rows = 4
        cols = ["A", "C", "D", "F"]  # mais espaço
    elif classe_id == "executiva":
        n_rows = 6
        cols = ["A", "C", "D", "F"]
    else:
        cols = ["A", "B", "C", "D", "E", "F"]
    occupied = set()
    seed = int(seed or 1)
    for r in range(1, n_rows + 1):
        for c in cols:
            h = (seed * 31 + r * 17 + ord(c)) % 11
            if h < 3:
                occupied.add(f"{r}{c}")
    return {"rows": list(range(1, n_rows + 1)), "cols": cols, "occupied": occupied}


def _trechos(booking: dict) -> int:
    return 2 if _is_round_trip(booking) else 1


def _total(booking: dict) -> tuple[float, str]:
    unit = float(booking.get("ticket_preco") or 0)
    n = _n_pax(booking)
    # crianças a 70% se preço fixo
    adultos = max(0, int(booking.get("n_adultos") or 0))
    criancas = max(0, int(booking.get("n_criancas") or 0))
    if unit > 0:
        sub = unit * adultos + unit * 0.7 * criancas
    else:
        sub = 0
    moeda = booking.get("ticket_moeda") or "USD"
    return sub * _trechos(booking), moeda


def _search_tickets(booking: dict) -> tuple[list[dict], str]:
    """Opções reais: GDS/API + catálogo da agência (BD) + pacotes + cotação.

    Nunca gera preços fictícios de companhias. Devolve (tickets, fonte).
    """
    dest_pais = booking.get("destino_pais") or ""
    dest_cid = booking.get("destino_cidade") or ""
    classe_nome = _classe_nome(booking.get("classe") or "economica", _lang())

    # --- Voos em tempo real (Amadeus / Kiwi) — só se API configurada e com dados ---
    flight_results, fonte = search_flights(booking)
    results: list[dict] = list(flight_results)

    # --- Catálogo da agência (preços/voos que VOCÊ cadastrou no Admin) ---
    db = get_db()
    sql = "SELECT * FROM voos WHERE ativo = 1"
    params: list = []
    if dest_cid:
        sql += " AND destino LIKE ?"
        params.append(f"%{dest_cid}%")
    elif dest_pais:
        sql += " AND destino LIKE ?"
        params.append(f"%{dest_pais}%")
    orig_cid = booking.get("origem_cidade") or ""
    if orig_cid:
        sql += " AND origem LIKE ?"
        params.append(f"%{orig_cid}%")
    rows = db.execute(sql + " ORDER BY preco", params).fetchall()
    for v in rows:
        # Só o que está na BD — sem inventar horário
        keys = v.keys() if hasattr(v, "keys") else []
        horario = ""
        flight_no = ""
        if "horario" in keys:
            horario = (v["horario"] or "").strip()
        if "flight_no" in keys:
            flight_no = (v["flight_no"] or "").strip()
        results.append(
            {
                "uid": f"voo-{v['id']}",
                "id": v["id"],
                "kind": "voo",
                "tipo": "catalogo",
                "origem": v["origem"],
                "destino": v["destino"],
                "companhia": v["companhia"],
                "classe": v["classe"] or classe_nome,
                "duracao": v["duracao"] or "—",
                "horario": horario or "—",
                "flight_no": flight_no,
                "preco": float(v["preco"]),
                "moeda": v["moeda"],
                "label": f"{v['origem']} → {v['destino']}",
                "detalhes": (
                    f"Catálogo oficial SKYTICKETservice · {v['companhia']}"
                    + (f" · {flight_no}" if flight_no else "")
                    + (f" · Partida {horario}" if horario and horario != "—" else "")
                    + " · Preço da agência"
                ),
                "fonte": "catalogo",
                "live": False,
            }
        )
    if rows and fonte in (
        "sem_api",
        "sem_resultados",
        "sem_iata",
        "sem_data",
        "mercado",
    ):
        fonte = "catalogo" if not flight_results else fonte

    # --- Pacotes (destino) ---
    sql_p = "SELECT * FROM pacotes WHERE ativo = 1"
    params_p: list = []
    if dest_pais or dest_cid:
        sql_p += " AND (destino LIKE ? OR titulo LIKE ? OR descricao LIKE ?)"
        q = f"%{dest_cid or dest_pais}%"
        params_p.extend([q, q, q])
    pacs = db.execute(sql_p + " ORDER BY preco", params_p).fetchall()
    for p in pacs:
        results.append(
            {
                "uid": f"pacote-{p['id']}",
                "id": p["id"],
                "kind": "pacote",
                "tipo": "catalogo",
                "origem": f"{booking.get('origem_cidade')}, {booking.get('origem_pais')}",
                "destino": p["destino"],
                "companhia": "Pacote SKYTICKETservice",
                "classe": classe_nome,
                "duracao": f"{p['duracao_dias']} dias",
                "horario": "Conforme programa",
                "preco": float(p["preco"]),
                "moeda": p["moeda"],
                "label": p["titulo"],
                "detalhes": (p["inclui"] or p["descricao"] or "")[:180],
                "fonte": "pacote",
            }
        )

    # Cotação real pela agência (sem preço inventado — confirmação posterior)
    results.append(
        {
            "uid": "cotacao-0",
            "id": 0,
            "kind": "cotacao",
            "tipo": "cotacao",
            "origem": f"{booking.get('origem_cidade')}, {booking.get('origem_pais')}",
            "destino": f"{booking.get('destino_cidade')}, {booking.get('destino_pais')}",
            "companhia": "SKYTICKETservice — Cotação pela agência",
            "classe": classe_nome,
            "duracao": "conforme companhia aérea",
            "horario": "A confirmar com a companhia",
            "preco": 0,
            "moeda": "USD",
            "label": _route_label(booking),
            "detalhes": (
                f"Pedido real à equipa SKYTICKETservice · Classe {classe_nome} · "
                "Preço e horários confirmados com a companhia antes do pagamento"
            ),
            "fonte": "cotacao",
            "live": False,
        }
    )
    db.close()

    mode = (booking.get("ticket_mode") or "").strip().lower()
    results = _apply_ticket_mode(results, mode)

    # Fonte para a UI: live se houver GDS; senão catálogo/cotação
    if any(
        t.get("live") or t.get("fonte") in ("duffel", "amadeus", "kiwi")
        for t in results
    ):
        if fonte not in ("duffel", "amadeus", "kiwi", "live"):
            fonte = "live"
    elif any(t.get("fonte") == "catalogo" for t in results if t.get("kind") == "voo"):
        if fonte in ("sem_api", "sem_resultados", "sem_iata", "sem_data", ""):
            fonte = "catalogo"

    return results, fonte


def _ticket_usd(t: dict) -> float:
    p = float(t.get("preco") or 0)
    if p <= 0:
        return 1e12
    moeda = (t.get("moeda") or "USD").upper()
    return p / 64.0 if moeda == "MZN" else p


def _is_premium_ticket(t: dict) -> bool:
    code = (t.get("airline_code") or "").upper().strip()
    if code and code in PREMIUM_CODES:
        return True
    name = (t.get("companhia") or "").lower().strip()
    if not name:
        return False
    # match por nome completo ou início (evita "ana" dentro de "ryanair")
    for p in PREMIUM_AIRLINES:
        if name == p or name.startswith(p + " ") or p in name.split():
            return True
        # nomes multi-palavra contidos com segurança
        if len(p) >= 5 and p in name:
            return True
    return False


def _apply_ticket_mode(results: list[dict], mode: str) -> list[dict]:
    """Garante resultados fiéis à escolha: baratos OU melhores companhias.

    Ofertas LIVE (Duffel/Amadeus) nunca são todas escondidas: se o filtro
    ficar vazio, mostram-se os voos reais ordenados por preço.
    """
    voos = [t for t in results if t.get("kind") == "voo"]
    extras = [
        t
        for t in results
        if t.get("kind") in ("cotacao", "pacote")
    ]
    live_voos = [
        t
        for t in voos
        if t.get("live") or t.get("fonte") in ("duffel", "amadeus", "kiwi")
    ]

    if mode == "melhores":
        # Preferir premium; se a API não trouxer premium, manter TODOS os voos reais
        base = [t for t in voos if _is_premium_ticket(t) and not t.get("low_cost")]
        if not base:
            base = [t for t in voos if _is_premium_ticket(t)]
        if not base:
            base = list(voos)
        priority = {"EK": 0, "QR": 1, "ET": 2, "TP": 3, "BA": 4, "LH": 5}

        def _best_key(t: dict):
            code = (t.get("airline_code") or "").upper()
            return (priority.get(code, 10), _ticket_usd(t), t.get("horario") or "")

        base.sort(key=_best_key)
        return base + extras

    if mode == "baratos":
        # Preferir não-premium / low-cost, mas se filtrar tudo, usar voos reais por preço
        base = [
            t
            for t in voos
            if t.get("low_cost") or not _is_premium_ticket(t)
        ]
        base = [t for t in base if not _is_premium_ticket(t)]
        if not base:
            base = sorted(voos, key=_ticket_usd)
        # Garantia: ofertas live nunca desaparecem todas
        if not base and live_voos:
            base = sorted(live_voos, key=_ticket_usd)
        base.sort(key=lambda t: (_ticket_usd(t), t.get("horario") or ""))
        # cortar outliers caros (manter o terço/ metade mais barato se houver muitos)
        if len(base) > 12:
            priced = [t for t in base if _ticket_usd(t) < 1e12]
            if priced:
                prices = sorted(_ticket_usd(t) for t in priced)
                median = prices[len(prices) // 2]
                # aceitar até ~1.35× a mediana (ainda “barato” de verdade)
                cap = median * 1.35
                tight = [t for t in base if _ticket_usd(t) <= cap]
                if len(tight) >= 6:
                    base = tight
        return base + extras

    # sem modo: todos por preço
    voos.sort(key=lambda t: (_ticket_usd(t), t.get("horario") or ""))
    return voos + extras


def _booking_context(step: int, booking: dict, **extra):
    lang = _lang()
    return {
        "steps": BOOKING_STEPS,
        "step": step,
        "booking": booking,
        "phase_key": BOOKING_STEPS[step - 1]["key"],
        "route_label": _route_label(booking),
        "round_trip": _is_round_trip(booking),
        "classes": _classes(lang),
        "pagamentos": _pagamentos(lang),
        "n_pax": _n_pax(booking),
        **extra,
    }


def _require_search(booking: dict) -> bool:
    return bool(
        booking.get("pesquisa_feita")
        and booking.get("destino_pais")
        and booking.get("data_viagem")
        and find_country(booking.get("destino_pais") or "", _lang())
    )


def _require_ticket(booking: dict) -> bool:
    return bool(booking.get("ticket_label"))


def register_booking_routes(app, gerar_codigo):
    """Rotas em páginas completamente separadas (nunca o mesmo ecrã)."""

    from email_ticket import build_eticket_html, send_confirmation_email

    def _ctx(page_title, page_class, booking, **extra):
        lang = _lang()
        return {
            "page_title": page_title,
            "page_class": page_class,
            "booking": booking,
            "route_label": _route_label(booking),
            "round_trip": _is_round_trip(booking),
            "classes": _classes(lang),
            "pagamentos": _pagamentos(lang),
            "n_pax": _n_pax(booking),
            **extra,
        }

    def _card_gateway_ctx() -> dict:
        """Estado do gateway de cartão para o ecrã de pagamento."""
        cfg = load_payment_config()
        ready, status = payment_gateway_status(cfg)
        active = (cfg.get("active_card_gateway") or "none").strip().lower()
        publishable = ""
        if ready and active == "stripe":
            publishable = (cfg.get("stripe_publishable_key") or "").strip()
        elif ready and active == "adyen":
            publishable = (cfg.get("adyen_client_key") or "").strip()
        elif ready and active == "worldpay":
            publishable = (cfg.get("worldpay_client_key") or "").strip()
        return {
            "card_gateway_ready": bool(ready),
            "card_gateway_name": active,
            "card_gateway_status": status,
            "card_publishable_key": publishable,
        }

    def _process_pesquisa_form(booking):
        """Valida POST da Fase 1. Devolve (ok: bool, booking)."""
        tipo_viagem = request.form.get("tipo_viagem", "ida_volta").strip()
        if tipo_viagem not in ("ida", "ida_volta"):
            tipo_viagem = "ida_volta"
        data_viagem = request.form.get("data_viagem", "").strip()
        data_regresso = request.form.get("data_regresso", "").strip()
        classe = request.form.get("classe", "economica").strip()
        try:
            n_adultos = max(1, min(9, int(request.form.get("n_adultos") or 1)))
        except ValueError:
            n_adultos = 1
        try:
            n_criancas = max(0, min(8, int(request.form.get("n_criancas") or 0)))
        except ValueError:
            n_criancas = 0
        if n_adultos + n_criancas < 1:
            n_adultos = 1

        origem_pais = request.form.get("origem_pais", "").strip()
        destino_pais = request.form.get("destino_pais", "").strip()
        origem_cidade = request.form.get("origem_cidade", "").strip()
        destino_cidade = request.form.get("destino_cidade", "").strip()
        o_ok = find_country(origem_pais, _lang())
        d_ok = find_country(destino_pais, _lang())
        if o_ok:
            origem_pais = o_ok["nome"]
        if d_ok:
            destino_pais = d_ok["nome"]

        lang = _lang()
        if not d_ok:
            flash(t("err_dest_country", lang), "error")
            return False, booking
        if not o_ok:
            flash(t("err_orig_country", lang), "error")
            return False, booking
        # Cidades: só da lista do país seleccionado
        origem_cidade_ok = canonical_city(origem_pais, origem_cidade)
        destino_cidade_ok = canonical_city(destino_pais, destino_cidade)
        if not origem_cidade_ok:
            flash(t("err_city_origin", lang), "error")
            return False, booking
        if not destino_cidade_ok:
            flash(t("err_city_dest", lang), "error")
            return False, booking
        origem_cidade = origem_cidade_ok
        destino_cidade = destino_cidade_ok
        if not data_viagem:
            flash(t("err_date_depart", lang), "error")
            return False, booking
        if tipo_viagem == "ida_volta" and not data_regresso:
            flash(t("err_date_return", lang), "error")
            return False, booking
        if (
            tipo_viagem == "ida_volta"
            and data_regresso
            and data_regresso < data_viagem
        ):
            flash(t("err_date_order", lang), "error")
            return False, booking
        if classe not in {c["id"] for c in CLASSES_META}:
            flash(t("err_class", lang), "error")
            return False, booking

        changed = (
            booking.get("destino_pais") != destino_pais
            or booking.get("n_adultos") != n_adultos
            or booking.get("n_criancas") != n_criancas
            or booking.get("classe") != classe
            or booking.get("data_viagem") != data_viagem
        )
        booking.update(
            {
                "origem_pais": origem_pais,
                "destino_pais": destino_pais,
                "origem_cidade": origem_cidade,
                "destino_cidade": destino_cidade,
                "tipo_viagem": tipo_viagem,
                "data_viagem": data_viagem,
                "data_regresso": data_regresso if tipo_viagem == "ida_volta" else "",
                "n_adultos": n_adultos,
                "n_criancas": n_criancas,
                "n_passageiros": n_adultos + n_criancas,
                "classe": classe,
                "classe_nome": _classe_nome(classe, lang),
                "pesquisa_feita": True,
                # nova pesquisa → voltar a pedir preferência de resultados
                "ticket_mode": "",
            }
        )
        if changed:
            booking["item_id"] = None
            booking["ticket_label"] = ""
            booking["assentos"] = []
            booking["assentos_volta"] = []
            booking["passageiros"] = []
        _save_booking(booking)
        return True, booking

    # ---- Página 0: Bem-vindo + escolha de idioma ----
    @app.route("/")
    def index():
        """Fase 0 — boas-vindas, slogan e escolha de idioma."""
        return render_template(
            "pages/fase0_bemvindo.html",
            page_title="Bem-vindo",
            page_class="page-fase0",
        )

    # ---- Fase 1: Pesquisa (página separada) ----
    @app.route("/reserva/pesquisa", methods=["GET", "POST"])
    def reserva_pesquisa():
        booking = _get_booking()
        _db = get_db()
        n_paises = _db.execute("SELECT COUNT(*) AS n FROM paises").fetchone()["n"]
        _db.close()

        if request.method == "POST":
            ok, booking = _process_pesquisa_form(booking)
            if ok:
                # Antes dos resultados: ecrã de preferência (baratos vs melhores)
                return redirect(url_for("reserva_preferencia"))

        return render_template(
            "pages/fase1_home.html",
            **_ctx("Pesquisa", "page-fase1", booking, n_paises=n_paises),
        )

    # redirecionamentos de compatibilidade
    @app.route("/reserva")
    def reserva():
        if not request.args:
            session.pop("booking", None)
        return redirect(url_for("reserva_pesquisa"))

    @app.route("/reserva/fase/<int:fase>", methods=["GET", "POST"])
    def reserva_fase(fase: int):
        mapping = {
            0: "index",
            1: "reserva_pesquisa",
            2: "reserva_preferencia",
            3: "reserva_opcoes",
            4: "reserva_passageiros",
            5: "reserva_assentos",
            6: "reserva_confirmacao",
            7: "reserva_pagamento",
        }
        endpoint = mapping.get(fase, "index")
        return redirect(url_for(endpoint))

    # ---- Preferência de resultados (antes dos bilhetes) ----
    @app.route("/reserva/preferencia", methods=["GET", "POST"])
    def reserva_preferencia():
        """Após a pesquisa: escolher baratos vs melhores companhias."""
        booking = _get_booking()
        if not _require_search(booking):
            flash(t("err_start_phase1", _lang()), "warning")
            return redirect(url_for("reserva_pesquisa"))

        if request.method == "POST":
            mode = (request.form.get("ticket_mode") or "").strip().lower()
            if mode not in ("baratos", "melhores"):
                flash(t("err_choose_mode", _lang()), "error")
            else:
                booking["ticket_mode"] = mode
                booking["item_id"] = None
                booking["ticket_label"] = ""
                booking["assentos"] = []
                booking["assentos_volta"] = []
                _save_booking(booking)
                return redirect(url_for("reserva_opcoes"))

        # Se já escolheu e volta a abrir, pode mudar a preferência
        return render_template(
            "pages/fase1b_preferencia.html",
            **_ctx(
                t("pref_title", _lang()),
                "page-fase1 pref-page",
                booking,
            ),
        )

    # ---- Fase 2 ----
    @app.route("/reserva/opcoes", methods=["GET", "POST"])
    def reserva_opcoes():
        booking = _get_booking()
        if not _require_search(booking):
            flash(t("err_start_phase1", _lang()), "warning")
            return redirect(url_for("reserva_pesquisa"))
        if (booking.get("ticket_mode") or "") not in ("baratos", "melhores"):
            return redirect(url_for("reserva_preferencia"))

        def _cache_key() -> str:
            return "|".join(
                [
                    booking.get("origem_cidade") or "",
                    booking.get("destino_cidade") or "",
                    booking.get("data_viagem") or "",
                    booking.get("data_regresso") or "",
                    booking.get("tipo_viagem") or "",
                    booking.get("classe") or "",
                    str(booking.get("n_adultos") or 1),
                    str(booking.get("n_criancas") or 0),
                    booking.get("ticket_mode") or "",
                ]
            )

        # Ofertas live (Duffel) mudam de ID a cada pesquisa — cache na sessão
        cache = session.get("tickets_cache") or {}
        if request.method == "POST":
            uid = request.form.get("ticket_uid", "").strip()
            tickets = list(cache.get("tickets") or [])
            fonte = cache.get("fonte") or ""
            # se a pesquisa mudou, recarregar
            if cache.get("key") != _cache_key() or not tickets:
                tickets, fonte = _search_tickets(booking)
                session["tickets_cache"] = {
                    "key": _cache_key(),
                    "tickets": tickets,
                    "fonte": fonte,
                }
                session.modified = True
            chosen = next((t for t in tickets if t.get("uid") == uid), None)
            if not chosen:
                flash(t("err_choose_ticket", _lang()), "error")
                # repor lista actual para o utilizador escolher de novo
                tickets, fonte = _search_tickets(booking)
                session["tickets_cache"] = {
                    "key": _cache_key(),
                    "tickets": tickets,
                    "fonte": fonte,
                }
                session.modified = True
            else:
                booking.update(
                    {
                        "item_id": chosen.get("id") or 0,
                        "item_kind": chosen.get("kind") or "voo",
                        "ticket_tipo": chosen.get("tipo") or "",
                        "ticket_label": chosen.get("label") or "",
                        "ticket_companhia": chosen.get("companhia") or "",
                        # preco = venda (com margem); preco_base = fornecedor
                        "ticket_preco": chosen.get("preco") or 0,
                        "ticket_preco_base": chosen.get("preco_base")
                        if chosen.get("preco_base") is not None
                        else chosen.get("preco") or 0,
                        "ticket_markup_percent": chosen.get("markup_percent") or 0,
                        "ticket_markup_amount": chosen.get("markup_amount") or 0,
                        "ticket_moeda": chosen.get("moeda") or "USD",
                        "ticket_duracao": chosen.get("duracao") or "",
                        "ticket_horario": chosen.get("horario") or "",
                        "ticket_horario_chegada": chosen.get("horario_chegada")
                        or "",
                        "ticket_detalhes": chosen.get("detalhes") or "",
                        "ticket_fonte": chosen.get("fonte") or "",
                        "ticket_flight_no": chosen.get("flight_no") or "",
                        "ticket_airline_code": chosen.get("airline_code") or "",
                        "ticket_stops": chosen.get("stops"),
                        "ticket_stops_label": chosen.get("stops_label") or "",
                        "ticket_live": bool(
                            chosen.get("live")
                            or chosen.get("fonte")
                            in ("duffel", "amadeus", "kiwi")
                        ),
                        "duffel_offer_id": chosen.get("duffel_offer_id")
                        or (
                            chosen.get("uid", "").replace("duffel-", "", 1)
                            if str(chosen.get("uid", "")).startswith("duffel-")
                            else ""
                        ),
                        "ticket_segments": chosen.get("segments") or [],
                        "classe_nome": chosen.get("classe")
                        or booking.get("classe_nome"),
                    }
                )
                booking["assentos"] = []
                booking["assentos_volta"] = []
                booking["passageiros"] = []
                _save_booking(booking)
                return redirect(url_for("reserva_passageiros"))
        else:
            # GET: nova pesquisa (ofertas frescas) e cache
            tickets, fonte = _search_tickets(booking)
            session["tickets_cache"] = {
                "key": _cache_key(),
                "tickets": tickets,
                "fonte": fonte,
            }
            session.modified = True

        return render_template(
            "pages/fase2_opcoes.html",
            **_ctx(
                "Opções de voo e pacotes",
                "page-fase2",
                booking,
                tickets=tickets,
                tickets_count=len(tickets),
                tickets_fonte=fonte,
            ),
        )

    # ---- Fase 3 ----
    @app.route("/reserva/passageiros", methods=["GET", "POST"])
    def reserva_passageiros():
        booking = _get_booking()
        if not _require_search(booking):
            return redirect(url_for("reserva_pesquisa"))
        if not _require_ticket(booking):
            flash(t("err_choose_ticket_first", _lang()), "warning")
            return redirect(url_for("reserva_opcoes"))

        n_pax = _n_pax(booking)
        lang = _lang()
        from datetime import date as _date

        today_iso = _date.today().isoformat()
        travel_date = (booking.get("data_viagem") or today_iso)[:10]

        # Avisos de validação por campo — formulário NÃO é limpo em caso de erro
        pax_field_errors: dict[int, dict[str, str]] = {}
        pax_error_summary: list[str] = []

        def _empty_pax(idx: int) -> dict:
            return {
                "titulo": "",
                "sexo": "",
                "apelido": "",
                "nomes": "",
                "nome": "",
                "nascimento": "",
                "local_nascimento": "",
                "nacionalidade": booking.get("origem_pais") or "",
                "residencia": booking.get("origem_pais") or "",
                "tipo_documento": "PASSAPORTE",
                "documento": "",
                "pais_documento": booking.get("origem_pais") or "",
                "doc_emissao": "",
                "doc_validade": "",
                "telefone": "",
                "email": "",
                "emergencia_nome": "",
                "emergencia_telefone": "",
                "ff_numero": "",
                "ff_companhia": "",
                "necessidades": "",
                "tipo_pax": t("adult", lang)
                if idx < int(booking.get("n_adultos") or 1)
                else t("child", lang),
            }

        def _draft_from_form(i: int) -> dict:
            """Lê o POST e devolve um rascunho completo (mesmo com erros)."""
            titulo = request.form.get(f"titulo_{i}", "").strip().upper()
            sexo = request.form.get(f"sexo_{i}", "").strip().upper()
            apelido = request.form.get(f"apelido_{i}", "").strip().upper()
            nomes = request.form.get(f"nomes_{i}", "").strip().upper()
            nome = " / ".join(x for x in (apelido, nomes) if x)
            nascimento = request.form.get(f"nascimento_{i}", "").strip()
            local_nascimento = request.form.get(
                f"local_nascimento_{i}", ""
            ).strip()
            nacionalidade = request.form.get(f"nacionalidade_{i}", "").strip()
            residencia = request.form.get(f"residencia_{i}", "").strip()
            documento = request.form.get(f"documento_{i}", "").strip().upper()
            pais_documento = request.form.get(f"pais_documento_{i}", "").strip()
            doc_emissao = request.form.get(f"doc_emissao_{i}", "").strip()
            doc_validade = request.form.get(f"doc_validade_{i}", "").strip()
            telefone_raw = request.form.get(f"telefone_{i}", "").strip()
            email = request.form.get(f"email_{i}", "").strip()
            emergencia_nome = request.form.get(
                f"emergencia_nome_{i}", ""
            ).strip()
            emergencia_telefone_raw = request.form.get(
                f"emergencia_telefone_{i}", ""
            ).strip()
            ff_numero = request.form.get(f"ff_numero_{i}", "").strip()
            ff_companhia = request.form.get(f"ff_companhia_{i}", "").strip()
            necessidades = request.form.get(f"necessidades_{i}", "").strip()

            lang = _lang()
            nat = find_country(nacionalidade, lang)
            if nat:
                nacionalidade = nat["nome"]
            res = find_country(residencia, lang) if residencia else None
            if res:
                residencia = res["nome"]
            iss = find_country(pais_documento, lang) if pais_documento else None
            if iss:
                pais_documento = iss["nome"]

            default_iso = nat["codigo"] if nat else "MZ"
            telefone, tel_err = normalize_phone(
                telefone_raw, default_iso, lang=lang
            )
            emergencia_telefone, em_err = normalize_phone(
                emergencia_telefone_raw, default_iso, lang=lang
            )

            # Manter o que o utilizador escreveu se a normalização falhar
            telefone_keep = telefone or telefone_raw
            em_keep = emergencia_telefone or emergencia_telefone_raw

            draft = {
                "titulo": titulo,
                "sexo": sexo,
                "apelido": apelido,
                "nomes": nomes,
                "nome": nome,
                "nascimento": nascimento,
                "local_nascimento": local_nascimento,
                "nacionalidade": nacionalidade or booking.get("origem_pais") or "",
                "residencia": residencia or nacionalidade or booking.get("origem_pais") or "",
                "tipo_documento": "PASSAPORTE",
                "documento": documento,
                "pais_documento": pais_documento or nacionalidade or booking.get("origem_pais") or "",
                "doc_emissao": doc_emissao,
                "doc_validade": doc_validade,
                "telefone": telefone_keep,
                "email": email,
                "emergencia_nome": emergencia_nome,
                "emergencia_telefone": em_keep,
                "ff_numero": ff_numero,
                "ff_companhia": ff_companhia,
                "necessidades": necessidades,
                "tipo_pax": t("adult", lang)
                if i < int(booking.get("n_adultos") or 1)
                else t("child", lang),
                "_nat_ok": bool(nat),
                "_tel_ok": bool(telefone) and not tel_err,
                "_tel_err": tel_err or "",
                "_em_ok": bool(emergencia_telefone) and not em_err,
                "_em_err": em_err or "",
                "_telefone_norm": telefone,
                "_em_norm": emergencia_telefone,
            }
            return draft

        def _validate_draft(i: int, d: dict) -> dict[str, str]:
            """Devolve mapa campo → mensagem (vazio se OK)."""
            errs: dict[str, str] = {}
            req_msg = t("err_pax_field_required", lang)

            if not d.get("titulo"):
                errs["titulo"] = req_msg
            if d.get("sexo") not in ("M", "F"):
                errs["sexo"] = req_msg
            if not d.get("apelido"):
                errs["apelido"] = req_msg
            if not d.get("nomes"):
                errs["nomes"] = req_msg
            if not d.get("nascimento"):
                errs["nascimento"] = req_msg
            if not d.get("local_nascimento"):
                errs["local_nascimento"] = req_msg
            if not d.get("_nat_ok"):
                errs["nacionalidade"] = t("err_nationality", lang)
            if not (d.get("residencia") or "").strip():
                errs["residencia"] = req_msg
            if not d.get("documento"):
                errs["documento"] = req_msg
            if not (d.get("pais_documento") or "").strip():
                errs["pais_documento"] = req_msg
            if not d.get("doc_emissao"):
                errs["doc_emissao"] = req_msg
            elif d["doc_emissao"] > today_iso:
                errs["doc_emissao"] = t("err_pax_doc_issue_future", lang)
            if not d.get("doc_validade"):
                errs["doc_validade"] = req_msg
            elif d["doc_validade"] < today_iso or (
                travel_date and d["doc_validade"] < travel_date
            ):
                errs["doc_validade"] = t("err_pax_doc_expiry", lang)
            if not d.get("_tel_ok"):
                errs["telefone"] = d.get("_tel_err") or req_msg
            if not d.get("email") or "@" not in d.get("email", ""):
                errs["email"] = t("err_pax_email", lang)
            if not d.get("emergencia_nome"):
                errs["emergencia_nome"] = req_msg
            if not d.get("_em_ok"):
                errs["emergencia_telefone"] = d.get("_em_err") or req_msg
            return errs

        if request.method == "POST":
            drafts: list[dict] = []
            for i in range(n_pax):
                draft = _draft_from_form(i)
                field_errs = _validate_draft(i, draft)
                if field_errs:
                    pax_field_errors[i] = field_errs
                    pax_label = f"{t('passenger_n', lang)} {i + 1}"
                    # Uma linha profissional por passageiro com problemas
                    labels = {
                        "titulo": t("pax_title", lang),
                        "sexo": t("pax_gender", lang),
                        "apelido": t("pax_surname", lang),
                        "nomes": t("pax_given_names", lang),
                        "nascimento": t("birth_date", lang),
                        "local_nascimento": t("pax_birth_place", lang),
                        "nacionalidade": t("nationality", lang),
                        "residencia": t("pax_residence", lang),
                        "documento": t("pax_passport_number", lang),
                        "pais_documento": t("pax_passport_country", lang),
                        "doc_emissao": t("pax_doc_issue", lang),
                        "doc_validade": t("pax_doc_expiry", lang),
                        "telefone": t("phone", lang),
                        "email": t("email", lang),
                        "emergencia_nome": t("pax_emergency_name", lang),
                        "emergencia_telefone": t("pax_emergency_phone", lang),
                    }
                    for fk, msg in field_errs.items():
                        nice = labels.get(fk, fk)
                        pax_error_summary.append(f"{pax_label} — {nice}: {msg}")
                drafts.append(draft)

            # Observações sempre preservadas no reenvio
            booking["observacoes"] = request.form.get("observacoes", "").strip()

            if not pax_field_errors:
                pax_list = []
                for d in drafts:
                    pax_list.append(
                        {
                            "titulo": d["titulo"],
                            "sexo": d["sexo"],
                            "apelido": d["apelido"],
                            "nomes": d["nomes"],
                            "nome": d["nome"],
                            "nascimento": d["nascimento"],
                            "local_nascimento": d["local_nascimento"],
                            "nacionalidade": d["nacionalidade"],
                            "residencia": d["residencia"],
                            "tipo_documento": "PASSAPORTE",
                            "documento": d["documento"],
                            "pais_documento": d["pais_documento"],
                            "doc_emissao": d["doc_emissao"],
                            "doc_validade": d["doc_validade"],
                            "telefone": d.get("_telefone_norm") or d["telefone"],
                            "email": d["email"],
                            "emergencia_nome": d["emergencia_nome"],
                            "emergencia_telefone": d.get("_em_norm")
                            or d["emergencia_telefone"],
                            "ff_numero": d["ff_numero"],
                            "ff_companhia": d["ff_companhia"],
                            "necessidades": d["necessidades"],
                            "tipo_pax": d["tipo_pax"],
                        }
                    )
                booking["passageiros"] = pax_list
                _save_booking(booking)
                return redirect(url_for("reserva_assentos"))

            # Erro: repor o formulário com TUDO o que foi preenchido
            existing = drafts
            # Flash curto + detalhe no painel da página
            flash(t("err_pax_review", lang), "warning")
        else:
            existing = list(booking.get("passageiros") or [])

        lang = _lang()
        while len(existing) < n_pax:
            existing.append(_empty_pax(len(existing)))

        # normalizar pax antigos (sessões anteriores)
        for p in existing:
            if not p.get("apelido") and p.get("nome"):
                parts = str(p["nome"]).replace(" / ", " ").split()
                if len(parts) >= 2:
                    p.setdefault("apelido", parts[0])
                    p.setdefault("nomes", " ".join(parts[1:]))
                else:
                    p.setdefault("apelido", p.get("nome", ""))
                    p.setdefault("nomes", "")
            p.setdefault("tipo_documento", "PASSAPORTE")
            p.setdefault("pais_documento", p.get("nacionalidade") or "")
            p.setdefault("residencia", p.get("nacionalidade") or "")

        return render_template(
            "pages/fase3_passageiros.html",
            **_ctx(
                "Dados dos passageiros",
                "page-fase3",
                booking,
                passageiros_form=existing,
                today_iso=today_iso,
                pax_field_errors=pax_field_errors,
                pax_error_summary=pax_error_summary,
            ),
        )

    # ---- Fase 4 ----
    @app.route("/reserva/assentos", methods=["GET", "POST"])
    def reserva_assentos():
        booking = _get_booking()
        if not _require_search(booking) or not _require_ticket(booking):
            return redirect(url_for("reserva_pesquisa"))
        n_pax = _n_pax(booking)
        if not booking.get("passageiros") or len(booking["passageiros"]) != n_pax:
            flash(t("err_fill_pax", _lang()), "warning")
            return redirect(url_for("reserva_passageiros"))

        classe_id = booking.get("classe") or "economica"
        seed = booking.get("item_id") or abs(
            hash(f"{booking.get('origem_pais')}-{booking.get('destino_pais')}")
        ) % 10000
        layout = _seat_layout(seed, classe_id=classe_id)
        round_trip = _is_round_trip(booking)
        is_pacote = booking.get("item_kind") == "pacote"
        layout_volta = (
            _seat_layout((int(seed) + 17) % 10000, classe_id=classe_id)
            if round_trip and not is_pacote
            else None
        )

        # Pré-selecção (sessão) — em erro de POST mantém o que o utilizador clicou
        sel_ida = set(booking.get("assentos") or [])
        sel_volta = set(booking.get("assentos_volta") or [])

        if request.method == "POST":
            if is_pacote:
                booking["assentos"] = ["PKG"] * n_pax
                booking["assentos_volta"] = []
                _save_booking(booking)
                return redirect(url_for("reserva_confirmacao"))

            selected = [
                s.strip().upper()
                for s in request.form.getlist("assentos")
                if s.strip()
            ]
            selected_volta = [
                s.strip().upper()
                for s in request.form.getlist("assentos_volta")
                if s.strip()
            ]
            # Sempre repor a selecção no ecrã (não apagar se faltar um assento)
            sel_ida = set(selected)
            sel_volta = set(selected_volta)

            valid, err = [], None
            for s in selected:
                if s in layout["occupied"]:
                    err = t("err_seat_occupied_out", _lang()).format(seat=s)
                    break
                if s not in valid:
                    valid.append(s)
            valid_v = []
            if not err and round_trip:
                for s in selected_volta:
                    if s in layout_volta["occupied"]:
                        err = t("err_seat_occupied_ret", _lang()).format(seat=s)
                        break
                    if s not in valid_v:
                        valid_v.append(s)
            if err:
                flash(err, "warning")
            elif len(valid) != n_pax:
                flash(t("err_seats_out", _lang()), "warning")
            elif round_trip and len(valid_v) != n_pax:
                flash(t("err_seats_ret", _lang()), "warning")
            else:
                booking["assentos"] = valid
                booking["assentos_volta"] = valid_v if round_trip else []
                for i, p in enumerate(booking["passageiros"]):
                    if i < len(valid):
                        p["assento"] = valid[i]
                    if round_trip and i < len(valid_v):
                        p["assento_volta"] = valid_v[i]
                _save_booking(booking)
                return redirect(url_for("reserva_confirmacao"))

        return render_template(
            "pages/fase4_assentos.html",
            **_ctx(
                "Escolha de assentos",
                "page-fase4",
                booking,
                layout=layout,
                layout_volta=layout_volta,
                selected=sel_ida,
                selected_volta=sel_volta,
                is_pacote=is_pacote,
            ),
        )

    # ---- Fase 5 ----
    @app.route("/reserva/confirmacao", methods=["GET", "POST"])
    def reserva_confirmacao():
        booking = _get_booking()
        n_pax = _n_pax(booking)
        if not booking.get("passageiros"):
            return redirect(url_for("reserva_passageiros"))
        is_pacote = booking.get("item_kind") == "pacote"
        if not is_pacote and (
            not booking.get("assentos") or len(booking["assentos"]) != n_pax
        ):
            return redirect(url_for("reserva_assentos"))

        total, moeda = _total(booking)
        unit = float(booking.get("ticket_preco") or 0)
        cotacao = unit <= 0

        if request.method == "POST":
            return redirect(url_for("reserva_pagamento"))

        return render_template(
            "pages/fase5_confirmacao.html",
            **_ctx(
                "Confirmação da reserva",
                "page-fase5",
                booking,
                total=total,
                moeda=moeda,
                unit=unit,
                trechos=_trechos(booking),
                cotacao=cotacao,
            ),
        )

    # ---- Fase 6 ----
    @app.route("/reserva/pagamento", methods=["GET", "POST"])
    def reserva_pagamento():
        booking = _get_booking()
        if not booking.get("passageiros") or not _require_ticket(booking):
            return redirect(url_for("reserva_pesquisa"))

        total, moeda = _total(booking)
        unit = float(booking.get("ticket_preco") or 0)
        cotacao = unit <= 0
        lang = _lang()
        gw_ctx = _card_gateway_ctx()

        form_pay = {
            "metodo": PAGAMENTOS_ALIASES.get(
                booking.get("pagamento_metodo") or "",
                booking.get("pagamento_metodo") or "",
            ),
            "pag_titular": booking.get("pag_titular") or "",
            "pag_numero": booking.get("pag_numero") or "",
            "pag_validade": booking.get("pag_validade") or "",
            "pag_cvv": booking.get("pag_cvv") or "",
            "pag_telefone": booking.get("pag_telefone") or "",
            "pag_referencia": booking.get("pag_referencia") or "",
            "pag_paypal_email": booking.get("pag_paypal_email") or "",
            "card_payment_id": booking.get("card_payment_id") or "",
        }
        pay_field_errors: dict[str, str] = {}
        pay_error_summary: list[str] = []

        if request.method == "POST":
            metodo = request.form.get("pagamento_metodo", "").strip()
            metodo = PAGAMENTOS_ALIASES.get(metodo, metodo)
            form_pay = {
                "metodo": metodo,
                "pag_titular": request.form.get("pag_titular", "").strip(),
                "pag_numero": request.form.get("pag_numero", "").strip(),
                "pag_validade": request.form.get("pag_validade", "").strip(),
                "pag_cvv": request.form.get("pag_cvv", "").strip(),
                "pag_telefone": request.form.get("pag_telefone", "").strip(),
                "pag_referencia": request.form.get("pag_referencia", "").strip(),
                "pag_paypal_email": request.form.get("pag_paypal_email", "").strip(),
                "card_payment_id": request.form.get("card_payment_id", "").strip(),
            }
            req = t("err_pax_field_required", lang)
            card_ready = bool(gw_ctx.get("card_gateway_ready"))

            if metodo not in set(PAGAMENTOS_IDS):
                pay_field_errors["metodo"] = t("err_payment", lang)
                pay_error_summary.append(t("err_payment", lang))
            elif metodo == "cartao":
                if card_ready:
                    # Cartão via gateway (Stripe Elements) — sem dados PCI no servidor
                    pid = form_pay["card_payment_id"]
                    if not pid:
                        pay_field_errors["card_payment_id"] = t(
                            "err_pay_card_gateway", lang
                        )
                    else:
                        gw = get_card_gateway()
                        confirm = gw.confirm_payment(pid) if gw else None
                        if not confirm or not confirm.ok:
                            msg = (
                                (confirm.message if confirm else "")
                                or t("err_pay_card_gateway", lang)
                            )
                            pay_field_errors["card_payment_id"] = msg
                            pay_error_summary.append(msg)
                        else:
                            booking["card_payment_id"] = confirm.payment_id
                            booking["card_payment_provider"] = confirm.provider
                            booking["card_payment_status"] = confirm.status
                else:
                    # Fallback local (gateway ainda sem chaves)
                    if not form_pay["pag_titular"]:
                        pay_field_errors["pag_titular"] = req
                    digits = "".join(
                        c for c in form_pay["pag_numero"] if c.isdigit()
                    )
                    if len(digits) < 13 or len(digits) > 19:
                        pay_field_errors["pag_numero"] = t(
                            "err_pay_card_number", lang
                        )
                    val = form_pay["pag_validade"].replace(" ", "")
                    if len(val) < 4 or "/" not in val:
                        pay_field_errors["pag_validade"] = t(
                            "err_pay_card_exp", lang
                        )
                    cvv = "".join(c for c in form_pay["pag_cvv"] if c.isdigit())
                    if len(cvv) < 3:
                        pay_field_errors["pag_cvv"] = t("err_pay_cvv", lang)
            elif metodo in ("mpesa", "emola"):
                digits = "".join(c for c in form_pay["pag_telefone"] if c.isdigit())
                if not digits:
                    p0 = (booking.get("passageiros") or [{}])[0]
                    form_pay["pag_telefone"] = (p0.get("telefone") or "").strip()
                    digits = "".join(
                        c for c in form_pay["pag_telefone"] if c.isdigit()
                    )
                if not digits or len(digits) < 8:
                    pay_field_errors["pag_telefone"] = t("err_pay_mobile", lang)
            elif metodo == "paypal":
                em = form_pay["pag_paypal_email"]
                if not em or "@" not in em:
                    pay_field_errors["pag_paypal_email"] = t("err_pay_paypal", lang)
            elif metodo in ("multibanco", "transferencia"):
                pass
            # agencia: sem campos extra

            if pay_field_errors:
                labels = {
                    "pag_titular": t("card_name", lang),
                    "pag_numero": t("card_number", lang),
                    "pag_validade": t("card_exp", lang),
                    "pag_cvv": t("card_cvv", lang),
                    "pag_telefone": t("mobile_number", lang),
                    "pag_referencia": t("ref_proof", lang),
                    "card_payment_id": t("card_data", lang),
                    "metodo": t("pay_method", lang),
                }
                for fk, msg in pay_field_errors.items():
                    if fk == "metodo":
                        continue
                    pay_error_summary.append(f"{labels.get(fk, fk)}: {msg}")
                flash(t("err_pax_review", lang), "warning")
            else:
                booking["pagamento_metodo"] = metodo
                booking["pag_titular"] = form_pay["pag_titular"]
                booking["pag_numero"] = (
                    (
                        "*" * max(0, len(form_pay["pag_numero"]) - 4)
                        + form_pay["pag_numero"][-4:]
                    )
                    if form_pay["pag_numero"]
                    else ""
                )
                booking["pag_validade"] = form_pay["pag_validade"]
                booking["pag_cvv"] = ""
                booking["pag_telefone"] = form_pay["pag_telefone"]
                booking["pag_referencia"] = form_pay["pag_referencia"]
                booking["pag_paypal_email"] = form_pay.get("pag_paypal_email") or ""
                if form_pay.get("card_payment_id"):
                    booking["card_payment_id"] = form_pay["card_payment_id"]
                _save_booking(booking)
                # Limpar cache de bilhetes (sessão grande) antes de finalizar
                session.pop("tickets_cache", None)
                try:
                    codigo = _finalize_booking(booking, gerar_codigo)
                except Exception as exc:  # noqa: BLE001
                    flash(
                        f"{t('err_payment', lang)} ({exc})",
                        "error",
                    )
                    return render_template(
                        "pages/fase6_pagamento.html",
                        **_ctx(
                            "Pagamento",
                            "page-fase6",
                            booking,
                            total=total,
                            moeda=moeda,
                            unit=unit,
                            cotacao=cotacao,
                            form_pay=form_pay,
                            pay_field_errors=pay_field_errors,
                            pay_error_summary=[str(exc)],
                            **gw_ctx,
                        ),
                    )
                return redirect(url_for("reserva_ok", codigo=codigo))

        return render_template(
            "pages/fase6_pagamento.html",
            **_ctx(
                "Pagamento",
                "page-fase6",
                booking,
                total=total,
                moeda=moeda,
                unit=unit,
                cotacao=cotacao,
                form_pay=form_pay,
                pay_field_errors=pay_field_errors,
                pay_error_summary=pay_error_summary,
                **gw_ctx,
            ),
        )

    @app.route("/reserva/pagamento/create-intent", methods=["POST"])
    def reserva_pagamento_create_intent():
        """Cria PaymentIntent (Stripe) / sessão cartão — autorização + captura automática."""
        booking = _get_booking()
        if not booking.get("passageiros") or not _require_ticket(booking):
            return jsonify(ok=False, message="Sessão de reserva inválida."), 400

        total, moeda = _total(booking)
        if total <= 0:
            return (
                jsonify(
                    ok=False,
                    message="Valor sob cotação — contacte a agência para pagar com cartão.",
                ),
                400,
            )

        gw = get_card_gateway()
        if gw is None or not gw.is_configured():
            return (
                jsonify(
                    ok=False,
                    message=(
                        "Gateway de cartão ainda sem chaves. "
                        "Configure em Admin → Pagamentos."
                    ),
                ),
                400,
            )

        # Stripe: moedas zero-decimal já tratadas no gateway; MZN pode falhar
        cur = (moeda or "USD").upper()
        if cur == "MZN":
            # Stripe não lista MZN de forma fiável — cobrar em USD se possível
            cur = "USD"

        principal = booking["passageiros"][0]
        result = gw.create_payment(
            amount=float(total),
            currency=cur,
            description=f"SKYTICKETservice · {_route_label(booking)}"[:500],
            metadata={
                "route": _route_label(booking)[:200],
                "companhia": (booking.get("ticket_companhia") or "")[:100],
                "email": (principal.get("email") or "")[:200],
            },
            customer_email=(principal.get("email") or "").strip(),
        )
        if not result.ok:
            return jsonify(ok=False, message=result.message or "Falha no gateway."), 400

        booking["card_payment_id"] = result.payment_id
        booking["card_payment_provider"] = result.provider
        _save_booking(booking)

        return jsonify(
            ok=True,
            provider=result.provider,
            payment_id=result.payment_id,
            client_secret=result.client_secret,
            publishable_key=result.publishable_key,
            message=result.message,
        )

    @app.route("/reserva/pagamento/confirm-card", methods=["POST"])
    def reserva_pagamento_confirm_card():
        """Confirma PaymentIntent no servidor e finaliza a reserva (JSON)."""
        booking = _get_booking()
        lang = _lang()
        if not booking.get("passageiros") or not _require_ticket(booking):
            return jsonify(ok=False, message="Sessão de reserva inválida."), 400

        data = request.get_json(silent=True) or {}
        payment_id = (
            (data.get("payment_id") or request.form.get("card_payment_id") or "")
            .strip()
        )
        if not payment_id:
            return jsonify(ok=False, message=t("err_pay_card_gateway", lang)), 400

        gw = get_card_gateway()
        if gw is None or not gw.is_configured():
            return jsonify(ok=False, message="Gateway de cartão não configurado."), 400

        confirm = gw.confirm_payment(payment_id)
        if not confirm.ok:
            return (
                jsonify(ok=False, message=confirm.message or t("err_payment", lang)),
                400,
            )

        booking["pagamento_metodo"] = "cartao"
        booking["card_payment_id"] = confirm.payment_id
        booking["card_payment_provider"] = confirm.provider
        booking["card_payment_status"] = confirm.status
        booking["pag_titular"] = (
            data.get("cardholder") or booking.get("pag_titular") or ""
        ).strip()
        booking["pag_numero"] = ""
        booking["pag_validade"] = ""
        booking["pag_cvv"] = ""
        _save_booking(booking)
        session.pop("tickets_cache", None)

        try:
            codigo = _finalize_booking(booking, gerar_codigo)
        except Exception as exc:  # noqa: BLE001
            return jsonify(ok=False, message=f"{t('err_payment', lang)} ({exc})"), 500

        return jsonify(
            ok=True,
            codigo=codigo,
            redirect=url_for("reserva_ok", codigo=codigo),
            message="Pagamento autorizado e capturado.",
        )

    def _finalize_booking(booking: dict, gerar_codigo_fn) -> str:
        principal = booking["passageiros"][0]
        n_pax = _n_pax(booking)
        total, moeda = _total(booking)
        assentos_txt = ", ".join(booking.get("assentos") or [])
        assentos_volta_txt = ", ".join(booking.get("assentos_volta") or [])
        tipo_viagem = booking.get("tipo_viagem") or "ida_volta"
        tipo_lbl = "Ida e volta" if tipo_viagem == "ida_volta" else "Só ida"
        route = _route_label(booking)
        metodo = booking.get("pagamento_metodo") or ""
        metodo_nome = pay_label(metodo, _lang())[0]
        if metodo == "cartao" and booking.get("card_payment_provider"):
            metodo_nome = (
                f"{metodo_nome} ({booking.get('card_payment_provider')}"
                f" · {booking.get('card_payment_id') or 'ok'})"
            )

        pax_txt = " || ".join(
            f"{p.get('titulo','')}|{p.get('sexo','')}|{p.get('nome','')}|"
            f"{p.get('nascimento','')}|{p.get('local_nascimento','')}|"
            f"{p.get('nacionalidade','')}|{p.get('residencia','')}|"
            f"{p.get('tipo_documento','')}|{p.get('documento','')}|"
            f"{p.get('pais_documento','')}|{p.get('doc_emissao','')}|"
            f"{p.get('doc_validade','')}|{p.get('telefone','')}|{p.get('email','')}|"
            f"EMERG:{p.get('emergencia_nome','')}/{p.get('emergencia_telefone','')}|"
            f"FF:{p.get('ff_companhia','')}/{p.get('ff_numero','')}|"
            f"NEED:{p.get('necessidades','')}"
            for p in booking["passageiros"]
        )
        extra = (
            f"Tipo: {tipo_lbl} | Classe: {booking.get('classe_nome')} | "
            f"Adultos: {booking.get('n_adultos')} Crianças: {booking.get('n_criancas')} | "
            f"Bilhete: {booking.get('ticket_label')} | "
            f"Companhia: {booking.get('ticket_companhia')} | "
            f"Horário: {booking.get('ticket_horario')} | "
            f"Pagamento: {metodo_nome} | "
            f"PAX: {pax_txt}"
        )
        if assentos_txt:
            extra += f" | Assentos ida: {assentos_txt}"
        if assentos_volta_txt:
            extra += f" | Assentos volta: {assentos_volta_txt}"

        is_cotacao = booking.get("ticket_tipo") == "cotacao" or total <= 0
        kind = booking.get("item_kind") or "voo"
        tipo_db = "pacote" if kind == "pacote" else "voo"
        item_id = int(booking.get("item_id") or 0)

        db = get_db()
        cur = db.cursor()
        cur.execute(
            """INSERT INTO clientes (nome, email, telefone, documento)
               VALUES (?,?,?,?)""",
            (
                principal["nome"],
                principal["email"],
                principal.get("telefone") or "",
                principal.get("documento") or "",
            ),
        )
        cliente_id = cur.lastrowid
        codigo = gerar_codigo_fn()
        cur.execute(
            """INSERT INTO reservas
               (codigo, cliente_id, tipo, item_id, data_viagem, passageiros,
                total, moeda, status, observacoes, assentos, fase,
                origem_pais, destino_pais, origem_cidade, destino_cidade, rota_livre,
                tipo_viagem, data_regresso, assentos_volta)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                codigo,
                cliente_id,
                tipo_db,
                item_id,
                booking.get("data_viagem") or None,
                n_pax,
                total,
                moeda,
                "confirmada",
                extra,
                assentos_txt,
                "pago",
                booking.get("origem_pais"),
                booking.get("destino_pais"),
                booking.get("origem_cidade"),
                booking.get("destino_cidade"),
                1 if is_cotacao else 0,
                tipo_viagem,
                booking.get("data_regresso") or None,
                assentos_volta_txt or None,
            ),
        )
        db.commit()
        res_row = db.execute(
            """SELECT r.*, c.nome, c.email, c.telefone
               FROM reservas r JOIN clientes c ON c.id = r.cliente_id
               WHERE r.codigo = ?""",
            (codigo,),
        ).fetchone()
        db.close()

        # Bilhete electrónico + e-mail
        pax_lines = "<br>".join(
            (
                f"• {p.get('titulo','')} <strong>{p.get('nome','')}</strong> "
                f"({p.get('tipo_pax','')}) · sexo {p.get('sexo','—')}<br>"
                f"&nbsp;&nbsp;Nasc.: {p.get('nascimento','—')}"
                f"{' · ' + p['local_nascimento'] if p.get('local_nascimento') else ''}"
                f" · Nac.: {p.get('nacionalidade','—')}<br>"
                f"&nbsp;&nbsp;Passaporte {p.get('documento','—')}"
                f" · val. {p.get('doc_validade','—')}"
                f" · emitido: {p.get('pais_documento','—')}"
            )
            for p in booking["passageiros"]
        )
        html_ticket = build_eticket_html(
            res_row,
            passageiros_txt=pax_lines,
            pagamento=metodo_nome,
            extras={
                "ticket_companhia": booking.get("ticket_companhia") or "",
                "ticket_flight_no": booking.get("ticket_flight_no") or "",
                "ticket_horario": booking.get("ticket_horario") or "",
                "ticket_horario_chegada": booking.get("ticket_horario_chegada")
                or "",
                "ticket_duracao": booking.get("ticket_duracao") or "",
                "classe_nome": booking.get("classe_nome") or "",
            },
        )
        email_ok, email_msg = send_confirmation_email(
            principal.get("email") or "",
            codigo,
            html_ticket,
            nome=principal.get("nome") or "",
        )

        detalhe = (
            f"{route} ({tipo_lbl}) | {booking.get('ticket_companhia')} | "
            f"Pagamento: {metodo_nome}"
        )
        data_wa = booking.get("data_viagem") or ""
        if booking.get("data_regresso"):
            data_wa = f"{data_wa} → {booking['data_regresso']}"
        texto_wa = mensagem_nova_reserva(
            codigo=codigo,
            nome=principal["nome"],
            email=principal["email"],
            telefone=principal.get("telefone") or "",
            tipo=tipo_db,
            detalhe=detalhe,
            passageiros=n_pax,
            data_viagem=data_wa or None,
            total=total,
            moeda=moeda,
            pagamento=metodo_nome,
            companhia=booking.get("ticket_companhia") or "",
            voo=booking.get("ticket_flight_no") or "",
            estado="confirmada / bilhete emitido",
        )
        # WhatsApp imediato ao administrador (CallMeBot se configurado)
        notif = notify_if_enabled("reserva", texto_wa)
        # Só guardar o LINK na sessão (QR em base64 rebenta o cookie do browser)
        wa_link = notif.get("link") or whatsapp_qr_for_admin(texto_wa).get("link", "")

        # Cópia por e-mail ao admin (canal extra, se SMTP/Brevo estiver pronto)
        admin_email_ok = False
        admin_email_msg = ""
        try:
            from email_ticket import load_smtp_config, smtp_is_ready

            smtp_cfg = load_smtp_config()
            ready, _ = smtp_is_ready(smtp_cfg)
            admin_to = (
                smtp_cfg.get("admin_email") or smtp_cfg.get("mail_from") or ""
            ).strip()
            if ready and admin_to:
                admin_email_ok, admin_email_msg = send_confirmation_email(
                    admin_to,
                    codigo,
                    html_ticket,
                    nome=f"ADMIN — {principal.get('nome') or ''}",
                )
        except Exception as exc:  # noqa: BLE001
            admin_email_msg = str(exc)

        session["last_wa_notif"] = {
            "codigo": codigo,
            "auto_sent": bool(notif.get("auto_sent", False)),
            "message": (notif.get("message") or "")[:500],
            "link": wa_link,
            "ok": bool(notif.get("ok", False)),
            "admin_email_ok": admin_email_ok,
            "admin_email_msg": (admin_email_msg or "")[:300],
            # texto curto para regenerar QR na página de sucesso
            "wa_text": texto_wa[:3500],
        }
        session["last_booking_code"] = codigo
        session["last_pagamento"] = metodo_nome
        session["last_email_ok"] = email_ok
        session["last_email_msg"] = (email_msg or "")[:500]
        session.pop("booking", None)
        session.pop("tickets_cache", None)
        return codigo

    @app.route("/reserva/ok/<codigo>")
    def reserva_ok(codigo: str):
        db = get_db()
        res = db.execute(
            """SELECT r.*, c.nome, c.email, c.telefone
               FROM reservas r JOIN clientes c ON c.id = r.cliente_id
               WHERE r.codigo = ?""",
            (codigo,),
        ).fetchone()
        db.close()
        if not res:
            flash(t("err_booking_nf", _lang()), "error")
            return redirect(url_for("index"))

        notif = session.pop("last_wa_notif", None)
        pagamento = session.pop("last_pagamento", "")
        email_ok = session.pop("last_email_ok", False)
        email_msg = session.pop("last_email_msg", "")
        if not notif or notif.get("codigo") != codigo:
            o = f"{res['origem_cidade'] or ''}, {res['origem_pais'] or ''}".strip(", ")
            d = f"{res['destino_cidade'] or ''}, {res['destino_pais'] or ''}".strip(
                ", "
            )
            detalhe = f"{o} → {d}" if (o or d) else (res["tipo"] or "voo")
            texto = mensagem_nova_reserva(
                codigo=res["codigo"],
                nome=res["nome"],
                email=res["email"],
                telefone=res["telefone"] or "",
                tipo=res["tipo"],
                detalhe=detalhe,
                passageiros=res["passageiros"],
                data_viagem=res["data_viagem"],
                total=res["total"],
                moeda=res["moeda"],
                pagamento=pagamento or "",
                estado=res["status"] or "confirmada",
            )
            wa_qr = whatsapp_qr_for_admin(texto)
            notif = {
                "codigo": codigo,
                "auto_sent": False,
                "link": wa_qr.get("link", ""),
                "qr": wa_qr.get("qr", ""),
            }
        else:
            # Regenerar QR a partir do link/texto (não vem na sessão — cookie limitado)
            from notifications import qr_data_uri

            if notif.get("wa_text"):
                pack = whatsapp_qr_for_admin(notif["wa_text"])
                notif["link"] = pack.get("link") or notif.get("link", "")
                notif["qr"] = pack.get("qr", "")
            elif notif.get("link"):
                notif["qr"] = qr_data_uri(notif["link"])

        return render_template(
            "pages/fase7_sucesso.html",
            page_title=t("booking_done", _lang()),
            page_class="page-sucesso",
            reserva=res,
            wa_notif=notif,
            pagamento=pagamento,
            email_ok=email_ok,
            email_msg=email_msg,
        )

    @app.route("/reserva/bilhete/<codigo>")
    def reserva_bilhete(codigo: str):
        """Entrega / visualização do bilhete electrónico (sempre com logotipo)."""
        from email_ticket import build_eticket_html, save_eticket

        db = get_db()
        res = db.execute(
            """SELECT r.*, c.nome, c.email, c.telefone
               FROM reservas r JOIN clientes c ON c.id = r.cliente_id
               WHERE r.codigo = ?""",
            (codigo,),
        ).fetchone()
        db.close()
        if not res:
            flash(t("err_ticket_nf", _lang()), "error")
            return redirect(url_for("index"))

        # Regenerar com logotipo actual (impressão / visualização credível)
        pagamento = ""
        try:
            # observacoes pode ter "Pagamento: …"
            obs = res["observacoes"] if "observacoes" in res.keys() else ""
            if obs and "Pagamento:" in str(obs):
                for part in str(obs).split("|"):
                    if "Pagamento:" in part:
                        pagamento = part.split("Pagamento:", 1)[-1].strip()
                        break
        except Exception:
            pagamento = ""

        html = build_eticket_html(res, pagamento=pagamento)
        try:
            save_eticket(codigo, html)
        except OSError:
            pass
        return html, 200, {"Content-Type": "text/html; charset=utf-8"}


    # aliases usados noutros redirects de falha
    # (pesquisa é o início do fluxo de reserva)
