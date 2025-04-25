"""
Script para testar o funcionamento do agente de trading esportivo.
"""

import os
import sys
import time
import json
import logging
from datetime import datetime

# Adicionar diretório src ao path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.config import (
    ODDS_API_KEY, API_FUTEBOL_KEY, TELEGRAM_BOT_TOKEN,
    ODDS_DATA_FILE, MATCHES_DATA_FILE, OPPORTUNITIES_FILE,
    CACHE_FILE
)
from src.utils import setup_logger, send_telegram_message
from src.data_collector import OddsAPIClient, APIFutebolClient, DataCollector
from src.analyzer import TradingAnalyzer
from src.agent import TradingAgent
from src.telegram_bot import TelegramBot

# Configurar logger
logger = setup_logger("logs/test.log")

def test_api_keys():
    """Testa se as chaves de API estão configuradas."""
    logger.info("Testando chaves de API...")
    
    if ODDS_API_KEY == "YOUR_API_KEY":
        logger.warning("Chave da The Odds API não configurada. Configure-a em src/config.py")
        return False
    
    if API_FUTEBOL_KEY == "YOUR_API_KEY":
        logger.warning("Chave da API-Futebol não configurada. Configure-a em src/config.py")
        return False
    
    if not TELEGRAM_BOT_TOKEN:
        logger.warning("Token do bot do Telegram não configurado. Configure-o em src/config.py")
        return False
    
    logger.info("Chaves de API configuradas corretamente")
    return True

def test_odds_api():
    """Testa a conexão com a The Odds API."""
    logger.info("Testando conexão com a The Odds API...")
    
    try:
        client = OddsAPIClient(ODDS_API_KEY, "https://api.the-odds-api.com/v4")
        sports = client.get_sports()
        
        if sports:
            logger.info(f"Conexão com The Odds API bem-sucedida. {len(sports)} esportes disponíveis.")
            logger.info(f"Requisições restantes: {client.remaining_requests}")
            return True
        else:
            logger.error("Falha ao obter dados da The Odds API")
            return False
    except Exception as e:
        logger.error(f"Erro ao conectar com The Odds API: {e}")
        return False

def test_api_futebol():
    """Testa a conexão com a API-Futebol."""
    logger.info("Testando conexão com a API-Futebol...")
    
    try:
        client = APIFutebolClient(API_FUTEBOL_KEY, "https://api.api-futebol.com.br/v1")
        matches = client.get_live_matches()
        
        if isinstance(matches, list):
            logger.info(f"Conexão com API-Futebol bem-sucedida. {len(matches)} partidas ao vivo.")
            return True
        else:
            logger.error("Falha ao obter dados da API-Futebol")
            return False
    except Exception as e:
        logger.error(f"Erro ao conectar com API-Futebol: {e}")
        return False

def test_telegram_bot():
    """Testa a conexão com o Telegram."""
    logger.info("Testando conexão com o Telegram...")
    
    try:
        bot = TelegramBot(TELEGRAM_BOT_TOKEN)
        
        # Tentar obter atualizações
        updates = bot.process_updates()
        
        # Enviar mensagem de teste se houver chat_id
        if bot.chat_id:
            success = send_telegram_message(
                TELEGRAM_BOT_TOKEN, 
                bot.chat_id, 
                "🧪 Teste do Agente de Trading Esportivo 🧪\n\nEsta é uma mensagem de teste para verificar a conexão com o Telegram."
            )
            
            if success:
                logger.info(f"Mensagem de teste enviada com sucesso para o chat {bot.chat_id}")
                return True
            else:
                logger.error("Falha ao enviar mensagem de teste")
                return False
        else:
            logger.warning("Chat ID não definido. Envie uma mensagem para o bot para definir o chat_id.")
            return None
    except Exception as e:
        logger.error(f"Erro ao testar bot do Telegram: {e}")
        return False

def test_data_collector():
    """Testa o coletor de dados."""
    logger.info("Testando coletor de dados...")
    
    try:
        collector = DataCollector()
        
        # Testar coleta de odds
        odds_data = collector.collect_odds_data()
        if odds_data:
            logger.info(f"Coleta de odds bem-sucedida. Dados coletados para {len(odds_data)} esportes.")
        else:
            logger.warning("Nenhum dado de odds coletado")
        
        # Testar coleta de partidas ao vivo
        matches_data = collector.collect_live_matches()
        if matches_data:
            logger.info(f"Coleta de partidas ao vivo bem-sucedida.")
        else:
            logger.warning("Nenhum dado de partidas ao vivo coletado")
        
        # Verificar se os arquivos foram criados
        if os.path.exists(ODDS_DATA_FILE):
            logger.info(f"Arquivo de odds criado: {ODDS_DATA_FILE}")
        else:
            logger.warning(f"Arquivo de odds não criado: {ODDS_DATA_FILE}")
        
        if os.path.exists(MATCHES_DATA_FILE):
            logger.info(f"Arquivo de partidas criado: {MATCHES_DATA_FILE}")
        else:
            logger.warning(f"Arquivo de partidas não criado: {MATCHES_DATA_FILE}")
        
        # Verificar cache
        if os.path.exists(CACHE_FILE):
            logger.info(f"Arquivo de cache criado: {CACHE_FILE}")
        else:
            logger.warning(f"Arquivo de cache não criado: {CACHE_FILE}")
        
        return True
    except Exception as e:
        logger.error(f"Erro ao testar coletor de dados: {e}")
        return False

def test_analyzer():
    """Testa o analisador de oportunidades."""
    logger.info("Testando analisador de oportunidades...")
    
    try:
        analyzer = TradingAnalyzer()
        
        # Testar análise de oportunidades
        opportunities = analyzer.analyze_back_lay_opportunities()
        
        if opportunities is not None:
            logger.info(f"Análise de oportunidades bem-sucedida. {len(opportunities)} oportunidades encontradas.")
        else:
            logger.warning("Nenhuma oportunidade encontrada")
        
        # Verificar se o arquivo de oportunidades foi criado
        if os.path.exists(OPPORTUNITIES_FILE):
            logger.info(f"Arquivo de oportunidades criado: {OPPORTUNITIES_FILE}")
        else:
            logger.warning(f"Arquivo de oportunidades não criado: {OPPORTUNITIES_FILE}")
        
        # Testar método dos ciclos
        cycle_opps = analyzer.get_cycle_opportunities()
        logger.info(f"Oportunidades para o método dos ciclos: {len(cycle_opps)}")
        
        # Testar diferentes perfis
        for profile in ["default", "conservative", "aggressive"]:
            analyzer.set_cycle_profile(profile)
            logger.info(f"Perfil do método dos ciclos definido para: {profile}")
        
        # Testar configurações personalizadas
        analyzer.set_custom_cycle_settings(0.04, 0.12, 3)
        analyzer.set_cycle_profile("custom")
        logger.info("Configurações personalizadas definidas e aplicadas")
        
        return True
    except Exception as e:
        logger.error(f"Erro ao testar analisador: {e}")
        return False

def test_agent():
    """Testa o agente completo."""
    logger.info("Testando agente completo...")
    
    try:
        agent = TradingAgent()
        
        # Iniciar o agente
        agent.start()
        logger.info("Agente iniciado com sucesso")
        
        # Aguardar alguns segundos para coleta e análise
        logger.info("Aguardando 30 segundos para coleta e análise de dados...")
        time.sleep(30)
        
        # Verificar status
        status = agent.get_status()
        logger.info(f"Status do agente: {status}")
        
        # Verificar oportunidades
        opportunities = agent.get_opportunities()
        logger.info(f"Oportunidades encontradas: {len(opportunities)}")
        
        # Verificar oportunidades para o método dos ciclos
        cycle_opps = agent.get_opportunities(cycle_only=True)
        logger.info(f"Oportunidades para o método dos ciclos: {len(cycle_opps)}")
        
        # Parar o agente
        agent.stop()
        logger.info("Agente parado com sucesso")
        
        return True
    except Exception as e:
        logger.error(f"Erro ao testar agente: {e}")
        return False

def run_all_tests():
    """Executa todos os testes."""
    logger.info("Iniciando testes do agente de trading esportivo...")
    
    tests = [
        ("Verificação de chaves de API", test_api_keys),
        ("Conexão com The Odds API", test_odds_api),
        ("Conexão com API-Futebol", test_api_futebol),
        ("Conexão com Telegram", test_telegram_bot),
        ("Coletor de dados", test_data_collector),
        ("Analisador de oportunidades", test_analyzer),
        ("Agente completo", test_agent)
    ]
    
    results = []
    
    for name, test_func in tests:
        logger.info(f"\n{'='*50}\nExecutando teste: {name}\n{'='*50}")
        try:
            start_time = time.time()
            success = test_func()
            end_time = time.time()
            
            duration = end_time - start_time
            
            if success is None:
                status = "PENDENTE"
            else:
                status = "PASSOU" if success else "FALHOU"
            
            logger.info(f"Teste '{name}' {status} em {duration:.2f} segundos")
            
            results.append({
                "name": name,
                "status": status,
                "duration": duration
            })
        except Exception as e:
            logger.error(f"Erro ao executar teste '{name}': {e}")
            results.append({
                "name": name,
                "status": "ERRO",
                "duration": 0,
                "error": str(e)
            })
    
    # Exibir resumo
    logger.info("\n\n" + "="*50)
    logger.info("RESUMO DOS TESTES")
    logger.info("="*50)
    
    passed = sum(1 for r in results if r["status"] == "PASSOU")
    failed = sum(1 for r in results if r["status"] == "FALHOU")
    pending = sum(1 for r in results if r["status"] == "PENDENTE")
    errors = sum(1 for r in results if r["status"] == "ERRO")
    
    for result in results:
        status_str = result["status"]
        if status_str == "PASSOU":
            status_str = f"\033[92m{status_str}\033[0m"  # Verde
        elif status_str == "FALHOU":
            status_str = f"\033[93m{status_str}\033[0m"  # Amarelo
        elif status_str == "PENDENTE":
            status_str = f"\033[94m{status_str}\033[0m"  # Azul
        else:
            status_str = f"\033[91m{status_str}\033[0m"  # Vermelho
        
        logger.info(f"{result['name']}: {status_str} ({result['duration']:.2f}s)")
    
    logger.info(f"\nTotal: {len(results)}, Passou: {passed}, Falhou: {failed}, Pendente: {pending}, Erros: {errors}")
    
    return passed, failed, pending, errors

if __name__ == "__main__":
    # Criar diretórios necessários
    os.makedirs("logs", exist_ok=True)
    os.makedirs("data", exist_ok=True)
    
    # Executar todos os testes
    passed, failed, pending, errors = run_all_tests()
    
    # Definir código de saída
    if errors > 0 or failed > 0:
        sys.exit(1)
    else:
        sys.exit(0)
