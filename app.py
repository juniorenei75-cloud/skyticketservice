"""SKYTICKETservice — Sistema de Agência de Viagens e Turismo."""

from __future__ import annotations

import os
import secrets
import string
from datetime import datetime
from functools import wraps

from flask import (
    Flask,
    flash,
    g,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from werkzeug.security import check_password_hash

from cities import all_cities_by_country
from countries import (
    CONTINENTES,
    all_countries,
    default_country_name,
    find_country,
    localize_continent,
)
from database import get_db, init_db
from i18n import LANGUAGES, DEFAULT_LANG, normalize_lang, t as translate
from phone_codes import all_phone_countries
from email_ticket import (
    load_smtp_config,
    save_smtp_config,
    send_test_email,
    smtp_is_ready,
)
from flight_search import (
    flight_api_status,
    load_flight_api_config,
    save_flight_api_config,
    search_amadeus,
    search_duffel,
    search_kiwi_tequila,
)
from notifications import (
    load_config as load_whatsapp_config,
    mensagem_contacto,
    mensagem_nova_reserva,
    mensagem_status_reserva,
    notify_if_enabled,
    save_config as save_whatsapp_config,
    wa_me_link,
)
from payment_gateways import (
    load_payment_config,
    payment_gateway_status,
    save_payment_config,
)

app = Flask(__name__)
app.secret_key = os.environ.get(
    "SECRET_KEY", "skyticket-service-dev-key-change-in-production"
)
# Idioma e reserva persistem entre visitas no mesmo browser
app.config["PERMANENT_SESSION_LIFETIME"] = 60 * 60 * 24 * 30  # 30 dias

# Base de dados pronta ao arrancar (local e online)
init_db()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def gerar_codigo(prefix: str = "SKY") -> str:
    chars = string.ascii_uppercase + string.digits
    return f"{prefix}-{''.join(secrets.choice(chars) for _ in range(8))}"


def format_money(value: float, moeda: str = "MZN") -> str:
    try:
        v = float(value)
    except (TypeError, ValueError):
        return f"0 {moeda}"
    if moeda == "MZN":
        return f"{v:,.0f} MT".replace(",", " ")
    return f"{moeda} {v:,.2f}"


app.jinja_env.filters["money"] = format_money


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("user_id"):
            flash(translate("err_login", session.get("lang")), "warning")
            return redirect(url_for("admin_login", next=request.path))
        return view(*args, **kwargs)

    return wrapped


@app.before_request
def load_user():
    g.user = None
    if session.get("user_id"):
        db = get_db()
        g.user = db.execute(
            "SELECT id, username FROM users WHERE id = ?", (session["user_id"],)
        ).fetchone()
        db.close()


@app.context_processor
def inject_globals():
    lang = normalize_lang(session.get("lang") or DEFAULT_LANG)

    def _(key: str) -> str:
        return translate(key, lang)

    locale_map = {"pt": "pt_MZ", "en": "en_GB", "fr": "fr_FR", "es": "es_ES"}
    # Domínio oficial da marca (SEO e partilhas). Em local use 127.0.0.1.
    site = {
        "nome": "SKYTICKETservice",
        "dominio": "skyticketservice.com",
        "url": "https://www.skyticketservice.com",
        "url_alt": "https://skyticketservice.com",
        "descricao": _("site_description"),
        "keywords": _("site_keywords"),
        "locale": locale_map.get(lang, "pt_MZ"),
    }
    # Strings usadas pelo JS (pickers de país/cidade/telefone)
    js_i18n_keys = (
        "js_confirm",
        "js_country_placeholder",
        "js_country_selected",
        "js_country_hint",
        "js_country_suggestions",
        "js_country_results",
        "js_country_none",
        "js_country_only_list",
        "js_city_placeholder",
        "js_city_need_country",
        "js_city_selected",
        "js_city_hint",
        "js_city_filter",
        "js_city_list",
        "js_city_none",
        "js_phone_placeholder",
        "js_phone_hint",
        "js_pick_country_alert",
        "js_pick_city_alert",
        "js_pick_phone_alert",
    )
    js_i18n = {k: _(k) for k in js_i18n_keys}
    return {
        "ano": datetime.now().year,
        "agencia": site["nome"],
        "slogan": _("slogan"),
        "site": site,
        "paises_mundo": all_countries(lang),
        "cidades_por_pais": all_cities_by_country(lang),
        "phone_countries": all_phone_countries(lang),
        "continentes": [translate(f"continent_{x}", lang) for x in (
            "africa", "america", "asia", "europe", "oceania"
        )],
        "lang": lang,
        "languages": LANGUAGES,
        "_": _,
        "default_origem_pais": default_country_name(lang, "MZ"),
        "js_i18n": js_i18n,
        "contacto": {
            "responsavel": "Júnior Jamal",
            "telefone": "+258 84 905 3340",
            "telefone_raw": "+258849053340",
            "whatsapp": "+258849053340",
            "whatsapp_link": "https://wa.me/258849053340",
            "email": "skyticketservicee@gmail.com",
            "locais": _("locations"),
            "local_principal": _("hq_nampula"),
            "horario": _("hours_24_7"),
            "website": site["url"],
        },
    }


@app.route("/idioma/<code>")
def set_language(code: str):
    """Define o idioma e regressa à página anterior (ou início)."""
    session["lang"] = normalize_lang(code)
    session.permanent = True
    # Re-localizar países já guardados na reserva para o novo idioma
    booking = session.get("booking")
    if isinstance(booking, dict):
        for field in (
            "origem_pais",
            "destino_pais",
        ):
            info = find_country(booking.get(field) or "", session["lang"])
            if info:
                booking[field] = info["nome"]
        pax_list = booking.get("passageiros") or []
        if isinstance(pax_list, list):
            for pax in pax_list:
                if not isinstance(pax, dict):
                    continue
                for field in ("nacionalidade", "residencia", "pais_documento"):
                    info = find_country(pax.get(field) or "", session["lang"])
                    if info:
                        pax[field] = info["nome"]
        session["booking"] = booking
    nxt = request.args.get("next") or request.referrer or url_for("index")
    # Evitar open redirect para fora do site
    if nxt.startswith("http") and request.host not in nxt:
        nxt = url_for("index")
    return redirect(nxt)


# ---------------------------------------------------------------------------
# Site público
# ---------------------------------------------------------------------------

# A página inicial («/») é a Fase 1 da reserva — registada em booking_flow.py

@app.route("/robots.txt")
def robots_txt():
    return app.send_static_file("robots.txt")


@app.route("/sitemap.xml")
def sitemap_xml():
    """Sitemap para motores de busca (domínio live / SITE_URL)."""
    base = (os.environ.get("SITE_URL") or request.url_root.rstrip("/")).rstrip("/")
    pages = [
        ("/", "1.0", "daily"),
        ("/destinos", "1.0", "weekly"),
        ("/pacotes", "0.9", "weekly"),
        ("/voos", "0.9", "weekly"),
        ("/hoteis", "0.7", "weekly"),
        ("/sobre", "0.8", "monthly"),
        ("/contacto", "0.8", "monthly"),
        ("/reserva", "0.9", "weekly"),
    ]
    urls = []
    for path, priority, freq in pages:
        urls.append(
            f"  <url>\n"
            f"    <loc>{base}{path}</loc>\n"
            f"    <changefreq>{freq}</changefreq>\n"
            f"    <priority>{priority}</priority>\n"
            f"  </url>"
        )
    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + "\n".join(urls)
        + "\n</urlset>\n"
    )
    return app.response_class(xml, mimetype="application/xml")


@app.route("/pacotes")
def pacotes():
    db = get_db()
    q = request.args.get("q", "").strip()
    if q:
        rows = db.execute(
            """SELECT * FROM pacotes WHERE ativo = 1
               AND (titulo LIKE ? OR destino LIKE ? OR descricao LIKE ?)
               ORDER BY titulo""",
            (f"%{q}%", f"%{q}%", f"%{q}%"),
        ).fetchall()
    else:
        rows = db.execute(
            "SELECT * FROM pacotes WHERE ativo = 1 ORDER BY titulo"
        ).fetchall()
    db.close()
    return render_template("pacotes.html", pacotes=rows, q=q)


@app.route("/pacotes/<int:pid>")
def pacote_detalhe(pid: int):
    db = get_db()
    pacote = db.execute(
        "SELECT * FROM pacotes WHERE id = ? AND ativo = 1", (pid,)
    ).fetchone()
    db.close()
    if not pacote:
        flash("Pacote não encontrado.", "error")
        return redirect(url_for("pacotes"))
    return render_template("pacote_detalhe.html", pacote=pacote)


@app.route("/voos")
def voos():
    db = get_db()
    origem = request.args.get("origem", "").strip()
    destino = request.args.get("destino", "").strip()
    pais_destino = request.args.get("pais", "").strip()
    sql = "SELECT * FROM voos WHERE ativo = 1"
    params: list = []
    if origem:
        sql += " AND origem LIKE ?"
        params.append(f"%{origem}%")
    if destino:
        sql += " AND destino LIKE ?"
        params.append(f"%{destino}%")
    if pais_destino:
        sql += " AND destino LIKE ?"
        params.append(f"%{pais_destino}%")
    sql += " ORDER BY preco"
    rows = db.execute(sql, params).fetchall()
    cidades = db.execute(
        """SELECT DISTINCT cidade FROM (
             SELECT origem AS cidade FROM voos WHERE ativo = 1
             UNION
             SELECT destino AS cidade FROM voos WHERE ativo = 1
           ) ORDER BY cidade"""
    ).fetchall()
    n_paises = db.execute("SELECT COUNT(*) AS n FROM paises").fetchone()["n"]
    db.close()
    return render_template(
        "voos.html",
        voos=rows,
        origem=origem,
        destino=destino,
        pais=pais_destino,
        cidades=[c["cidade"] for c in cidades],
        n_paises=n_paises,
    )


@app.route("/destinos")
def destinos():
    """Todos os países do mundo — sem limites."""
    q = request.args.get("q", "").strip()
    continente = request.args.get("continente", "").strip()
    db = get_db()
    sql = "SELECT * FROM paises WHERE 1=1"
    params: list = []
    if q:
        sql += " AND (nome LIKE ? OR codigo LIKE ? OR continente LIKE ?)"
        params.extend([f"%{q}%", f"%{q}%", f"%{q}%"])
    if continente:
        sql += " AND continente = ?"
        params.append(continente)
    sql += " ORDER BY continente, nome"
    rows = db.execute(sql, params).fetchall()
    total = db.execute("SELECT COUNT(*) AS n FROM paises").fetchone()["n"]
    db.close()
    by_cont = {}
    for r in rows:
        by_cont.setdefault(r["continente"], []).append(r)
    return render_template(
        "destinos.html",
        by_cont=by_cont,
        q=q,
        continente=continente,
        total=total,
        encontrados=len(rows),
        continentes_lista=[
            {"value": c, "label": localize_continent(c, session.get("lang") or DEFAULT_LANG)}
            for c in CONTINENTES
        ],
    )


@app.route("/hoteis")
def hoteis():
    db = get_db()
    cidade = request.args.get("cidade", "").strip()
    if cidade:
        rows = db.execute(
            "SELECT * FROM hoteis WHERE ativo = 1 AND cidade LIKE ? ORDER BY estrelas DESC",
            (f"%{cidade}%",),
        ).fetchall()
    else:
        rows = db.execute(
            "SELECT * FROM hoteis WHERE ativo = 1 ORDER BY cidade, estrelas DESC"
        ).fetchall()
    cidades = db.execute(
        "SELECT DISTINCT cidade FROM hoteis WHERE ativo = 1 ORDER BY cidade"
    ).fetchall()
    db.close()
    return render_template(
        "hoteis.html",
        hoteis=rows,
        cidade=cidade,
        cidades=[c["cidade"] for c in cidades],
    )


# ---------------------------------------------------------------------------
# Reserva em fases (6 fases) — ver booking_flow.py
# ---------------------------------------------------------------------------

from booking_flow import register_booking_routes

register_booking_routes(app, gerar_codigo)


@app.route("/contacto", methods=["GET", "POST"])
def contacto():
    if request.method == "POST":
        nome = request.form.get("nome", "").strip()
        email = request.form.get("email", "").strip()
        telefone = request.form.get("telefone", "").strip()
        assunto = request.form.get("assunto", "").strip()
        corpo = request.form.get("corpo", "").strip()
        if not nome or not email or not corpo:
            flash(translate("err_contact_fields", session.get("lang")), "error")
        else:
            db = get_db()
            db.execute(
                """INSERT INTO mensagens (nome, email, telefone, assunto, corpo)
                   VALUES (?,?,?,?,?)""",
                (nome, email, telefone, assunto, corpo),
            )
            db.commit()
            db.close()

            texto_wa = mensagem_contacto(
                nome=nome,
                email=email,
                telefone=telefone,
                assunto=assunto,
                corpo=corpo,
            )
            notif = notify_if_enabled("contacto", texto_wa)
            if notif.get("auto_sent"):
                flash(translate("msg_contact_wa", session.get("lang")), "success")
            else:
                flash(translate("msg_contact_ok", session.get("lang")), "success")
                session["contacto_wa_link"] = notif.get("link", "")
            return redirect(url_for("contacto"))
    wa_link = session.pop("contacto_wa_link", None)
    return render_template("contacto.html", wa_link=wa_link)


@app.route("/sobre")
def sobre():
    return render_template("sobre.html")


# ---------------------------------------------------------------------------
# Admin — auth
# ---------------------------------------------------------------------------

@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if session.get("user_id"):
        return redirect(url_for("admin_dashboard"))
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        db = get_db()
        user = db.execute(
            "SELECT * FROM users WHERE username = ?", (username,)
        ).fetchone()
        db.close()
        if user and check_password_hash(user["password_hash"], password):
            session.clear()
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            nxt = request.args.get("next") or url_for("admin_dashboard")
            return redirect(nxt)
        flash(translate("err_login_bad", session.get("lang")), "error")
    return render_template("admin/login.html")


@app.route("/admin/logout")
def admin_logout():
    lang = session.get("lang")
    session.clear()
    if lang:
        session["lang"] = lang
    flash(translate("msg_logout", session.get("lang")), "success")
    return redirect(url_for("admin_login"))


@app.route("/admin")
@app.route("/admin/dashboard")
@login_required
def admin_dashboard():
    db = get_db()
    stats = {
        "reservas": db.execute("SELECT COUNT(*) AS n FROM reservas").fetchone()["n"],
        "pendentes": db.execute(
            "SELECT COUNT(*) AS n FROM reservas WHERE status = 'pendente'"
        ).fetchone()["n"],
        "confirmadas": db.execute(
            "SELECT COUNT(*) AS n FROM reservas WHERE status = 'confirmada'"
        ).fetchone()["n"],
        "clientes": db.execute("SELECT COUNT(*) AS n FROM clientes").fetchone()["n"],
        "pacotes": db.execute(
            "SELECT COUNT(*) AS n FROM pacotes WHERE ativo = 1"
        ).fetchone()["n"],
        "voos": db.execute(
            "SELECT COUNT(*) AS n FROM voos WHERE ativo = 1"
        ).fetchone()["n"],
        "mensagens": db.execute(
            "SELECT COUNT(*) AS n FROM mensagens WHERE lida = 0"
        ).fetchone()["n"],
        "receita": db.execute(
            """SELECT COALESCE(SUM(total), 0) AS t FROM reservas
               WHERE status = 'confirmada'"""
        ).fetchone()["t"],
    }
    recentes = db.execute(
        """SELECT r.*, c.nome AS cliente_nome
           FROM reservas r JOIN clientes c ON c.id = r.cliente_id
           ORDER BY r.id DESC LIMIT 8"""
    ).fetchall()
    db.close()
    return render_template("admin/dashboard.html", stats=stats, recentes=recentes)


# ---------------------------------------------------------------------------
# Admin — pacotes
# ---------------------------------------------------------------------------

@app.route("/admin/pacotes")
@login_required
def admin_pacotes():
    db = get_db()
    rows = db.execute("SELECT * FROM pacotes ORDER BY id DESC").fetchall()
    db.close()
    return render_template("admin/pacotes.html", pacotes=rows)


@app.route("/admin/pacotes/novo", methods=["GET", "POST"])
@login_required
def admin_pacote_novo():
    if request.method == "POST":
        db = get_db()
        db.execute(
            """INSERT INTO pacotes
               (titulo, destino, descricao, inclui, duracao_dias, preco, moeda, imagem_url, ativo)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            (
                request.form.get("titulo", "").strip(),
                request.form.get("destino", "").strip(),
                request.form.get("descricao", "").strip(),
                request.form.get("inclui", "").strip(),
                int(request.form.get("duracao_dias") or 1),
                float(request.form.get("preco") or 0),
                request.form.get("moeda", "MZN"),
                request.form.get("imagem_url", "").strip(),
                1 if request.form.get("ativo") else 0,
            ),
        )
        db.commit()
        db.close()
        flash("Pacote criado.", "success")
        return redirect(url_for("admin_pacotes"))
    return render_template("admin/pacote_form.html", pacote=None)


@app.route("/admin/pacotes/<int:pid>/editar", methods=["GET", "POST"])
@login_required
def admin_pacote_editar(pid: int):
    db = get_db()
    pacote = db.execute("SELECT * FROM pacotes WHERE id = ?", (pid,)).fetchone()
    if not pacote:
        db.close()
        flash("Pacote não encontrado.", "error")
        return redirect(url_for("admin_pacotes"))
    if request.method == "POST":
        db.execute(
            """UPDATE pacotes SET titulo=?, destino=?, descricao=?, inclui=?,
               duracao_dias=?, preco=?, moeda=?, imagem_url=?, ativo=? WHERE id=?""",
            (
                request.form.get("titulo", "").strip(),
                request.form.get("destino", "").strip(),
                request.form.get("descricao", "").strip(),
                request.form.get("inclui", "").strip(),
                int(request.form.get("duracao_dias") or 1),
                float(request.form.get("preco") or 0),
                request.form.get("moeda", "MZN"),
                request.form.get("imagem_url", "").strip(),
                1 if request.form.get("ativo") else 0,
                pid,
            ),
        )
        db.commit()
        db.close()
        flash("Pacote actualizado.", "success")
        return redirect(url_for("admin_pacotes"))
    db.close()
    return render_template("admin/pacote_form.html", pacote=pacote)


@app.route("/admin/pacotes/<int:pid>/apagar", methods=["POST"])
@login_required
def admin_pacote_apagar(pid: int):
    db = get_db()
    db.execute("DELETE FROM pacotes WHERE id = ?", (pid,))
    db.commit()
    db.close()
    flash("Pacote removido.", "success")
    return redirect(url_for("admin_pacotes"))


# ---------------------------------------------------------------------------
# Admin — voos
# ---------------------------------------------------------------------------

@app.route("/admin/voos")
@login_required
def admin_voos():
    db = get_db()
    rows = db.execute("SELECT * FROM voos ORDER BY id DESC").fetchall()
    db.close()
    return render_template("admin/voos.html", voos=rows)


@app.route("/admin/voos/novo", methods=["GET", "POST"])
@login_required
def admin_voo_novo():
    if request.method == "POST":
        db = get_db()
        db.execute(
            """INSERT INTO voos
               (origem, destino, companhia, preco, moeda, duracao, classe, ativo)
               VALUES (?,?,?,?,?,?,?,?)""",
            (
                request.form.get("origem", "").strip(),
                request.form.get("destino", "").strip(),
                request.form.get("companhia", "").strip(),
                float(request.form.get("preco") or 0),
                request.form.get("moeda", "MZN"),
                request.form.get("duracao", "").strip(),
                request.form.get("classe", "Económica"),
                1 if request.form.get("ativo") else 0,
            ),
        )
        db.commit()
        db.close()
        flash("Voo criado.", "success")
        return redirect(url_for("admin_voos"))
    return render_template("admin/voo_form.html", voo=None)


@app.route("/admin/voos/<int:vid>/editar", methods=["GET", "POST"])
@login_required
def admin_voo_editar(vid: int):
    db = get_db()
    voo = db.execute("SELECT * FROM voos WHERE id = ?", (vid,)).fetchone()
    if not voo:
        db.close()
        flash("Voo não encontrado.", "error")
        return redirect(url_for("admin_voos"))
    if request.method == "POST":
        db.execute(
            """UPDATE voos SET origem=?, destino=?, companhia=?, preco=?, moeda=?,
               duracao=?, classe=?, ativo=? WHERE id=?""",
            (
                request.form.get("origem", "").strip(),
                request.form.get("destino", "").strip(),
                request.form.get("companhia", "").strip(),
                float(request.form.get("preco") or 0),
                request.form.get("moeda", "MZN"),
                request.form.get("duracao", "").strip(),
                request.form.get("classe", "Económica"),
                1 if request.form.get("ativo") else 0,
                vid,
            ),
        )
        db.commit()
        db.close()
        flash("Voo actualizado.", "success")
        return redirect(url_for("admin_voos"))
    db.close()
    return render_template("admin/voo_form.html", voo=voo)


@app.route("/admin/voos/<int:vid>/apagar", methods=["POST"])
@login_required
def admin_voo_apagar(vid: int):
    db = get_db()
    db.execute("DELETE FROM voos WHERE id = ?", (vid,))
    db.commit()
    db.close()
    flash("Voo removido.", "success")
    return redirect(url_for("admin_voos"))


# ---------------------------------------------------------------------------
# Admin — clientes, reservas, mensagens
# ---------------------------------------------------------------------------

@app.route("/admin/clientes")
@login_required
def admin_clientes():
    db = get_db()
    rows = db.execute(
        """SELECT c.*,
                  (SELECT COUNT(*) FROM reservas r WHERE r.cliente_id = c.id) AS n_reservas
           FROM clientes c ORDER BY c.id DESC"""
    ).fetchall()
    db.close()
    return render_template("admin/clientes.html", clientes=rows)


@app.route("/admin/reservas")
@login_required
def admin_reservas():
    status = request.args.get("status", "").strip()
    db = get_db()
    if status:
        rows = db.execute(
            """SELECT r.*, c.nome AS cliente_nome, c.email, c.telefone
               FROM reservas r JOIN clientes c ON c.id = r.cliente_id
               WHERE r.status = ? ORDER BY r.id DESC""",
            (status,),
        ).fetchall()
    else:
        rows = db.execute(
            """SELECT r.*, c.nome AS cliente_nome, c.email, c.telefone
               FROM reservas r JOIN clientes c ON c.id = r.cliente_id
               ORDER BY r.id DESC"""
        ).fetchall()
    db.close()
    return render_template("admin/reservas.html", reservas=rows, status=status)


@app.route("/admin/reservas/<int:rid>/status", methods=["POST"])
@login_required
def admin_reserva_status(rid: int):
    novo = request.form.get("status", "")
    if novo not in ("pendente", "confirmada", "cancelada"):
        flash("Estado inválido.", "error")
        return redirect(url_for("admin_reservas"))
    db = get_db()
    row = db.execute(
        """SELECT r.*, c.nome AS cliente_nome, c.telefone AS cliente_telefone
           FROM reservas r JOIN clientes c ON c.id = r.cliente_id
           WHERE r.id = ?""",
        (rid,),
    ).fetchone()
    db.execute("UPDATE reservas SET status = ? WHERE id = ?", (novo, rid))
    db.commit()
    db.close()

    if row:
        texto = mensagem_status_reserva(
            codigo=row["codigo"],
            nome=row["cliente_nome"],
            status=novo,
            total=row["total"],
            moeda=row["moeda"],
        )
        # Notifica o admin (registo / eco). Cliente: link se tiver telefone.
        notify_if_enabled("status", texto)

    flash(f"Reserva actualizada para «{novo}».", "success")
    return redirect(url_for("admin_reservas", status=request.args.get("status", "")))


@app.route("/admin/whatsapp", methods=["GET", "POST"])
@login_required
def admin_whatsapp():
    cfg = load_whatsapp_config()
    test_result = ""
    test_ok = False
    if request.method == "POST":
        action = request.form.get("action", "save")
        provider = (request.form.get("provider") or "callmebot").strip().lower()
        if provider not in ("callmebot", "link"):
            provider = "callmebot"
        new_key = (request.form.get("callmebot_apikey") or "").strip()
        # Manter apikey anterior se o campo vier vazio
        if not new_key:
            new_key = cfg.get("callmebot_apikey") or ""
        updates = {
            "enabled": request.form.get("enabled") == "1",
            "admin_phone": "".join(
                c for c in request.form.get("admin_phone", "") if c.isdigit()
            )
            or cfg.get("admin_phone", "258849053340"),
            "admin_name": request.form.get("admin_name", "").strip()
            or "Júnior Jamal",
            "provider": provider,
            "callmebot_apikey": new_key,
            "notify_on_reserva": request.form.get("notify_on_reserva") == "1",
            "notify_on_contacto": request.form.get("notify_on_contacto") == "1",
            "notify_on_status_change": request.form.get("notify_on_status_change")
            == "1",
        }
        cfg = save_whatsapp_config(updates)
        if action == "test":
            from notifications import send_whatsapp_to_admin

            txt = (
                "✅ *SKYTICKETservice — Teste WhatsApp*\n\n"
                "Se recebeu esta mensagem, o envio automático ao admin está a funcionar.\n"
                f"Número: +{cfg.get('admin_phone')}"
            )
            result = send_whatsapp_to_admin(txt)
            test_ok = bool(result.get("auto_sent"))
            test_result = result.get("message") or ""
            if test_ok:
                flash("Mensagem de teste enviada para o seu WhatsApp.", "success")
            else:
                flash(
                    test_result
                    or "Não foi possível enviar automaticamente. Confirme a apikey CallMeBot.",
                    "warning",
                )
        else:
            flash("Configuração WhatsApp guardada.", "success")
            return redirect(url_for("admin_whatsapp"))
    return render_template(
        "admin/whatsapp.html",
        cfg=cfg,
        test_result=test_result,
        test_ok=test_ok,
    )


@app.route("/admin/voos-api", methods=["GET", "POST"])
@login_required
def admin_voos_api():
    """Configurar Amadeus / Kiwi para bilhetes em tempo real por companhia."""
    cfg = load_flight_api_config()
    test_result = ""
    test_ok = False
    if request.method == "POST":
        action = (request.form.get("action") or "save").strip()
        updates = {
            "duffel_access_token": request.form.get(
                "duffel_access_token", ""
            ).strip(),
            "amadeus_client_id": request.form.get("amadeus_client_id", "").strip(),
            "amadeus_client_secret": request.form.get(
                "amadeus_client_secret", ""
            ).strip(),
            "amadeus_env": (
                request.form.get("amadeus_env") or "test"
            ).strip().lower(),
            "tequila_api_key": request.form.get("tequila_api_key", "").strip(),
            "prefer_live_only": True,
        }
        try:
            updates["max_live_results"] = int(
                request.form.get("max_live_results") or 80
            )
        except ValueError:
            updates["max_live_results"] = 80
        try:
            updates["agency_markup_percent"] = float(
                (request.form.get("agency_markup_percent") or "5").replace(",", ".")
            )
        except ValueError:
            updates["agency_markup_percent"] = 5.0
        if updates["amadeus_env"] not in ("test", "production"):
            updates["amadeus_env"] = "test"
        cfg = save_flight_api_config(updates)
        if action == "test":
            ready, msg = flight_api_status(cfg)
            if not ready:
                test_result = msg
                test_ok = False
            else:
                from datetime import date, timedelta

                dep = (date.today() + timedelta(days=21)).isoformat()
                # Rota de teste estável na sandox Duffel (ex. LHR-JFK ou LIS-MAD)
                n_duffel = len(
                    search_duffel("LHR", "JFK", dep, None, 1, 0, "economica", 5, cfg)
                )
                if n_duffel == 0:
                    n_duffel = len(
                        search_duffel(
                            "LIS", "MAD", dep, None, 1, 0, "economica", 5, cfg
                        )
                    )
                n_ama = len(
                    search_amadeus("LIS", "MAD", dep, None, 1, 0, "economica", 5, cfg)
                )
                n_kiwi = len(
                    search_kiwi_tequila(
                        "LIS", "MAD", dep, None, 1, 0, "economica", 5, cfg
                    )
                )
                test_ok = (n_duffel + n_ama + n_kiwi) > 0
                test_result = (
                    f"{msg}. Teste em {dep}: "
                    f"Duffel={n_duffel}, Amadeus={n_ama}, Kiwi={n_kiwi} oferta(s)."
                )
                if not test_ok:
                    test_result += (
                        " Nenhuma oferta. Confirme o token Duffel (duffel_test_…), "
                        "a data da viagem e a cobertura de companhias da sua conta."
                    )
            flash(
                "Teste concluído." if test_ok else "Teste sem ofertas live.",
                "success" if test_ok else "warning",
            )
        else:
            flash("Configuração de voos em tempo real guardada.", "success")
            return redirect(url_for("admin_voos_api"))

    ready, status_msg = flight_api_status(cfg)
    return render_template(
        "admin/voos_api.html",
        cfg=cfg,
        ready=ready,
        status_msg=status_msg,
        test_result=test_result,
        test_ok=test_ok,
    )


@app.route("/admin/smtp", methods=["GET", "POST"])
@login_required
def admin_smtp():
    """Configuração SMTP para envio de confirmação e e-ticket."""
    cfg = load_smtp_config()
    if request.method == "POST":
        action = request.form.get("action", "save")
        if action == "test":
            to_email = request.form.get("test_email", "").strip()
            ok, msg = send_test_email(to_email)
            flash(msg, "success" if ok else "error")
            return redirect(url_for("admin_smtp"))

        # Guardar
        try:
            port = int(request.form.get("port") or 587)
        except ValueError:
            port = 587
        password = request.form.get("password", "")
        brevo_key = request.form.get("brevo_api_key", "")
        provider = (request.form.get("provider") or "smtp").strip().lower()
        if provider not in ("smtp", "brevo"):
            provider = "smtp"
        updates = {
            "enabled": request.form.get("enabled") == "1",
            "provider": provider,
            "host": request.form.get("host", "").strip() or "smtp.gmail.com",
            "port": port,
            "user": request.form.get("user", "").strip(),
            "mail_from": request.form.get("mail_from", "").strip()
            or request.form.get("user", "").strip(),
            "from_name": request.form.get("from_name", "").strip()
            or "SKYTICKETservice",
            "use_tls": request.form.get("use_tls") == "1",
            "use_ssl": request.form.get("use_ssl") == "1",
            "bcc_admin": request.form.get("bcc_admin") == "1",
            "admin_email": request.form.get("admin_email", "").strip()
            or request.form.get("user", "").strip()
            or request.form.get("mail_from", "").strip(),
            "brevo_api_key": "",  # placeholder; só grava se preenchido
        }
        if password.strip():
            updates["password"] = password.strip()
        if brevo_key.strip():
            updates["brevo_api_key"] = brevo_key.strip()
        else:
            # não apagar chave antiga
            updates.pop("brevo_api_key", None)
        save_smtp_config(updates)
        flash("Configuração de e-mail guardada.", "success")
        ready, status = smtp_is_ready()
        if ready:
            flash(
                "Pronto: as reservas enviarão o e-ticket ao e-mail do passageiro.",
                "success",
            )
        else:
            flash(status, "warning")
        return redirect(url_for("admin_smtp"))

    ready, status_msg = smtp_is_ready(cfg)
    has_password = bool((cfg.get("password") or "").strip())
    has_brevo = bool((cfg.get("brevo_api_key") or "").strip())
    safe_cfg = dict(cfg)
    safe_cfg["password"] = ""
    safe_cfg["brevo_api_key"] = ""
    return render_template(
        "admin/smtp.html",
        cfg=safe_cfg,
        ready=ready,
        status_msg=status_msg,
        has_password=has_password,
        has_brevo=has_brevo,
    )


@app.route("/admin/pagamentos", methods=["GET", "POST"])
@login_required
def admin_pagamentos():
    """Configurar Stripe / Adyen / Worldpay (cartão crédito e débito)."""
    cfg = load_payment_config()
    if request.method == "POST":
        active = (request.form.get("active_card_gateway") or "stripe").strip().lower()
        if active not in ("stripe", "adyen", "worldpay", "none"):
            active = "stripe"
        updates = {
            "active_card_gateway": active,
            "stripe_publishable_key": request.form.get(
                "stripe_publishable_key", ""
            ).strip(),
            "adyen_merchant_account": request.form.get(
                "adyen_merchant_account", ""
            ).strip(),
            "adyen_client_key": request.form.get("adyen_client_key", "").strip(),
            "adyen_environment": (
                "live"
                if request.form.get("adyen_environment") == "live"
                else "test"
            ),
            "worldpay_merchant_id": request.form.get(
                "worldpay_merchant_id", ""
            ).strip(),
            "worldpay_client_key": request.form.get(
                "worldpay_client_key", ""
            ).strip(),
            "worldpay_environment": (
                "live"
                if request.form.get("worldpay_environment") == "live"
                else "test"
            ),
        }
        sk = request.form.get("stripe_secret_key", "").strip()
        if sk:
            updates["stripe_secret_key"] = sk
        wh = request.form.get("stripe_webhook_secret", "").strip()
        if wh:
            updates["stripe_webhook_secret"] = wh
        adyen_key = request.form.get("adyen_api_key", "").strip()
        if adyen_key:
            updates["adyen_api_key"] = adyen_key
        wp_key = request.form.get("worldpay_service_key", "").strip()
        if wp_key:
            updates["worldpay_service_key"] = wp_key

        cfg = save_payment_config(updates)
        flash("Configuração de pagamentos (cartão) guardada.", "success")
        ready, status = payment_gateway_status(cfg)
        if ready:
            flash(
                "Cartão activo: autorização instantânea + captura automática.",
                "success",
            )
        else:
            flash(status, "warning")
        return redirect(url_for("admin_pagamentos"))

    ready, status_msg = payment_gateway_status(cfg)
    has_stripe = bool(
        (cfg.get("stripe_secret_key") or "").strip()
        and (cfg.get("stripe_publishable_key") or "").strip()
    )
    has_stripe_wh = bool((cfg.get("stripe_webhook_secret") or "").strip())
    has_adyen = bool(
        (cfg.get("adyen_api_key") or "").strip()
        and (cfg.get("adyen_merchant_account") or "").strip()
        and (cfg.get("adyen_client_key") or "").strip()
    )
    has_worldpay = bool(
        (cfg.get("worldpay_merchant_id") or "").strip()
        and (cfg.get("worldpay_service_key") or "").strip()
        and (cfg.get("worldpay_client_key") or "").strip()
    )
    safe = dict(cfg)
    safe["stripe_secret_key"] = ""
    safe["stripe_webhook_secret"] = ""
    safe["adyen_api_key"] = ""
    safe["worldpay_service_key"] = ""
    return render_template(
        "admin/pagamentos.html",
        cfg=safe,
        ready=ready,
        status_msg=status_msg,
        has_stripe=has_stripe,
        has_stripe_wh=has_stripe_wh,
        has_adyen=has_adyen,
        has_worldpay=has_worldpay,
    )


@app.route("/admin/mensagens")
@login_required
def admin_mensagens():
    db = get_db()
    rows = db.execute("SELECT * FROM mensagens ORDER BY id DESC").fetchall()
    db.close()
    return render_template("admin/mensagens.html", mensagens=rows)


@app.route("/admin/mensagens/<int:mid>/lida", methods=["POST"])
@login_required
def admin_mensagem_lida(mid: int):
    db = get_db()
    db.execute("UPDATE mensagens SET lida = 1 WHERE id = ?", (mid,))
    db.commit()
    db.close()
    flash("Mensagem marcada como lida.", "success")
    return redirect(url_for("admin_mensagens"))


# ---------------------------------------------------------------------------
# Boot
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import socket

    # Descobre IPs da rede local (preferir Wi‑Fi 192.168.x / 10.x, não VPN)
    lan_ips = []
    try:
        hostname = socket.gethostname()
        for info in socket.getaddrinfo(hostname, None, socket.AF_INET):
            ip = info[4][0]
            if ip.startswith("127."):
                continue
            if ip not in lan_ips:
                lan_ips.append(ip)
    except OSError:
        pass
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        if ip not in lan_ips and not ip.startswith("127."):
            lan_ips.insert(0, ip)
    except OSError:
        pass

    def _score(ip: str) -> int:
        if ip.startswith("192.168."):
            return 0
        if ip.startswith("10."):
            return 1
        if ip.startswith("172."):
            return 3  # muitas vezes VPN/docker
        return 2

    lan_ips = sorted(lan_ips, key=_score)
    principal = lan_ips[0] if lan_ips else "127.0.0.1"
    port = int(os.environ.get("PORT", "5000"))

    print("=" * 56)
    print("  SKYTICKETservice — Agência de Viagens")
    print(f"  Neste PC:     http://127.0.0.1:{port}")
    print(f"  Na Wi‑Fi:     http://{principal}:{port}")
    print("  Online:       publique no Render (ver PUBLICAR-ONLINE.md)")
    print("  Admin:        /admin  |  Login: admin / admin123")
    print("=" * 56)
    # 0.0.0.0 = rede local; em produção use gunicorn (Procfile)
    app.run(debug=os.environ.get("FLASK_DEBUG", "1") == "1", host="0.0.0.0", port=port)
