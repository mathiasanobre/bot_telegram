"""
Interface web para o agente de trading esportivo.
"""

import os
import json
import time
import threading
from datetime import datetime
from typing import Dict, List, Any, Optional

from flask import Flask, render_template, jsonify, request, redirect, url_for
import pandas as pd
import plotly
import plotly.graph_objs as go

# Importar componentes do agente
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from agent import TradingAgent
from config import OPPORTUNITIES_FILE, DATA_DIR
from utils import load_data, setup_logger

# Configurar logger
logger = setup_logger("../logs/web_interface.log")

# Inicializar Flask
app = Flask(__name__, 
            template_folder='../templates',
            static_folder='../static')

# Inicializar agente
agent = TradingAgent()
agent_thread = None

def start_agent_thread():
    """Inicia o agente em uma thread separada."""
    global agent_thread
    if agent_thread is None or not agent_thread.is_alive():
        agent_thread = threading.Thread(target=agent.start)
        agent_thread.daemon = True
        agent_thread.start()
        logger.info("Thread do agente iniciada")

@app.route('/')
def index():
    """Página inicial."""
    return render_template('index.html', status=agent.get_status())

@app.route('/start')
def start_agent():
    """Inicia o agente."""
    if not agent.running:
        start_agent_thread()
        logger.info("Agente iniciado via interface web")
    return redirect(url_for('index'))

@app.route('/stop')
def stop_agent():
    """Para o agente."""
    if agent.running:
        agent.stop()
        logger.info("Agente parado via interface web")
    return redirect(url_for('index'))

@app.route('/status')
def get_status():
    """Retorna o status do agente em formato JSON."""
    return jsonify(agent.get_status())

@app.route('/opportunities')
def get_opportunities():
    """Página de oportunidades."""
    active_only = request.args.get('active_only', 'true').lower() == 'true'
    opportunities = agent.get_opportunities(active_only=active_only)
    
    # Ordenar por diferença percentual
    opportunities = sorted(
        opportunities, 
        key=lambda x: x.get('difference_percent', 0), 
        reverse=True
    )
    
    return render_template(
        'opportunities.html', 
        opportunities=opportunities,
        active_only=active_only
    )

@app.route('/api/opportunities')
def api_opportunities():
    """API para obter oportunidades em formato JSON."""
    active_only = request.args.get('active_only', 'true').lower() == 'true'
    opportunities = agent.get_opportunities(active_only=active_only)
    return jsonify(opportunities)

@app.route('/opportunity/<event_id>')
def get_opportunity(event_id):
    """Página de detalhes de uma oportunidade específica."""
    opportunity = agent.get_opportunity_by_id(event_id)
    if opportunity:
        return render_template('opportunity_detail.html', opportunity=opportunity)
    else:
        return render_template('error.html', message="Oportunidade não encontrada"), 404

@app.route('/dashboard')
def dashboard():
    """Dashboard com gráficos e estatísticas."""
    opportunities = agent.get_opportunities(active_only=False)
    
    # Preparar dados para gráficos
    sports = {}
    strategies = {}
    actions = {}
    
    for opp in opportunities:
        sport = opp.get('sport', 'unknown')
        strategy = opp.get('recommendation', {}).get('strategy', 'unknown')
        action = opp.get('recommendation', {}).get('action', 'unknown')
        
        sports[sport] = sports.get(sport, 0) + 1
        strategies[strategy] = strategies.get(strategy, 0) + 1
        actions[action] = actions.get(action, 0) + 1
    
    # Criar gráficos com Plotly
    sport_fig = go.Figure(data=[go.Pie(labels=list(sports.keys()), values=list(sports.values()))])
    sport_fig.update_layout(title_text='Oportunidades por Esporte')
    sport_chart = json.dumps(sport_fig, cls=plotly.utils.PlotlyJSONEncoder)
    
    strategy_fig = go.Figure(data=[go.Bar(x=list(strategies.keys()), y=list(strategies.values()))])
    strategy_fig.update_layout(title_text='Oportunidades por Estratégia')
    strategy_chart = json.dumps(strategy_fig, cls=plotly.utils.PlotlyJSONEncoder)
    
    action_fig = go.Figure(data=[go.Bar(x=list(actions.keys()), y=list(actions.values()))])
    action_fig.update_layout(title_text='Oportunidades por Ação Recomendada')
    action_chart = json.dumps(action_fig, cls=plotly.utils.PlotlyJSONEncoder)
    
    return render_template(
        'dashboard.html',
        sport_chart=sport_chart,
        strategy_chart=strategy_chart,
        action_chart=action_chart,
        opportunities_count=len(opportunities),
        active_count=len(agent.get_opportunities(active_only=True))
    )

@app.route('/settings')
def settings():
    """Página de configurações."""
    # Ler configurações atuais
    config_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config.py')
    with open(config_file, 'r') as f:
        config_content = f.read()
    
    return render_template('settings.html', config_content=config_content)

@app.route('/logs')
def logs():
    """Página de logs."""
    log_file = "../logs/trader_esportivo.log"
    log_content = "Logs não disponíveis"
    
    try:
        with open(log_file, 'r') as f:
            # Ler as últimas 100 linhas
            lines = f.readlines()[-100:]
            log_content = ''.join(lines)
    except Exception as e:
        log_content = f"Erro ao ler logs: {e}"
    
    return render_template('logs.html', log_content=log_content)

@app.route('/help')
def help_page():
    """Página de ajuda."""
    return render_template('help.html')

def create_template_files():
    """Cria os arquivos de template necessários."""
    os.makedirs('../templates', exist_ok=True)
    os.makedirs('../static/css', exist_ok=True)
    os.makedirs('../static/js', exist_ok=True)
    
    # Criar arquivo base.html
    base_html = """<!DOCTYPE html>
<html lang="pt-br">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Agente de Trading Esportivo</title>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css">
    <link rel="stylesheet" href="{{ url_for('static', filename='css/style.css') }}">
    {% block head %}{% endblock %}
</head>
<body>
    <nav class="navbar navbar-expand-lg navbar-dark bg-dark">
        <div class="container">
            <a class="navbar-brand" href="/">Agente de Trading Esportivo</a>
            <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#navbarNav">
                <span class="navbar-toggler-icon"></span>
            </button>
            <div class="collapse navbar-collapse" id="navbarNav">
                <ul class="navbar-nav">
                    <li class="nav-item">
                        <a class="nav-link" href="/">Home</a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link" href="/opportunities">Oportunidades</a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link" href="/dashboard">Dashboard</a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link" href="/settings">Configurações</a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link" href="/logs">Logs</a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link" href="/help">Ajuda</a>
                    </li>
                </ul>
            </div>
        </div>
    </nav>

    <div class="container mt-4">
        {% block content %}{% endblock %}
    </div>

    <footer class="bg-dark text-white text-center py-3 mt-5">
        <div class="container">
            <p>Agente de Trading Esportivo &copy; 2025</p>
        </div>
    </footer>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/jquery@3.6.0/dist/jquery.min.js"></script>
    <script src="{{ url_for('static', filename='js/main.js') }}"></script>
    {% block scripts %}{% endblock %}
</body>
</html>
"""
    
    # Criar arquivo index.html
    index_html = """{% extends 'base.html' %}

{% block content %}
<div class="row">
    <div class="col-md-12">
        <div class="card">
            <div class="card-header bg-primary text-white">
                <h2>Status do Agente</h2>
            </div>
            <div class="card-body">
                <div class="row">
                    <div class="col-md-6">
                        <div class="status-card">
                            <h4>Status: 
                                {% if status.running %}
                                <span class="badge bg-success">Em execução</span>
                                {% else %}
                                <span class="badge bg-danger">Parado</span>
                                {% endif %}
                            </h4>
                            <p>Última atualização: {{ status.last_update }}</p>
                            <p>Oportunidades ativas: {{ status.active_opportunities_count }}</p>
                            <p>Total de oportunidades: {{ status.opportunities_count }}</p>
                            
                            <div class="mt-3">
                                {% if status.running %}
                                <a href="/stop" class="btn btn-danger">Parar Agente</a>
                                {% else %}
                                <a href="/start" class="btn btn-success">Iniciar Agente</a>
                                {% endif %}
                                <a href="/opportunities" class="btn btn-primary">Ver Oportunidades</a>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-6">
                        <div class="info-card">
                            <h4>Informações</h4>
                            <p>O agente de trading esportivo monitora continuamente as odds de diferentes casas de apostas e identifica oportunidades de Back e Lay.</p>
                            <p>Quando encontra diferenças significativas entre as odds, o agente gera recomendações de trading com base em estratégias predefinidas.</p>
                            <p>Para ver as oportunidades identificadas, clique no botão "Ver Oportunidades".</p>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
</div>

<div class="row mt-4">
    <div class="col-md-12">
        <div class="card">
            <div class="card-header bg-info text-white">
                <h3>Resumo de Oportunidades</h3>
            </div>
            <div class="card-body">
                <div id="opportunities-summary">
                    <p>Carregando dados...</p>
                </div>
            </div>
        </div>
    </div>
</div>
{% endblock %}

{% block scripts %}
<script>
    // Atualizar status a cada 10 segundos
    setInterval(function() {
        $.getJSON('/status', function(data) {
            if (data.running) {
                $('.status-card h4 span').removeClass('bg-danger').addClass('bg-success').text('Em execução');
                $('.status-card .btn-success').hide();
                $('.status-card .btn-danger').show();
            } else {
                $('.status-card h4 span').removeClass('bg-success').addClass('bg-danger').text('Parado');
                $('.status-card .btn-danger').hide();
                $('.status-card .btn-success').show();
            }
            $('.status-card p:nth-child(2)').text('Última atualização: ' + data.last_update);
            $('.status-card p:nth-child(3)').text('Oportunidades ativas: ' + data.active_opportunities_count);
            $('.status-card p:nth-child(4)').text('Total de oportunidades: ' + data.opportunities_count);
        });
        
        // Atualizar resumo de oportunidades
        $.getJSON('/api/opportunities?active_only=true', function(data) {
            if (data.length === 0) {
                $('#opportunities-summary').html('<p>Nenhuma oportunidade ativa no momento.</p>');
                return;
            }
            
            var html = '<div class="table-responsive"><table class="table table-striped">';
            html += '<thead><tr><th>Evento</th><th>Time</th><th>Back</th><th>Lay</th><th>Diferença</th><th>Recomendação</th></tr></thead>';
            html += '<tbody>';
            
            // Mostrar apenas as 5 primeiras oportunidades
            var count = Math.min(data.length, 5);
            for (var i = 0; i < count; i++) {
                var opp = data[i];
                html += '<tr>';
                html += '<td>' + opp.home_team + ' vs ' + opp.away_team + '</td>';
                html += '<td>' + opp.team + '</td>';
                html += '<td>' + opp.back.bookmaker + ' @ ' + opp.back.price.toFixed(2) + '</td>';
                html += '<td>' + opp.lay.bookmaker + ' @ ' + opp.lay.price.toFixed(2) + '</td>';
                html += '<td>' + opp.difference_percent.toFixed(2) + '%</td>';
                html += '<td>' + opp.recommendation.action + '</td>';
                html += '</tr>';
            }
            
            html += '</tbody></table></div>';
            
            if (data.length > 5) {
                html += '<p><a href="/opportunities" class="btn btn-sm btn-info">Ver todas as ' + data.length + ' oportunidades</a></p>';
            }
            
            $('#opportunities-summary').html(html);
        });
    }, 10000);
    
    // Executar uma vez ao carregar a página
    $(document).ready(function() {
        $.getJSON('/api/opportunities?active_only=true', function(data) {
            if (data.length === 0) {
                $('#opportunities-summary').html('<p>Nenhuma oportunidade ativa no momento.</p>');
                return;
            }
            
            var html = '<div class="table-responsive"><table class="table table-striped">';
            html += '<thead><tr><th>Evento</th><th>Time</th><th>Back</th><th>Lay</th><th>Diferença</th><th>Recomendação</th></tr></thead>';
            html += '<tbody>';
            
            // Mostrar apenas as 5 primeiras oportunidades
            var count = Math.min(data.length, 5);
            for (var i = 0; i < count; i++) {
                var opp = data[i];
                html += '<tr>';
                html += '<td>' + opp.home_team + ' vs ' + opp.away_team + '</td>';
                html += '<td>' + opp.team + '</td>';
                html += '<td>' + opp.back.bookmaker + ' @ ' + opp.back.price.toFixed(2) + '</td>';
                html += '<td>' + opp.lay.bookmaker + ' @ ' + opp.lay.price.toFixed(2) + '</td>';
                html += '<td>' + opp.difference_percent.toFixed(2) + '%</td>';
                html += '<td>' + opp.recommendation.action + '</td>';
                html += '</tr>';
            }
            
            html += '</tbody></table></div>';
            
            if (data.length > 5) {
                html += '<p><a href="/opportunities" class="btn btn-sm btn-info">Ver todas as ' + data.length + ' oportunidades</a></p>';
            }
            
            $('#opportunities-summary').html(html);
        });
    });
</script>
{% endblock %}
"""
    
    # Criar arquivo opportunities.html
    opportunities_html = """{% extends 'base.html' %}

{% block content %}
<div class="card">
    <div class="card-header bg-primary text-white d-flex justify-content-between align-items-center">
        <h2>Oportunidades de Trading</h2>
        <div class="form-check form-switch">
            <
(Content truncated due to size limit. Use line ranges to read in chunks)