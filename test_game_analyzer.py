"""
Script para testar a funcionalidade de análise de jogos específicos.
"""

import os
import sys
import time
import json
import logging
from datetime import datetime

# Adicionar diretório src ao path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.utils import setup_logger, send_telegram_message
from src.game_analyzer import GameAnalyzer
from src.telegram_bot import TelegramBot
from src.config import TELEGRAM_BOT_TOKEN, OPPORTUNITIES_FILE

# Configurar logger
logger = setup_logger("logs/test_game_analyzer.log")

def test_game_search():
    """Testa a funcionalidade de busca de jogos por nome."""
    logger.info("Testando busca de jogos por nome...")
    
    try:
        analyzer = GameAnalyzer()
        
        # Testar diferentes termos de busca
        search_terms = [
            ["Barcelona"],
            ["Real", "Madrid"],
            ["Liverpool", "Manchester"],
            ["Bayern", "Munich"]
        ]
        
        for terms in search_terms:
            logger.info(f"Buscando jogos com termos: {terms}")
            results = analyzer.find_games_by_team_names(terms)
            
            if results:
                logger.info(f"Encontrados {len(results)} jogos para os termos {terms}")
                for i, game in enumerate(results[:3]):  # Mostrar apenas os 3 primeiros
                    logger.info(f"  {i+1}. {game.get('home_team')} vs {game.get('away_team')}")
            else:
                logger.info(f"Nenhum jogo encontrado para os termos {terms}")
        
        return True
    except Exception as e:
        logger.error(f"Erro ao testar busca de jogos: {e}")
        return False

def test_game_analysis():
    """Testa a funcionalidade de análise de jogos específicos."""
    logger.info("Testando análise de jogos específicos...")
    
    try:
        analyzer = GameAnalyzer()
        
        # Carregar oportunidades para obter um ID de evento válido
        opportunities = analyzer.opportunities
        
        if not opportunities:
            logger.warning("Nenhuma oportunidade disponível para teste")
            return None
        
        # Selecionar o primeiro evento para análise
        event = opportunities[0]
        event_id = event.get('event_id')
        
        if not event_id:
            logger.warning("Evento sem ID válido")
            return None
        
        logger.info(f"Analisando evento com ID: {event_id}")
        analysis = analyzer.analyze_specific_game(event_id)
        
        if "error" in analysis:
            logger.error(f"Erro na análise: {analysis['error']}")
            return False
        
        # Verificar se a análise contém as informações esperadas
        required_fields = ["event_id", "home_team", "away_team", "back", "lay", "recommendation", "cycle_method"]
        for field in required_fields:
            if field not in analysis:
                logger.error(f"Campo obrigatório ausente na análise: {field}")
                return False
        
        logger.info(f"Análise bem-sucedida para {analysis['home_team']} vs {analysis['away_team']}")
        
        # Verificar análise do método dos ciclos
        cycle_method = analysis.get('cycle_method', {})
        if cycle_method.get('is_applicable'):
            logger.info(f"Método dos ciclos aplicável: {cycle_method.get('type')} com odds {cycle_method.get('odds')}")
            
            # Verificar cenários de stake
            scenarios = cycle_method.get('analysis', {}).get('scenarios', [])
            if scenarios:
                logger.info(f"Cenários de stake calculados: {len(scenarios)}")
                for scenario in scenarios[:2]:  # Mostrar apenas os 2 primeiros
                    logger.info(f"  Stake: {scenario.get('stake')}, Green: {scenario.get('green_percent')}%, Red: {scenario.get('red_percent')}%")
        else:
            logger.info("Método dos ciclos não aplicável para este evento")
        
        return True
    except Exception as e:
        logger.error(f"Erro ao testar análise de jogos: {e}")
        return False

def test_telegram_game_commands():
    """Testa os comandos de jogo no Telegram."""
    logger.info("Testando comandos de jogo no Telegram...")
    
    try:
        bot = TelegramBot(TELEGRAM_BOT_TOKEN)
        
        # Verificar se há chat_id configurado
        if not bot.chat_id:
            logger.warning("Chat ID não definido. Envie uma mensagem para o bot para definir o chat_id.")
            return None
        
        # Simular processamento de comandos
        commands = [
            "/jogo Barcelona Real",
            "/analisar event_12345"  # ID fictício, provavelmente não existirá
        ]
        
        for command in commands:
            logger.info(f"Simulando comando: {command}")
            
            if command.startswith('/jogo'):
                bot._process_game_search_command(bot.chat_id, command)
            elif command.startswith('/analisar'):
                bot._process_analyze_event_command(bot.chat_id, command)
        
        # Enviar mensagem de teste
        test_msg = (
            "🧪 *Teste de Comandos de Jogo* 🧪\n\n"
            "Os comandos de busca e análise de jogos foram implementados com sucesso!\n\n"
            "Você pode usar:\n"
            "- `/jogo Barcelona Real` para buscar jogos com esses termos\n"
            "- `/analisar event_ID` para analisar um jogo específico\n\n"
            "Experimente esses comandos para encontrar e analisar jogos específicos."
        )
        
        success = send_telegram_message(TELEGRAM_BOT_TOKEN, bot.chat_id, test_msg)
        
        if success:
            logger.info("Mensagem de teste enviada com sucesso")
            return True
        else:
            logger.error("Falha ao enviar mensagem de teste")
            return False
    except Exception as e:
        logger.error(f"Erro ao testar comandos de jogo no Telegram: {e}")
        return False

def run_all_tests():
    """Executa todos os testes."""
    logger.info("Iniciando testes da funcionalidade de análise de jogos específicos...")
    
    tests = [
        ("Busca de jogos por nome", test_game_search),
        ("Análise de jogos específicos", test_game_analysis),
        ("Comandos de jogo no Telegram", test_telegram_game_commands)
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
