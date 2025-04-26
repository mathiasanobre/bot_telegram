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

from src.config import (
    TELEGRAM_BOT_TOKEN,
    TELEGRAM_CHAT_ID,
    TELEGRAM_UPDATE_INTERVAL,
    OPPORTUNITIES_FILE,
    DATA_DIR
)
from src.utils import (
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
                    msg += f"   💰 Lucro potencial: {potential_profit:2f}\n"
                    msg += f"   ⚠️ Responsabilidade máxima: {max_liability:.2f}\n\n"
                  # Informações do método dos ciclos
                if 'cycle_info' in event:
                    cycle_info = event.get('cycle_info', {})
                    cycle_type = cycle_info.get('type', '')
                    cycle_odds = cycle_info.get('odds', 0)
                    green_pct = cycle_info.get('green_percent', 0) * 100
                    red_pct = cycle_info.get('red_percent', 0) * 100
                    risk_reward = cycle_info.get('risk_reward_ratio', 0)
                    stake = cycle_info.get('stake', 0)
                    
                    msg += f"🔄 *Método dos Ciclos*\n"
                    msg += f"   ▶️ Tipo: {cycle_type}\n"
                    msg += f"   📊 Odds: {cycle_odds:.2f}\n"
                    msg += f"   📈 Green: {green_pct:.1f}%\n"
                    msg += f"   📉 Red: {red_pct:.1f}%\n"
                    msg += f"   ⚖️ Proporção: 1:{risk_reward:.1f}\n"
                    msg += f"   💰 Stake recomendado: {stake:.2f}\n"
                
                send_telegram_message(self.token, chat_id, msg)
            else:
                send_telegram_message(self.token, chat_id, f"❌ Evento com ID {event_id} não encontrado. Verifique o ID e tente novamente.")
        except Exception as e:
            logger.error(f"Erro ao processar comando de análise de evento: {e}")
            send_telegram_message(self.token, chat_id, f"❌ Erro ao analisar evento: {str(e)}")
    
    def _process_config_command(self, chat_id: int, text: str) -> None:
        """
        Processa um comando de configuração.
        
        Args:
            chat_id: ID do chat
            text: Texto do comando
        """
        try:
            # Extrair parâmetros
            parts = text.split()
            params = {}
            
            for part in parts[1:]:
                if '=' in part:
                    key, value = part.split('=')
                    params[key.strip()] = float(value.strip())
            
            # Verificar parâmetros
            if 'green' in params and 'red' in params and 'ratio' in params:
                green = params['green']
                red = params['red']
                ratio = int(params['ratio'])
                
                # Validar valores
                if 0 < green < 1 and 0 < red < 1 and ratio > 0:
                    # Enviar mensagem de confirmação
                    msg = (
                        f"✅ Configuração atualizada:\n\n"
                        f"📈 Green alvo: {green*100:.1f}%\n"
                        f"📉 Red máximo: {red*100:.1f}%\n"
                        f"⚖️ Proporção: 1:{ratio}\n\n"
                        f"As novas configurações serão aplicadas na próxima análise."
                    )
                    send_telegram_message(self.token, chat_id, msg)
                    
                    # Salvar configuração em um arquivo para ser lido pelo analisador
                    config_file = "../data/custom_cycle_config.json"
                    os.makedirs(os.path.dirname(config_file), exist_ok=True)
                    
                    with open(config_file, 'w') as f:
                        json.dump({
                            'green_target': green,
                            'max_red': red,
                            'risk_reward_ratio': ratio
                        }, f, indent=4)
                    
                    logger.info(f"Configuração personalizada salva: green={green}, red={red}, ratio={ratio}")
                else:
                    send_telegram_message(self.token, chat_id, "❌ Valores inválidos. Green e Red devem estar entre 0 e 1, e Ratio deve ser maior que 0.")
            else:
                send_telegram_message(self.token, chat_id, "❌ Formato inválido. Use: /config green=0.05 red=0.15 ratio=3")
        except Exception as e:
            logger.error(f"Erro ao processar comando de configuração: {e}")
            send_telegram_message(self.token, chat_id, f"❌ Erro ao processar comando: {str(e)}")
    
    def _send_status(self, chat_id: int) -> None:
        """
        Envia o status do agente.
        
        Args:
            chat_id: ID do chat
        """
        try:
            # Carregar oportunidades
            opportunities = load_data(OPPORTUNITIES_FILE) or []
            
            # Contar oportunidades ativas
            now = int(time.time())
            active_count = 0
            cycle_count = 0
            
            for opp in opportunities:
                commence_time = opp.get('commence_time')
                if commence_time:
                    try:
                        dt = datetime.fromisoformat(commence_time.replace('Z', '+00:00'))
                        commence_timestamp = int(dt.timestamp())
                        
                        if commence_timestamp > now:
                            active_count += 1
                            if 'cycle_info' in opp:
                                cycle_count += 1
                    except:
                        pass
            
            # Enviar mensagem de status
            msg = (
                "📊 *Status do Agente de Trading Esportivo* 📊\n\n"
                f"⏰ Última atualização: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n"
                f"🔍 Oportunidades ativas: {active_count}\n"
                f"🔄 Oportunidades para método dos ciclos: {cycle_count}\n"
                f"📝 Total de oportunidades: {len(opportunities)}\n"
                f"📡 Captura de dados: {'ATIVA' if self.capture_active else 'INATIVA'}\n\n"
                f"Use /oportunidades para ver a lista de oportunidades ativas."
            )
            
            send_telegram_message(self.token, chat_id, msg)
        except Exception as e:
            logger.error(f"Erro ao enviar status: {e}")
            send_telegram_message(self.token, chat_id, "❌ Erro ao obter status do agente.")
    
    def _send_opportunities(self, chat_id: int) -> None:
        """
        Envia a lista de oportunidades ativas.
        
        Args:
            chat_id: ID do chat
        """
        try:
            # Carregar oportunidades
            opportunities = load_data(OPPORTUNITIES_FILE) or []
            
            # Filtrar oportunidades ativas
            now = int(time.time())
            active_opps = []
            
            for opp in opportunities:
                commence_time = opp.get('commence_time')
                if commence_time:
                    try:
                        dt = datetime.fromisoformat(commence_time.replace('Z', '+00:00'))
                        commence_timestamp = int(dt.timestamp())
                        
                        if commence_timestamp > now:
                            active_opps.append(opp)
                    except:
                        pass
            
            # Ordenar por confiança
            active_opps.sort(key=lambda x: x.get('recommendation', {}).get('confidence', 0), reverse=True)
            
            # Enviar mensagem com oportunidades
            if active_opps:
                msg = f"🔍 *Oportunidades Ativas ({len(active_opps)})* 🔍\n\n"
                
                # Enviar no máximo 5 oportunidades para não sobrecarregar a mensagem
                for i, opp in enumerate(active_opps[:5]):
                    action = opp.get('recommendation', {}).get('action', 'UNKNOWN')
                    confidence = opp.get('recommendation', {}).get('confidence', 0) * 100
                    event_id = opp.get('event_id', 'unknown')
                    
                    msg += f"{i+1}. {opp.get('home_team')} vs {opp.get('away_team')}\n"
                    msg += f"   ▶️ {action} {opp.get('team')} ({confidence:.0f}%)\n"
                    
                    if action == "BACK":
                        msg += f"   📊 Odds: {opp.get('back', {}).get('price', 0):.2f}\n"
                    elif action == "LAY":
                        msg += f"   📊 Odds: {opp.get('lay', {}).get('price', 0):.2f}\n"
                    
                    msg += f"   ℹ️ Use /analisar {event_id} para análise detalhada\n\n"
                
                if len(active_opps) > 5:
                    msg += f"... e mais {len(active_opps) - 5} oportunidades."
                
                send_telegram_message(self.token, chat_id, msg)
            else:
                send_telegram_message(self.token, chat_id, "❌ Nenhuma oportunidade ativa no momento.")
        except Exception as e:
            logger.error(f"Erro ao enviar oportunidades: {e}")
            send_telegram_message(self.token, chat_id, "❌ Erro ao obter oportunidades.")
    
    def _send_cycle_opportunities(self, chat_id: int) -> None:
        """
        Envia a lista de oportunidades para o método dos ciclos.
        
        Args:
            chat_id: ID do chat
        """
        try:
            # Carregar oportunidades
            opportunities = load_data(OPPORTUNITIES_FILE) or []
            
            # Filtrar oportunidades para o método dos ciclos
            cycle_opps = [opp for opp in opportunities if 'cycle_info' in opp]
            
            # Filtrar apenas ativas
            now = int(time.time())
            active_cycle_opps = []
            
            for opp in cycle_opps:
                commence_time = opp.get('commence_time')
                if commence_time:
                    try:
                        dt = datetime.fromisoformat(commence_time.replace('Z', '+00:00'))
                        commence_timestamp = int(dt.timestamp())
                        
                        if commence_timestamp > now:
                            active_cycle_opps.append(opp)
                    except:
                        pass
            
            # Ordenar por green esperado
            active_cycle_opps.sort(key=lambda x: x.get('cycle_info', {}).get('green_percent', 0), reverse=True)
            
            # Enviar mensagem com oportunidades
            if active_cycle_opps:
                msg = f"🔄 *Método dos Ciclos - Oportunidades ({len(active_cycle_opps)})* 🔄\n\n"
                
                # Enviar no máximo 5 oportunidades para não sobrecarregar a mensagem
                for i, opp in enumerate(active_cycle_opps[:5]):
                    cycle_info = opp.get('cycle_info', {})
                    op_type = cycle_info.get('type', 'UNKNOWN')
                    green_pct = cycle_info.get('green_percent', 0) * 100
                    red_pct = cycle_info.get('red_percent', 0) * 100
                    event_id = opp.get('event_id', 'unknown')
                    
                    msg += f"{i+1}. {opp.get('home_team')} vs {opp.get('away_team')}\n"
                    msg += f"   ▶️ {op_type} {opp.get('team')}\n"
                    msg += f"   📊 Odds: {cycle_info.get('odds', 0):.2f}\n"
                    msg += f"   📈 Green: {green_pct:.1f}% | 📉 Red: {red_pct:.1f}%\n"
                    msg += f"   ⚖️ Proporção: 1:{cycle_info.get('risk_reward_ratio', 0):.1f}\n"
                    msg += f"   ℹ️ Use /analisar {event_id} para análise detalhada\n\n"
                
                if len(active_cycle_opps) > 5:
                    msg += f"... e mais {len(active_cycle_opps) - 5} oportunidades."
                
                send_telegram_message(self.token, chat_id, msg)
            else:
                send_telegram_message(self.token, chat_id, "❌ Nenhuma oportunidade para o método dos ciclos no momento.")
        except Exception as e:
            logger.error(f"Erro ao enviar oportunidades para o método dos ciclos: {e}")
            send_telegram_message(self.token, chat_id, "❌ Erro ao obter oportunidades para o método dos ciclos.")
    
    def _send_help(self, chat_id: int) -> None:
        """
        Envia a mensagem de ajuda.
        
        Args:
            chat_id: ID do chat
        """
        msg = (
            "🤖 *Ajuda do Agente de Trading Esportivo* 🤖\n\n"
            "Este bot envia notificações sobre oportunidades de trading esportivo, com foco no método dos ciclos.\n\n"
            "*Comandos disponíveis:*\n"
            "/status - Verificar status do agente\n"
            "/oportunidades - Listar oportunidades ativas\n"
            "/ciclos - Listar oportunidades para o método dos ciclos\n"
            "/jogo [nome_time1] [nome_time2] - Buscar jogos específicos por nome\n"
            "/analisar [event_id] - Analisar um evento específico por ID\n"
            "/iniciar_captura - Iniciar coleta de dados das APIs\n"
            "/parar_captura - Parar coleta de dados das APIs\n"
            "/config green=X red=Y ratio=Z - Configurar parâmetros do método dos ciclos\n"
            "/ajuda - Exibir esta mensagem\n\n"
            "*Sobre o Método dos Ciclos:*\n"
            "O método dos ciclos busca entradas seguras com proporção de risco/retorno controlada, "
            "visando green de 3-5% e limitando o red potencial.\n\n"
            "Para Back, buscamos odds baixas (até 1.06).\n"
            "Para Lay, buscamos odds altas (acima de 30).\n\n"
            "A proporção padrão é de 1:3 (risco:retorno).\n\n"
            "*Economia de Créditos das APIs:*\n"
            "Use /iniciar_captura quando quiser coletar dados e /parar_captura quando não precisar mais, "
            "para economizar créditos das APIs."
        )
        
        send_telegram_message(self.token, chat_id, msg)
    
    def send_opportunity_notification(self, opportunity: Dict[str, Any]) -> bool:
        """
        Envia uma notificação sobre uma oportunidade.
        
        Args:
            opportunity: Dicionário com informações da oportunidade
            
        Returns:
            True se a notificação foi enviada com sucesso, False caso contrário
        """
        # Verificar se a captura está ativa
        if not self.capture_active:
            logger.info("Captura inativa. Notificações de oportunidades desativadas.")
            return False
        
        if not self.chat_id:
            logger.warning("Chat ID não definido. Não é possível enviar notificação.")
            return False
        
        # Verificar se já enviamos esta oportunidade
        event_id = opportunity.get('event_id')
        if event_id in self.sent_opportunities:
            logger.info(f"Oportunidade {event_id} já foi enviada. Ignorando.")
            return False
        
        # Formatar mensagem
        if 'cycle_info' in opportunity:
            message = format_cycle_opportunity_message(opportunity)
        else:
            message = format_opportunity_message(opportunity)
        
        # Adicionar link para análise detalhada
        message += f"\n\nℹ️ Use /analisar {event_id} para análise detalhada"
        
        # Enviar mensagem
        success = send_telegram_message(self.token, self.chat_id, message)
        
        if success:
            # Adicionar à lista de oportunidades enviadas
            self.sent_opportunities.add(event_id)
            self._save_config()
            logger.info(f"Notificação enviada para oportunidade {event_id}")
        
        return success
    
    def check_new_opportunities(self) -> None:
        """Verifica e notifica sobre novas oportunidades."""
        # Verificar se a captura está ativa
        if not self.capture_active:
            return
        
        try:
            # Carregar oportunidades
            opportunities = load_data(OPPORTUNITIES_FILE) or []
            
            # Filtrar oportunidades ativas
            now = int(time.time())
            active_opps = []
            
            for opp in opportunities:
                commence_time = opp.get('commence_time')
                if commence_time:
                    try:
                        dt = datetime.fromisoformat(commence_time.replace('Z', '+00:00'))
                        commence_timestamp = int(dt.timestamp())
                        
                        if commence_timestamp > now:
                            active_opps.append(opp)
                    except:
                        pass
            
            # Priorizar oportunidades para o método dos ciclos
            cycle_opps = [opp for opp in active_opps if 'cycle_info' in opp]
            
            # Enviar notificações para oportunidades do método dos ciclos
            for opp in cycle_opps:
                event_id = opp.get('event_id')
                if event_id and event_id not in self.sent_opportunities:
                    self.send_opportunity_notification(opp)
            
            # Enviar notificações para outras oportunidades de alta confiança
            high_confidence_opps = [
                opp for opp in active_opps 
                if opp.get('recommendation', {}).get('confidence', 0) >= 0.9
                and opp.get('event_id') not in self.sent_opportunities
                and 'cycle_info' not in opp  # Não enviar duplicatas
            ]
            
            for opp in high_confidence_opps[:3]:  # Limitar a 3 notificações por vez
                self.send_opportunity_notification(opp)
                
        except Exception as e:
            logger.error(f"Erro ao verificar novas oportunidades: {e}")
    
    def is_capture_active(self) -> bool:
        """
        Verifica se a captura de dados está ativa.
        
        Returns:
            True se a captura está ativa, False caso contrário
        """
        return self.capture_active
    
    def run(self) -> None:
        """Executa o bot em um loop."""
        logger.info(f"Iniciando bot do Telegram com token: {self.token[:5]}...{self.token[-5:]}")
        
        try:
            while True:
                # Processar atualizações
                self.process_updates()
                
                # Verificar novas oportunidades
                if self.chat_id:
                    self.check_new_opportunities()
                
                # Aguardar próximo ciclo
                time.sleep(TELEGRAM_UPDATE_INTERVAL)
        except KeyboardInterrupt:
            logger.info("Bot interrompido pelo usuário")
        except Exception as e:
            logger.error(f"Erro no loop do bot: {e}")


if __name__ == "__main__":
    bot = TelegramBot(TELEGRAM_BOT_TOKEN)
    bot.run()