"""
Módulo para coleta de dados de APIs esportivas.
Implementa controle de captura para economizar créditos.
"""

import time
import requests
import json
import os
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta

from src.config import (
    ODDS_API_KEY, API_FUTEBOL_KEY,
    ODDS_API_BASE_URL, API_FUTEBOL_BASE_URL,
    ODDS_DATA_FILE, MATCHES_DATA_FILE,
    SPORTS_TO_MONITOR, ODDS_API_REGIONS, ODDS_API_MARKETS,
    UPDATE_INTERVAL, DATA_DIR,
    MAX_DAILY_REQUESTS
)
from src.utils import setup_logger, load_data, save_data

# Configurar logger
logger = setup_logger("../logs/data_collector.log")

class DataCollector:
    """Coletor de dados de APIs esportivas."""
    
    def __init__(self, telegram_bot=None):
        """
        Inicializa o coletor de dados.
        
        Args:
            telegram_bot: Instância do bot do Telegram para verificar estado da captura
        """
        self.odds_data = {}
        self.matches_data = {}
        self.last_request_time = 0
        self.daily_requests = 0
        self.last_request_reset = datetime.now().date()
        self.telegram_bot = telegram_bot
        
        # Criar diretório de dados se não existir
        os.makedirs(DATA_DIR, exist_ok=True)
        
        # Carregar contadores de requisições
        self._load_request_counters()
    
    def _load_request_counters(self) -> None:
        """Carrega contadores de requisições de arquivo."""
        counter_file = os.path.join(DATA_DIR, "api_counters.json")
        
        if os.path.exists(counter_file):
            try:
                with open(counter_file, 'r') as f:
                    data = json.load(f)
                    
                    # Verificar se é o mesmo dia
                    last_date = datetime.strptime(data.get('date', '2000-01-01'), '%Y-%m-%d').date()
                    today = datetime.now().date()
                    
                    if last_date == today:
                        self.daily_requests = data.get('daily_requests', 0)
                        self.last_request_reset = last_date
                    else:
                        # Novo dia, resetar contadores
                        self.daily_requests = 0
                        self.last_request_reset = today
                        
                    logger.info(f"Contadores de requisições carregados. Requisições hoje: {self.daily_requests}")
            except Exception as e:
                logger.error(f"Erro ao carregar contadores de requisições: {e}")
    
    def _save_request_counters(self) -> None:
        """Salva contadores de requisições em arquivo."""
        counter_file = os.path.join(DATA_DIR, "api_counters.json")
        
        try:
            data = {
                'date': self.last_request_reset.strftime('%Y-%m-%d'),
                'daily_requests': self.daily_requests
            }
            
            with open(counter_file, 'w') as f:
                json.dump(data, f, indent=4)
                
            logger.info(f"Contadores de requisições salvos. Requisições hoje: {self.daily_requests}")
        except Exception as e:
            logger.error(f"Erro ao salvar contadores de requisições: {e}")
    
    def _check_capture_active(self) -> bool:
        """
        Verifica se a captura de dados está ativa.
        
        Returns:
            True se a captura está ativa, False caso contrário
        """
        if self.telegram_bot:
            return self.telegram_bot.is_capture_active()
        
        # Se não houver bot do Telegram, verificar arquivo de configuração
        config_file = os.path.join(DATA_DIR, "telegram_config.json")
        
        if os.path.exists(config_file):
            try:
                with open(config_file, 'r') as f:
                    config = json.load(f)
                    return config.get('capture_active', False)
            except Exception as e:
                logger.error(f"Erro ao verificar estado da captura: {e}")
                return False
        
        # Por padrão, captura ativa
        return True
    
    def _check_rate_limit(self) -> bool:
        """
        Verifica se estamos dentro dos limites de requisições.
        
        Returns:
            True se podemos fazer mais requisições, False caso contrário
        """
        # Verificar se é um novo dia
        today = datetime.now().date()
        if today > self.last_request_reset:
            self.daily_requests = 0
            self.last_request_reset = today
            self._save_request_counters()
        
        # Verificar limite diário
        if self.daily_requests >= MAX_DAILY_REQUESTS:
            logger.warning(f"Limite diário de requisições atingido: {self.daily_requests}/{MAX_DAILY_REQUESTS}")
            return False
        
        # Verificar intervalo entre requisições
        current_time = time.time()
        time_since_last_request = current_time - self.last_request_time
        
        if time_since_last_request < UPDATE_INTERVAL:
            time_to_wait = UPDATE_INTERVAL - time_since_last_request
            logger.info(f"Aguardando {time_to_wait:.2f}s para respeitar intervalo entre requisições")
            time.sleep(time_to_wait)
        
        return True
    
    def _update_request_counters(self) -> None:
        """Atualiza contadores de requisições."""
        self.last_request_time = time.time()
        self.daily_requests += 1
        self._save_request_counters()
    
    def collect_odds_data(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        Coleta dados de odds da The Odds API.
        
        Returns:
            Dicionário com dados de odds por esporte
        """
        # Verificar se a captura está ativa
        if not self._check_capture_active():
            logger.info("Captura de dados inativa. Pulando coleta de odds.")
            return self.odds_data
        
        # Verificar se já temos dados recentes em cache
        if os.path.exists(ODDS_DATA_FILE):
            file_age = time.time() - os.path.getmtime(ODDS_DATA_FILE)
            
            # Se o arquivo tiver menos de 15 minutos, usar cache
            if file_age < 900:  # 15 minutos em segundos
                logger.info(f"Usando dados de odds em cache (idade: {file_age/60:.1f} minutos)")
                self.odds_data = load_data(ODDS_DATA_FILE) or {}
                return self.odds_data
        
        # Coletar dados para cada esporte
        for sport in SPORTS_TO_MONITOR:
            # Verificar limites de requisições
            if not self._check_rate_limit():
                break
            
            logger.info(f"Coletando dados de odds para {sport}")
            
            # Construir URL
            url = f"{ODDS_API_BASE_URL}/{sport}/odds?regions={','.join(ODDS_API_REGIONS)}&markets={','.join(ODDS_API_MARKETS)}&oddsFormat=decimal&apiKey={ODDS_API_KEY}"
            
            try:
                response = requests.get(url)
                self._update_request_counters()
                
                if response.status_code == 200:
                    data = response.json()
                    self.odds_data[sport] = data
                    logger.info(f"Dados de odds coletados para {sport}: {len(data)} eventos")
                else:
                    logger.error(f"Erro ao coletar dados de odds para {sport}: {response.status_code} - {response.text}")
            except Exception as e:
                logger.error(f"Erro ao coletar dados de odds para {sport}: {e}")
        
        # Salvar dados
        save_data(self.odds_data, ODDS_DATA_FILE)
        
        return self.odds_data
    
    def collect_matches_data(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        Coleta dados de partidas da API-Futebol.
        
        Returns:
            Dicionário com dados de partidas
        """
        # Verificar se a captura está ativa
        if not self._check_capture_active():
            logger.info("Captura de dados inativa. Pulando coleta de partidas.")
            return self.matches_data
        
        # Verificar se já temos dados recentes em cache
        if os.path.exists(MATCHES_DATA_FILE):
            file_age = time.time() - os.path.getmtime(MATCHES_DATA_FILE)
            
            # Se o arquivo tiver menos de 15 minutos, usar cache
            if file_age < 900:  # 15 minutos em segundos
                logger.info(f"Usando dados de partidas em cache (idade: {file_age/60:.1f} minutos)")
                self.matches_data = load_data(MATCHES_DATA_FILE) or {}
                return self.matches_data
        
        # Inicializar estrutura de dados
        self.matches_data = {
            'live_matches': [],
            'upcoming_matches': []
        }
        
        # Verificar limites de requisições
        if not self._check_rate_limit():
            return self.matches_data
        
        # Coletar partidas ao vivo
        logger.info("Coletando dados de partidas ao vivo")
        
        try:
            headers = {
                'Authorization': f'Bearer {API_FUTEBOL_KEY}'
            }
            
            # Partidas ao vivo
            live_url = f"{API_FUTEBOL_BASE_URL}/ao-vivo"
            live_response = requests.get(live_url, headers=headers)
            self._update_request_counters()
            
            if live_response.status_code == 200:
                live_data = live_response.json()
                self.matches_data['live_matches'] = live_data
                logger.info(f"Dados de partidas ao vivo coletados: {len(live_data)} partidas")
            else:
                logger.error(f"Erro ao coletar dados de partidas ao vivo: {live_response.status_code} - {live_response.text}")
            
            # Verificar limites de requisições
            if not self._check_rate_limit():
                return self.matches_data
            
            # Partidas do dia
            today = datetime.now().strftime('%Y-%m-%d')
            upcoming_url = f"{API_FUTEBOL_BASE_URL}/partidas/{today}"
            upcoming_response = requests.get(upcoming_url, headers=headers)
            self._update_request_counters()
            
            if upcoming_response.status_code == 200:
                upcoming_data = upcoming_response.json()
                self.matches_data['upcoming_matches'] = upcoming_data
                logger.info(f"Dados de partidas do dia coletados: {len(upcoming_data)} partidas")
            else:
                logger.error(f"Erro ao coletar dados de partidas do dia: {upcoming_response.status_code} - {upcoming_response.text}")
        except Exception as e:
            logger.error(f"Erro ao coletar dados de partidas: {e}")
        
        # Salvar dados
        save_data(self.matches_data, MATCHES_DATA_FILE)
        
        return self.matches_data
    
    def collect_all_data(self) -> Tuple[Dict[str, List[Dict[str, Any]]], Dict[str, List[Dict[str, Any]]]]:
        """
        Coleta todos os dados disponíveis.
        
        Returns:
            Tupla com dados de odds e dados de partidas
        """
        # Verificar se a captura está ativa
        if not self._check_capture_active():
            logger.info("Captura de dados inativa. Pulando coleta de dados.")
            return self.odds_data, self.matches_data
        
        logger.info("Iniciando coleta de todos os dados")
        
        # Coletar dados de odds
        odds_data = self.collect_odds_data()
        
        # Coletar dados de partidas
        matches_data = self.collect_matches_data()
        
        logger.info("Coleta de dados concluída")
        
        return odds_data, matches_data
    
    def get_remaining_credits(self) -> int:
        """
        Calcula créditos restantes da The Odds API.
        
        Returns:
            Número de créditos restantes
        """
        # Verificar se é um novo dia
        today = datetime.now().date()
        if today > self.last_request_reset:
            self.daily_requests = 0
            self.last_request_reset = today
            self._save_request_counters()
        
        # Calcular créditos restantes
        remaining = MAX_DAILY_REQUESTS - self.daily_requests
        
        return max(0, remaining)
    
    def run_collection_loop(self, interval: int = 900) -> None:
        """
        Executa o loop de coleta de dados.
        
        Args:
            interval: Intervalo entre coletas em segundos (padrão: 15 minutos)
        """
        logger.info(f"Iniciando loop de coleta de dados com intervalo de {interval} segundos")
        
        try:
            while True:
                # Verificar se a captura está ativa
                if self._check_capture_active():
                    logger.info(f"Coletando dados às {time.strftime('%H:%M:%S')}")
                    
                    # Coletar todos os dados
                    self.collect_all_data()
                    
                    # Calcular créditos restantes
                    remaining_credits = self.get_remaining_credits()
                    logger.info(f"Créditos restantes: {remaining_credits}/{MAX_DAILY_REQUESTS}")
                    
                    logger.info(f"Próxima coleta em {interval} segundos")
                else:
                    logger.info("Captura de dados inativa. Aguardando próximo ciclo.")
                
                # Aguardar próximo ciclo
                time.sleep(interval)
        except KeyboardInterrupt:
            logger.info("Loop de coleta interrompido pelo usuário")
        except Exception as e:
            logger.error(f"Erro no loop de coleta: {e}")


if __name__ == "__main__":
    collector = DataCollector()
    collector.run_collection_loop()
