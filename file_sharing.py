"""
Módulo para compartilhamento de arquivos do agente de trading esportivo.
Implementa mecanismos para compartilhar arquivos compactados.
"""

import os
import logging
import time
import requests
import json
import base64
import hashlib
import hmac
import urllib.parse
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple

from config import DATA_DIR, TELEGRAM_BOT_TOKEN
from utils import setup_logger
from file_manager import FileManager

# Configurar logger
logger = setup_logger("../logs/file_sharing.log")

class FileSharing:
    """Gerenciador de compartilhamento de arquivos."""
    
    def __init__(self, file_manager: Optional[FileManager] = None):
        """
        Inicializa o gerenciador de compartilhamento.
        
        Args:
            file_manager: Instância do gerenciador de arquivos
        """
        self.file_manager = file_manager or FileManager()
        
        # Diretório para arquivos temporários
        self.temp_dir = os.path.join(os.path.dirname(DATA_DIR), "temp")
        os.makedirs(self.temp_dir, exist_ok=True)
        
        # Arquivo para armazenar links compartilhados
        self.links_file = os.path.join(DATA_DIR, "shared_links.json")
    
    def share_via_telegram(self, chat_id: int, include_logs: bool = True) -> bool:
        """
        Compartilha dados via Telegram.
        
        Args:
            chat_id: ID do chat para enviar o arquivo
            include_logs: Se True, inclui arquivos de log na compactação
            
        Returns:
            True se o arquivo foi enviado com sucesso, False caso contrário
        """
        logger.info("Iniciando compartilhamento via Telegram")
        
        try:
            # Compactar dados
            zip_path = self.file_manager.compress_data(include_logs)
            
            if not zip_path:
                logger.error("Falha ao compactar dados para compartilhamento")
                return False
            
            # Verificar tamanho do arquivo
            file_size_mb = os.path.getsize(zip_path) / (1024 * 1024)
            
            if file_size_mb > 50:
                logger.warning(f"Arquivo muito grande para enviar pelo Telegram: {file_size_mb:.1f}MB")
                
                # Enviar mensagem informando que o arquivo é muito grande
                self._send_telegram_message(
                    chat_id,
                    f"⚠️ O arquivo é muito grande ({file_size_mb:.1f}MB) para enviar pelo Telegram.\n\n"
                    f"O arquivo foi salvo em: {zip_path}\n\n"
                    "Você pode acessá-lo diretamente no servidor ou usar um serviço de compartilhamento de arquivos."
                )
                
                return False
            
            # Enviar arquivo pelo Telegram
            success = self.file_manager.send_file_telegram(zip_path, chat_id)
            
            if success:
                logger.info(f"Arquivo enviado com sucesso via Telegram: {zip_path}")
                
                # Registrar link compartilhado
                self._register_shared_link("telegram", zip_path, f"Enviado para chat_id: {chat_id}")
                
                return True
            else:
                logger.error(f"Falha ao enviar arquivo via Telegram: {zip_path}")
                return False
        except Exception as e:
            logger.error(f"Erro ao compartilhar via Telegram: {e}")
            return False
    
    def _send_telegram_message(self, chat_id: int, text: str) -> bool:
        """
        Envia uma mensagem pelo Telegram.
        
        Args:
            chat_id: ID do chat
            text: Texto da mensagem
            
        Returns:
            True se a mensagem foi enviada com sucesso, False caso contrário
        """
        try:
            url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
            data = {
                'chat_id': chat_id,
                'text': text,
                'parse_mode': 'Markdown'
            }
            
            response = requests.post(url, json=data)
            
            if response.status_code == 200:
                return True
            else:
                logger.error(f"Erro ao enviar mensagem: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            logger.error(f"Erro ao enviar mensagem: {e}")
            return False
    
    def _register_shared_link(self, method: str, file_path: str, details: str) -> None:
        """
        Registra um link compartilhado.
        
        Args:
            method: Método de compartilhamento
            file_path: Caminho do arquivo
            details: Detalhes adicionais
        """
        try:
            # Carregar links existentes
            links = []
            
            if os.path.exists(self.links_file):
                with open(self.links_file, 'r') as f:
                    links = json.load(f)
            
            # Adicionar novo link
            links.append({
                'method': method,
                'file_path': file_path,
                'file_name': os.path.basename(file_path),
                'file_size': os.path.getsize(file_path) / (1024 * 1024),  # MB
                'details': details,
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            })
            
            # Salvar links
            with open(self.links_file, 'w') as f:
                json.dump(links, f, indent=4)
            
            logger.info(f"Link compartilhado registrado: {method} - {file_path}")
        except Exception as e:
            logger.error(f"Erro ao registrar link compartilhado: {e}")
    
    def get_shared_links(self) -> List[Dict[str, Any]]:
        """
        Obtém a lista de links compartilhados.
        
        Returns:
            Lista de links compartilhados
        """
        try:
            if os.path.exists(self.links_file):
                with open(self.links_file, 'r') as f:
                    return json.load(f)
            
            return []
        except Exception as e:
            logger.error(f"Erro ao obter links compartilhados: {e}")
            return []
    
    def clean_old_shared_links(self, max_age_days: int = 7) -> int:
        """
        Remove links compartilhados antigos.
        
        Args:
            max_age_days: Idade máxima dos links em dias
            
        Returns:
            Número de links removidos
        """
        try:
            # Carregar links existentes
            links = self.get_shared_links()
            
            if not links:
                return 0
            
            # Calcular data limite
            limit_date = datetime.now() - timedelta(days=max_age_days)
            
            # Filtrar links
            new_links = []
            removed_count = 0
            
            for link in links:
                try:
                    link_date = datetime.strptime(link.get('timestamp', '2000-01-01'), '%Y-%m-%d %H:%M:%S')
                    
                    if link_date > limit_date:
                        new_links.append(link)
                    else:
                        removed_count += 1
                except:
                    # Se não conseguir converter a data, manter o link
                    new_links.append(link)
            
            # Salvar links filtrados
            with open(self.links_file, 'w') as f:
                json.dump(new_links, f, indent=4)
            
            logger.info(f"{removed_count} links antigos removidos")
            return removed_count
        except Exception as e:
            logger.error(f"Erro ao limpar links antigos: {e}")
            return 0


if __name__ == "__main__":
    # Exemplo de uso
    file_manager = FileManager()
    file_sharing = FileSharing(file_manager)
    
    # Obter links compartilhados
    links = file_sharing.get_shared_links()
    print(f"Links compartilhados: {len(links)}")
    
    for link in links:
        print(f"- {link.get('method')}: {link.get('file_name')} ({link.get('file_size'):.1f}MB) - {link.get('timestamp')}")
