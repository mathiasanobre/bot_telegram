"""
Utilitários para o agente de trading esportivo.
Inclui funções para o método dos ciclos e cálculos de risco/retorno.
"""

import logging
import json
import os
import time
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple

# Configuração de logging
def setup_logger(log_file: str, log_level: str = "INFO") -> logging.Logger:
    """
    Configura o logger para o agente.
    
    Args:
        log_file: Caminho para o arquivo de log
        log_level: Nível de logging (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        
    Returns:
        Logger configurado
    """
    # Criar diretório de logs se não existir
    os.makedirs(os.path.dirname(log_file), exist_ok=True)
    
    # Configurar o logger
    logger = logging.getLogger("trader_esportivo")
    level = getattr(logging, log_level)
    logger.setLevel(level)
    
    # Handler para arquivo
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(level)
    
    # Handler para console
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    
    # Formato do log
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    
    # Adicionar handlers ao logger
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger

# Funções para manipulação de dados
def save_data(data: Any, file_path: str) -> None:
    """
    Salva dados em um arquivo JSON.
    
    Args:
        data: Dados a serem salvos
        file_path: Caminho para o arquivo
    """
    # Criar diretório se não existir
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def load_data(file_path: str) -> Any:
    """
    Carrega dados de um arquivo JSON.
    
    Args:
        file_path: Caminho para o arquivo
        
    Returns:
        Dados carregados ou None se o arquivo não existir
    """
    if not os.path.exists(file_path):
        return None
    
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)

# Funções para cálculos de trading
def decimal_to_probability(odds: float) -> float:
    """
    Converte odds decimais para probabilidade.
    
    Args:
        odds: Odds em formato decimal
        
    Returns:
        Probabilidade (0-1)
    """
    return 1 / odds if odds > 0 else 0

def calculate_lay_liability(stake: float, odds: float) -> float:
    """
    Calcula a responsabilidade (liability) para uma aposta Lay.
    
    Args:
        stake: Valor da aposta
        odds: Odds em formato decimal
        
    Returns:
        Valor da responsabilidade
    """
    return stake * (odds - 1)

def calculate_back_profit(stake: float, odds: float) -> float:
    """
    Calcula o lucro potencial para uma aposta Back.
    
    Args:
        stake: Valor da aposta
        odds: Odds em formato decimal
        
    Returns:
        Lucro potencial
    """
    return stake * (odds - 1)

def identify_arbitrage(back_odds: float, lay_odds: float) -> Tuple[bool, float]:
    """
    Identifica se existe oportunidade de arbitragem entre odds de Back e Lay.
    
    Args:
        back_odds: Odds de Back em formato decimal
        lay_odds: Odds de Lay em formato decimal
        
    Returns:
        Tupla com (existe_arbitragem, margem_percentual)
    """
    back_prob = decimal_to_probability(back_odds)
    lay_prob = decimal_to_probability(lay_odds)
    
    # Se a soma das probabilidades for menor que 1, existe arbitragem
    total_prob = back_prob + lay_prob
    
    if total_prob < 0.98:  # Considerando uma pequena margem de erro
        margin = (1 - total_prob) * 100  # Margem em percentual
        return True, margin
    
    return False, 0.0

def format_timestamp(timestamp: int) -> str:
    """
    Formata um timestamp Unix para data e hora legíveis.
    
    Args:
        timestamp: Timestamp Unix em segundos
        
    Returns:
        String formatada com data e hora
    """
    return datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')

# Funções para o método dos ciclos
def calculate_cycle_opportunity(
    odds: float, 
    is_back: bool, 
    green_target: float, 
    max_red: float, 
    risk_reward_ratio: int
) -> Dict[str, Any]:
    """
    Calcula se uma oportunidade atende aos critérios do método dos ciclos.
    
    Args:
        odds: Odds em formato decimal
        is_back: Se é uma operação de Back (True) ou Lay (False)
        green_target: Percentual de lucro alvo (0.05 = 5%)
        max_red: Percentual máximo de perda aceitável (0.15 = 15%)
        risk_reward_ratio: Proporção risco:retorno (3 = 1:3)
        
    Returns:
        Dicionário com informações da oportunidade
    """
    result = {
        "is_valid": False,
        "type": "BACK" if is_back else "LAY",
        "odds": odds,
        "green_percent": 0,
        "red_percent": 0,
        "stake": 100,  # Valor base para cálculos
        "green_value": 0,
        "red_value": 0,
        "risk_reward_ratio": 0
    }
    
    if is_back:
        # Para Back, o green é o lucro potencial
        result["green_percent"] = (odds - 1)
        result["green_value"] = calculate_back_profit(result["stake"], odds)
        result["red_percent"] = 1.0  # Perda total do stake
        result["red_value"] = result["stake"]
    else:
        # Para Lay, o green é o valor do stake
        result["green_percent"] = 1 / odds
        result["green_value"] = result["stake"]
        result["red_percent"] = (odds - 1) / odds
        result["red_value"] = calculate_lay_liability(result["stake"], odds)
    
    # Verificar se atende aos critérios do método dos ciclos
    actual_ratio = result["red_percent"] / result["green_percent"] if result["green_percent"] > 0 else float('inf')
    result["risk_reward_ratio"] = actual_ratio
    
    # Verificar se a oportunidade é válida para o método dos ciclos
    if is_back:
        # Para Back, queremos odds baixas (até 1.06 por padrão)
        result["is_valid"] = (
            result["green_percent"] >= green_target and 
            result["green_percent"] <= green_target * 1.5 and  # Não queremos green muito alto também
            actual_ratio <= risk_reward_ratio
        )
    else:
        # Para Lay, queremos odds altas (acima de 30 por padrão)
        result["is_valid"] = (
            result["green_percent"] >= green_target and
            result["red_percent"] <= max_red and
            actual_ratio <= risk_reward_ratio
        )
    
    return result

def adjust_stake_for_cycle(
    odds: float, 
    is_back: bool, 
    target_green_percent: float, 
    bankroll: float = 1000
) -> Dict[str, Any]:
    """
    Ajusta o valor do stake para atingir o percentual de green desejado.
    
    Args:
        odds: Odds em formato decimal
        is_back: Se é uma operação de Back (True) ou Lay (False)
        target_green_percent: Percentual de lucro alvo (0.05 = 5%)
        bankroll: Valor total disponível para apostas
        
    Returns:
        Dicionário com informações do stake ajustado
    """
    result = {
        "stake": 0,
        "green_value": 0,
        "red_value": 0,
        "green_percent": 0,
        "red_percent": 0
    }
    
    if is_back:
        # Para Back, calculamos o stake necessário para atingir o green alvo
        profit_multiplier = odds - 1
        if profit_multiplier > 0:
            result["stake"] = (target_green_percent * bankroll) / profit_multiplier
            result["green_value"] = result["stake"] * profit_multiplier
            result["red_value"] = result["stake"]
            result["green_percent"] = target_green_percent
            result["red_percent"] = result["stake"] / bankroll
    else:
        # Para Lay, calculamos o stake necessário para atingir o green alvo
        result["stake"] = target_green_percent * bankroll
        result["green_value"] = result["stake"]
        result["red_value"] = calculate_lay_liability(result["stake"], odds)
        result["green_percent"] = target_green_percent
        result["red_percent"] = result["red_value"] / bankroll
    
    return result

# Funções para cache e otimização de uso das APIs
def get_cached_data(cache_file: str, key: str, max_age_seconds: int) -> Optional[Any]:
    """
    Obtém dados do cache se estiverem dentro do período de validade.
    
    Args:
        cache_file: Caminho para o arquivo de cache
        key: Chave para os dados no cache
        max_age_seconds: Idade máxima dos dados em segundos
        
    Returns:
        Dados do cache ou None se não existirem ou estiverem expirados
    """
    cache = load_data(cache_file) or {}
    
    if key in cache:
        timestamp = cache[key].get("timestamp", 0)
        current_time = int(time.time())
        
        if current_time - timestamp <= max_age_seconds:
            return cache[key].get("data")
    
    return None

def save_to_cache(cache_file: str, key: str, data: Any) -> None:
    """
    Salva dados no cache.
    
    Args:
        cache_file: Caminho para o arquivo de cache
        key: Chave para os dados no cache
        data: Dados a serem salvos
    """
    cache = load_data(cache_file) or {}
    
    cache[key] = {
        "timestamp": int(time.time()),
        "data": data
    }
    
    save_data(cache, cache_file)

def should_make_api_request(cache_file: str, key: str, max_daily_requests: int) -> bool:
    """
    Verifica se deve fazer uma requisição à API com base no limite diário.
    
    Args:
        cache_file: Caminho para o arquivo de cache
        key: Chave para o contador de requisições
        max_daily_requests: Número máximo de requisições diárias
        
    Returns:
        True se deve fazer a requisição, False caso contrário
    """
    cache = load_data(cache_file) or {}
    
    # Obter contador de requisições
    request_counter = cache.get("request_counter", {})
    today = datetime.now().strftime("%Y-%m-%d")
    
    # Inicializar contador para hoje se não existir
    if today not in request_counter:
        request_counter[today] = 0
    
    # Verificar se atingiu o limite diário
    if request_counter[today] >= max_daily_requests:
        return False
    
    # Incrementar contador
    request_counter[today] += 1
    
    # Atualizar cache
    cache["request_counter"] = request_counter
    save_data(cache, cache_file)
    
    return True

# Funções para integração com Telegram
def send_telegram_message(bot_token: str, chat_id: str, message: str) -> bool:
    """
    Envia uma mensagem para um chat do Telegram.
    
    Args:
        bot_token: Token do bot do Telegram
        chat_id: ID do chat
        message: Mensagem a ser enviada
        
    Returns:
        True se a mensagem foi enviada com sucesso, False caso contrário
    """
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    
    data = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "HTML"
    }
    
    try:
        response = requests.post(url, data=data)
        response.raise_for_status()
        return True
    except Exception as e:
        logging.error(f"Erro ao enviar mensagem para o Telegram: {e}")
        return False

def get_telegram_updates(bot_token: str, offset: int = 0) -> List[Dict[str, Any]]:
    """
    Obtém atualizações do bot do Telegram.
    
    Args:
        bot_token: Token do bot do Telegram
        offset: ID da última atualização processada
        
    Returns:
        Lista de atualizações
    """
    url = f"https://api.telegram.org/bot{bot_token}/getUpdates"
    
    params = {
        "offset": offset,
        "timeout": 30
    }
    
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        return response.json().get("result", [])
    except Exception as e:
        logging.error(f"Erro ao obter atualizações do Telegram: {e}")
        return []

def format_opportunity_message(opportunity: Dict[str, Any]) -> str:
    """
    Formata uma oportunidade como mensagem para o Telegram.
    
    Args:
        opportunity: Dicionário com informações da oportunidade
        
    Returns:
        Mensagem formatada
    """
    recommendation = opportunity.get("recommendation", {})
    action = recommendation.get("action", "UNKNOWN")
    
    # Formatar horário de início
    commence_time = opportunity.get("commence_time", "")
    if commence_time:
        try:
            dt = datetime.fromisoformat(commence_time.replace('Z', '+00:00'))
            commence_time = dt.strftime("%d/%m/%Y %H:%M")
        except:
            pass
    
    # Criar mensagem
    message = f"🚨 <b>OPORTUNIDADE DE TRADING</b> 🚨\n\n"
    message += f"⚽ <b>Evento:</b> {opportunity.get('home_team')} vs {opportunity.get('away_team')}\n"
    message += f"🕒 <b>Horário:</b> {commence_time}\n"
    message += f"🏆 <b>Esporte:</b> {opportunity.get('sport')}\n\n"
    
    if action == "BACK":
        message += f"✅ <b>RECOMENDAÇÃO: BACK</b>\n"
        message += f"🎯 <b>Time:</b> {opportunity.get('team')}\n"
        message += f"📊 <b>Odds:</b> {opportunity.get('back', {}).get('price', 0):.2f} ({opportunity.get('back', {}).get('bookmaker', '')})\n"
    elif action == "LAY":
        message += f"❌ <b>RECOMENDAÇÃO: LAY</b>\n"
        message += f"🎯 <b>Time:</b> {opportunity.get('team')}\n"
        message += f"📊 <b>Odds:</b> {opportunity.get('lay', {}).get('price', 0):.2f} ({opportunity.get('lay', {}).get('bookmaker', '')})\n"
    elif action == "BACK_AND_LAY":
        message += f"⚖️ <b>RECOMENDAÇÃO: BACK & LAY</b>\n"
        message += f"🎯 <b>Time:</b> {opportunity.get('team')}\n"
        message += f"📊 <b>Back:</b> {opportunity.get('back', {}).get('price', 0):.2f} ({opportunity.get('back', {}).get('bookmaker', '')})\n"
        message += f"📊 <b>Lay:</b> {opportunity.get('lay', {}).get('price', 0):.2f} ({opportunity.get('lay', {}).get('bookmaker', '')})\n"
    
    message += f"\n💰 <b>Stake Recomendado:</b> {recommendation.get('stake_recommendation', 0):.2f}\n"
    message += f"📈 <b>Lucro Potencial:</b> {recommendation.get('potential_profit', 0):.2f}\n"
    message += f"📉 <b>Responsabilidade Máxima:</b> {recommendation.get('max_liability', 0):.2f}\n"
    message += f"🎲 <b>Confiança:</b> {recommendation.get('confidence', 0) * 100:.0f}%\n"
    message += f"📋 <b>Estratégia:</b> {recommendation.get('strategy', '')}\n"
    
    # Adicionar informações do método dos ciclos se disponíveis
    cycle_info = opportunity.get("cycle_info", {})
    if cycle_info:
        message += f"\n🔄 <b>MÉTODO DOS CICLOS</b>\n"
        message += f"📈 <b>Green Esperado:</b> {cycle_info.get('green_percent', 0) * 100:.2f}%\n"
        message += f"📉 <b>Red Máximo:</b> {cycle_info.get('red_percent', 0) * 100:.2f}%\n"
        message += f"⚖️ <b>Proporção Risco/Retorno:</b> 1:{cycle_info.get('risk_reward_ratio', 0):.1f}\n"
    
    message += f"\n🔗 <b>ID do Evento:</b> {opportunity.get('event_id', '')}"
    
    return message

def format_cycle_opportunity_message(opportunity: Dict[str, Any]) -> str:
    """
    Formata uma oportunidade do método dos ciclos como mensagem para o Telegram.
    
    Args:
        opportunity: Dicionário com informações da oportunidade
        
    Returns:
        Mensagem formatada
    """
    cycle_info = opportunity.get("cycle_info", {})
    
    # Formatar horário de início
    commence_time = opportunity.get("commence_time", "")
    if commence_time:
        try:
            dt = datetime.fromisoformat(commence_time.replace('Z', '+00:00'))
            commence_time = dt.strftime("%d/%m/%Y %H:%M")
        except:
            pass
    
    # Criar mensagem
    message = f"🔄 <b>MÉTODO DOS CICLOS - OPORTUNIDADE</b> 🔄\n\n"
    message += f"⚽ <b>Evento:</b> {opportunity.get('home_team')} vs {opportunity.get('aw
(Content truncated due to size limit. Use line ranges to read in chunks)