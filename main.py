"""
Script principal para iniciar o agente de trading esportivo.
"""

import os
import sys
import argparse
import time
import logging
from threading import Thread

# Adicionar diretório src ao path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.agent import TradingAgent
from src.utils import setup_logger

# Configurar logger
logger = setup_logger("logs/main.log")

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Agente de Trading Esportivo')
    parser.add_argument('--no-telegram', action='store_true', help='Executar sem notificações do Telegram')
    parser.add_argument('--cycle-profile', type=str, default='default', 
                        choices=['default', 'conservative', 'aggressive', 'custom'],
                        help='Perfil para o método dos ciclos')
    parser.add_argument('--green', type=float, help='Percentual de green alvo (0.05 = 5%%)')
    parser.add_argument('--red', type=float, help='Percentual de red máximo (0.15 = 15%%)')
    parser.add_argument('--ratio', type=int, help='Proporção risco:retorno (3 = 1:3)')
    return parser.parse_args()

def run_agent(args):
    """Executa o agente de trading."""
    logger.info("Iniciando agente de trading esportivo")
    
    # Criar diretórios necessários
    os.makedirs("logs", exist_ok=True)
    os.makedirs("data", exist_ok=True)
    
    # Inicializar agente
    agent = TradingAgent()
    
    # Configurar perfil do método dos ciclos
    if args.cycle_profile:
        agent.analyzer.set_cycle_profile(args.cycle_profile)
    
    # Configurar parâmetros personalizados
    if args.green and args.red and args.ratio:
        agent.analyzer.set_custom_cycle_settings(args.green, args.red, args.ratio)
        agent.analyzer.set_cycle_profile("custom")
    
    try:
        # Iniciar agente
        agent.start()
        
        # Manter o programa em execução
        while True:
            status = agent.get_status()
            logger.info(f"Status do agente: Executando={status['running']}, Oportunidades ativas={status['active_opportunities_count']}")
            
            # Exibir oportunidades para o método dos ciclos
            cycle_opps = agent.get_opportunities(active_only=True, cycle_only=True)
            if cycle_opps:
                logger.info(f"Oportunidades para o método dos ciclos: {len(cycle_opps)}")
                
                for i, opp in enumerate(cycle_opps[:3]):
                    cycle_info = opp.get('cycle_info', {})
                    logger.info(f"Oportunidade {i+1}: {opp.get('home_team')} vs {opp.get('away_team')}, "
                               f"{cycle_info.get('type')} {opp.get('team')} @ {cycle_info.get('odds'):.2f}, "
                               f"Green={cycle_info.get('green_percent', 0)*100:.2f}%, "
                               f"Red={cycle_info.get('red_percent', 0)*100:.2f}%")
            
            time.sleep(60)  # Atualizar a cada minuto
            
    except KeyboardInterrupt:
        logger.info("Encerrando o agente...")
        agent.stop()
        logger.info("Agente encerrado.")
    except Exception as e:
        logger.error(f"Erro ao executar o agente: {e}")
        agent.stop()
        sys.exit(1)

if __name__ == "__main__":
    # Analisar argumentos
    args = parse_args()
    
    # Executar agente
    run_agent(args)
