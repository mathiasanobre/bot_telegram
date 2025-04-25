"""
Interface principal do agente de trading esportivo.
Integra coleta de dados, análise e notificações Telegram.
"""

import logging
import time
import threading
import os
import json
from typing import Dict, List, Any, Optional
from datetime import datetime

from config import (
    UPDATE_INTERVAL, OPPORTUNITIES_FILE,
    LOG_FILE, LOG_LEVEL, TELEGRAM_BOT_TOKEN,
    TELEGRAM_UPDATE_INTERVAL
)
from utils import setup_logger, load_data
from data_collector import DataCollector
from analyzer import TradingAnalyzer
from telegram_bot import TelegramBot

# Configurar logger
logger = setup_logger(LOG_FILE, LOG_LEVEL)

class TradingAgent:
    """Agente de trading esportivo."""
    
    def __init__(self):
        """Inicializa o agente de trading."""
        self.collector = DataCollector()
        self.analyzer = TradingAnalyzer()
        self.telegram_bot = TelegramBot(TELEGRAM_BOT_TOKEN)
        self.running = False
        self.collector_thread = None
        self.analyzer_thread = None
        self.telegram_thread = None
        
        # Carregar configurações personalizadas se existirem
        self._load_custom_cycle_config()
        
    def _load_custom_cycle_config(self) -> None:
        """Carrega configurações personalizadas para o método dos ciclos."""
        config_file = "../data/custom_cycle_config.json"
        if os.path.exists(config_file):
            try:
                with open(config_file, 'r') as f:
                    config = json.load(f)
                    
                    green_target = config.get('green_target')
                    max_red = config.get('max_red')
                    risk_reward_ratio = config.get('risk_reward_ratio')
                    
                    if green_target and max_red and risk_reward_ratio:
                        self.analyzer.set_custom_cycle_settings(
                            green_target, max_red, risk_reward_ratio
                        )
                        self.analyzer.set_cycle_profile("custom")
                        logger.info(f"Configurações personalizadas carregadas: green={green_target}, red={max_red}, ratio={risk_reward_ratio}")
            except Exception as e:
                logger.error(f"Erro ao carregar configurações personalizadas: {e}")
        
    def start(self) -> None:
        """Inicia o agente de trading."""
        if self.running:
            logger.warning("O agente já está em execução")
            return
        
        self.running = True
        
        # Iniciar thread de coleta de dados
        self.collector_thread = threading.Thread(
            target=self._run_collector,
            daemon=True
        )
        self.collector_thread.start()
        
        # Iniciar thread de análise
        self.analyzer_thread = threading.Thread(
            target=self._run_analyzer,
            daemon=True
        )
        self.analyzer_thread.start()
        
        # Iniciar thread do Telegram
        self.telegram_thread = threading.Thread(
            target=self._run_telegram_bot,
            daemon=True
        )
        self.telegram_thread.start()
        
        logger.info("Agente de trading iniciado")
        
    def stop(self) -> None:
        """Para o agente de trading."""
        if not self.running:
            logger.warning("O agente não está em execução")
            return
        
        self.running = False
        logger.info("Agente de trading parado")
        
    def _run_collector(self) -> None:
        """Executa o coletor de dados em um loop."""
        while self.running:
            try:
                # Coletar dados
                self.collector.collect_odds_data()
                self.collector.collect_live_matches()
                
                # Aguardar próximo ciclo
                for _ in range(UPDATE_INTERVAL):
                    if not self.running:
                        break
                    time.sleep(1)
            except Exception as e:
                logger.error(f"Erro no coletor de dados: {e}")
                time.sleep(10)  # Esperar um pouco antes de tentar novamente
    
    def _run_analyzer(self) -> None:
        """Executa o analisador em um loop."""
        # Esperar um pouco para que o coletor tenha tempo de obter dados
        time.sleep(10)
        
        while self.running:
            try:
                # Recarregar dados
                self.analyzer.reload_data()
                
                # Analisar oportunidades
                opportunities = self.analyzer.analyze_back_lay_opportunities()
                
                # Verificar se há configurações personalizadas novas
                self._load_custom_cycle_config()
                
                # Aguardar próximo ciclo
                for _ in range(UPDATE_INTERVAL // 2):  # Analisar com mais frequência
                    if not self.running:
                        break
                    time.sleep(1)
            except Exception as e:
                logger.error(f"Erro no analisador: {e}")
                time.sleep(10)  # Esperar um pouco antes de tentar novamente
    
    def _run_telegram_bot(self) -> None:
        """Executa o bot do Telegram em um loop."""
        # Esperar um pouco para que o analisador tenha tempo de processar dados
        time.sleep(20)
        
        while self.running:
            try:
                # Processar atualizações do Telegram
                self.telegram_bot.process_updates()
                
                # Verificar novas oportunidades
                if self.telegram_bot.chat_id:
                    self.telegram_bot.check_new_opportunities()
                
                # Aguardar próximo ciclo
                for _ in range(TELEGRAM_UPDATE_INTERVAL):
                    if not self.running:
                        break
                    time.sleep(1)
            except Exception as e:
                logger.error(f"Erro no bot do Telegram: {e}")
                time.sleep(10)  # Esperar um pouco antes de tentar novamente
    
    def get_opportunities(self, active_only: bool = True, cycle_only: bool = False) -> List[Dict[str, Any]]:
        """
        Obtém as oportunidades de trading identificadas.
        
        Args:
            active_only: Se True, retorna apenas oportunidades ativas
            cycle_only: Se True, retorna apenas oportunidades para o método dos ciclos
            
        Returns:
            Lista de oportunidades
        """
        if cycle_only:
            if active_only:
                return self.analyzer.get_active_opportunities(cycle_only=True)
            else:
                return self.analyzer.get_cycle_opportunities()
        else:
            if active_only:
                return self.analyzer.get_active_opportunities()
            else:
                return self.analyzer.opportunities
    
    def get_opportunity_by_id(self, event_id: str) -> Optional[Dict[str, Any]]:
        """
        Obtém uma oportunidade específica pelo ID do evento.
        
        Args:
            event_id: ID do evento
            
        Returns:
            Oportunidade ou None se não encontrada
        """
        for opp in self.analyzer.opportunities:
            if opp.get('event_id') == event_id:
                return opp
        return None
    
    def get_status(self) -> Dict[str, Any]:
        """
        Obtém o status atual do agente.
        
        Returns:
            Status do agente
        """
        cycle_opps = self.get_opportunities(active_only=True, cycle_only=True)
        
        return {
            "running": self.running,
            "collector_running": self.collector_thread is not None and self.collector_thread.is_alive(),
            "analyzer_running": self.analyzer_thread is not None and self.analyzer_thread.is_alive(),
            "telegram_running": self.telegram_thread is not None and self.telegram_thread.is_alive(),
            "telegram_chat_id": self.telegram_bot.chat_id,
            "opportunities_count": len(self.analyzer.opportunities),
            "active_opportunities_count": len(self.analyzer.get_active_opportunities()),
            "cycle_opportunities_count": len(cycle_opps),
            "cycle_profile": self.analyzer.cycle_profile,
            "last_update": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }


if __name__ == "__main__":
    agent = TradingAgent()
    
    try:
        agent.start()
        
        # Manter o programa em execução
        while True:
            status = agent.get_status()
            print(f"Status do agente: {json.dumps(status, indent=2)}")
            
            # Exibir oportunidades ativas para o método dos ciclos
            cycle_opportunities = agent.get_opportunities(active_only=True, cycle_only=True)
            print(f"Oportunidades ativas para o método dos ciclos: {len(cycle_opportunities)}")
            
            for i, opp in enumerate(cycle_opportunities[:3]):  # Mostrar apenas as 3 primeiras
                cycle_info = opp.get('cycle_info', {})
                print(f"\nOportunidade {i+1} (Método dos Ciclos):")
                print(f"  Evento: {opp.get('home_team')} vs {opp.get('away_team')}")
                print(f"  Time: {opp.get('team')}")
                print(f"  Tipo: {cycle_info.get('type')}")
                print(f"  Odds: {cycle_info.get('odds'):.2f}")
                print(f"  Green: {cycle_info.get('green_percent', 0) * 100:.2f}%")
                print(f"  Red: {cycle_info.get('red_percent', 0) * 100:.2f}%")
                print(f"  Proporção: 1:{cycle_info.get('risk_reward_ratio', 0):.1f}")
            
            time.sleep(60)  # Atualizar a cada minuto
            
    except KeyboardInterrupt:
        print("\nEncerrando o agente...")
        agent.stop()
        print("Agente encerrado.")
