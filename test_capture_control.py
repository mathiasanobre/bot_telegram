"""
Script para testar as funcionalidades de controle de captura e download de dados.
"""

import os
import sys
import time
import json
import logging
from datetime import datetime

# Adicionar diretório src ao path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.utils import setup_logger
from src.telegram_bot import TelegramBot
from src.data_collector import DataCollector
from src.file_manager import FileManager
from src.file_sharing import FileSharing
from src.config import TELEGRAM_BOT_TOKEN, DATA_DIR

# Configurar logger
logger = setup_logger("logs/test_capture_control.log")

def test_capture_control():
    """Testa a funcionalidade de controle de captura."""
    logger.info("Testando controle de captura...")
    
    try:
        # Criar instância do bot do Telegram
        bot = TelegramBot(TELEGRAM_BOT_TOKEN)
        
        # Verificar estado inicial da captura
        initial_state = bot.is_capture_active()
        logger.info(f"Estado inicial da captura: {'ATIVO' if initial_state else 'INATIVO'}")
        
        # Alternar estado da captura
        if initial_state:
            bot.capture_active = False
            logger.info("Captura desativada para teste")
        else:
            bot.capture_active = True
            logger.info("Captura ativada para teste")
        
        # Salvar configuração
        bot._save_config()
        
        # Criar instância do coletor de dados
        collector = DataCollector(bot)
        
        # Verificar se o coletor respeita o estado da captura
        capture_check = collector._check_capture_active()
        logger.info(f"Coletor reconhece estado da captura: {'SIM' if capture_check == bot.capture_active else 'NÃO'}")
        
        # Tentar coletar dados
        logger.info("Tentando coletar dados...")
        odds_data, matches_data = collector.collect_all_data()
        
        # Verificar se os dados foram coletados de acordo com o estado da captura
        if bot.capture_active:
            logger.info(f"Dados coletados: odds={bool(odds_data)}, matches={bool(matches_data)}")
        else:
            logger.info(f"Dados não coletados (esperado): odds={bool(odds_data)}, matches={bool(matches_data)}")
        
        # Restaurar estado original
        bot.capture_active = initial_state
        bot._save_config()
        logger.info(f"Estado da captura restaurado para: {'ATIVO' if initial_state else 'INATIVO'}")
        
        return True
    except Exception as e:
        logger.error(f"Erro ao testar controle de captura: {e}")
        return False

def test_file_compression():
    """Testa a funcionalidade de compactação de arquivos."""
    logger.info("Testando compactação de arquivos...")
    
    try:
        # Criar instância do gerenciador de arquivos
        file_manager = FileManager()
        
        # Verificar se o diretório de dados existe
        if not os.path.exists(DATA_DIR):
            os.makedirs(DATA_DIR, exist_ok=True)
            logger.info(f"Diretório de dados criado: {DATA_DIR}")
        
        # Criar alguns arquivos de teste se o diretório estiver vazio
        if not os.listdir(DATA_DIR):
            logger.info("Criando arquivos de teste...")
            
            # Criar arquivo de teste
            test_file = os.path.join(DATA_DIR, "test_data.json")
            with open(test_file, 'w') as f:
                json.dump({
                    "test": True,
                    "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    "data": [1, 2, 3, 4, 5]
                }, f, indent=4)
            
            logger.info(f"Arquivo de teste criado: {test_file}")
        
        # Compactar dados
        logger.info("Compactando dados...")
        zip_path = file_manager.compress_data(include_logs=True)
        
        if zip_path:
            logger.info(f"Dados compactados com sucesso: {zip_path}")
            
            # Verificar se o arquivo zip existe
            if os.path.exists(zip_path):
                file_size_mb = os.path.getsize(zip_path) / (1024 * 1024)
                logger.info(f"Tamanho do arquivo zip: {file_size_mb:.2f}MB")
                
                # Verificar conteúdo do arquivo zip
                import zipfile
                with zipfile.ZipFile(zip_path, 'r') as zipf:
                    file_list = zipf.namelist()
                    logger.info(f"Arquivos no zip: {len(file_list)}")
                    for file in file_list[:5]:  # Mostrar apenas os 5 primeiros
                        logger.info(f"- {file}")
                
                return True
            else:
                logger.error(f"Arquivo zip não encontrado: {zip_path}")
                return False
        else:
            logger.error("Falha ao compactar dados")
            return False
    except Exception as e:
        logger.error(f"Erro ao testar compactação de arquivos: {e}")
        return False

def test_file_sharing():
    """Testa a funcionalidade de compartilhamento de arquivos."""
    logger.info("Testando compartilhamento de arquivos...")
    
    try:
        # Criar instância do gerenciador de arquivos
        file_manager = FileManager()
        
        # Criar instância do compartilhador de arquivos
        file_sharing = FileSharing(file_manager)
        
        # Registrar um link de teste
        logger.info("Registrando link de teste...")
        
        # Criar arquivo de teste se não existir
        test_file = os.path.join(DATA_DIR, "test_data.json")
        if not os.path.exists(test_file):
            with open(test_file, 'w') as f:
                json.dump({
                    "test": True,
                    "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    "data": [1, 2, 3, 4, 5]
                }, f, indent=4)
        
        # Registrar link
        file_sharing._register_shared_link("test", test_file, "Teste de compartilhamento")
        
        # Obter links compartilhados
        links = file_sharing.get_shared_links()
        
        if links:
            logger.info(f"Links compartilhados: {len(links)}")
            
            # Mostrar links
            for link in links[:3]:  # Mostrar apenas os 3 primeiros
                logger.info(f"- {link.get('method')}: {link.get('file_name')} ({link.get('file_size', 0):.2f}MB) - {link.get('timestamp')}")
            
            # Limpar links antigos
            removed = file_sharing.clean_old_shared_links(max_age_days=30)  # Usar 30 dias para não remover o link de teste
            logger.info(f"Links antigos removidos: {removed}")
            
            return True
        else:
            logger.error("Nenhum link compartilhado encontrado")
            return False
    except Exception as e:
        logger.error(f"Erro ao testar compartilhamento de arquivos: {e}")
        return False

def test_telegram_commands():
    """Testa os comandos do Telegram para controle de captura e download."""
    logger.info("Testando comandos do Telegram...")
    
    try:
        # Criar instância do bot do Telegram
        bot = TelegramBot(TELEGRAM_BOT_TOKEN)
        
        # Verificar se há chat_id configurado
        if not bot.chat_id:
            logger.warning("Chat ID não definido. Envie uma mensagem para o bot para definir o chat_id.")
            return None
        
        # Simular processamento de comandos
        commands = [
            "/iniciar_captura",
            "/parar_captura",
            "/download_dados"
        ]
        
        for command in commands:
            logger.info(f"Simulando comando: {command}")
            
            if command == "/iniciar_captura":
                bot._start_capture(bot.chat_id)
            elif command == "/parar_captura":
                bot._stop_capture(bot.chat_id)
            elif command == "/download_dados":
                bot._compress_and_send_data(bot.chat_id)
        
        # Verificar estado final da captura
        final_state = bot.is_capture_active()
        logger.info(f"Estado final da captura: {'ATIVO' if final_state else 'INATIVO'}")
        
        return True
    except Exception as e:
        logger.error(f"Erro ao testar comandos do Telegram: {e}")
        return False

def run_all_tests():
    """Executa todos os testes."""
    logger.info("Iniciando testes de controle de captura e download de dados...")
    
    tests = [
        ("Controle de captura", test_capture_control),
        ("Compactação de arquivos", test_file_compression),
        ("Compartilhamento de arquivos", test_file_sharing),
        ("Comandos do Telegram", test_telegram_commands)
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
