"""Base de dados SQLite e dados demo da SKYTICKETservice."""

import os
import sqlite3
from pathlib import Path

from werkzeug.security import generate_password_hash

from countries import PAISES_MUNDO

# Em produção pode usar DATABASE_PATH (ex.: disco persistente no Render)
_default = Path(__file__).resolve().parent / "skyticket.db"
DB_PATH = Path(os.environ.get("DATABASE_PATH", str(_default)))


def get_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    """Cria tabelas e popula com dados demo se a BD estiver vazia."""
    conn = get_db()
    cur = conn.cursor()

    cur.executescript(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS paises (
            codigo TEXT PRIMARY KEY,
            nome TEXT NOT NULL,
            continente TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS pacotes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            titulo TEXT NOT NULL,
            destino TEXT NOT NULL,
            descricao TEXT NOT NULL,
            inclui TEXT,
            duracao_dias INTEGER NOT NULL,
            preco REAL NOT NULL,
            moeda TEXT NOT NULL DEFAULT 'MZN',
            imagem_url TEXT,
            ativo INTEGER NOT NULL DEFAULT 1
        );

        CREATE TABLE IF NOT EXISTS voos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            origem TEXT NOT NULL,
            destino TEXT NOT NULL,
            companhia TEXT NOT NULL,
            preco REAL NOT NULL,
            moeda TEXT NOT NULL DEFAULT 'MZN',
            duracao TEXT,
            classe TEXT NOT NULL DEFAULT 'Económica',
            ativo INTEGER NOT NULL DEFAULT 1
        );

        CREATE TABLE IF NOT EXISTS hoteis (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            cidade TEXT NOT NULL,
            estrelas INTEGER NOT NULL DEFAULT 3,
            preco_noite REAL NOT NULL,
            moeda TEXT NOT NULL DEFAULT 'MZN',
            descricao TEXT,
            ativo INTEGER NOT NULL DEFAULT 1
        );

        CREATE TABLE IF NOT EXISTS clientes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            email TEXT NOT NULL,
            telefone TEXT,
            documento TEXT,
            criado_em TEXT NOT NULL DEFAULT (datetime('now','localtime'))
        );

        CREATE TABLE IF NOT EXISTS reservas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            codigo TEXT UNIQUE NOT NULL,
            cliente_id INTEGER NOT NULL,
            tipo TEXT NOT NULL,
            item_id INTEGER,
            data_viagem TEXT,
            passageiros INTEGER NOT NULL DEFAULT 1,
            total REAL NOT NULL,
            moeda TEXT NOT NULL DEFAULT 'MZN',
            status TEXT NOT NULL DEFAULT 'pendente'
                CHECK (status IN ('pendente', 'confirmada', 'cancelada')),
            observacoes TEXT,
            criado_em TEXT NOT NULL DEFAULT (datetime('now','localtime')),
            FOREIGN KEY (cliente_id) REFERENCES clientes(id)
        );

        CREATE TABLE IF NOT EXISTS mensagens (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            email TEXT NOT NULL,
            telefone TEXT,
            assunto TEXT,
            corpo TEXT NOT NULL,
            lida INTEGER NOT NULL DEFAULT 0,
            criado_em TEXT NOT NULL DEFAULT (datetime('now','localtime'))
        );
        CREATE TABLE IF NOT EXISTS pedidos_visto (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            codigo TEXT UNIQUE NOT NULL,
            pais_destino TEXT NOT NULL,
            nacionalidade TEXT NOT NULL,
            proposito TEXT NOT NULL,
            data_viagem_inicio TEXT,
            data_viagem_fim TEXT,
            num_requerentes INTEGER NOT NULL DEFAULT 1,
            nome TEXT NOT NULL,
            email TEXT NOT NULL,
            telefone TEXT NOT NULL,
            passaporte TEXT,
            notas TEXT,
            status TEXT NOT NULL DEFAULT 'pendente'
                CHECK (status IN ('pendente', 'em_analise', 'contactado', 'concluido', 'cancelado')),
            criado_em TEXT NOT NULL DEFAULT (datetime('now','localtime'))
        );

        """
    )

    # Migrações leves (BD já existentes)
    cols = {
        r[1]
        for r in cur.execute("PRAGMA table_info(reservas)").fetchall()
    }
    if "assentos" not in cols:
        cur.execute("ALTER TABLE reservas ADD COLUMN assentos TEXT")
    if "fase" not in cols:
        cur.execute(
            "ALTER TABLE reservas ADD COLUMN fase TEXT DEFAULT 'confirmacao'"
        )
    for col, decl in (
        ("origem_pais", "TEXT"),
        ("destino_pais", "TEXT"),
        ("origem_cidade", "TEXT"),
        ("destino_cidade", "TEXT"),
        ("rota_livre", "INTEGER DEFAULT 0"),
        ("tipo_viagem", "TEXT DEFAULT 'ida'"),
        ("data_regresso", "TEXT"),
        ("assentos_volta", "TEXT"),
    ):
        if col not in cols:
            cur.execute(f"ALTER TABLE reservas ADD COLUMN {col} {decl}")

    # Pedidos de visto — dados opcionais Sherpa
    visto_cols = {
        r[1]
        for r in cur.execute("PRAGMA table_info(pedidos_visto)").fetchall()
    }
    for col, decl in (
        ("sherpa_product_id", "TEXT"),
        ("sherpa_info", "TEXT"),
    ):
        if col not in visto_cols:
            cur.execute(f"ALTER TABLE pedidos_visto ADD COLUMN {col} {decl}")

    # Sempre sincroniza a lista mundial de países (completa, sem limites)
    cur.execute("DELETE FROM paises")
    cur.executemany(
        "INSERT INTO paises (codigo, nome, continente) VALUES (?,?,?)",
        PAISES_MUNDO,
    )

    # Seed só se ainda não houver admin
    admin = cur.execute("SELECT id FROM users WHERE username = ?", ("admin",)).fetchone()
    if not admin:
        cur.execute(
            "INSERT INTO users (username, password_hash) VALUES (?, ?)",
            ("admin", generate_password_hash("admin123")),
        )

        pacotes = [
            (
                "Maputo City Break",
                "Maputo",
                "Fim de semana na capital: baía, mercado central, FEIMA e jantar com mariscos.",
                "Hotel 3 noites, city tour, transfer aeroporto",
                3,
                18500,
                "MZN",
                "https://images.unsplash.com/photo-1488646953014-85cb44e25828?w=800",
            ),
            (
                "Paraíso de Nampula & Ilha",
                "Nampula / Ilha de Moçambique",
                "Descubra o norte: património UNESCO na Ilha de Moçambique e cultura makhuwa.",
                "Hotel 5 noites, transfer, guia local, bilhete de entrada museus",
                5,
                42000,
                "MZN",
                "https://images.unsplash.com/photo-1507525428034-b723cf961d3e?w=800",
            ),
            (
                "Beira & Sofala Natureza",
                "Beira",
                "Praia, delta do Púnguè e experiências gastronómicas da região centro.",
                "Hotel 4 noites, half-board, excursão de dia",
                4,
                28000,
                "MZN",
                "https://images.unsplash.com/photo-1506905925346-21bda4d32df4?w=800",
            ),
            (
                "Lisboa Express",
                "Lisboa",
                "A capital portuguesa: Alfama, Belém, Tram 28 e pastéis de nata.",
                "Hotel 6 noites, city card, transfer aeroporto",
                6,
                980,
                "USD",
                "https://images.unsplash.com/photo-1555881400-74d7acaacd8b?w=800",
            ),
            (
                "Johannesburg Business & Safari",
                "Johannesburg / Pilanesberg",
                "Reuniões na cidade e safári de fim de semana em Pilanesberg.",
                "Hotel 5 noites, safári 1 dia, transfer",
                5,
                1250,
                "USD",
                "https://images.unsplash.com/photo-1516426122078-c23e76319801?w=800",
            ),
            (
                "Dubai Luxury Escape",
                "Dubai",
                "Arranha-céus, deserto e compras no maior shopping do mundo.",
                "Hotel 5* 5 noites, desert safari, Burj Khalifa tickets",
                5,
                1890,
                "USD",
                "https://images.unsplash.com/photo-1512453979798-5ea266f8880c?w=800",
            ),
            (
                "Istanbul Cultural",
                "Istanbul",
                "Entre dois continentes: Hagia Sophia, Grande Bazar e cruzeiro no Bósforo.",
                "Hotel 6 noites, city tour, cruzeiro Bósforo",
                6,
                1100,
                "USD",
                "https://images.unsplash.com/photo-1524231757912-21f4fe3a7200?w=800",
            ),
            (
                "Cabo Delgado Praias",
                "Pemba / Cabo Delgado",
                "Águas cristalinas do Índico, snorkel e relax total.",
                "Resort 7 noites, meia pensão, atividades aquáticas",
                7,
                55000,
                "MZN",
                "https://images.unsplash.com/photo-1544551763-46a013bb70d5?w=800",
            ),
        ]
        cur.executemany(
            """INSERT INTO pacotes
               (titulo, destino, descricao, inclui, duracao_dias, preco, moeda, imagem_url)
               VALUES (?,?,?,?,?,?,?,?)""",
            pacotes,
        )

        # Catálogo de voos: vazio na instalação.
        # A agência cadastra no Admin → Voos apenas tarifas REAIS (preço e rota confirmados).
        # Bilhetes em tempo real por companhia: Admin → Voos tempo real (Amadeus/Kiwi).
        # Não semear preços inventados de companhias internacionais.

        hoteis = [
            ("Hotel Polana Serena", "Maputo", 5, 9500, "MZN", "Ícone histórico com vista para a baía."),
            ("Cardoso Hotel", "Maputo", 4, 7200, "MZN", "Vista panorâmica e localização central."),
            ("Hotel Milénio", "Nampula", 3, 4500, "MZN", "Conforto e bom custo-benefício no norte."),
            ("Avenida Hotel", "Beira", 3, 3800, "MZN", "Próximo da praia e do centro comercial."),
            ("Radisson Blu Maputo", "Maputo", 5, 11000, "MZN", "Piscina rooftop e restaurante internacional."),
            ("Pemba Beach Hotel", "Pemba", 4, 8500, "MZN", "Resort frente ao mar em Cabo Delgado."),
            ("Hotel Altis Avenida", "Lisboa", 4, 140, "USD", "No coração da Avenida da Liberdade."),
            ("Sandton Sun", "Johannesburg", 5, 180, "USD", "Negócios e lazer no distrito de Sandton."),
        ]
        cur.executemany(
            """INSERT INTO hoteis
               (nome, cidade, estrelas, preco_noite, moeda, descricao)
               VALUES (?,?,?,?,?,?)""",
            hoteis,
        )

    conn.commit()
    conn.close()
