"""
Módulo para análise específica de jogos solicitados pelo usuário.
"""

import logging
import time
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime

from config import (
    ODDS_DATA_FILE, MATCHES_DATA_FILE, OPPORTUNITIES_FILE,
    MAX_BACK_ODDS, MIN_LAY_ODDS
)
from utils import (
    setup_logger, load_data, save_data,
    calculate_back_profit, calculate_lay_liability
)

# Configurar logger
logger = setup_logger("../logs/game_analyzer.log")

class GameAnalyzer:
    """Analisador específico para jogos solicitados pelo usuário."""
    
    def __init__(self):
        """Inicializa o analisador de jogos."""
        # Carregar dados existentes
        self.opportunities = load_data(OPPORTUNITIES_FILE) or []
    
    def reload_data(self) -> None:
        """Recarrega os dados das oportunidades."""
        self.opportunities = load_data(OPPORTUNITIES_FILE) or []
    
    def find_games_by_team_names(self, search_terms: List[str]) -> List[Dict[str, Any]]:
        """
        Busca jogos que correspondem aos termos de busca nos nomes das equipes.
        
        Args:
            search_terms: Lista de termos para buscar
            
        Returns:
            Lista de jogos que correspondem aos termos de busca
        """
        matches = []
        
        # Converter termos de busca para minúsculas para comparação case-insensitive
        search_terms_lower = [term.lower() for term in search_terms]
        
        for opp in self.opportunities:
            home_team = opp.get('home_team', '').lower()
            away_team = opp.get('away_team', '').lower()
            team = opp.get('team', '').lower()
            
            # Verificar se algum termo de busca está presente nos nomes das equipes
            if any(term in home_team or term in away_team or term in team for term in search_terms_lower):
                matches.append(opp)
        
        logger.info(f"Encontrados {len(matches)} jogos para os termos: {search_terms}")
        return matches
    
    def get_event_by_id(self, event_id: str) -> Optional[Dict[str, Any]]:
        """
        Busca um evento específico pelo ID.
        
        Args:
            event_id: ID do evento
            
        Returns:
            Evento encontrado ou None se não encontrado
        """
        for opp in self.opportunities:
            if opp.get('event_id') == event_id:
                logger.info(f"Evento encontrado com ID: {event_id}")
                return opp
        
        logger.warning(f"Evento não encontrado com ID: {event_id}")
        return None
    
    def analyze_specific_game(self, event_id: str) -> Dict[str, Any]:
        """
        Realiza uma análise detalhada de um jogo específico.
        
        Args:
            event_id: ID do evento
            
        Returns:
            Análise detalhada do jogo
        """
        event = self.get_event_by_id(event_id)
        
        if not event:
            logger.warning(f"Não foi possível analisar o jogo com ID: {event_id}")
            return {"error": "Evento não encontrado"}
        
        # Extrair informações básicas
        home_team = event.get('home_team', '')
        away_team = event.get('away_team', '')
        team = event.get('team', '')
        sport = event.get('sport', '')
        
        # Informações de Back/Lay
        back_info = event.get('back', {})
        back_price = back_info.get('price', 0)
        back_bookmaker = back_info.get('bookmaker', '')
        back_prob = back_info.get('probability', 0) * 100
        
        lay_info = event.get('lay', {})
        lay_price = lay_info.get('price', 0)
        lay_bookmaker = lay_info.get('bookmaker', '')
        lay_prob = lay_info.get('probability', 0) * 100
        
        # Diferença percentual e arbitragem
        diff_percent = event.get('difference_percent', 0)
        is_arbitrage = event.get('is_arbitrage', False)
        arbitrage_margin = event.get('arbitrage_margin', 0)
        
        # Recomendação
        recommendation = event.get('recommendation', {})
        action = recommendation.get('action', '')
        confidence = recommendation.get('confidence', 0) * 100
        strategy = recommendation.get('strategy', '')
        stake_recommendation = recommendation.get('stake_recommendation', 0)
        potential_profit = recommendation.get('potential_profit', 0)
        max_liability = recommendation.get('max_liability', 0)
        
        # Método dos ciclos
        cycle_info = event.get('cycle_info', {})
        cycle_type = cycle_info.get('type', '')
        cycle_odds = cycle_info.get('odds', 0)
        green_pct = cycle_info.get('green_percent', 0) * 100
        red_pct = cycle_info.get('red_percent', 0) * 100
        risk_reward = cycle_info.get('risk_reward_ratio', 0)
        cycle_stake = cycle_info.get('stake', 0)
        
        # Análise adicional para o método dos ciclos
        cycle_analysis = {}
        if cycle_type:
            # Calcular diferentes cenários de stake
            stakes = [50, 100, 200, 500, 1000]
            scenarios = []
            
            for stake in stakes:
                if cycle_type == "BACK":
                    profit = calculate_back_profit(stake, cycle_odds)
                    liability = stake
                    green_amount = profit
                    red_amount = liability
                else:  # LAY
                    profit = stake
                    liability = calculate_lay_liability(stake, cycle_odds)
                    green_amount = profit
                    red_amount = liability
                
                scenarios.append({
                    "stake": stake,
                    "green_amount": round(green_amount, 2),
                    "green_percent": round((green_amount / stake) * 100, 2),
                    "red_amount": round(red_amount, 2),
                    "red_percent": round((red_amount / stake) * 100, 2)
                })
            
            cycle_analysis = {
                "is_valid_cycle": True,
                "scenarios": scenarios,
                "recommended_stake": cycle_stake,
                "risk_reward_ratio": risk_reward
            }
        
        # Construir análise completa
        analysis = {
            "event_id": event_id,
            "sport": sport,
            "home_team": home_team,
            "away_team": away_team,
            "team": team,
            "back": {
                "price": back_price,
                "bookmaker": back_bookmaker,
                "probability": back_prob
            },
            "lay": {
                "price": lay_price,
                "bookmaker": lay_bookmaker,
                "probability": lay_prob
            },
            "difference_percent": diff_percent,
            "arbitrage": {
                "is_arbitrage": is_arbitrage,
                "margin": arbitrage_margin
            },
            "recommendation": {
                "action": action,
                "confidence": confidence,
                "strategy": strategy,
                "stake": stake_recommendation,
                "potential_profit": potential_profit,
                "max_liability": max_liability
            },
            "cycle_method": {
                "is_applicable": bool(cycle_type),
                "type": cycle_type,
                "odds": cycle_odds,
                "green_percent": green_pct,
                "red_percent": red_pct,
                "risk_reward_ratio": risk_reward,
                "analysis": cycle_analysis
            },
            "timestamp": int(time.time())
        }
        
        logger.info(f"Análise completa gerada para o jogo: {home_team} vs {away_team}")
        return analysis
    
    def get_live_game_stats(self, event_id: str) -> Dict[str, Any]:
        """
        Obtém estatísticas em tempo real para um jogo específico.
        
        Args:
            event_id: ID do evento
            
        Returns:
            Estatísticas em tempo real do jogo
        """
        # Carregar dados de partidas ao vivo
        matches_data = load_data(MATCHES_DATA_FILE) or {}
        live_matches = matches_data.get('live_matches', [])
        
        # Buscar partida específica
        for match in live_matches:
            match_id = str(match.get('partida_id', ''))
            if match_id == event_id:
                logger.info(f"Estatísticas ao vivo encontradas para o jogo com ID: {event_id}")
                return {
                    "event_id": event_id,
                    "status": "live",
                    "match_time": match.get('hora_partida', ''),
                    "current_time": match.get('tempo_partida', ''),
                    "score": {
                        "home": match.get('placar_mandante', 0),
                        "away": match.get('placar_visitante', 0)
                    },
                    "stats": match.get('estatisticas', {}),
                    "timestamp": int(time.time())
                }
        
        logger.warning(f"Estatísticas ao vivo não encontradas para o jogo com ID: {event_id}")
        return {"error": "Estatísticas ao vivo não disponíveis para este jogo"}
    
    def get_recommended_games(self, max_results: int = 5) -> List[Dict[str, Any]]:
        """
        Obtém uma lista de jogos recomendados para o método dos ciclos.
        
        Args:
            max_results: Número máximo de resultados a retornar
            
        Returns:
            Lista de jogos recomendados
        """
        # Filtrar jogos que são adequados para o método dos ciclos
        cycle_games = []
        
        for opp in self.opportunities:
            if 'cycle_info' in opp:
                cycle_games.append(opp)
        
        # Ordenar por green esperado
        cycle_games.sort(key=lambda x: x.get('cycle_info', {}).get('green_percent', 0), reverse=True)
        
        # Limitar número de resultados
        recommended = cycle_games[:max_results]
        
        logger.info(f"Encontrados {len(recommended)} jogos recomendados para o método dos ciclos")
        return recommended


if __name__ == "__main__":
    analyzer = GameAnalyzer()
    
    # Exemplo de uso
    search_results = analyzer.find_games_by_team_names(["Barcelona", "Real"])
    print(f"Encontrados {len(search_results)} jogos")
    
    if search_results:
        event_id = search_results[0].get('event_id')
        analysis = analyzer.analyze_specific_game(event_id)
        print(f"Análise para {analysis.get('home_team')} vs {analysis.get('away_team')}")
