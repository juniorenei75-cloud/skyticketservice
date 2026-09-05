"""Cidades principais por país (ISO) — autocomplete restrito à lista do país."""

from __future__ import annotations

from countries import PAISES_MUNDO, find_country

# Capital + cidades principais / aeroportos relevantes
CIDADES_POR_CODIGO: dict[str, list[str]] = {
    # África
    "DZ": ["Argel", "Orã", "Constantina", "Annaba"],
    "AO": ["Luanda", "Benguela", "Lubango", "Huambo"],
    "BJ": ["Porto-Novo", "Cotonou", "Parakou"],
    "BW": ["Gaborone", "Francistown", "Maun"],
    "BF": ["Ouagadougou", "Bobo-Dioulasso"],
    "BI": ["Gitega", "Bujumbura"],
    "CV": ["Praia", "Mindelo", "Sal", "Boa Vista"],
    "CM": ["Yaoundé", "Douala", "Garoua"],
    "TD": ["N'Djamena", "Moundou"],
    "KM": ["Moroni", "Mutsamudu"],
    "CG": ["Brazzaville", "Pointe-Noire"],
    "CD": ["Kinshasa", "Lubumbashi", "Goma", "Kisangani"],
    "CI": ["Yamoussoukro", "Abidjan", "Bouaké", "San Pedro"],
    "DJ": ["Djibuti"],
    "EG": ["Cairo", "Alexandria", "Luxor", "Sharm el-Sheikh", "Hurghada", "Giza"],
    "ER": ["Asmara", "Massawa"],
    "SZ": ["Mbabane", "Manzini"],
    "ET": ["Adis Abeba", "Dire Dawa", "Mekelle"],
    "GA": ["Libreville", "Port-Gentil"],
    "GM": ["Banjul", "Serekunda"],
    "GH": ["Acra", "Kumasi", "Tamale"],
    "GN": ["Conacri", "Kankan"],
    "GQ": ["Malabo", "Bata"],
    "GW": ["Bissau", "Bafatá"],
    "LS": ["Maseru"],
    "LR": ["Monróvia"],
    "LY": ["Trípoli", "Benghazi", "Misurata"],
    "MG": ["Antananarivo", "Toamasina", "Nosy Be"],
    "MW": ["Lilongwe", "Blantyre"],
    "ML": ["Bamako", "Timbuktu", "Sikasso"],
    "MA": ["Rabat", "Casablanca", "Marrakech", "Fez", "Tânger", "Agadir"],
    "MU": ["Port Louis", "Curepipe"],
    "MR": ["Nouakchott", "Nouadhibou"],
    "MZ": [
        "Maputo",
        "Nampula",
        "Beira",
        "Pemba",
        "Quelimane",
        "Tete",
        "Inhambane",
        "Chimoio",
        "Xai-Xai",
        "Lichinga",
        "Nacala",
        "Vilanculos",
    ],
    "NA": ["Windhoek", "Walvis Bay", "Swakopmund"],
    "NE": ["Niamey", "Zinder"],
    "NG": ["Abuja", "Lagos", "Kano", "Port Harcourt", "Ibadan"],
    "CF": ["Bangui"],
    "KE": ["Nairobi", "Mombaça", "Kisumu", "Nakuru"],
    "RW": ["Kigali"],
    "ST": ["São Tomé", "Santo António"],
    "SN": ["Dakar", "Saint-Louis", "Thiès"],
    "SL": ["Freetown", "Bo"],
    "SC": ["Victoria", "Mahé"],
    "SO": ["Mogadíscio", "Hargeisa"],
    "ZA": [
        "Johannesburg",
        "Cidade do Cabo",
        "Durban",
        "Pretória",
        "Port Elizabeth",
        "Bloemfontein",
    ],
    "SS": ["Juba"],
    "SD": ["Cartum", "Port Sudan"],
    "TZ": ["Dodoma", "Dar es Salaam", "Arusha", "Zanzibar", "Mwanza"],
    "TG": ["Lomé", "Sokodé"],
    "TN": ["Tunes", "Sfax", "Sousse", "Djerba"],
    "UG": ["Kampala", "Entebbe", "Jinja"],
    "ZM": ["Lusaka", "Livingstone", "Ndola"],
    "ZW": ["Harare", "Bulawayo", "Victoria Falls"],
    # Europa
    "AL": ["Tirana", "Durrës"],
    "DE": ["Berlim", "Munique", "Frankfurt", "Hamburgo", "Colónia", "Düsseldorf", "Estugarda"],
    "AD": ["Andorra-a-Velha"],
    "AT": ["Viena", "Salzburgo", "Innsbruck", "Graz"],
    "BE": ["Bruxelas", "Antuérpia", "Bruges", "Liège"],
    "BY": ["Minsk", "Brest"],
    "BA": ["Sarajevo", "Banja Luka", "Mostar"],
    "BG": ["Sófia", "Varna", "Plovdiv", "Burgas"],
    "CY": ["Nicósia", "Larnaca", "Limassol", "Paphos"],
    "HR": ["Zagreb", "Split", "Dubrovnik", "Zadar"],
    "DK": ["Copenhaga", "Aarhus", "Odense"],
    "SK": ["Bratislava", "Košice"],
    "SI": ["Liubliana", "Maribor"],
    "ES": ["Madrid", "Barcelona", "Valência", "Sevilha", "Málaga", "Bilbau", "Palma"],
    "EE": ["Tallinn", "Tartu"],
    "FI": ["Helsínquia", "Tampere", "Turku"],
    "FR": ["Paris", "Lyon", "Marselha", "Nice", "Toulouse", "Bordéus", "Nantes", "Lille"],
    "GR": ["Atenas", "Tessalónica", "Heraclião", "Rodes", "Míconos"],
    "HU": ["Budapeste", "Debrecen"],
    "IE": ["Dublin", "Cork", "Galway", "Shannon"],
    "IS": ["Reiquiavique", "Akureyri"],
    "IT": ["Roma", "Milão", "Nápoles", "Veneza", "Florença", "Turim", "Bolonha", "Palermo"],
    "XK": ["Pristina"],
    "LV": ["Riga", "Daugavpils"],
    "LI": ["Vaduz"],
    "LT": ["Vilnius", "Kaunas"],
    "LU": ["Luxemburgo"],
    "MK": ["Skopje", "Ohrid"],
    "MT": ["Valeta", "Mdina"],
    "MD": ["Chisinau"],
    "MC": ["Mónaco", "Monte Carlo"],
    "ME": ["Podgorica", "Budva", "Tivat"],
    "NO": ["Oslo", "Bergen", "Trondheim", "Stavanger"],
    "NL": ["Amesterdão", "Roterdão", "Haia", "Utrecht", "Eindhoven"],
    "PL": ["Varsóvia", "Cracóvia", "Gdansk", "Wrocław", "Poznań"],
    "PT": ["Lisboa", "Porto", "Faro", "Funchal", "Ponta Delgada", "Coimbra", "Braga"],
    "GB": ["Londres", "Manchester", "Edimburgo", "Birmingham", "Glasgow", "Bristol", "Liverpool"],
    "CZ": ["Praga", "Brno", "Ostrava"],
    "RO": ["Bucareste", "Cluj-Napoca", "Timișoara", "Iași"],
    "RU": ["Moscovo", "São Petersburgo", "Sochi", "Ecaterimburgo", "Novosibirsk", "Vladivostok"],
    "SM": ["San Marino"],
    "SE": ["Estocolmo", "Gotemburgo", "Malmö"],
    "CH": ["Zurique", "Genebra", "Berna", "Basileia", "Lausanne"],
    "RS": ["Belgrado", "Novi Sad", "Niš"],
    "UA": ["Kiev", "Lviv", "Odessa", "Kharkiv"],
    "VA": ["Cidade do Vaticano"],
    # Ásia
    "AF": ["Cabul", "Herat", "Kandahar"],
    "SA": ["Riade", "Jidá", "Meca", "Medina", "Dammam"],
    "AM": ["Erevan", "Gyumri"],
    "AZ": ["Baku", "Ganja"],
    "BH": ["Manama"],
    "BD": ["Daca", "Chittagong", "Sylhet"],
    "BN": ["Bandar Seri Begawan"],
    "BT": ["Thimphu", "Paro"],
    "KH": ["Phnom Penh", "Siem Reap", "Sihanoukville"],
    "KZ": ["Astana", "Almaty", "Shymkent"],
    "CN": ["Pequim", "Xangai", "Guangzhou", "Shenzhen", "Chengdu", "Hong Kong", "Xi'an", "Hangzhou"],
    "SG": ["Singapura"],
    "KP": ["Pyongyang"],
    "KR": ["Seul", "Busan", "Incheon", "Jeju"],
    "AE": ["Dubai", "Abu Dhabi", "Sharjah", "Ajman", "Ras Al Khaimah"],
    "PH": ["Manila", "Cebu", "Davao", "Boracay"],
    "GE": ["Tbilisi", "Batumi"],
    "IN": ["Nova Deli", "Mumbai", "Bangalore", "Chennai", "Hyderabad", "Calcutá", "Goa", "Jaipur"],
    "ID": ["Jacarta", "Bali", "Surabaya", "Yogyakarta", "Medan"],
    "IR": ["Teerão", "Isfahan", "Shiraz", "Mashhad"],
    "IQ": ["Bagdade", "Basra", "Erbil", "Najaf"],
    "IL": ["Telavive", "Jerusalém", "Haifa", "Eilat"],
    "JP": ["Tóquio", "Osaka", "Quioto", "Nagoya", "Fukuoka", "Sapporo", "Hiroshima"],
    "YE": ["Sanaa", "Aden"],
    "JO": ["Amã", "Aqaba", "Petra"],
    "KW": ["Cidade do Kuwait"],
    "LA": ["Vientiane", "Luang Prabang"],
    "LB": ["Beirute", "Trípoli"],
    "MY": ["Kuala Lumpur", "Penang", "Johor Bahru", "Kota Kinabalu", "Langkawi"],
    "MV": ["Malé"],
    "MN": ["Ulaanbaatar"],
    "MM": ["Naypyidaw", "Yangon", "Mandalay", "Bagan"],
    "NP": ["Catmandu", "Pokhara"],
    "OM": ["Mascate", "Salalah"],
    "PK": ["Islamabad", "Carachi", "Lahore", "Peshawar"],
    "QA": ["Doha"],
    "KG": ["Bisqueque", "Osh"],
    "SY": ["Damasco", "Alepo", "Latakia"],
    "LK": ["Colombo", "Kandy", "Galle"],
    "TJ": ["Dushanbe"],
    "TH": ["Banguecoque", "Phuket", "Chiang Mai", "Pattaya", "Krabi"],
    "TW": ["Taipé", "Kaohsiung", "Taichung"],
    "TL": ["Díli"],
    "TM": ["Asgabate"],
    "TR": ["Istambul", "Ancara", "Antália", "Esmirna", "Capadócia"],
    "UZ": ["Tashkent", "Samarcanda", "Bucara"],
    "VN": ["Hanói", "Cidade de Ho Chi Minh", "Da Nang", "Hoi An", "Nha Trang"],
    "PS": ["Ramallah", "Gaza", "Belém"],
    # América
    "AG": ["Saint John's"],
    "AR": ["Buenos Aires", "Córdoba", "Mendoza", "Bariloche", "Rosário"],
    "BS": ["Nassau", "Freeport"],
    "BB": ["Bridgetown"],
    "BZ": ["Belmopan", "Belize City"],
    "BO": ["La Paz", "Santa Cruz", "Sucre", "Cochabamba"],
    "BR": [
        "São Paulo",
        "Rio de Janeiro",
        "Brasília",
        "Salvador",
        "Fortaleza",
        "Belo Horizonte",
        "Recife",
        "Porto Alegre",
        "Manaus",
        "Curitiba",
    ],
    "CA": ["Toronto", "Vancouver", "Montreal", "Ottawa", "Calgary", "Quebec"],
    "CL": ["Santiago", "Valparaíso", "Antofagasta", "Punta Arenas"],
    "CO": ["Bogotá", "Medellín", "Cartagena", "Cali", "Barranquilla"],
    "CR": ["San José", "Liberia", "Puntarenas"],
    "CU": ["Havana", "Santiago de Cuba", "Varadero"],
    "DM": ["Roseau"],
    "SV": ["San Salvador"],
    "EC": ["Quito", "Guayaquil", "Cuenca"],
    "US": [
        "Nova Iorque",
        "Los Angeles",
        "Chicago",
        "Miami",
        "Washington",
        "São Francisco",
        "Las Vegas",
        "Boston",
        "Houston",
        "Atlanta",
        "Seattle",
        "Dallas",
    ],
    "GD": ["Saint George's"],
    "GT": ["Cidade da Guatemala", "Antigua"],
    "GY": ["Georgetown"],
    "HT": ["Porto Príncipe", "Cap-Haïtien"],
    "HN": ["Tegucigalpa", "San Pedro Sula"],
    "JM": ["Kingston", "Montego Bay", "Ocho Rios"],
    "MX": ["Cidade do México", "Cancún", "Guadalajara", "Monterrey", "Tijuana", "Puebla"],
    "NI": ["Manágua", "León"],
    "PA": ["Cidade do Panamá", "Colón"],
    "PY": ["Assunção", "Ciudad del Este"],
    "PE": ["Lima", "Cusco", "Arequipa", "Iquitos"],
    "DO": ["Santo Domingo", "Punta Cana", "Santiago"],
    "KN": ["Basseterre"],
    "LC": ["Castries"],
    "VC": ["Kingstown"],
    "SR": ["Paramaribo"],
    "TT": ["Port of Spain", "San Fernando"],
    "UY": ["Montevidéu", "Punta del Este"],
    "VE": ["Caracas", "Maracaibo", "Valencia"],
    # Oceania
    "AU": ["Sydney", "Melbourne", "Brisbane", "Perth", "Adelaide", "Canberra", "Darwin", "Cairns"],
    "FJ": ["Suva", "Nadi"],
    "MH": ["Majuro"],
    "SB": ["Honiara"],
    "KI": ["Tarawa"],
    "NR": ["Yaren"],
    "NZ": ["Auckland", "Wellington", "Christchurch", "Queenstown"],
    "PW": ["Ngerulmud", "Koror"],
    "PG": ["Port Moresby", "Lae"],
    "WS": ["Apia"],
    "TO": ["Nuku'alofa"],
    "TV": ["Funafuti"],
    "VU": ["Port Vila"],
    "FM": ["Palikir", "Pohnpei"],
}


def cities_for_country_code(codigo: str) -> list[str]:
    codigo = (codigo or "").upper()
    cities = CIDADES_POR_CODIGO.get(codigo, [])
    return sorted(set(cities), key=lambda x: x.lower())


def cities_for_country_name(nome_pais: str) -> list[str]:
    """Devolve cidades do país (nome em qualquer idioma ou ISO)."""
    info = find_country(nome_pais)
    if not info:
        return []
    return cities_for_country_code(info["codigo"])


def is_valid_city(nome_pais: str, cidade: str) -> bool:
    cidade = (cidade or "").strip()
    if not cidade:
        return False
    cities = cities_for_country_name(nome_pais)
    return any(c.lower() == cidade.lower() for c in cities)


def canonical_city(nome_pais: str, cidade: str) -> str | None:
    cidade = (cidade or "").strip()
    for c in cities_for_country_name(nome_pais):
        if c.lower() == cidade.lower():
            return c
    return None


def all_cities_by_country(lang: str = "pt") -> dict[str, list[str]]:
    """Mapa nome_país (idioma actual + aliases) → cidades (JSON frontend)."""
    from countries import country_aliases, country_display_name

    out: dict[str, list[str]] = {}
    for codigo, _nome_pt, _cont in PAISES_MUNDO:
        cities = cities_for_country_code(codigo)
        # chave principal = nome no idioma da sessão
        out[country_display_name(codigo, lang)] = cities
        # aliases (pt/en/fr/es + ISO) para valores antigos na sessão
        for alias in country_aliases(codigo):
            out.setdefault(alias, cities)
    return out


def ensure_all_countries_have_cities() -> None:
    """Garante que todos os códigos de PAISES_MUNDO têm pelo menos 1 cidade."""
    missing = []
    for codigo, nome, _ in PAISES_MUNDO:
        if not CIDADES_POR_CODIGO.get(codigo):
            # fallback: capital = nome do país
            CIDADES_POR_CODIGO[codigo] = [nome]
            missing.append(codigo)
    return None


ensure_all_countries_have_cities()
