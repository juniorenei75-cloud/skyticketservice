"""Internacionalização — todo o sistema no idioma da sessão."""

from __future__ import annotations

LANGUAGES = [
    {"code": "pt", "name": "Português", "flag": "🇲🇿"},
    {"code": "en", "name": "English", "flag": "🇬🇧"},
    {"code": "fr", "name": "Français", "flag": "🇫🇷"},
    {"code": "es", "name": "Español", "flag": "🇪🇸"},
]

DEFAULT_LANG = "pt"


def _e(pt: str, en: str, fr: str, es: str) -> dict[str, str]:
    return {"pt": pt, "en": en, "fr": fr, "es": es}


STRINGS: dict[str, dict[str, str]] = {
    # --- Página 0 ---
    "welcome_kicker": _e("Bem-vindo à", "Welcome to", "Bienvenue chez", "Bienvenido a"),
    "welcome_lead": _e(
        "A melhor agência de viagens para o levar a qualquer parte do mundo — com segurança, transparência e apoio 24 horas.",
        "The best travel agency to take you anywhere in the world — with safety, transparency and 24/7 support.",
        "La meilleure agence de voyages pour vous emmener partout dans le monde — sécurité, transparence et assistance 24h/24.",
        "La mejor agencia de viajes para llevarle a cualquier parte del mundo — con seguridad, transparencia y apoyo 24 horas.",
    ),
    "welcome_tagline": _e(
        "«A única preocupação que deve ter é fazer as malas.»",
        "«The only thing you should worry about is packing your bags.»",
        "«Votre seule préoccupation doit être de faire vos valises.»",
        "«La única preocupación debe ser hacer las maletas.»",
    ),
    "continue": _e("Continuar", "Continue", "Continuer", "Continuar"),
    "choose_language": _e(
        "Escolha o idioma",
        "Choose your language",
        "Choisissez votre langue",
        "Elija su idioma",
    ),
    "lang_hint": _e(
        "Todo o sistema (todas as páginas e fases) ficará neste idioma.",
        "The entire system (all pages and steps) will use this language.",
        "Tout le système (toutes les pages et étapes) utilisera cette langue.",
        "Todo el sistema (todas las páginas y fases) usará este idioma.",
    ),
    "locations": _e(
        "Nampula (Agência Mãe) · Maputo · Beira · Online · 24h",
        "Nampula (Head office) · Maputo · Beira · Online · 24h",
        "Nampula (Siège) · Maputo · Beira · En ligne · 24h",
        "Nampula (Oficina principal) · Maputo · Beira · Online · 24h",
    ),
    "slogan": _e(
        "Agência de Viagens e Turismo",
        "Travel & Tourism Agency",
        "Agence de Voyages et Tourisme",
        "Agencia de Viajes y Turismo",
    ),
    # --- Navegação / gerais ---
    "phase": _e("Fase", "Step", "Étape", "Fase"),
    "of": _e("de", "of", "sur", "de"),
    "search": _e("Pesquisa", "Search", "Recherche", "Búsqueda"),
    "flights_packages": _e(
        "Bilhetes e pacotes", "Flights & packages", "Vols et forfaits", "Vuelos y paquetes"
    ),
    "passengers": _e("Passageiros", "Passengers", "Passagers", "Pasajeros"),
    "seats": _e("Assentos", "Seats", "Sièges", "Asientos"),
    "confirmation": _e("Confirmação", "Confirmation", "Confirmation", "Confirmación"),
    "payment": _e("Pagamento", "Payment", "Paiement", "Pago"),
    "welcome": _e("Bem-vindo", "Welcome", "Bienvenue", "Bienvenido"),
    "btn_search": _e("🔎 Pesquisar", "🔎 Search", "🔎 Rechercher", "🔎 Buscar"),
    "btn_continue": _e("Continuar →", "Continue →", "Continuer →", "Continuar →"),
    "btn_back": _e("← Voltar", "← Back", "← Retour", "← Volver"),
    "btn_new_search": _e("Nova pesquisa", "New search", "Nouvelle recherche", "Nueva búsqueda"),
    "btn_home": _e("Início", "Home", "Accueil", "Inicio"),
    "btn_pay": _e(
        "✓ Pagar e receber bilhete",
        "✓ Pay and get ticket",
        "✓ Payer et recevoir le billet",
        "✓ Pagar y recibir billete",
    ),
    "btn_confirm_pay": _e(
        "Confirmar e ir para Pagamento →",
        "Confirm and go to Payment →",
        "Confirmer et aller au paiement →",
        "Confirmar e ir al pago →",
    ),
    "btn_open_ticket": _e(
        "🎟 Abrir bilhete electrónico",
        "🎟 Open electronic ticket",
        "🎟 Ouvrir le billet électronique",
        "🎟 Abrir billete electrónico",
    ),
    "nav_home": _e("Início", "Home", "Accueil", "Inicio"),
    "nav_book": _e("Reservar", "Book", "Réserver", "Reservar"),
    "nav_about": _e("Sobre", "About", "À propos", "Acerca de"),
    "nav_contact": _e("Contacto", "Contact", "Contact", "Contacto"),
    "nav_help": _e("Ajuda", "Help", "Aide", "Ayuda"),
    "nav_contact_us": _e("Contacte-nos", "Contact us", "Contactez-nous", "Contáctenos"),
    "nav_login": _e("Entrar", "Log in", "Connexion", "Iniciar sesión"),
    "nav_experience": _e("Experiência", "Experience", "Expérience", "Experiencia"),
    "nav_club": _e("Clube Privilege", "Privilege Club", "Privilege Club", "Privilege Club"),
    "nav_destinations": _e("Destinos", "Destinations", "Destinations", "Destinos"),
    "nav_deals": _e("Ofertas", "Deals", "Offres", "Ofertas"),
    "nav_book_flight": _e(
        "Reservar voo", "Book a flight", "Réserver un vol", "Reservar vuelo"
    ),
    "nav_menu": _e("Menu", "Menu", "Menu", "Menú"),
    "nav_packages": _e(
        "Pacotes de férias", "Holiday packages", "Forfaits vacances", "Paquetes de vacaciones"
    ),
    "nav_hotels": _e("Hotéis", "Hotels", "Hôtels", "Hoteles"),
    "nav_flight_deals": _e(
        "Ofertas de voos", "Flight deals", "Offres de vols", "Ofertas de vuelos"
    ),
    "nav_about_us": _e("Sobre nós", "About us", "À propos de nous", "Sobre nosotros"),
    "nav_help_contact": _e(
        "Ajuda e contacto", "Help & contact", "Aide et contact", "Ayuda y contacto"
    ),
    "nav_email_us": _e("Enviar e-mail", "Email us", "Nous écrire", "Escríbanos"),
    "footer_blurb": _e(
        "Agência de viagens — voos, pacotes e hotéis em todo o mundo. Nampula (Agência Mãe), Maputo, Beira e online · 24h.",
        "Travel agency — flights, packages and hotels worldwide. Nampula (Head Office), Maputo, Beira & online · 24/7.",
        "Agence de voyages — vols, forfaits et hôtels dans le monde. Nampula (siège), Maputo, Beira et en ligne · 24h/24.",
        "Agencia de viajes — vuelos, paquetes y hoteles en todo el mundo. Nampula (oficina principal), Maputo, Beira y online · 24h.",
    ),
    "footer_rights": _e(
        "Todos os direitos reservados.",
        "All rights reserved.",
        "Tous droits réservés.",
        "Todos los derechos reservados.",
    ),
    "footer_mozambique": _e("Moçambique", "Mozambique", "Mozambique", "Mozambique"),
    "continent_africa": _e("África", "Africa", "Afrique", "África"),
    "continent_america": _e("América", "Americas", "Amériques", "América"),
    "continent_asia": _e("Ásia", "Asia", "Asie", "Asia"),
    "continent_europe": _e("Europa", "Europe", "Europe", "Europa"),
    "continent_oceania": _e("Oceania", "Oceania", "Océanie", "Oceanía"),
    "hq_nampula": _e(
        "Nampula — Agência Mãe",
        "Nampula — Head office",
        "Nampula — Siège",
        "Nampula — Oficina principal",
    ),
    "hours_24_7": _e(
        "24 horas por dia, 7 dias por semana",
        "24 hours a day, 7 days a week",
        "24 heures sur 24, 7 jours sur 7",
        "24 horas al día, 7 días a la semana",
    ),
    "site_description": _e(
        "SKYTICKETservice — Agência de Viagens sem limites. Bilhetes e pacotes para qualquer país do mundo. Nampula (Agência Mãe), Maputo, Beira e online. Atendimento 24h.",
        "SKYTICKETservice — Travel agency without limits. Tickets and packages to any country. Nampula (Head office), Maputo, Beira and online. 24/7 support.",
        "SKYTICKETservice — Agence de voyages sans limites. Billets et forfaits vers tous les pays. Nampula (siège), Maputo, Beira et en ligne. Assistance 24h/24.",
        "SKYTICKETservice — Agencia de viajes sin límites. Billetes y paquetes a cualquier país. Nampula (oficina principal), Maputo, Beira y online. Atención 24h.",
    ),
    "site_keywords": _e(
        "SKYTICKETservice, agência de viagens, bilhetes, voos internacionais, Moçambique, Nampula",
        "SKYTICKETservice, travel agency, tickets, international flights, Mozambique, Nampula",
        "SKYTICKETservice, agence de voyages, billets, vols internationaux, Mozambique, Nampula",
        "SKYTICKETservice, agencia de viajes, billetes, vuelos internacionales, Mozambique, Nampula",
    ),
    "city_ph_origin": _e(
        "Cidade do país de origem…",
        "City in the origin country…",
        "Ville du pays d'origine…",
        "Ciudad del país de origen…",
    ),
    "city_ph_dest": _e(
        "Cidade do país de destino…",
        "City in the destination country…",
        "Ville du pays de destination…",
        "Ciudad del país de destino…",
    ),
    "js_confirm": _e(
        "Tem a certeza?", "Are you sure?", "Êtes-vous sûr ?", "¿Está seguro?"
    ),
    "js_country_placeholder": _e(
        "Clique para ver países ou digite para filtrar…",
        "Click to see countries or type to filter…",
        "Cliquez pour voir les pays ou tapez pour filtrer…",
        "Clic para ver países o escriba para filtrar…",
    ),
    "js_country_selected": _e(
        "✓ País seleccionado: {name}",
        "✓ Selected country: {name}",
        "✓ Pays sélectionné : {name}",
        "✓ País seleccionado: {name}",
    ),
    "js_country_hint": _e(
        "{n} países · seleccione apenas da lista (não pode inventar nomes)",
        "{n} countries · select from the list only (custom names not allowed)",
        "{n} pays · sélectionnez uniquement dans la liste",
        "{n} países · seleccione solo de la lista",
    ),
    "js_country_suggestions": _e(
        "Sugestões ({n} países) — digite para filtrar:",
        "Suggestions ({n} countries) — type to filter:",
        "Suggestions ({n} pays) — tapez pour filtrer :",
        "Sugerencias ({n} países) — escriba para filtrar:",
    ),
    "js_country_results": _e(
        "{n} resultado(s) para «{q}»",
        "{n} result(s) for «{q}»",
        "{n} résultat(s) pour «{q}»",
        "{n} resultado(s) para «{q}»",
    ),
    "js_country_none": _e(
        "Nenhum país começa com «{q}»",
        "No country starts with «{q}»",
        "Aucun pays ne commence par «{q}»",
        "Ningún país empieza por «{q}»",
    ),
    "js_country_only_list": _e(
        "Escolha um país da lista oficial. Nomes fora da lista não são aceites.",
        "Choose a country from the official list. Names outside the list are not accepted.",
        "Choisissez un pays de la liste officielle. Les noms hors liste ne sont pas acceptés.",
        "Elija un país de la lista oficial. Los nombres fuera de la lista no se aceptan.",
    ),
    "js_city_placeholder": _e(
        "Seleccione o país primeiro…",
        "Select the country first…",
        "Sélectionnez d'abord le pays…",
        "Seleccione primero el país…",
    ),
    "js_city_need_country": _e(
        "Seleccione primeiro o país.",
        "Select the country first.",
        "Sélectionnez d'abord le pays.",
        "Seleccione primero el país.",
    ),
    "js_city_selected": _e(
        "✓ Cidade: {city} ({country})",
        "✓ City: {city} ({country})",
        "✓ Ville : {city} ({country})",
        "✓ Ciudad: {city} ({country})",
    ),
    "js_city_hint": _e(
        "{n} cidades em {country} — digite para filtrar; só da lista.",
        "{n} cities in {country} — type to filter; list only.",
        "{n} villes à {country} — tapez pour filtrer ; liste uniquement.",
        "{n} ciudades en {country} — escriba para filtrar; solo lista.",
    ),
    "js_city_filter": _e(
        "{n} cidade(s) em {country}",
        "{n} city(ies) in {country}",
        "{n} ville(s) à {country}",
        "{n} ciudad(es) en {country}",
    ),
    "js_city_list": _e(
        "Cidades de {country} ({n}) — digite para filtrar:",
        "Cities in {country} ({n}) — type to filter:",
        "Villes de {country} ({n}) — tapez pour filtrer :",
        "Ciudades de {country} ({n}) — escriba para filtrar:",
    ),
    "js_city_none": _e(
        "Nenhuma cidade encontrada em {country}",
        "No cities found in {country}",
        "Aucune ville trouvée à {country}",
        "No se encontraron ciudades en {country}",
    ),
    "js_phone_placeholder": _e(
        "Pesquisar país ou código…",
        "Search country or code…",
        "Rechercher pays ou indicatif…",
        "Buscar país o código…",
    ),
    "js_phone_hint": _e(
        "Seleccione o código do país do telemóvel",
        "Select the mobile country calling code",
        "Sélectionnez l'indicatif du pays",
        "Seleccione el código telefónico del país",
    ),
    "js_pick_country_alert": _e(
        "Seleccione um país válido da lista.",
        "Select a valid country from the list.",
        "Sélectionnez un pays valide dans la liste.",
        "Seleccione un país válido de la lista.",
    ),
    "js_pick_city_alert": _e(
        "Seleccione uma cidade válida da lista do país.",
        "Select a valid city from the country list.",
        "Sélectionnez une ville valide dans la liste du pays.",
        "Seleccione una ciudad válida de la lista del país.",
    ),
    "js_pick_phone_alert": _e(
        "Seleccione um código telefónico válido.",
        "Select a valid phone country code.",
        "Sélectionnez un indicatif téléphonique valide.",
        "Seleccione un código telefónico válido.",
    ),
    "err_phone_missing": _e(
        "Telefone em falta.", "Phone number missing.", "Téléphone manquant.", "Falta el teléfono."
    ),
    "err_phone_short": _e(
        "Número de telefone demasiado curto.",
        "Phone number too short.",
        "Numéro de téléphone trop court.",
        "Número de teléfono demasiado corto.",
    ),
    "err_phone_long": _e(
        "Número de telefone demasiado longo (máx. 15 dígitos).",
        "Phone number too long (max 15 digits).",
        "Numéro de téléphone trop long (max. 15 chiffres).",
        "Número de teléfono demasiado largo (máx. 15 dígitos).",
    ),
    "err_phone_national": _e(
        "Número nacional inválido após o código do país.",
        "Invalid national number after country code.",
        "Numéro national invalide après l'indicatif.",
        "Número nacional inválido tras el código de país.",
    ),
    "err_phone_intl": _e(
        "Código de país ou número internacional inválido.",
        "Invalid country code or international number.",
        "Indicatif ou numéro international invalide.",
        "Código de país o número internacional inválido.",
    ),
    "err_phone_incomplete": _e(
        "Indique o número completo (ou use +código do país).",
        "Enter the full number (or use +country code).",
        "Indiquez le numéro complet (ou utilisez +indicatif).",
        "Indique el número completo (o use +código de país).",
    ),
    "admin": _e("Admin", "Admin", "Admin", "Admin"),
    # --- Fase 1 ---
    "where_travel": _e(
        "✈ Onde quer viajar?",
        "✈ Where do you want to travel?",
        "✈ Où souhaitez-vous voyager ?",
        "✈ ¿A dónde desea viajar?",
    ),
    "phase1_lead": _e(
        "Preencha o formulário e clique em Pesquisar. O destino usa autocomplete com os países do mundo (só opções da lista).",
        "Fill in the form and click Search. Destination uses world-country autocomplete (list only).",
        "Remplissez le formulaire et cliquez sur Rechercher. Destination avec autocomplétion (liste uniquement).",
        "Complete el formulario y pulse Buscar. Destino con autocompletado (solo de la lista).",
    ),
    "origin_dest": _e(
        "Origem e destino *",
        "Origin and destination *",
        "Origine et destination *",
        "Origen y destino *",
    ),
    "country_origin": _e(
        "País de origem *", "Country of origin *", "Pays d'origine *", "País de origen *"
    ),
    "country_dest": _e(
        "País de destino *",
        "Destination country *",
        "Pays de destination *",
        "País de destino *",
    ),
    "city_origin": _e(
        "Cidade de origem", "City of origin", "Ville d'origine", "Ciudad de origen"
    ),
    "city_dest": _e(
        "Cidade de destino",
        "Destination city",
        "Ville de destination",
        "Ciudad de destino",
    ),
    "one_way": _e("➡ Só ida", "➡ One way", "➡ Aller simple", "➡ Solo ida"),
    "round_trip": _e(
        "⇄ Ida e volta", "⇄ Round trip", "⇄ Aller-retour", "⇄ Ida y vuelta"
    ),
    "date_depart": _e(
        "Data de ida *", "Departure date *", "Date de départ *", "Fecha de ida *"
    ),
    "date_return": _e(
        "Data de volta *", "Return date *", "Date de retour *", "Fecha de regreso *"
    ),
    "date_depart_only": _e(
        "Data de partida *", "Departure date *", "Date de départ *", "Fecha de salida *"
    ),
    "dates_trip": _e(
        "Datas de ida e volta *",
        "Departure and return dates *",
        "Dates aller et retour *",
        "Fechas de ida y vuelta *",
    ),
    "adults": _e("Adultos *", "Adults *", "Adultes *", "Adultos *"),
    "children": _e("Crianças", "Children", "Enfants", "Niños"),
    "class_label": _e("Classe *", "Class *", "Classe *", "Clase *"),
    "trip_type": _e(
        "Tipo de viagem *", "Trip type *", "Type de voyage *", "Tipo de viaje *"
    ),
    "class_economy": _e("Económica", "Economy", "Économique", "Económica"),
    "class_business": _e("Executiva", "Business", "Affaires", "Ejecutiva"),
    "class_first": _e(
        "Primeira classe", "First class", "Première classe", "Primera clase"
    ),
    "motivo_lazer": _e("Lazer", "Leisure", "Loisirs", "Ocio"),
    "motivo_negocios": _e("Negócios", "Business", "Affaires", "Negocios"),
    "motivo_lua": _e("Lua de mel", "Honeymoon", "Lune de miel", "Luna de miel"),
    "motivo_familiar": _e("Familiar", "Family", "Familial", "Familiar"),
    "motivo_outro": _e("Outro", "Other", "Autre", "Otro"),
    # --- Preferência de resultados (após pesquisa) ---
    "pref_title": _e(
        "Como deseja ver os bilhetes?",
        "How do you want to see tickets?",
        "Comment souhaitez-vous voir les billets ?",
        "¿Cómo desea ver los billetes?",
    ),
    "pref_lead": _e(
        "Seleccione uma opção. Os resultados seguintes correspondem exactamente à sua escolha — sem misturar.",
        "Select one option. The following results match your choice exactly — no mix.",
        "Sélectionnez une option. Les résultats correspondent exactement à votre choix.",
        "Seleccione una opción. Los resultados coinciden exactamente con su elección.",
    ),
    "pref_cheap": _e(
        "Procurar bilhetes mais baratos",
        "Search for the cheapest tickets",
        "Chercher les billets les moins chers",
        "Buscar los billetes más baratos",
    ),
    "pref_cheap_hint": _e(
        "Apenas tarifas económicas e low-cost, ordenadas do preço mais baixo para o mais alto.",
        "Only economy and low-cost fares, sorted from lowest to highest price.",
        "Uniquement tarifs économiques et low-cost, du moins cher au plus cher.",
        "Solo tarifas económicas y low-cost, de menor a mayor precio.",
    ),
    "pref_best": _e(
        "Filtrar pelas melhores companhias — como Emirates, Qatar Airways e Ethiopian Airlines",
        "Filter by top airlines — such as Emirates, Qatar Airways and Ethiopian Airlines",
        "Filtrer par les meilleures compagnies — Emirates, Qatar Airways et Ethiopian Airlines",
        "Filtrar por las mejores aerolíneas — Emirates, Qatar Airways y Ethiopian Airlines",
    ),
    "pref_best_hint": _e(
        "Apenas companhias full-service (Emirates, Qatar Airways, Ethiopian e similares). Sem low-cost.",
        "Only full-service airlines (Emirates, Qatar Airways, Ethiopian and similar). No low-cost.",
        "Uniquement compagnies full-service (Emirates, Qatar, Ethiopian…). Pas de low-cost.",
        "Solo aerolíneas full-service (Emirates, Qatar, Ethiopian…). Sin low-cost.",
    ),
    "err_choose_mode": _e(
        "Seleccione uma das opções de pesquisa.",
        "Select one of the search options.",
        "Sélectionnez une des options de recherche.",
        "Seleccione una de las opciones de búsqueda.",
    ),
    "mode_cheap_badge": _e(
        "Modo: mais baratos",
        "Mode: cheapest",
        "Mode : moins chers",
        "Modo: más baratos",
    ),
    "mode_best_badge": _e(
        "Modo: melhores companhias",
        "Mode: top airlines",
        "Mode : meilleures compagnies",
        "Modo: mejores aerolíneas",
    ),
    "show_flight_details": _e(
        "Mostrar detalhes do voo",
        "Show flight details",
        "Afficher les détails du vol",
        "Mostrar detalles del vuelo",
    ),
    "hide_flight_details": _e(
        "Ocultar detalhes do voo",
        "Hide flight details",
        "Masquer les détails du vol",
        "Ocultar detalles del vuelo",
    ),
    "flight_segment_out": _e(
        "Segmento de ida",
        "Outbound segment",
        "Segment aller",
        "Segmento de ida",
    ),
    "flight_segment_ret": _e(
        "Segmento de volta",
        "Return segment",
        "Segment retour",
        "Segmento de vuelta",
    ),
    "aircraft_label": _e(
        "Aeronave", "Aircraft", "Appareil", "Aeronave"
    ),
    "operated_by": _e(
        "Operado por", "Operated by", "Opéré par", "Operado por"
    ),
    "baggage_hold": _e(
        "Bagagem de porão", "Checked baggage", "Bagages en soute", "Equipaje facturado"
    ),
    "baggage_cabin": _e(
        "Bagagem de cabine", "Cabin baggage", "Bagage cabine", "Equipaje de cabina"
    ),
    "seats_remaining": _e(
        "Lugares a este preço",
        "Seats at this price",
        "Sièges à ce prix",
        "Asientos a este precio",
    ),
    # --- Fase 2 ---
    "phase2_title": _e(
        "🎫 Bilhetes disponíveis",
        "🎫 Available tickets",
        "🎫 Billets disponibles",
        "🎫 Billetes disponibles",
    ),
    "phase2_lead": _e(
        "Dezenas de opções de companhias aéreas, ordenadas do mais barato ao mais caro. Escolha uma e avance.",
        "Dozens of airline options, sorted from cheapest to most expensive. Choose one and continue.",
        "Des dizaines d'options de compagnies, du moins cher au plus cher. Choisissez et continuez.",
        "Decenas de opciones de aerolíneas, de la más barata a la más cara. Elija una y continúe.",
    ),
    "phase2_sorted": _e(
        "Ordenado por preço: mais barato → mais caro",
        "Sorted by price: cheapest → most expensive",
        "Trié par prix : moins cher → plus cher",
        "Ordenado por precio: más barato → más caro",
    ),
    "phase2_count": _e(
        "{n} opções encontradas",
        "{n} options found",
        "{n} options trouvées",
        "{n} opciones encontradas",
    ),
    "phase2_source_live": _e(
        "Inclui tarifas em tempo real (Amadeus) + mercado aéreo",
        "Includes real-time fares (Amadeus) + air market",
        "Inclut tarifs en temps réel (Amadeus) + marché aérien",
        "Incluye tarifas en tiempo real (Amadeus) + mercado aéreo",
    ),
    "phase2_source_market": _e(
        "Sem tarifas GDS neste momento. Configure API em Admin → Voos tempo real, ou escolha cotação pela agência / catálogo com preços reais.",
        "No GDS fares right now. Configure API under Admin → Live flights, or choose agency quote / catalog with real prices.",
        "Pas de tarifs GDS pour le moment. Configurez l'API ou choisissez le devis de l'agence.",
        "Sin tarifas GDS. Configure la API o elija cotización de la agencia.",
    ),
    "phase2_source_catalog": _e(
        "Ofertas do catálogo oficial SKYTICKETservice (preços e rotas registados pela agência).",
        "Official SKYTICKETservice catalog offers (routes and prices registered by the agency).",
        "Offres du catalogue officiel SKYTICKETservice.",
        "Ofertas del catálogo oficial SKYTICKETservice.",
    ),
    "phase2_source_no_api": _e(
        "API de voos em tempo real ainda não configurada. Use a cotação pela agência ou o catálogo com tarifas reais. Configure em Admin → Voos tempo real.",
        "Real-time flight API not configured yet. Use agency quote or the real-price catalog. Configure under Admin → Live flights.",
        "API temps réel non configurée. Utilisez le devis agence ou le catalogue.",
        "API en tiempo real no configurada. Use cotización o catálogo.",
    ),
    "phase2_source_no_results": _e(
        "A API não devolveu voos para esta rota/data. Peça cotação à agência — confirmamos com a companhia aérea.",
        "The API returned no flights for this route/date. Request an agency quote — we confirm with the airline.",
        "L'API n'a renvoyé aucun vol. Demandez un devis à l'agence.",
        "La API no devolvió vuelos. Solicite cotización a la agencia.",
    ),
    "phase2_source_no_iata": _e(
        "Não foi possível identificar o aeroporto (código IATA) desta cidade. Experimente a capital (ex.: Lisboa, Madrid, Maputo) ou peça cotação.",
        "Could not identify the airport (IATA code) for this city. Try the capital (e.g. Lisbon, Madrid, Maputo) or request a quote.",
        "Aéroport (IATA) introuvable pour cette ville. Essayez la capitale ou demandez un devis.",
        "No se identificó el aeropuerto (IATA). Pruebe la capital o pida cotización.",
    ),
    "live_offers_count": _e(
        "ofertas em tempo real",
        "live offers",
        "offres en temps réel",
        "ofertas en tiempo real",
    ),
    "includes_agency_service": _e(
        "inclui serviço da agência",
        "includes agency service",
        "inclut le service de l'agence",
        "incluye servicio de la agencia",
    ),
    "fare_supplier": _e(
        "Tarifa companhia / GDS",
        "Airline / GDS fare",
        "Tarif compagnie / GDS",
        "Tarifa aerolínea / GDS",
    ),
    "agency_markup": _e(
        "Margem SKYTICKET",
        "SKYTICKET markup",
        "Marge SKYTICKET",
        "Margen SKYTICKET",
    ),
    "wa_qr_title": _e(
        "Enviar dados ao WhatsApp da agência",
        "Send details to the agency WhatsApp",
        "Envoyer les données au WhatsApp de l'agence",
        "Enviar datos al WhatsApp de la agencia",
    ),
    "wa_qr_lead": _e(
        "Se estiver no computador, aponte a câmara do telemóvel a este QR Code. Abre o WhatsApp com a mensagem do bilhete pronta para enviar.",
        "If you are on a computer, point your phone camera at this QR code. It opens WhatsApp with the ticket message ready to send.",
        "Sur ordinateur, scannez ce QR avec le téléphone. WhatsApp s'ouvre avec le message du billet prêt à envoyer.",
        "Si está en el ordenador, escanee este QR con el móvil. Abre WhatsApp con el mensaje del billete listo para enviar.",
    ),
    "wa_qr_hint": _e(
        "O QR leva ao WhatsApp da SKYTICKETservice com o código e detalhes da reserva.",
        "The QR opens SKYTICKETservice WhatsApp with the booking code and details.",
        "Le QR ouvre WhatsApp SKYTICKETservice avec le code et les détails.",
        "El QR abre WhatsApp de SKYTICKETservice con el código y los detalles.",
    ),
    "wa_open_button": _e(
        "Abrir WhatsApp com os dados",
        "Open WhatsApp with details",
        "Ouvrir WhatsApp avec les données",
        "Abrir WhatsApp con los datos",
    ),
    "phase2_source_live": _e(
        "Tarifas em tempo real por companhia aérea (GDS / meta-search). Preço, horário e número de voo no momento da pesquisa.",
        "Real-time fares by airline (GDS / meta-search). Price, schedule and flight number at search time.",
        "Tarifs en temps réel par compagnie (GDS / méta-recherche).",
        "Tarifas en tiempo real por aerolínea (GDS / meta-búsqueda).",
    ),
    "phase2_source_duffel": _e(
        "Tarifas em tempo real via Duffel — cada oferta é de uma companhia aérea real (preço e voo no momento da pesquisa).",
        "Real-time fares via Duffel — each offer is from a real airline (price and flight at search time).",
        "Tarifs temps réel via Duffel — chaque offre vient d'une compagnie réelle.",
        "Tarifas en tiempo real vía Duffel — cada oferta es de una aerolínea real.",
    ),
    "phase2_source_amadeus": _e(
        "Tarifas GDS em tempo real (Amadeus) — cada oferta corresponde a uma companhia e voo reais.",
        "Real-time GDS fares (Amadeus) — each offer is a real airline and flight.",
        "Tarifs GDS temps réel (Amadeus).",
        "Tarifas GDS en tiempo real (Amadeus).",
    ),
    "phase2_source_kiwi": _e(
        "Tarifas em tempo real (Kiwi Tequila) — multi-companhia com preço e horários actuais.",
        "Real-time fares (Kiwi Tequila) — multi-airline with current price and times.",
        "Tarifs temps réel (Kiwi Tequila).",
        "Tarifas en tiempo real (Kiwi Tequila).",
    ),
    "live_fare_airline": _e(
        "Tempo real · companhia",
        "Live · airline",
        "Temps réel · compagnie",
        "Tiempo real · aerolínea",
    ),
    "cheapest": _e("Mais barato", "Cheapest", "Moins cher", "Más barato"),
    "per_adult": _e("/ adulto", "/ adult", "/ adulte", "/ adulto"),
    "quote": _e("Cotação", "Quote", "Devis", "Cotización"),
    "package": _e("Pacote", "Package", "Forfait", "Paquete"),
    "flight": _e("Voo", "Flight", "Vol", "Vuelo"),
    "live_fare": _e("Tempo real", "Live", "Temps réel", "Tiempo real"),
    "market_fare": _e("Mercado", "Market", "Marché", "Mercado"),
    "custom": _e("Personalizado", "Custom", "Personnalisé", "Personalizado"),
    "schedule": _e("Horário", "Schedule", "Horaire", "Horario"),
    "duration": _e("Duração", "Duration", "Durée", "Duración"),
    "class_word": _e("Classe", "Class", "Classe", "Clase"),
    "no_options": _e(
        "Nenhuma opção encontrada.",
        "No options found.",
        "Aucune option trouvée.",
        "No se encontraron opciones.",
    ),
    # --- Fase 3 ---
    "phase3_title": _e(
        "Dados dos passageiros",
        "Passenger details",
        "Données des passagers",
        "Datos de los pasajeros",
    ),
    "phase3_lead": _e(
        "Preencha todos os dados exactamente como constam no passaporte.",
        "Enter all details exactly as shown on the passport.",
        "Saisissez toutes les données exactement comme sur le passeport.",
        "Introduzca todos los datos exactamente como en el pasaporte.",
    ),
    "phase3_airport_note": _e(
        "Apenas o passaporte é aceite para esta viagem. Os dados são verificados no check-in e no controlo de fronteiras. Qualquer diferença em relação ao passaporte pode impedir o embarque.",
        "Only a passport is accepted for this trip. Details are checked at check-in and border control. Any mismatch with the passport may prevent boarding.",
        "Seul le passeport est accepté. Les données sont vérifiées à l'enregistrement et à la frontière. Toute différence peut empêcher l'embarquement.",
        "Solo se acepta el pasaporte. Los datos se verifican en el check-in y el control fronterizo. Cualquier diferencia puede impedir el embarque.",
    ),
    "passenger_n": _e("Passageiro", "Passenger", "Passager", "Pasajero"),
    "pax_passport_hint": _e(
        "Copie do passaporte: apelido e nomes próprios, em maiúsculas, na mesma ordem.",
        "Copy from the passport: surname and given names, in capitals, same order.",
        "Copiez du passeport : nom et prénoms, en majuscules, même ordre.",
        "Copie del pasaporte: apellidos y nombres, en mayúsculas, mismo orden.",
    ),
    "pax_identity_passport_note": _e(
        "Título, sexo, nomes, data e local de nascimento e nacionalidade devem coincidir com o passaporte.",
        "Title, sex, names, date and place of birth and nationality must match the passport.",
        "Civilité, sexe, noms, date et lieu de naissance et nationalité doivent correspondre au passeport.",
        "Tratamiento, sexo, nombres, fecha y lugar de nacimiento y nacionalidad deben coincidir con el pasaporte.",
    ),
    "pax_passport_only_note": _e(
        "Documento aceite: apenas passaporte válido. BI, DIRE ou outros documentos não são válidos para esta reserva.",
        "Accepted document: valid passport only. National ID, residence permits or other documents are not valid for this booking.",
        "Document accepté : passeport valide uniquement. Carte d'identité ou titre de séjour non valables pour cette réservation.",
        "Documento aceptado: solo pasaporte válido. DNI, residencia u otros no son válidos para esta reserva.",
    ),
    "pax_sec_identity": _e(
        "1 · Identidade (conforme o passaporte)",
        "1 · Identity (as on the passport)",
        "1 · Identité (selon le passeport)",
        "1 · Identidad (según el pasaporte)",
    ),
    "pax_sec_document": _e(
        "2 · Passaporte",
        "2 · Passport",
        "2 · Passeport",
        "2 · Pasaporte",
    ),
    "pax_passport_number": _e(
        "Número do passaporte *",
        "Passport number *",
        "Numéro de passeport *",
        "Número de pasaporte *",
    ),
    "pax_passport_country": _e(
        "País de emissão do passaporte *",
        "Passport issuing country *",
        "Pays d'émission du passeport *",
        "País de emisión del pasaporte *",
    ),
    "pax_sec_contact": _e(
        "3 · Contacto",
        "3 · Contact",
        "3 · Contact",
        "3 · Contacto",
    ),
    "pax_sec_extra": _e(
        "4 · Emergência e preferências",
        "4 · Emergency & preferences",
        "4 · Urgence et préférences",
        "4 · Emergencia y preferencias",
    ),
    "pax_title": _e("Título *", "Title *", "Civilité *", "Tratamiento *"),
    "title_mr": _e("Sr. (MR)", "Mr", "M.", "Sr."),
    "title_mrs": _e("Sra. (MRS)", "Mrs", "Mme", "Sra."),
    "title_ms": _e("Srta. (MS)", "Ms", "Mlle / Ms", "Srta."),
    "title_miss": _e("Menina (MISS)", "Miss", "Mlle", "Srta. (menor)"),
    "title_mstr": _e("Menino (MSTR)", "Master", "Master", "Niño (MSTR)"),
    "title_dr": _e("Dr(a).", "Dr", "Dr", "Dr(a)."),
    "pax_gender": _e(
        "Sexo (conforme o passaporte) *",
        "Sex (as on passport) *",
        "Sexe (selon le passeport) *",
        "Sexo (según el pasaporte) *",
    ),
    "gender_m": _e("Masculino", "Male", "Masculin", "Masculino"),
    "gender_f": _e("Feminino", "Female", "Féminin", "Femenino"),
    "pax_surname": _e(
        "Apelido / sobrenome *",
        "Surname / last name *",
        "Nom de famille *",
        "Apellido(s) *",
    ),
    "pax_given_names": _e(
        "Nome(s) próprio(s) *",
        "Given name(s) *",
        "Prénom(s) *",
        "Nombre(s) *",
    ),
    "pax_full_name_preview": _e(
        "Nome no bilhete (automático)",
        "Name on ticket (auto)",
        "Nom sur le billet (auto)",
        "Nombre en billete (auto)",
    ),
    "pax_as_passport": _e(
        "Como no passaporte",
        "As on passport",
        "Comme sur le passeport",
        "Como en el pasaporte",
    ),
    "pax_birth_place": _e(
        "Local de nascimento *",
        "Place of birth *",
        "Lieu de naissance *",
        "Lugar de nacimiento *",
    ),
    "pax_city_country": _e(
        "Cidade, país",
        "City, country",
        "Ville, pays",
        "Ciudad, país",
    ),
    "pax_residence": _e(
        "País de residência *",
        "Country of residence *",
        "Pays de résidence *",
        "País de residencia *",
    ),
    "pax_doc_number_ph": _e(
        "Ex.: AB1234567 (como no passaporte)",
        "e.g. AB1234567 (as on passport)",
        "ex. AB1234567 (comme sur le passeport)",
        "ej. AB1234567 (como en el pasaporte)",
    ),
    "pax_doc_issue": _e(
        "Data de emissão do passaporte *",
        "Passport date of issue *",
        "Date d'émission du passeport *",
        "Fecha de emisión del pasaporte *",
    ),
    "pax_doc_expiry": _e(
        "Data de validade do passaporte *",
        "Passport expiry date *",
        "Date d'expiration du passeport *",
        "Fecha de caducidad del pasaporte *",
    ),
    "pax_doc_expiry_hint": _e(
        "O passaporte deve estar válido na data da viagem (muitos destinos exigem validade de +6 meses).",
        "The passport must be valid on the travel date (many destinations require 6+ months validity).",
        "Le passeport doit être valide à la date du voyage (souvent +6 mois de validité).",
        "El pasaporte debe ser válido en la fecha del viaje (a menudo +6 meses de validez).",
    ),
    "pax_emergency_name": _e(
        "Contacto de emergência (nome) *",
        "Emergency contact (name) *",
        "Contact d'urgence (nom) *",
        "Contacto de emergencia (nombre) *",
    ),
    "pax_emergency_name_ph": _e(
        "Pessoa a contactar em caso de emergência",
        "Person to contact in an emergency",
        "Personne à contacter en cas d'urgence",
        "Persona a contactar en emergencia",
    ),
    "pax_emergency_phone": _e(
        "Telefone de emergência *",
        "Emergency phone *",
        "Téléphone d'urgence *",
        "Teléfono de emergencia *",
    ),
    "pax_ff_number": _e(
        "N.º passageiro frequente",
        "Frequent flyer number",
        "N° passager fréquent",
        "N.º viajero frecuente",
    ),
    "pax_ff_airline": _e(
        "Programa / companhia FF",
        "FF programme / airline",
        "Programme FF / compagnie",
        "Programa FF / aerolínea",
    ),
    "pax_optional": _e("Opcional", "Optional", "Facultatif", "Opcional"),
    "pax_special": _e(
        "Assistência especial / refeição / necessidades",
        "Special assistance / meal / needs",
        "Assistance spéciale / repas / besoins",
        "Asistencia especial / comida / necesidades",
    ),
    "pax_special_ph": _e(
        "Ex.: cadeira de rodas, refeição vegetariana (opcional)",
        "e.g. wheelchair, vegetarian meal (optional)",
        "ex. fauteuil roulant, repas végétarien (facultatif)",
        "ej. silla de ruedas, comida vegetariana (opcional)",
    ),
    "pax_notes_ph": _e(
        "Notas gerais da reserva (opcional)",
        "General booking notes (optional)",
        "Notes générales (facultatif)",
        "Notas generales (opcional)",
    ),
    "pax_legal": _e(
        "Declaro que todas as informações coincidem com o passaporte que será apresentado no aeroporto e que o passaporte é o único documento de viagem utilizado nesta reserva.",
        "I confirm all information matches the passport presented at the airport and that the passport is the only travel document used for this booking.",
        "Je confirme que toutes les informations correspondent au passeport présenté à l'aéroport et que le passeport est le seul document de voyage pour cette réservation.",
        "Confirmo que toda la información coincide con el pasaporte presentado en el aeropuerto y que el pasaporte es el único documento de viaje de esta reserva.",
    ),
    "full_name": _e(
        "Nome completo *", "Full name *", "Nom complet *", "Nombre completo *"
    ),
    "birth_date": _e(
        "Data de nascimento *",
        "Date of birth *",
        "Date de naissance *",
        "Fecha de nacimiento *",
    ),
    "nationality": _e(
        "Nacionalidade *", "Nationality *", "Nationalité *", "Nacionalidad *"
    ),
    "document": _e(
        "Passaporte / BI *",
        "Passport / ID *",
        "Passeport / pièce d'identité *",
        "Pasaporte / documento *",
    ),
    "phone": _e(
        "Telefone móvel (com código do país) *",
        "Mobile phone (with country code) *",
        "Mobile (avec indicatif) *",
        "Móvil (con código de país) *",
    ),
    "email": _e("E-mail *", "Email *", "E-mail *", "Correo *"),
    "notes": _e("Observações da reserva", "Booking notes", "Remarques", "Observaciones"),
    "adult": _e("adulto", "adult", "adulte", "adulto"),
    "child": _e("criança", "child", "enfant", "niño"),
    "err_pax_doc_expiry": _e(
        "A validade do passaporte deve ser posterior à data de hoje e à data da viagem.",
        "Passport expiry must be after today and after the travel date.",
        "La date d'expiration du passeport doit être après aujourd'hui et après le voyage.",
        "La caducidad del pasaporte debe ser posterior a hoy y a la fecha del viaje.",
    ),
    "err_pax_names": _e(
        "Indique o apelido e o(s) nome(s) próprio(s) como no passaporte.",
        "Enter surname and given name(s) as on the passport.",
        "Indiquez le nom et le(s) prénom(s) comme sur le passeport.",
        "Indique apellido(s) y nombre(s) como en el pasaporte.",
    ),
    # --- Fase 4 ---
    "phase4_title": _e(
        "💺 Assentos no avião",
        "💺 Aircraft seats",
        "💺 Sièges dans l'avion",
        "💺 Asientos del avión",
    ),
    "phase4_lead": _e(
        "Escolha os lugares conforme a classe e disponibilidade.",
        "Choose seats according to class and availability.",
        "Choisissez les sièges selon la classe et la disponibilité.",
        "Elija asientos según clase y disponibilidad.",
    ),
    "phase4_package": _e(
        "Pacote turístico: os lugares aéreos serão atribuídos na emissão pela agência.",
        "Tour package: flight seats will be assigned when tickets are issued by the agency.",
        "Forfait: les sièges seront attribués à l'émission par l'agence.",
        "Paquete: los asientos se asignarán al emitir la agencia.",
    ),
    "outbound": _e("Ida", "Outbound", "Aller", "Ida"),
    "inbound": _e("Volta", "Return", "Retour", "Vuelta"),
    "free": _e("Livre", "Free", "Libre", "Libre"),
    "yours": _e("Seu", "Yours", "Votre", "Su"),
    "occupied": _e("Ocupado", "Occupied", "Occupé", "Ocupado"),
    # --- Fase 5 ---
    "phase5_title": _e(
        "📋 Confirmação da reserva",
        "📋 Booking confirmation",
        "📋 Confirmation de réservation",
        "📋 Confirmación de reserva",
    ),
    "phase5_lead": _e(
        "Reveja todos os dados antes de avançar para o pagamento.",
        "Review all details before proceeding to payment.",
        "Vérifiez toutes les données avant le paiement.",
        "Revise todos los datos antes del pago.",
    ),
    "label_destination": _e("Destino", "Destination", "Destination", "Destino"),
    "label_origin": _e("Origem", "Origin", "Origine", "Origen"),
    "label_dates": _e("Datas", "Dates", "Dates", "Fechas"),
    "label_ticket": _e("Bilhete", "Ticket", "Billet", "Billete"),
    "label_passengers": _e("Passageiros", "Passengers", "Passagers", "Pasajeros"),
    "label_seats": _e("Assentos", "Seats", "Sièges", "Asientos"),
    "label_total": _e("Preço total", "Total price", "Prix total", "Precio total"),
    "to_quote": _e("A cotar", "To be quoted", "Devis à faire", "A cotizar"),
    "dep_short": _e("Ida", "Out", "Aller", "Ida"),
    "ret_short": _e("Volta", "Return", "Retour", "Vuelta"),
    # --- Fase 6 ---
    "phase6_title": _e("Pagamento seguro", "Secure payment", "Paiement sécurisé", "Pago seguro"),
    "phase6_lead": _e(
        "Escolha como deseja pagar à SKYTICKETservice. Locais (Moçambique) e internacionais disponíveis.",
        "Choose how to pay SKYTICKETservice. Local (Mozambique) and international options available.",
        "Choisissez comment payer SKYTICKETservice. Options locales et internationales.",
        "Elija cómo pagar a SKYTICKETservice. Opciones locales e internacionales.",
    ),
    "pay_method": _e(
        "Escolha o método de pagamento",
        "Choose payment method",
        "Choisissez le mode de paiement",
        "Elija el método de pago",
    ),
    "pay_group_mz": _e(
        "Moçambique — carteiras móveis",
        "Mozambique — mobile wallets",
        "Mozambique — portefeuilles mobiles",
        "Mozambique — monederos móviles",
    ),
    "pay_group_intl": _e(
        "Internacional — cartões e PayPal",
        "International — cards and PayPal",
        "International — cartes et PayPal",
        "Internacional — tarjetas y PayPal",
    ),
    "pay_group_bank": _e(
        "Transferência / referência bancária",
        "Bank transfer / reference",
        "Virement / référence bancaire",
        "Transferencia / referencia bancaria",
    ),
    "pay_group_agency": _e(
        "Pagamento presencial",
        "In-person payment",
        "Paiement en agence",
        "Pago presencial",
    ),
    "card_data": _e(
        "Dados do cartão bancário",
        "Bank card details",
        "Données de la carte bancaire",
        "Datos de la tarjeta bancaria",
    ),
    "card_name": _e(
        "Nome impresso no cartão",
        "Name printed on card",
        "Nom imprimé sur la carte",
        "Nombre impreso en la tarjeta",
    ),
    "card_number": _e(
        "Número do cartão", "Card number", "Numéro de carte", "Número de tarjeta"
    ),
    "card_exp": _e(
        "Validade (MM/AA)", "Expiry (MM/YY)", "Expiration (MM/AA)", "Caducidad (MM/AA)"
    ),
    "card_cvv": _e(
        "CVV (código de segurança)",
        "CVV (security code)",
        "CVV (code de sécurité)",
        "CVV (código de seguridad)",
    ),
    "card_secure_note": _e(
        "Os dados do cartão são processados de forma segura (PCI) pelo gateway. Autorização instantânea e captura automática após confirmação.",
        "Card details are processed securely (PCI) by the gateway. Instant authorization and automatic capture after confirmation.",
        "Les données de carte sont traitées en PCI. Autorisation instantanée et capture automatique après confirmation.",
        "Los datos de tarjeta se procesan en PCI. Autorización instantánea y captura automática tras la confirmación.",
    ),
    "card_gateway_ready_note": _e(
        "Pagamento com cartão via gateway seguro. O valor é autorizado e capturado automaticamente após confirmação.",
        "Card payment via secure gateway. The amount is authorized and captured automatically after confirmation.",
        "Paiement par carte via passerelle sécurisée. Autorisation et capture automatiques après confirmation.",
        "Pago con tarjeta vía pasarela segura. Autorización y captura automáticas tras la confirmación.",
    ),
    "card_gateway_missing_note": _e(
        "Gateway de cartão ainda sem chaves. Configure Stripe, Adyen ou Worldpay em Admin → Pagamentos. Entretanto pode usar o formulário de teste abaixo.",
        "Card gateway keys not set yet. Configure Stripe, Adyen or Worldpay in Admin → Payments. Meanwhile you can use the test form below.",
        "Passerelle carte sans clés. Configurez Stripe, Adyen ou Worldpay dans Admin → Paiements. Formulaire de test ci-dessous.",
        "Pasarela de tarjeta sin claves. Configure Stripe, Adyen o Worldpay en Admin → Pagos. Formulario de prueba abajo.",
    ),
    "err_pay_card_gateway": _e(
        "Conclua o pagamento do cartão no formulário seguro antes de confirmar.",
        "Complete the secure card payment before confirming.",
        "Terminez le paiement carte sécurisé avant de confirmer.",
        "Complete el pago seguro con tarjeta antes de confirmar.",
    ),
    "btn_pay_card": _e(
        "Pagar com cartão",
        "Pay with card",
        "Payer par carte",
        "Pagar con tarjeta",
    ),
    "mobile_wallet": _e(
        "Número da carteira móvel",
        "Mobile wallet number",
        "Numéro du portefeuille mobile",
        "Número del monedero móvil",
    ),
    "mobile_number": _e(
        "Número de telemóvel (com +258)",
        "Mobile number (with +258)",
        "Numéro mobile (avec +258)",
        "Número móvil (con +258)",
    ),
    "mobile_mpesa_hint": _e(
        "Indique o número Vodacom registado no M-Pesa. Receberá o pedido de confirmação no telemóvel.",
        "Enter the Vodacom number registered on M-Pesa. You will get a confirmation prompt on your phone.",
        "Indiquez le numéro Vodacom M-Pesa. Vous recevrez une confirmation sur le téléphone.",
        "Indique el número Vodacom de M-Pesa. Recibirá confirmación en el móvil.",
    ),
    "mobile_emola_hint": _e(
        "Indique o número Movitel registado no e-Mola. Confirme o pagamento na app ou USSD.",
        "Enter the Movitel number registered on e-Mola. Confirm payment in the app or USSD.",
        "Indiquez le numéro Movitel e-Mola. Confirmez dans l'app ou USSD.",
        "Indique el número Movitel de e-Mola. Confirme en la app o USSD.",
    ),
    "ref_transfer": _e(
        "Transferência bancária",
        "Bank transfer",
        "Virement bancaire",
        "Transferencia bancaria",
    ),
    "ref_proof": _e(
        "Referência / NIB do comprovativo (opcional)",
        "Reference / proof ID (optional)",
        "Référence / preuve (optionnel)",
        "Referencia / comprobante (opcional)",
    ),
    "paypal_email": _e(
        "E-mail da conta PayPal",
        "PayPal account email",
        "E-mail du compte PayPal",
        "Correo de la cuenta PayPal",
    ),
    "pay_to_agency_note": _e(
        "Pagamento a favor da SKYTICKETservice (agência). A Duffel só fornece as tarifas aéreas — o valor é cobrado por nós e a comissão fica na agência.",
        "Payment to SKYTICKETservice (agency). Duffel only provides air fares — we collect the amount and the agency keeps its margin.",
        "Paiement à SKYTICKETservice. Duffel fournit les tarifs — l'agence encaisse et conserve sa marge.",
        "Pago a SKYTICKETservice. Duffel solo aporta tarifas — la agencia cobra y conserva su margen.",
    ),
    "pay_demo_note": _e(
        "Com cartão (Stripe/Adyen/Worldpay): autorização + captura automática. Outros métodos: a reserva/e-ticket são gerados e a equipa SKYTICKET confirma a emissão.",
        "With card (Stripe/Adyen/Worldpay): authorization + automatic capture. Other methods: booking/e-ticket are created and the SKYTICKET team confirms issuance.",
        "Carte (Stripe/Adyen/Worldpay) : autorisation + capture auto. Autres modes : billet généré, confirmation par l'équipe SKYTICKET.",
        "Con tarjeta (Stripe/Adyen/Worldpay): autorización + captura automática. Otros métodos: billete generado y confirmación por el equipo SKYTICKET.",
    ),
    "total_to_pay": _e("Total a pagar", "Total to pay", "Total à payer", "Total a pagar"),
    "under_quote": _e(
        "Sob cotação", "Under quote", "Sous devis", "Bajo cotización"
    ),
    "err_pay_card_exp": _e(
        "Indique a validade no formato MM/AA.",
        "Enter expiry as MM/YY.",
        "Indiquez l'expiration au format MM/AA.",
        "Indique la caducidad en formato MM/AA.",
    ),
    "err_pay_paypal": _e(
        "Indique um e-mail PayPal válido.",
        "Enter a valid PayPal email.",
        "Indiquez un e-mail PayPal valide.",
        "Indique un correo PayPal válido.",
    ),
    # payments
    "pay_credit": _e(
        "Cartão de crédito", "Credit card", "Carte de crédit", "Tarjeta de crédito"
    ),
    "pay_debit": _e(
        "Cartão de débito", "Debit card", "Carte de débit", "Tarjeta de débito"
    ),
    "pay_card": _e(
        "Cartão bancário internacional",
        "International bank card",
        "Carte bancaire internationale",
        "Tarjeta bancaria internacional",
    ),
    "pay_paypal": _e("PayPal", "PayPal", "PayPal", "PayPal"),
    "pay_multibanco": _e(
        "Multibanco (Portugal)",
        "Multibanco (Portugal)",
        "Multibanco (Portugal)",
        "Multibanco (Portugal)",
    ),
    "pay_mpesa": _e("M-Pesa", "M-Pesa", "M-Pesa", "M-Pesa"),
    "pay_emola": _e("e-Mola", "e-Mola", "e-Mola", "e-Mola"),
    "pay_transfer": _e(
        "Transferência bancária (nacional / SWIFT)",
        "Bank transfer (domestic / SWIFT)",
        "Virement bancaire (national / SWIFT)",
        "Transferencia bancaria (nacional / SWIFT)",
    ),
    "pay_agency": _e(
        "Pagar na agência SKYTICKET",
        "Pay at SKYTICKET agency",
        "Payer à l'agence SKYTICKET",
        "Pagar en la agencia SKYTICKET",
    ),
    "pay_credit_d": _e(
        "Visa, Mastercard",
        "Visa, Mastercard",
        "Visa, Mastercard",
        "Visa, Mastercard",
    ),
    "pay_debit_d": _e(
        "Débito directo", "Direct debit", "Débit direct", "Débito directo"
    ),
    "pay_card_d": _e(
        "Visa ou Mastercard — preencha os dados para débito do valor",
        "Visa or Mastercard — enter details to charge the amount",
        "Visa ou Mastercard — saisissez les données pour le débit",
        "Visa o Mastercard — complete los datos para el cargo",
    ),
    "pay_paypal_d": _e(
        "Pague com a sua conta PayPal (internacional)",
        "Pay with your PayPal account (international)",
        "Payez avec votre compte PayPal (international)",
        "Pague con su cuenta PayPal (internacional)",
    ),
    "pay_multibanco_d": _e(
        "Referência Multibanco para pagamento em Portugal / ATM",
        "Multibanco reference for payment in Portugal / ATM",
        "Référence Multibanco pour paiement au Portugal",
        "Referencia Multibanco para pago en Portugal",
    ),
    "pay_mpesa_d": _e(
        "Vodacom Moçambique — pagamento móvel instantâneo",
        "Vodacom Mozambique — instant mobile payment",
        "Vodacom Mozambique — paiement mobile instantané",
        "Vodacom Mozambique — pago móvil instantáneo",
    ),
    "pay_emola_d": _e(
        "Movitel Moçambique — carteira digital e-Mola",
        "Movitel Mozambique — e-Mola digital wallet",
        "Movitel Mozambique — portefeuille e-Mola",
        "Movitel Mozambique — monedero e-Mola",
    ),
    "pay_transfer_d": _e(
        "IBAN / NIB / SWIFT — envie o comprovativo à agência",
        "IBAN / account / SWIFT — send proof to the agency",
        "IBAN / SWIFT — envoyez la preuve à l'agence",
        "IBAN / SWIFT — envíe el comprobante a la agencia",
    ),
    "pay_agency_d": _e(
        "Nampula (Agência Mãe), Maputo ou Beira — pagamento presencial",
        "Nampula (HQ), Maputo or Beira — pay in person",
        "Nampula (siège), Maputo ou Beira — paiement en agence",
        "Nampula (sede), Maputo o Beira — pago presencial",
    ),
    # --- Sucesso ---
    "success_title": _e(
        "Confirmação final",
        "Final confirmation",
        "Confirmation finale",
        "Confirmación final",
    ),
    "success_lead": _e(
        "A sua reserva foi registada e o bilhete electrónico está pronto.",
        "Your booking was registered and the electronic ticket is ready.",
        "Votre réservation est enregistrée et le billet électronique est prêt.",
        "Su reserva quedó registrada y el billete electrónico está listo.",
    ),
    "thanks": _e("Obrigado", "Thank you", "Merci", "Gracias"),
    "email_sent": _e(
        "📧 Confirmação enviada por e-mail com o bilhete electrónico.",
        "📧 Confirmation sent by email with the electronic ticket.",
        "📧 Confirmation envoyée par e-mail avec le billet électronique.",
        "📧 Confirmación enviada por correo con el billete electrónico.",
    ),
    "label_payment": _e("Pagamento", "Payment", "Paiement", "Pago"),
    "label_route": _e("Rota", "Route", "Itinéraire", "Ruta"),
    "label_status": _e("Estado", "Status", "Statut", "Estado"),
    "booking_done": _e(
        "Reserva concluída", "Booking complete", "Réservation terminée", "Reserva completada"
    ),
    # --- Sobre / Contacto ---
    "about_title": _e("Sobre nós", "About us", "À propos", "Sobre nosotros"),
    "about_body": _e(
        "A SKYTICKETservice é uma agência de viagens e turismo dedicada a tornar cada deslocação simples, segura e memorável. Trabalhamos bilhetes aéreos, pacotes turísticos, hotéis e assistência personalizada.",
        "SKYTICKETservice is a travel agency dedicated to making every trip simple, safe and memorable. We handle air tickets, tour packages, hotels and personalised assistance.",
        "SKYTICKETservice est une agence de voyages dédiée à rendre chaque déplacement simple, sûr et mémorable. Billets, forfaits, hôtels et assistance personnalisée.",
        "SKYTICKETservice es una agencia de viajes dedicada a hacer cada viaje simple, seguro y memorable. Billetes, paquetes, hoteles y asistencia personalizada.",
    ),
    "mission": _e("A nossa missão", "Our mission", "Notre mission", "Nuestra misión"),
    "mission_body": _e(
        "Ligar Moçambique ao mundo — e o mundo a Moçambique — com serviços transparentes, preços competitivos e acompanhamento em todas as etapas da viagem.",
        "Connect Mozambique to the world — and the world to Mozambique — with transparent services, competitive prices and support at every stage.",
        "Relier le Mozambique au monde — et le monde au Mozambique — avec des services transparents et un accompagnement à chaque étape.",
        "Conectar Mozambique con el mundo — y el mundo con Mozambique — con servicios transparentes y apoyo en cada etapa.",
    ),
    "what_we_do": _e("O que fazemos", "What we do", "Ce que nous faisons", "Qué hacemos"),
    "where_we_are": _e("Onde estamos", "Where we are", "Où nous sommes", "Dónde estamos"),
    "contact_title": _e("Contacte-nos", "Contact us", "Contactez-nous", "Contáctenos"),
    "contact_lead": _e(
        "Estamos prontos para planear a sua próxima viagem",
        "We are ready to plan your next trip",
        "Nous sommes prêts à planifier votre prochain voyage",
        "Estamos listos para planear su próximo viaje",
    ),
    "name": _e("Nome *", "Name *", "Nom *", "Nombre *"),
    "subject": _e("Assunto", "Subject", "Sujet", "Asunto"),
    "message": _e("Mensagem *", "Message *", "Message *", "Mensaje *"),
    "send_message": _e(
        "Enviar mensagem", "Send message", "Envoyer le message", "Enviar mensaje"
    ),
    "responsible": _e("Responsável", "Contact person", "Responsable", "Responsable"),
    "hours": _e("Horário", "Hours", "Horaires", "Horario"),
    "whatsapp_btn": _e(
        "Falar no WhatsApp", "Chat on WhatsApp", "Parler sur WhatsApp", "Hablar por WhatsApp"
    ),
    # --- Flashes ---
    "err_dest_country": _e(
        "Seleccione o país de destino na lista de autocomplete (197 países).",
        "Select the destination country from the autocomplete list (197 countries).",
        "Sélectionnez le pays de destination dans la liste (197 pays).",
        "Seleccione el país de destino en la lista (197 países).",
    ),
    "err_orig_country": _e(
        "Seleccione o país de origem na lista de autocomplete.",
        "Select the origin country from the autocomplete list.",
        "Sélectionnez le pays d'origine dans la liste.",
        "Seleccione el país de origen en la lista.",
    ),
    "err_city_origin": _e(
        "Seleccione a cidade de origem da lista do país escolhido.",
        "Select the origin city from the list of the chosen country.",
        "Sélectionnez la ville d'origine dans la liste du pays choisi.",
        "Seleccione la ciudad de origen de la lista del país elegido.",
    ),
    "err_city_dest": _e(
        "Seleccione a cidade de destino da lista do país escolhido.",
        "Select the destination city from the list of the chosen country.",
        "Sélectionnez la ville de destination dans la liste du pays choisi.",
        "Seleccione la ciudad de destino de la lista del país elegido.",
    ),
    "err_date_depart": _e(
        "Indique a data de ida.",
        "Enter the departure date.",
        "Indiquez la date de départ.",
        "Indique la fecha de ida.",
    ),
    "err_date_return": _e(
        "Indique a data de volta.",
        "Enter the return date.",
        "Indiquez la date de retour.",
        "Indique la fecha de regreso.",
    ),
    "err_date_order": _e(
        "A data de volta deve ser igual ou depois da data de ida.",
        "Return date must be on or after departure date.",
        "La date de retour doit être égale ou postérieure au départ.",
        "La fecha de regreso debe ser igual o posterior a la de ida.",
    ),
    "err_class": _e(
        "Seleccione a classe pretendida.",
        "Select the desired class.",
        "Sélectionnez la classe souhaitée.",
        "Seleccione la clase deseada.",
    ),
    "err_trip_type": _e(
        "Seleccione o tipo de viagem.",
        "Select the trip type.",
        "Sélectionnez le type de voyage.",
        "Seleccione el tipo de viaje.",
    ),
    "err_start_phase1": _e(
        "Comece pela pesquisa da viagem (Fase 1).",
        "Start with the trip search (Step 1).",
        "Commencez par la recherche (Étape 1).",
        "Empiece por la búsqueda (Fase 1).",
    ),
    "err_choose_ticket": _e(
        "Escolha um bilhete ou pacote da lista.",
        "Choose a ticket or package from the list.",
        "Choisissez un billet ou forfait dans la liste.",
        "Elija un billete o paquete de la lista.",
    ),
    "err_choose_ticket_first": _e(
        "Escolha primeiro um bilhete ou pacote.",
        "Choose a ticket or package first.",
        "Choisissez d'abord un billet ou forfait.",
        "Elija primero un billete o paquete.",
    ),
    "err_pax_fields": _e(
        "Preencha todos os campos obrigatórios de cada passageiro conforme o passaporte (identidade, passaporte, contacto e emergência).",
        "Fill in all required fields for each passenger as on the passport (identity, passport, contact and emergency).",
        "Remplissez tous les champs de chaque passager.",
        "Complete todos los campos de cada pasajero.",
    ),
    "err_pax_review": _e(
        "Revise os campos assinalados. Os restantes dados foram mantidos.",
        "Please review the highlighted fields. Your other details were kept.",
        "Veuillez vérifier les champs indiqués. Les autres données ont été conservées.",
        "Revise los campos marcados. El resto de datos se conservó.",
    ),
    "err_pax_field_required": _e(
        "Campo obrigatório.",
        "Required field.",
        "Champ obligatoire.",
        "Campo obligatorio.",
    ),
    "err_pax_email": _e(
        "Indique um e-mail válido.",
        "Enter a valid email address.",
        "Indiquez une adresse e-mail valide.",
        "Indique un correo electrónico válido.",
    ),
    "err_pax_doc_issue_future": _e(
        "A data de emissão não pode ser no futuro.",
        "Issue date cannot be in the future.",
        "La date d'émission ne peut pas être dans le futur.",
        "La fecha de emisión no puede ser futura.",
    ),
    "pax_fix_alert_title": _e(
        "É necessária uma correcção",
        "A correction is needed",
        "Une correction est nécessaire",
        "Se necesita una corrección",
    ),
    "pax_fix_alert_lead": _e(
        "Os dados já preenchidos foram preservados. Corrija apenas o(s) ponto(s) abaixo e continue.",
        "Your filled-in details were preserved. Please fix only the item(s) below and continue.",
        "Vos données déjà saisies ont été conservées. Corrigez uniquement le(s) point(s) ci-dessous puis continuez.",
        "Se conservaron los datos ya completados. Corrija solo el/los punto(s) abajo y continúe.",
    ),
    "err_nationality": _e(
        "Seleccione um país da lista.",
        "Select a country from the list.",
        "Sélectionnez un pays dans la liste.",
        "Seleccione un país de la lista.",
    ),
    "err_fill_pax": _e(
        "Preencha os dados dos passageiros.",
        "Fill in passenger details.",
        "Remplissez les données des passagers.",
        "Complete los datos de los pasajeros.",
    ),
    "err_seat_occupied_out": _e(
        "O assento de ida {seat} já não está disponível. Escolha outro — a restante selecção foi mantida.",
        "Outbound seat {seat} is no longer available. Choose another — your other selections were kept.",
        "Le siège aller {seat} n'est plus disponible. Choisissez-en un autre — le reste a été conservé.",
        "El asiento de ida {seat} ya no está disponible. Elija otro — se mantuvo el resto de la selección.",
    ),
    "err_seat_occupied_ret": _e(
        "O assento de volta {seat} já não está disponível. Escolha outro — a restante selecção foi mantida.",
        "Return seat {seat} is no longer available. Choose another — your other selections were kept.",
        "Le siège retour {seat} n'est plus disponible. Choisissez-en un autre — le reste a été conservé.",
        "El asiento de vuelta {seat} ya no está disponible. Elija otro — se mantuvo el resto de la selección.",
    ),
    "err_seats_out": _e(
        "Seleccione os assentos de ida.",
        "Select outbound seats.",
        "Sélectionnez les sièges aller.",
        "Seleccione asientos de ida.",
    ),
    "err_seats_ret": _e(
        "Seleccione os assentos de volta.",
        "Select return seats.",
        "Sélectionnez les sièges retour.",
        "Seleccione asientos de regreso.",
    ),
    "pay_form_alert_title": _e(
        "Revise os dados de pagamento",
        "Please review payment details",
        "Vérifiez les données de paiement",
        "Revise los datos de pago",
    ),
    "pay_form_alert_lead": _e(
        "Os campos já preenchidos foram mantidos. Corrija apenas o indicado.",
        "Your filled-in fields were kept. Please fix only what is listed.",
        "Les champs déjà saisis ont été conservés. Corrigez uniquement ce qui est indiqué.",
        "Se conservaron los campos completados. Corrija solo lo indicado.",
    ),
    "err_pay_card_number": _e(
        "Indique um número de cartão válido (mín. 12 dígitos).",
        "Enter a valid card number (min. 12 digits).",
        "Indiquez un numéro de carte valide (min. 12 chiffres).",
        "Indique un número de tarjeta válido (mín. 12 dígitos).",
    ),
    "err_pay_cvv": _e(
        "Indique o CVV (3 ou 4 dígitos).",
        "Enter the CVV (3 or 4 digits).",
        "Indiquez le CVV (3 ou 4 chiffres).",
        "Indique el CVV (3 o 4 dígitos).",
    ),
    "err_pay_mobile": _e(
        "Indique o número M-Pesa / e-Mola completo.",
        "Enter the full M-Pesa / e-Mola number.",
        "Indiquez le numéro M-Pesa / e-Mola complet.",
        "Indique el número M-Pesa / e-Mola completo.",
    ),
    "err_pay_ref": _e(
        "Indique a referência ou comprovativo da transferência.",
        "Enter the transfer reference or proof.",
        "Indiquez la référence ou la preuve du virement.",
        "Indique la referencia o comprobante de la transferencia.",
    ),
    "booking_ref_hint": _e(
        "Guarde este código — é a referência da sua reserva.",
        "Save this code — it is your booking reference.",
        "Conservez ce code — c'est la référence de votre réservation.",
        "Guarde este código — es la referencia de su reserva.",
    ),
    "err_payment": _e(
        "Escolha uma forma de pagamento.",
        "Choose a payment method.",
        "Choisissez un mode de paiement.",
        "Elija una forma de pago.",
    ),
    "err_booking_nf": _e(
        "Reserva não encontrada.",
        "Booking not found.",
        "Réservation introuvable.",
        "Reserva no encontrada.",
    ),
    "err_ticket_nf": _e(
        "Bilhete não encontrado.",
        "Ticket not found.",
        "Billet introuvable.",
        "Billete no encontrado.",
    ),
    "err_login": _e(
        "Faça login para aceder ao painel.",
        "Please log in to access the panel.",
        "Connectez-vous pour accéder au panneau.",
        "Inicie sesión para acceder al panel.",
    ),
    "err_login_bad": _e(
        "Utilizador ou senha incorrectos.",
        "Incorrect username or password.",
        "Identifiant ou mot de passe incorrect.",
        "Usuario o contraseña incorrectos.",
    ),
    "msg_logout": _e(
        "Sessão terminada.", "Logged out.", "Session terminée.", "Sesión cerrada."
    ),
    "msg_contact_ok": _e(
        "Mensagem enviada! Entraremos em contacto em breve.",
        "Message sent! We will contact you soon.",
        "Message envoyé ! Nous vous contacterons bientôt.",
        "¡Mensaje enviado! Nos pondremos en contacto pronto.",
    ),
    "msg_contact_wa": _e(
        "Mensagem enviada! A agência foi notificada no WhatsApp.",
        "Message sent! The agency was notified on WhatsApp.",
        "Message envoyé ! L'agence a été notifiée sur WhatsApp.",
        "¡Mensaje enviado! La agencia fue notificada por WhatsApp.",
    ),
    "err_contact_fields": _e(
        "Preencha nome, e-mail e mensagem.",
        "Fill in name, email and message.",
        "Remplissez nom, e-mail et message.",
        "Complete nombre, correo y mensaje.",
    ),
    "seat_max": _e(
        "Já escolheu o máximo de assentos.",
        "You already selected the maximum seats.",
        "Nombre maximum de sièges atteint.",
        "Ya eligió el máximo de asientos.",
    ),
    "seat_need_out": _e(
        "Seleccione os assentos de ida.",
        "Select outbound seats.",
        "Sélectionnez les sièges aller.",
        "Seleccione asientos de ida.",
    ),
    "seat_need_ret": _e(
        "Seleccione os assentos de volta.",
        "Select return seats.",
        "Sélectionnez les sièges retour.",
        "Seleccione asientos de regreso.",
    ),
}


def normalize_lang(code: str | None) -> str:
    code = (code or DEFAULT_LANG).lower().strip()
    if code not in {l["code"] for l in LANGUAGES}:
        return DEFAULT_LANG
    return code


def t(key: str, lang: str | None = None, **fmt) -> str:
    lang = normalize_lang(lang)
    entry = STRINGS.get(key)
    if not entry:
        return key
    text = entry.get(lang) or entry.get(DEFAULT_LANG) or key
    if fmt:
        try:
            text = text.format(**fmt)
        except (KeyError, ValueError):
            pass
    return text


def class_label(class_id: str, lang: str | None = None) -> str:
    m = {
        "economica": "class_economy",
        "executiva": "class_business",
        "primeira": "class_first",
    }
    return t(m.get(class_id, "class_economy"), lang)


def motivo_label(motivo_id: str, lang: str | None = None) -> str:
    m = {
        "lazer": "motivo_lazer",
        "negocios": "motivo_negocios",
        "lua_de_mel": "motivo_lua",
        "familiar": "motivo_familiar",
        "outro": "motivo_outro",
    }
    return t(m.get(motivo_id, "motivo_outro"), lang)


def pay_label(pay_id: str, lang: str | None = None) -> tuple[str, str]:
    names = {
        "credito": ("pay_credit", "pay_credit_d"),
        "debito": ("pay_debit", "pay_debit_d"),
        "cartao": ("pay_card", "pay_card_d"),
        "paypal": ("pay_paypal", "pay_paypal_d"),
        "multibanco": ("pay_multibanco", "pay_multibanco_d"),
        "mpesa": ("pay_mpesa", "pay_mpesa_d"),
        "emola": ("pay_emola", "pay_emola_d"),
        "transferencia": ("pay_transfer", "pay_transfer_d"),
        "agencia": ("pay_agency", "pay_agency_d"),
    }
    nk, dk = names.get(pay_id, ("pay_agency", "pay_agency_d"))
    return t(nk, lang), t(dk, lang)
