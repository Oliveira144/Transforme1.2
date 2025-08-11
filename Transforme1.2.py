import streamlit as st
import json
import os
import time
from datetime import datetime
import numpy as np

class PredictiveAnalyzer:
    def __init__(self):
        self.emoji_map = {'C': '🔴', 'V': '🔵', 'E': '🟡'}
        self.color_names = {'C': 'Vermelho', 'V': 'Azul', 'E': 'Empate'}
        
        # --- Dados persistentes ---
        self.history = []
        self.signals = []
        self.performance = {'total': 0, 'hits': 0, 'misses': 0}
        self.pattern_scores = {
            'alternating': {'hits': 0, 'total': 0, 'priority': 3},
            'streak_end': {'hits': 0, 'total': 0, 'priority': 2},
            '2x2': {'hits': 0, 'total': 0, 'priority': 1}
        }
        
        # --- Análise atual ---
        self.analysis = {
            'patterns': [],
            'riskLevel': 'Baixo',
            'volatility': 'Baixa',
            'prediction': None,
            'confidence': 0,
            'recommendation': 'Observar'
        }
        
        self.load_data()

    # --- MÉTODOS DE GERENCIAMENTO DE DADOS PERSISTENTES ---
    def load_data(self):
        if os.path.exists('analyzer_data.json'):
            with open('analyzer_data.json', 'r') as f:
                try:
                    data = json.load(f)
                    self.history = data.get('history', [])
                    self.signals = data.get('signals', [])
                    self.performance = data.get('performance', {'total': 0, 'hits': 0, 'misses': 0})
                    self.pattern_scores = data.get('pattern_scores', self.pattern_scores)
                except json.JSONDecodeError:
                    st.warning("Arquivo de dados corrompido. Reiniciando o histórico.")
                    self.clear_history()
    
    def save_data(self):
        data = {
            'history': self.history,
            'signals': self.signals,
            'performance': self.performance,
            'pattern_scores': self.pattern_scores
        }
        with open('analyzer_data.json', 'w') as f:
            json.dump(data, f, indent=4)
    
    # --- MÉTODOS DE AÇÃO DO USUÁRIO ---
    def add_outcome(self, outcome):
        # 1. Verifica a previsão da rodada anterior antes de adicionar o novo resultado
        self.verify_previous_prediction(outcome)
        
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.history.append({'result': outcome, 'timestamp': timestamp})
        
        # 2. Reanalisa os dados e gera a nova previsão para a próxima rodada
        self.analyze_data()
        
        # 3. Adiciona o novo sinal (previsão para a próxima rodada)
        if self.analysis['prediction'] is not None:
            self.signals.append({
                'time': timestamp,
                'patterns': self.analysis['patterns'],
                'prediction': self.analysis['prediction'],
                'correct': None,
                'confidence': self.analysis['confidence']
            })

        self.save_data()

    def undo_last(self):
        if self.history:
            # Reverte a pontuação se a última jogada tiver uma previsão pendente
            if self.signals and self.signals[-1].get('correct') is None:
                self.signals.pop()
            
            # Remove o último resultado do histórico
            self.history.pop()

            # Recalcula a análise
            if self.history:
                self.analyze_data()
            else:
                self.analysis = {
                    'patterns': [], 'riskLevel': 'Baixo', 'volatility': 'Baixa',
                    'prediction': None, 'confidence': 0, 'recommendation': 'Observar'
                }
                
            self.save_data()
            return True
        return False
        
    def clear_history(self):
        self.history = []
        self.signals = []
        self.performance = {'total': 0, 'hits': 0, 'misses': 0}
        self.pattern_scores = {
            'alternating': {'hits': 0, 'total': 0, 'priority': 3},
            'streak_end': {'hits': 0, 'total': 0, 'priority': 2},
            '2x2': {'hits': 0, 'total': 0, 'priority': 1}
        }
        self.analysis = {
            'patterns': [], 'riskLevel': 'Baixo', 'volatility': 'Baixa',
            'prediction': None, 'confidence': 0, 'recommendation': 'Observar'
        }
        self.save_data()
    
    # --- MÉTODOS DE ANÁLISE E APRENDIZADO DA IA ---
    def analyze_data(self):
        data = self.history
        if len(data) < 3:
            self.analysis = {
                'patterns': [], 'riskLevel': 'Baixo', 'volatility': 'Baixa',
                'prediction': None, 'confidence': 0, 'recommendation': 'Observar'
            }
            return

        recent_data = data[-90:]
        
        patterns = self.detect_patterns(recent_data)
        risk_level = self._calculate_statistical_bias(recent_data)
        volatility = self._assess_volatility(recent_data)
        prediction_result = self.make_prediction(recent_data, patterns)
        
        self.analysis = {
            'patterns': patterns,
            'riskLevel': risk_level,
            'volatility': volatility,
            'prediction': prediction_result['color'],
            'confidence': prediction_result['confidence'],
            'recommendation': self.get_recommendation(risk_level, volatility, prediction_result['confidence'])
        }

    def detect_patterns(self, data):
        patterns = []
        results = [d['result'] for d in data]

        # Padrão: Alternância
        if len(results) >= 2 and results[-1] != results[-2] and len(set(results[-2:])) == 2:
            patterns.append({
                'type': 'alternating',
                'description': f'Padrão alternado (Ex: {results[-2]} {results[-1]}...)'
            })
        
        # Padrão: Fim de Sequência
        if len(results) >= 2 and results[-1] != results[-2]:
            streak_length = 1
            for i in range(len(results) - 2, -1, -1):
                if results[i] == results[-2]:
                    streak_length += 1
                else:
                    break
            if streak_length >= 2:
                patterns.append({
                    'type': 'streak_end',
                    'color': results[-2],
                    'length': streak_length,
                    'description': f'Fim de Sequência: {streak_length}x {self.color_names[results[-2]]}'
                })

        # Padrão: 2x2
        if len(results) >= 4:
            last4 = results[-4:]
            if last4[0] == last4[1] and last4[2] == last4[3] and last4[0] != last4[2]:
                patterns.append({
                    'type': '2x2',
                    'description': 'Padrão 2x2 (Ex: CCVV)'
                })

        return patterns

    def _calculate_statistical_bias(self, data):
        results = [d['result'] for d in data]
        if not results: return 'Baixo'
        
        c_count = results.count('C')
        v_count = results.count('V')
        e_count = results.count('E')
        
        total_non_tie = c_count + v_count
        
        # Análise do desvio de empates
        expected_e_ratio = 0.027  # Probabilidade teórica de empate
        actual_e_ratio = e_count / len(results)
        
        if actual_e_ratio > expected_e_ratio * 3 or e_count >= 3:
            return 'Alto'

        # Análise do desvio entre C e V
        if total_non_tie > 0:
            c_ratio = c_count / total_non_tie
            v_ratio = v_count / total_non_tie
            
            if abs(c_ratio - 0.5) > 0.15 or abs(v_ratio - 0.5) > 0.15:
                 return 'Médio'
                 
        return 'Baixo'

    def _assess_volatility(self, data):
        results = [d['result'] for d in data]
        if len(results) < 5: return 'Baixa'
        
        # Contagem de mudanças de cor
        changes = 0
        for i in range(1, len(results)):
            if results[i] != results[i-1]:
                changes += 1
        
        change_rate = changes / len(results)
        
        if change_rate < 0.2:
            return 'Alta' # Menos mudanças = sequências longas
        if change_rate > 0.6:
            return 'Baixa' # Muitas mudanças = alternância
        
        return 'Média'

    def make_prediction(self, data, patterns):
        results = [d['result'] for d in data]
        last_result = results[-1]
        
        # Padrão de maior prioridade
        best_pattern_type = None
        highest_priority = 0
        
        # Ajusta prioridade com base na taxa de acerto do aprendizado
        for p_type, scores in self.pattern_scores.items():
            if scores['total'] > 5 and scores['hits'] / scores['total'] > 0.5:
                scores['priority'] = int(min(5, (scores['hits'] / scores['total']) * 5))
            else:
                scores['priority'] = max(1, scores['priority'] - 1)
        
        for p in patterns:
            p_type = p['type']
            priority = self.pattern_scores.get(p_type, {}).get('priority', 1)
            
            if priority > highest_priority:
                highest_priority = priority
                best_pattern_type = p_type
                
        # Faz a previsão com base no padrão de maior prioridade
        prediction = {'color': None, 'confidence': 0, 'pattern_type': None}
        if best_pattern_type == 'alternating':
            prediction['color'] = 'C' if last_result == 'V' else 'V'
            prediction['pattern_type'] = 'alternating'
        elif best_pattern_type == 'streak_end':
            # Previsão: quebra da sequência
            streak_color = [p['color'] for p in patterns if p['type'] == 'streak_end'][0]
            prediction['color'] = 'C' if streak_color == 'V' else 'V'
            prediction['pattern_type'] = 'streak_end'
        elif best_pattern_type == '2x2':
            prediction['color'] = 'C' if last_result == 'V' else 'V'
            prediction['pattern_type'] = '2x2'
        
        if prediction['pattern_type']:
            p_type = prediction['pattern_type']
            scores = self.pattern_scores[p_type]
            if scores['total'] > 0:
                prediction['confidence'] = int((scores['hits'] / scores['total']) * 100)
            else:
                prediction['confidence'] = 50
        
        return prediction

    def get_recommendation(self, risk, volatility, confidence):
        if risk == 'Alto' or volatility == 'Alta':
            return 'Evitar'
        if confidence > 65 and risk == 'Baixo' and volatility == 'Baixa':
            return 'Apostar'
        return 'Observar'

    def verify_previous_prediction(self, current_outcome):
        for i in reversed(range(len(self.signals))):
            signal = self.signals[i]
            if signal.get('correct') is None:
                self.performance['total'] += 1
                
                # Aplica o aprendizado adaptativo
                if signal['prediction'] == current_outcome:
                    self.performance['hits'] += 1
                    signal['correct'] = "✅"
                    self._update_learning_score(signal, was_correct=True)
                else:
                    self.performance['misses'] += 1
                    signal['correct'] = "❌"
                    self._update_learning_score(signal, was_correct=False)
                return

    def _update_learning_score(self, signal, was_correct):
        for p in signal['patterns']:
            p_type = p['type']
            if p_type in self.pattern_scores:
                self.pattern_scores[p_type]['total'] += 1
                if was_correct:
                    self.pattern_scores[p_type]['hits'] += 1

    def get_accuracy(self):
        if self.performance['total'] == 0:
            return 0.0
        return (self.performance['hits'] / self.performance['total']) * 100

# --- INTERFACE DO USUÁRIO STREAMLIT ---
st.set_page_config(page_title="Sistema de Análise Preditiva - IA Avançada", layout="wide", page_icon="🎰")
st.title("🎰 Sistema de Análise Preditiva - Cassino")
st.markdown("---")

if 'analyzer' not in st.session_state:
    st.session_state.analyzer = PredictiveAnalyzer()

analyzer = st.session_state.analyzer

# SEÇÃO DE ENTRADA DE DADOS E CONTROLES
st.subheader("Entrada de Resultados")
col1, col2, col3 = st.columns(3)
with col1:
    if st.button("🔴 Vermelho (C)", use_container_width=True, type="primary"):
        analyzer.add_outcome('C')
        st.rerun()
with col2:
    if st.button("🔵 Azul (V)", use_container_width=True, type="primary"):
        analyzer.add_outcome('V')
        st.rerun()
with col3:
    if st.button("🟡 Empate (E)", use_container_width=True, type="primary"):
        analyzer.add_outcome('E')
        st.rerun()

st.markdown("<br>", unsafe_allow_html=True)
cols_controls = st.columns(2)
with cols_controls[0]:
    if st.button("↩️ Desfazer Último", use_container_width=True, type="secondary"):
        analyzer.undo_last()
        st.rerun()
with cols_controls[1]:
    if st.button("🗑️ Limpar Tudo", use_container_width=True, type="secondary"):
        analyzer.clear_history()
        st.rerun()

st.markdown("---")

# VISUALIZAÇÃO DE ANÁLISE E RECOMENDAÇÃO
st.subheader("📈 Análise Atual")
analysis = analyzer.analysis

if analysis['prediction']:
    display_prediction = analyzer.emoji_map.get(analysis['prediction']) + " " + analyzer.color_names.get(analysis['prediction'], "...")
    bg_color_prediction = ""
    if analysis['prediction'] == 'C': bg_color_prediction = "rgba(255, 0, 0, 0.2)"
    elif analysis['prediction'] == 'V': bg_color_prediction = "rgba(0, 0, 255, 0.2)"
    else: bg_color_prediction = "rgba(255, 255, 0, 0.2)"

    st.markdown(f"""
    <div style="
        background: {bg_color_prediction};
        border-radius: 15px;
        padding: 20px;
        margin: 20px 0;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        box-shadow: 0 6px 12px rgba(0,0,0,0.2);
        border: 2px solid #fff;
    ">
        <div style="font-size: 20px; font-weight: bold; margin-bottom: 10px;">
            Sugestão para a Próxima Rodada:
        </div>
        <div style="font-size: 40px; font-weight: bold; color: #fff; text-shadow: 2px 2px 4px rgba(0,0,0,0.5);">
            {display_prediction}
        </div>
        <div style="font-size: 24px; margin-top: 10px;">
            Confiança: {analysis['confidence']}%
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    st.write(f"**Recomendação:** {analysis['recommendation']}")
    st.write(f"**Nível de Risco Estatístico:** {analysis['riskLevel']}")
    st.write(f"**Nível de Volatilidade:** {analysis['volatility']}")

    if analysis['patterns']:
        st.write("### Padrões Detectados:")
        for p in analysis['patterns']:
            p_type = p['type']
            score = analyzer.pattern_scores.get(p_type, {'priority': 0})
            st.write(f"- {p['description']} (Prioridade: {score['priority']})")
else:
    st.info("Nenhum resultado registrado ainda. Adicione resultados para iniciar a análise.")

st.markdown("---")

# MÉTRICAS DE DESEMPENHO E HISTÓRICO
st.subheader("📊 Métricas de Desempenho")
accuracy = analyzer.get_accuracy()
col_met1, col_met2, col_met3 = st.columns(3)
col_met1.metric("Acurácia Geral", f"{accuracy:.2f}%")
col_met2.metric("Total de Previsões", analyzer.performance['total'])
col_met3.metric("Acertos", analyzer.performance['hits'])

# Adicionando gráfico de desempenho
if analyzer.performance['total'] > 0:
    hit_rate = analyzer.performance['hits'] / analyzer.performance['total']
    miss_rate = analyzer.performance['misses'] / analyzer.performance['total']
    
    chart_data = {
        'Métrica': ['Acertos', 'Erros'],
        'Taxa': [hit_rate, miss_rate]
    }
    st.bar_chart(chart_data, x='Métrica', y='Taxa', use_container_width=True)

st.markdown("---")

st.subheader("🎲 Histórico de Resultados")
if analyzer.history:
    max_results = 90
    recent_history = analyzer.history[-max_results:][::-1]
    
    lines = []
    for i in range(0, len(recent_history), 9):
        row = recent_history[i:i+9]
        emojis = [analyzer.emoji_map[r['result']] for r in row]
        lines.append(" ".join(emojis))
    
    for line in lines:
        st.markdown(f"<div style='font-size: 24px;'>**{line}**</div>", unsafe_allow_html=True)
else:
    st.info("Nenhum resultado inserido ainda.")

st.markdown("---")

st.subheader("📑 Últimas Sugestões Geradas")
if analyzer.signals:
    for signal in analyzer.signals[-5:][::-1]:
        display = analyzer.emoji_map.get(signal['prediction']) + " " + analyzer.color_names.get(signal['prediction'], "...")
        status = signal.get('correct', '...')
        confidence = signal.get('confidence', 0)
        bg_color = "rgba(0, 255, 0, 0.1)" if status == "✅" else "rgba(255, 0, 0, 0.1)" if status == "❌" else "rgba(128, 128, 128, 0.1)"
        
        st.markdown(f"""
        <div style="
            background: {bg_color};
            border-radius: 10px;
            padding: 12px;
            margin: 10px 0;
            display: flex;
            justify-content: space-between;
            align-items: center;
            box-shadow: 0 4px 8px rgba(0,0,0,0.1);
        ">
            <div>
                <strong>Sinal para aposta em:</strong><br>
                <small>{signal['time']}</small>
            </div>
            <div style="font-size: 24px; font-weight: bold;">{display}</div>
            <div style="font-size: 16px;">Confiança: {confidence}%</div>
            <div style="color: {'green' if status == '✅' else 'red' if status == '❌' else 'gray'}; 
                         font-weight: bold; font-size: 24px;">
                {status}
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        if 'patterns' in signal and signal['patterns']:
            patterns_info = " | ".join([p['description'] for p in signal['patterns']])
            st.caption(f"Padrões: {patterns_info}")
else:
    st.info("Registre resultados para que as sugestões e seu desempenho apareçam aqui.")

