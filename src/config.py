"""
Configurações para o agente de trading esportivo.
"""

# Configurações das APIs
ODDS_API_KEY = "b92e2c2fbcbbb0bb8cdbcb29db8c007b"  # Chave da The Odds API
API_FUTEBOL_KEY = "live_9506a431b215b8d309885a6eb8eadd"  # Chave da API-Futebol

# Configurações do Telegram
TELEGRAM_BOT_TOKEN = "7880179699:AAEtOghdEiHwCvnFJMKR_X0G1EQMdPfb8QE"
TELEGRAM_CHAT_ID = None  # Será preenchido automaticamente na primeira mensagem

# URLs base das APIs
ODDS_API_BASE_URL = "https://api.the-odds-api.com/v4/sports"
API_FUTEBOL_BASE_URL = "https://api.api-futebol.com.br/v1"

# Configurações de mercados e regiões para The Odds API
ODDS_API_REGIONS = "eu,uk"  # Regiões para obter odds (eu=Europa, uk=Reino Unido)
ODDS_API_MARKETS = "h2h,h2h_lay,totals"  # Mercados para obter odds (h2h=moneyline, h2h_lay=lay odds)

# Esportes para monitorar
SPORTS_TO_MONITOR = [
    "soccer_brazil_campeonato",  # Campeonato Brasileiro
    "soccer_brazil_serie_b",     # Campeonato Brasileiro Série B
    "soccer_epl",                # Premier League Inglesa
    "soccer_spain_la_liga",      # La Liga Espanhola
    "soccer_italy_serie_a",      # Série A Italiana
    "soccer_germany_bundesliga", # Bundesliga Alemã
]

# Configurações para o método dos ciclos
MAX_BACK_ODDS = 1.06  # Odds máximas para Back (retorno de 3-5%)
MIN_LAY_ODDS = 30.0   # Odds mínimas para Lay (retorno de 3-5%)
TARGET_GREEN_PERCENT = 0.05  # Alvo de 5% de green
MAX_RED_PERCENT = 0.15  # Máximo de 15% de red
RISK_REWARD_RATIO = 3  # Proporção de 1:3 (risco:retorno)

# Configurações para análise de oportunidades
MIN_ODDS_DIFFERENCE = 0.05  # Diferença mínima entre odds para considerar uma oportunidade
MIN_PROBABILITY = 0.60      # Probabilidade mínima para recomendar uma entrada

# Configurações de intervalo de atualização (em segundos)
UPDATE_INTERVAL = 300  # Intervalo para atualizar os dados das APIs (5 minutos para economizar créditos)
TELEGRAM_UPDATE_INTERVAL = 60  # Intervalo para enviar atualizações ao Telegram (1 minuto)

# Configurações de logs
LOG_FILE = "../logs/trader_esportivo.log"
LOG_LEVEL = "INFO"  # Níveis: DEBUG, INFO, WARNING, ERROR, CRITICAL

# Configurações de armazenamento de dados
DATA_DIR = "../data"
ODDS_DATA_FILE = f"{DATA_DIR}/odds_data.json"
MATCHES_DATA_FILE = f"{DATA_DIR}/matches_data.json"
OPPORTUNITIES_FILE = f"{DATA_DIR}/opportunities.json"
CACHE_FILE = f"{DATA_DIR}/api_cache.json"

# Configurações de cache para economizar créditos da API
CACHE_DURATION = 3600  # Duração do cache em segundos (1 hora)
MAX_DAILY_REQUESTS = 16  # Máximo de requisições diárias (500 créditos / 30 dias)

# Configurações para o método dos ciclos
CYCLE_SETTINGS = {
    "default": {
        "green_target": 0.05,  # 5% de lucro
        "max_red": 0.15,       # 15% de perda máxima
        "risk_reward_ratio": 3 # Proporção 1:3
    },
    "conservative": {
        "green_target": 0.03,  # 3% de lucro
        "max_red": 0.09,       # 9% de perda máxima
        "risk_reward_ratio": 3 # Proporção 1:3
    },
    "aggressive": {
        "green_target": 0.10,  # 10% de lucro
        "max_red": 0.30,       # 30% de perda máxima
        "risk_reward_ratio": 3 # Proporção 1:3
    },
    "custom": {
        "green_target": 0.05,  # Será configurado pelo usuário
        "max_red": 0.15,       # Será configurado pelo usuário
        "risk_reward_ratio": 3 # Será configurado pelo usuário
    }
}
