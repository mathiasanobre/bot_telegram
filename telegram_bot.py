"""
Módulo para integração com o Telegram.
Envia notificações sobre oportunidades de trading.
"""

import logging
import time
import requests
import json
import os
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime

from config import (
    TELEGRAM_BOT_TOKEN,
    TELEGRAM_CHAT_ID,
    TELEGRAM_UPDATE_INTERVAL,
    OPPORTUNITIES_FILE,
    DATA_DIR
)
from utils import (
    setup_logger, load_data, save_data,
    send_telegram_message, get_telegram_updates,
    format_opportunity_message, format_cycle_opportunity_message
)

# Configurar logger
logger = setup_logger("../logs/telegram_bot.log")

class TelegramBot:
    """Bot do Telegram para enviar notificações sobre oportunidades de trading."""
    
    def __init__(self, token: str, config_file: str = "../data/telegram_config.json"):
        """
        Inicializa o bot do Telegram.
        
        Args:
            token: Token do bot do Telegram
            config_file: Arquivo de configuração do bot
        """
        self.token = token
        self.config_file = config_file
        self.chat_id = None
        self.last_update_id = 0
        self.sent_opportunities = set()  # IDs de oportunidades já enviadas
        self.capture_active = False  # Flag para controlar a captura de dados
        
        # Carregar configuração
        self._load_config()
    
    def _load_config(self) -> None:
        """Carrega a configuração do bot."""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    config = json.load(f)
                    self.chat_id = config.get('chat_id')
                    self.last_update_id = config.get('last_update_id', 0)
                    self.sent_opportunities = set(config.get('sent_opportunities', []))
                    self.capture_active = config.get('capture_active', False)
                    logger.info(f"Configuração do bot carregada. Chat ID: {self.chat_id}, Captura ativa: {self.capture_active}")
            except Exception as e:
                logger.error(f"Erro ao carregar configuração do bot: {e}")
    
    def _save_config(self) -> None:
        """Salva a configuração do bot."""
        try:
            # Criar diretório se não existir
            os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
            
            config = {
                'chat_id': self.chat_id,
                'last_update_id': self.last_update_id,
                'sent_opportunities': list(self.sent_opportunities),
                'capture_active': self.capture_active
            }
            
            with open(self.config_file, 'w') as f:
                json.dump(config, f, indent=4)
                
            logger.info("Configuração do bot salva")
        except Exception as e:
            logger.error(f"Erro ao salvar configuração do bot: {e}")
    
    def process_updates(self) -> None:
        """Processa atualizações do bot."""
        try:
            updates = get_telegram_updates(self.token, self.last_update_id)
            
            for update in updates:
                update_id = update.get('update_id', 0)
                
                # Atualizar último ID processado
                if update_id > self.last_update_id:
                    self.last_update_id = update_id
                
                # Processar mensagem
                message = update.get('message', {})
                chat = message.get('chat', {})
                chat_id = chat.get('id')
                text = message.get('text', '')
                
                if chat_id and text:
                    # Salvar chat_id se for a primeira mensagem
                    if not self.chat_id:
                        self.chat_id = chat_id
                        logger.info(f"Chat ID definido: {chat_id}")
                        self._save_config()
                        
                        # Enviar mensagem de boas-vindas
                        welcome_msg = (
                            "🤖 *Agente de Trading Esportivo* 🤖\n\n"
                            "Olá! Estou pronto para enviar notificações sobre oportunidades de trading esportivo.\n\n"
                            "Comandos disponíveis:\n"
                            "/status - Verificar status do agente\n"
                            "/oportunidades - Listar oportunidades ativas\n"
                            "/ciclos - Listar oportunidades para o método dos ciclos\n"
                            "/jogo [nome_time1] [nome_time2] - Buscar jogos específicos por nome\n"
                            "/analisar [event_id] - Analisar evento por ID\n"
                            "/iniciar_captura - Iniciar coleta de dados das APIs\n"
                            "/parar_captura - Parar coleta de dados das APIs\n"
                            "/config green=X red=Y ratio=Z - Configurar parâmetros do método dos ciclos\n"
                            "/ajuda - Exibir ajuda\n\n"
                            "Você receberá notificações automáticas quando novas oportunidades forem identificadas."
                        )
                        send_telegram_message(self.token, chat_id, welcome_msg)
                    
                    # Processar comandos
                    self._process_command(chat_id, text)
            
            # Salvar configuração após processar atualizações
            if updates:
                self._save_config()
                
        except Exception as e:
            logger.error(f"Erro ao processar atualizações do bot: {e}")
    
    def _process_command(self, chat_id: int, text: str) -> None:
        """
        Processa um comando do bot.
        
        Args:
            chat_id: ID do chat
            text: Texto da mensagem
        """
        if text.startswith('/status'):
            self._send_status(chat_id)
        elif text.startswith('/oportunidades'):
            self._send_opportunities(chat_id)
        elif text.startswith('/ciclos'):
            self._send_cycle_opportunities(chat_id)
        elif text.startswith('/ajuda'):
            self._send_help(chat_id)
        elif text.startswith('/config'):
            # Formato: /config green=0.05 red=0.15 ratio=3
            self._process_config_command(chat_id, text)
        elif text.startswith('/jogo'):
            # Formato: /jogo Barcelona Real Madrid
            self._process_game_search_command(chat_id, text)
        elif text.startswith('/analisar'):
            # Formato: /analisar event_12345
            self._process_analyze_event_command(chat_id, text)
        elif text.startswith('/iniciar_captura'):
            # Iniciar coleta de dados
            self._start_capture(chat_id)
        elif text.startswith('/parar_captura'):
            # Parar coleta de dados
            self._stop_capture(chat_id)
    
    def _start_capture(self, chat_id: int) -> None:
        """
        Inicia a captura de dados das APIs.
        
        Args:
            chat_id: ID do chat
        """
        if self.capture_active:
            send_telegram_message(self.token, chat_id, "⚠️ A captura de dados já está ativa.")
            return
        
        self.capture_active = True
        self._save_config()
        
        send_telegram_message(
            self.token, 
            chat_id, 
            "✅ Captura de dados iniciada! O agente agora está coletando dados das APIs.\n\n"
            "Use /parar_captura para interromper a coleta e economizar créditos das APIs."
        )
        logger.info("Captura de dados iniciada pelo usuário")
    
    def _stop_capture(self, chat_id: int) -> None:
        """
        Para a captura de dados das APIs.
        
        Args:
            chat_id: ID do chat
        """
        if not self.capture_active:
            send_telegram_message(self.token, chat_id, "⚠️ A captura de dados já está inativa.")
            return
        
        self.capture_active = False
        self._save_config()
        
        send_telegram_message(
            self.token, 
            chat_id, 
            "✅ Captura de dados interrompida! O agente não está mais coletando dados das APIs.\n\n"
            "Use /iniciar_captura para retomar a coleta quando necessário."
        )
        logger.info("Captura de dados interrompida pelo usuário")
    
    def _process_game_search_command(self, chat_id: int, text: str) -> None:
        """
        Processa um comando de busca de jogo.
        
        Args:
            chat_id: ID do chat
            text: Texto do comando
        """
        try:
            # Extrair termos de busca
            parts = text.split()
            if len(parts) < 2:
                send_telegram_message(self.token, chat_id, "❌ Formato inválido. Use: /jogo Barcelona Real Madrid")
                return
            
            search_terms = parts[1:]
            
            # Enviar mensagem de processamento
            send_telegram_message(self.token, chat_id, f"🔍 Buscando jogos com os termos: {' '.join(search_terms)}...")
            
            # Carregar oportunidades
            opportunities = load_data(OPPORTUNITIES_FILE) or []
            
            # Filtrar jogos que correspondem aos termos de busca
            matches = []
            for opp in opportunities:
                home_team = opp.get('home_team', '').lower()
                away_team = opp.get('away_team', '').lower()
                team = opp.get('team', '').lower()
                
                # Verificar se algum termo de busca está presente nos nomes das equipes
                if any(term.lower() in home_team or term.lower() in away_team or term.lower() in team for term in search_terms):
                    matches.append(opp)
            
            # Enviar resultados
            if matches:
                msg = f"🎯 *Jogos encontrados ({len(matches)})* 🎯\n\n"
                
                for i, match in enumerate(matches[:5]):  # Limitar a 5 resultados
                    event_id = match.get('event_id', 'unknown')
                    home = match.get('home_team', '')
                    away = match.get('away_team', '')
                    
                    msg += f"{i+1}. {home} vs {away}\n"
                    msg += f"   🆔 ID: {event_id}\n"
                    
                    # Adicionar informações de Back/Lay se disponíveis
                    back_price = match.get('back', {}).get('price', 0)
                    lay_price = match.get('lay', {}).get('price', 0)
                    
                    if back_price:
                        msg += f"   🔵 Back: {back_price:.2f}\n"
                    if lay_price:
                        msg += f"   🔴 Lay: {lay_price:.2f}\n"
                    
                    # Adicionar informações do método dos ciclos se disponíveis
                    if 'cycle_info' in match:
                        cycle_info = match.get('cycle_info', {})
                        green_pct = cycle_info.get('green_percent', 0) * 100
                        red_pct = cycle_info.get('red_percent', 0) * 100
                        
                        msg += f"   📊 Método dos Ciclos: Green {green_pct:.1f}%, Red {red_pct:.1f}%\n"
                    
                    msg += f"   ℹ️ Use /analisar {event_id} para análise detalhada\n\n"
                
                if len(matches) > 5:
                    msg += f"... e mais {len(matches) - 5} jogos encontrados."
                
                send_telegram_message(self.token, chat_id, msg)
            else:
                send_telegram_message(self.token, chat_id, "❌ Nenhum jogo encontrado com esses termos. Tente termos mais genéricos ou verifique se o jogo está disponível nas APIs.")
        except Exception as e:
            logger.error(f"Erro ao processar comando de busca de jogo: {e}")
            send_telegram_message(self.token, chat_id, f"❌ Erro ao buscar jogos: {str(e)}")
    
    def _process_analyze_event_command(self, chat_id: int, text: str) -> None:
        """
        Processa um comando de análise de evento específico.
        
        Args:
            chat_id: ID do chat
            text: Texto do comando
        """
        try:
            # Extrair ID do evento
            parts = text.split()
            if len(parts) != 2:
                send_telegram_message(self.token, chat_id, "❌ Formato inválido. Use: /analisar event_12345")
                return
            
            event_id = parts[1]
            
            # Enviar mensagem de processamento
            send_telegram_message(self.token, chat_id, f"🔍 Analisando evento com ID: {event_id}...")
            
            # Carregar oportunidades
            opportunities = load_data(OPPORTUNITIES_FILE) or []
            
            # Buscar evento específico
            event = None
            for opp in opportunities:
                if opp.get('event_id') == event_id:
                    event = opp
                    break
            
            # Enviar resultado da análise
            if event:
                # Formatar mensagem detalhada
                home = event.get('home_team', '')
                away = event.get('away_team', '')
                team = event.get('team', '')
                sport = event.get('sport', '')
                
                msg = f"📊 *Análise Detalhada: {home} vs {away}* 📊\n\n"
                msg += f"🏆 Esporte: {sport}\n"
                msg += f"👥 Time analisado: {team}\n\n"
                
                # Informações de Back
                back_info = event.get('back', {})
                back_price = back_info.get('price', 0)
                back_bookmaker = back_info.get('bookmaker', '')
                back_prob = back_info.get('probability', 0) * 100
                
                if back_price:
                    msg += f"🔵 *Back*\n"
                    msg += f"   📈 Odds: {back_price:.2f}\n"
                    msg += f"   🏢 Casa: {back_bookmaker}\n"
                    msg += f"   🎲 Probabilidade: {back_prob:.1f}%\n\n"
                
                # Informações de Lay
                lay_info = event.get('lay', {})
                lay_price = lay_info.get('price', 0)
                lay_bookmaker = lay_info.get('bookmaker', '')
                lay_prob = lay_info.get('probability', 0) * 100
                
                if lay_price:
                    msg += f"🔴 *Lay*\n"
                    msg += f"   📉 Odds: {lay_price:.2f}\n"
                    msg += f"   🏢 Casa: {lay_bookmaker}\n"
                    msg += f"   🎲 Probabilidade: {lay_prob:.1f}%\n\n"
                
                # Diferença percentual
                diff_percent = event.get('difference_percent', 0)
                if diff_percent:
                    msg += f"📊 Diferença: {diff_percent:.2f}%\n"
                
                # Informações de arbitragem
                is_arbitrage = event.get('is_arbitrage', False)
                arbitrage_margin = event.get('arbitrage_margin', 0)
                
                if is_arbitrage:
                    msg += f"💰 Arbitragem detectada! Margem: {arbitrage_margin:.2f}%\n\n"
                
                # Recomendação
                recommendation = event.get('recommendation', {})
                action = recommendation.get('action', '')
                confidence = recommendation.get('confidence', 0) * 100
                strategy = recommendation.get('strategy', '')
                potential_profit = recommendation.get('potential_profit', 0)
                max_liability = recommendation.get('max_liability', 0)
                
                if action:
                    msg += f"🎯 *Recomendação*\n"
                    msg += f"   ▶️ Ação: {action}\n"
                    msg += f"   🎯 Confiança: {confidence:.1f}%\n"
                    msg += f"   📝 Estratégia: {strategy}\n"
                    msg += f"   💰 Lucro potenci
(Content truncated due to size limit. Use line ranges to read in chunks)