"""
Módulo para análise de dados e geração de recomendações de trading esportivo.
Inclui implementação do método dos ciclos e funções de filtragem por nome de equipe.
"""

import logging
import time
from typing import Dict, List, Any, Optional, Tuple
import os
import json
from datetime import datetime

from config import (
    MIN_ODDS_DIFFERENCE, MIN_PROBABILITY,
    ODDS_DATA_FILE, MATCHES_DATA_FILE, OPPORTUNITIES_FILE,
    MAX_BACK_ODDS, MIN_LAY_ODDS, TARGET_GREEN_PERCENT,
    MAX_RED_PERCENT, RISK_REWARD_RATIO, CYCLE_SETTINGS
)
from utils import (
    setup_logger, load_data, save_data,
    decimal_to_probability, identify_arbitrage,
    calculate_back_profit, calculate_lay_liability,
    calculate_cycle_opportunity, adjust_stake_for_cycle
)

# Configurar logger
logger = setup_logger("../logs/analyzer.log")

class TradingAnalyzer:
    """Analisador de oportunidades de trading esportivo."""
    
    def __init__(self):
        """Inicializa o analisador de trading."""
        # Carregar dados existentes
        self.odds_data = load_data(ODDS_DATA_FILE) or {}
        self.matches_data = load_data(MATCHES_DATA_FILE) or {}
        self.opportunities = load_data(OPPORTUNITIES_FILE) or []
        
        # Configurações para o método dos ciclos
        self.cycle_profile = "default"
        self.cycle_settings = CYCLE_SETTINGS[self.cycle_profile]
        
    def reload_data(self) -> None:
        """Recarrega os dados das fontes."""
        self.odds_data = load_data(ODDS_DATA_FILE) or {}
        self.matches_data = load_data(MATCHES_DATA_FILE) or {}
    
    def set_cycle_profile(self, profile: str) -> bool:
        """
        Define o perfil de configuração para o método dos ciclos.
        
        Args:
            profile: Nome do perfil (default, conservative, aggressive, custom)
            
        Returns:
            True se o perfil foi definido com sucesso, False caso contrário
        """
        if profile in CYCLE_SETTINGS:
            self.cycle_profile = profile
            self.cycle_settings = CYCLE_SETTINGS[profile]
            logger.info(f"Perfil do método dos ciclos definido para: {profile}")
            return True
        else:
            logger.warning(f"Perfil inválido: {profile}. Usando perfil padrão.")
            return False
    
    def set_custom_cycle_settings(
        self, green_target: float, max_red: float, risk_reward_ratio: int
    ) -> None:
        """
        Define configurações personalizadas para o método dos ciclos.
        
        Args:
            green_target: Percentual de lucro alvo (0.05 = 5%)
            max_red: Percentual máximo de perda aceitável (0.15 = 15%)
            risk_reward_ratio: Proporção risco:retorno (3 = 1:3)
        """
        CYCLE_SETTINGS["custom"] = {
            "green_target": green_target,
            "max_red": max_red,
            "risk_reward_ratio": risk_reward_ratio
        }
        
        if self.cycle_profile == "custom":
            self.cycle_settings = CYCLE_SETTINGS["custom"]
        
        logger.info(f"Configurações personalizadas definidas: green={green_target*100}%, red={max_red*100}%, ratio=1:{risk_reward_ratio}")
    
    def analyze_back_lay_opportunities(self) -> List[Dict[str, Any]]:
        """
        Analisa oportunidades de Back/Lay nos dados disponíveis.
        
        Returns:
            Lista de oportunidades identificadas
        """
        opportunities = []
        
        # Iterar sobre todos os esportes e eventos
        for sport, events in self.odds_data.items():
            for event in events:
                # Extrair informações básicas do evento
                event_id = event.get('id')
                home_team = event.get('home_team')
                away_team = event.get('away_team')
                commence_time = event.get('commence_time')
                
                # Analisar bookmakers para encontrar oportunidades
                bookmakers = event.get('bookmakers', [])
                for market_type in ['h2h', 'h2h_lay']:
                    market_opportunities = self._analyze_market(
                        event_id, home_team, away_team, commence_time,
                        bookmakers, market_type, sport
                    )
                    opportunities.extend(market_opportunities)
        
        # Analisar oportunidades para o método dos ciclos
        cycle_opportunities = self.analyze_cycle_opportunities(opportunities)
        
        # Atualizar e salvar oportunidades
        self.opportunities = opportunities
        save_data(opportunities, OPPORTUNITIES_FILE)
        
        logger.info(f"Identificadas {len(opportunities)} oportunidades de trading, {len(cycle_opportunities)} para o método dos ciclos")
        return opportunities
    
    def analyze_cycle_opportunities(self, opportunities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Analisa oportunidades específicas para o método dos ciclos.
        
        Args:
            opportunities: Lista de oportunidades identificadas
            
        Returns:
            Lista de oportunidades que atendem aos critérios do método dos ciclos
        """
        cycle_opportunities = []
        
        for opp in opportunities:
            # Verificar Back com odds baixas (até MAX_BACK_ODDS)
            back_price = opp.get('back', {}).get('price', 0)
            if back_price <= MAX_BACK_ODDS:
                cycle_info = calculate_cycle_opportunity(
                    back_price, True,
                    self.cycle_settings["green_target"],
                    self.cycle_settings["max_red"],
                    self.cycle_settings["risk_reward_ratio"]
                )
                
                if cycle_info["is_valid"]:
                    # Ajustar stake para atingir o percentual de green desejado
                    stake_info = adjust_stake_for_cycle(
                        back_price, True, 
                        self.cycle_settings["green_target"]
                    )
                    
                    # Combinar informações
                    cycle_info.update(stake_info)
                    
                    # Adicionar informações do ciclo à oportunidade
                    opp_copy = opp.copy()
                    opp_copy["cycle_info"] = cycle_info
                    cycle_opportunities.append(opp_copy)
            
            # Verificar Lay com odds altas (acima de MIN_LAY_ODDS)
            lay_price = opp.get('lay', {}).get('price', 0)
            if lay_price >= MIN_LAY_ODDS:
                cycle_info = calculate_cycle_opportunity(
                    lay_price, False,
                    self.cycle_settings["green_target"],
                    self.cycle_settings["max_red"],
                    self.cycle_settings["risk_reward_ratio"]
                )
                
                if cycle_info["is_valid"]:
                    # Ajustar stake para atingir o percentual de green desejado
                    stake_info = adjust_stake_for_cycle(
                        lay_price, False, 
                        self.cycle_settings["green_target"]
                    )
                    
                    # Combinar informações
                    cycle_info.update(stake_info)
                    
                    # Adicionar informações do ciclo à oportunidade
                    opp_copy = opp.copy()
                    opp_copy["cycle_info"] = cycle_info
                    cycle_opportunities.append(opp_copy)
        
        return cycle_opportunities
    
    def _analyze_market(
        self, event_id: str, home_team: str, away_team: str, 
        commence_time: str, bookmakers: List[Dict[str, Any]], 
        market_type: str, sport: str
    ) -> List[Dict[str, Any]]:
        """
        Analisa um tipo específico de mercado para encontrar oportunidades.
        
        Args:
            event_id: ID do evento
            home_team: Time da casa
            away_team: Time visitante
            commence_time: Horário de início
            bookmakers: Lista de casas de apostas
            market_type: Tipo de mercado (h2h, h2h_lay)
            sport: Esporte
            
        Returns:
            Lista de oportunidades para este mercado
        """
        opportunities = []
        
        # Coletar todas as odds disponíveis para este mercado
        all_odds = {}
        for bookmaker in bookmakers:
            bookmaker_name = bookmaker.get('key')
            markets = bookmaker.get('markets', [])
            
            for market in markets:
                if market.get('key') == market_type:
                    outcomes = market.get('outcomes', [])
                    for outcome in outcomes:
                        team = outcome.get('name')
                        price = outcome.get('price')
                        
                        if team not in all_odds:
                            all_odds[team] = []
                        
                        all_odds[team].append({
                            'bookmaker': bookmaker_name,
                            'price': price,
                            'market_type': market_type
                        })
        
        # Encontrar oportunidades de Back/Lay para cada time
        for team in all_odds:
            # Separar odds de Back e Lay
            back_odds = [o for o in all_odds[team] if o['market_type'] == 'h2h']
            lay_odds = [o for o in all_odds[team] if o['market_type'] == 'h2h_lay']
            
            # Encontrar as melhores odds de Back e Lay
            if back_odds and lay_odds:
                best_back = max(back_odds, key=lambda x: x['price'])
                best_lay = min(lay_odds, key=lambda x: x['price'])
                
                # Verificar se há diferença significativa entre Back e Lay
                back_price = best_back['price']
                lay_price = best_lay['price']
                
                # Para odds americanas, converter para decimal
                if isinstance(back_price, int):
                    back_price = self._american_to_decimal(back_price)
                if isinstance(lay_price, int):
                    lay_price = self._american_to_decimal(lay_price)
                
                # Calcular diferença percentual
                if back_price < lay_price:
                    diff_percent = (lay_price - back_price) / back_price
                    
                    if diff_percent >= MIN_ODDS_DIFFERENCE:
                        # Verificar se é uma oportunidade de arbitragem
                        is_arbitrage, margin = identify_arbitrage(back_price, lay_price)
                        
                        # Calcular probabilidade implícita
                        back_prob = decimal_to_probability(back_price)
                        
                        # Criar registro de oportunidade
                        opportunity = {
                            'event_id': event_id,
                            'sport': sport,
                            'home_team': home_team,
                            'away_team': away_team,
                            'team': team,
                            'commence_time': commence_time,
                            'timestamp': int(time.time()),
                            'back': {
                                'bookmaker': best_back['bookmaker'],
                                'price': back_price,
                                'probability': back_prob
                            },
                            'lay': {
                                'bookmaker': best_lay['bookmaker'],
                                'price': lay_price,
                                'probability': decimal_to_probability(lay_price)
                            },
                            'difference_percent': diff_percent * 100,
                            'is_arbitrage': is_arbitrage,
                            'arbitrage_margin': margin if is_arbitrage else 0,
                            'recommendation': self._generate_recommendation(
                                back_price, lay_price, back_prob, is_arbitrage
                            )
                        }
                        
                        # Verificar se atende aos critérios do método dos ciclos
                        if back_price <= MAX_BACK_ODDS or lay_price >= MIN_LAY_ODDS:
                            # Adicionar flag para indicar que é uma oportunidade potencial para o método dos ciclos
                            opportunity['potential_cycle'] = True
                        
                        opportunities.append(opportunity)
        
        return opportunities
    
    def _american_to_decimal(self, american_odds: int) -> float:
        """
        Converte odds americanas para formato decimal.
        
        Args:
            american_odds: Odds em formato americano
            
        Returns:
            Odds em formato decimal
        """
        if american_odds > 0:
            return (american_odds / 100) + 1
        else:
            return (100 / abs(american_odds)) + 1
    
    def _generate_recommendation(
        self, back_price: float, lay_price: float, 
        back_prob: float, is_arbitrage: bool
    ) -> Dict[str, Any]:
        """
        Gera uma recomendação de trading com base nas odds.
        
        Args:
            back_price: Preço de Back
            lay_price: Preço de Lay
            back_prob: Probabilidade implícita de Back
            is_arbitrage: Se é uma oportunidade de arbitragem
            
        Returns:
            Recomendação de trading
        """
        recommendation = {
            'action': None,
            'confidence': 0,
            'strategy': None,
            'stake_recommendation': 0,
            'potential_profit': 0,
            'max_liability': 0
        }
        
        # Verificar se atende aos critérios do método dos ciclos
        if back_price <= MAX_BACK_ODDS:
            recommendation['action'] = 'BACK'
            recommendation['confidence'] = 0.90
            recommendation['strategy'] = 'Método dos Ciclos (Back)'
            recommendation['stake_recommendation'] = 100  # Valor base
            recommendation['potential_profit'] = round(calculate_back_profit(100, back_price), 2)
            recommendation['max_liability'] = 100  # Stake de Back
            
            return recommendation
        
        if lay_price >= MIN_LAY_ODDS:
            recommendation['action'] = 'LAY'
            recommendation['confidence'] = 0.90
            recommendation['strategy'] = 'Método dos Ciclos (Lay)'
            recommendation['stake_recommendation'] = 100  # Valor base
            recommendation['potential_profit'] = 100  # Stake de Lay
            recommendation['max_liability'] = round(calculate_lay_liability(100, lay_price), 2)
            
            return recommendation
        
        # Estratégia baseada em arbitragem
        if is_arbitrage:
            recommendation['action'] = 'BACK_AND_LAY'
            recommendation['confidence'] = 0.95
            recommendation['strategy'] = 'Arbitragem'
            recommendation['stake_recommendation'] = 100  # Valor base
            
            # Calcular lucro potencial para stake de 100
            back_stake = 100
            lay_stake = back_stake * (back_price / lay_price)
            
            back_profit = calculate_back_profit(back_stake, back_price)
            lay_liability = calculate_lay_liability(lay_stake, lay_price)
            
            net_profit = back_profit - lay_liability
            recommendation['potential_profit'] = round(net_profit, 2)
            recommendation['max_liability'] = round(lay_liability, 2)
            
            return recommendation
        
        # Estratégia baseada em valor esperado
        if back_prob >= MIN_PROBABILITY and back_
(Content truncated due to size limit. Use line ranges to read in chunks)