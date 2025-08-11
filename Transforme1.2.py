import streamlit as st
import json
import os
import time
from datetime import datetime

# --- CLASSE PARA GERENCIAR O ESTADO E A LÓGICA ---
class PredictiveAnalyzer:
    def __init__(self):
        self.emoji_map = {'C': '🔴', 'V': '🔵', 'E': '🟡'}
        self.color_names = {'C': 'Vermelho', 'V': 'Azul', 'E': 'Empate'}
        
        self.history = []
        self.signals = []
        self.performance = {'total': 0, 'hits': 0, 'misses': 0}
        self.analysis = {
            'patterns': [],
            'riskLevel': 'low',
            'manipulation': 'none',
            'prediction': None,
            'confidence': 0,
            'recommendation': 'observar'
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
                except json.JSONDecodeError:
                    st.warning("Arquivo de dados corrompido. Reiniciando o histórico.")
                    self.history = []
                    self.signals = []
                    self.performance = {'total': 0, 'hits': 0, 'misses': 0}

    def save_data(self):
        data = {
            'history': self.history,
            'signals': self.signals,
            'performance': self.performance
        }
        with open('analyzer_data.json', 'w') as f:
            json.dump(data, f, indent=4)

    # --- MÉTODOS DE AÇÃO DO USUÁRIO ---
    def add_outcome(self, outcome):
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.history.append({'result': outcome, 'timestamp': timestamp})
        
        self.verify_previous_prediction(outcome)
        self.analyze_data()
        
        if self.analysis['prediction'] is not None:
            self.signals.append({
                'time': timestamp,
                'patterns': self.analysis['patterns'],
                'prediction': self.analysis['prediction'],
                'correct': None
            })

        self.save_data()

    def undo_last(self):
        if self.history:
            self.history.pop()
            
            if self.signals and self.signals[-1].get('correct') is None:
                self.signals.pop()

            if self.history:
                self.analyze_data()
            else:
                self.analysis = {
                    'patterns': [], 'riskLevel': 'low', 'manipulation': 'none',
                    'prediction': None, 'confidence': 0, 'recommendation': 'observar'
                }
                
            self.save_data()
            return True
        return False
        
    def clear_history(self):
        self.history = []
        self.signals = []
        self.performance = {'total': 0, 'hits': 0, 'misses': 0}
        self.analysis = {
            'patterns': [], 'riskLevel': 'low', 'manipulation': 'none',
            'prediction': None, 'confidence': 0, 'recommendation': 'observar'
        }
        self.save_data()
    
    # --- MÉTODOS DE ANÁLISE ---
    def analyze_data(self):
        data = self.history
        if len(data) < 3:
            self.analysis = {
                'patterns': [], 'riskLevel': 'low', 'manipulation': 'none',
                'prediction': None, 'confidence': 0, 'recommendation': 'observar'
            }
            return

        recent_data = data[-27:]
        
        patterns = self.detect_patterns(recent_data)
        risk_level = self.assess_risk(recent_data)
        manipulation = self.detect_manipulation(recent_data)
        prediction_result = self.make_prediction(recent_data, patterns)
        
        self.analysis = {
            'patterns': patterns,
            'riskLevel': risk_level,
            'manipulation': manipulation,
            'prediction': prediction_result['color'],
            'confidence': prediction_result['confidence'],
            'recommendation': self.get_recommendation(risk_level, manipulation, patterns)
        }

    def detect_patterns(self, data):
        patterns = []
        results = [d['result'] for d in data]

        # Padrão: Sequência (Streak)
        current_streak = 1
        current_color = results[-1]
        for i in range(len(results) - 2, -1, -1):
            if results[i] == current_color:
                current_streak += 1
            else:
                break
        if current_streak >= 2:
            patterns.append({
                'type': 'streak',
                'color': current_color,
                'length': current_streak,
                'description': f"{current_streak}x {self.color_names[current_color]} seguidos"
            })
            
        # Padrão: Alternância
        if len(results) >= 2 and results[-1] != results[-2]:
            patterns.append({'type': 'alternating', 'description': 'Padrão alternado (Ex: C V C)'})

        # Padrão: 2x2
        if len(results) >= 4:
            last4 = results[-4:]
            if last4[0] == last4[1] and last4[2] == last4[3] and last4[0] != last4[2]:
                patterns.append({'type': '2x2', 'description': 'Padrão 2x2 (Ex: CCVV)'})
                
        # Padrão: 2x Repetição
        if len(results) >= 3 and results[-1] == results[-2] and results[-2] == results[-3]:
            patterns.append({'type': 'triple_rep', 'description': f'Padrão de repetição (Ex: {results[-1]} {results[-1]} {results[-1]})'})

        return patterns

    def assess_risk(self, data):
        results = [d['result'] for d in data]
        risk_score = 0
        
        # Streaks longos aumentam o risco
        max_streak = 1
        current_streak = 1
        if results:
            current_color = results[0]
            for i in range(1, len(results)):
                if results[i] == current_color:
                    current_streak += 1
                    max_streak = max(max_streak, current_streak)
                else:
                    current_streak = 1
                    current_color = results[i]
        
        if max_streak >= 5: risk_score += 40
        elif max_streak >= 4: risk_score += 25
        elif max_streak >= 3: risk_score += 10
        
        # Empates consecutivos
        tie_streak = 0
        for r in reversed(results):
            if r == 'E':
                tie_streak += 1
            else:
                break
        if tie_streak >= 2: risk_score += 30

        if risk_score >= 50: return 'Alto'
        if risk_score >= 25: return 'Médio'
        return 'Baixo'

    def detect_manipulation(self, data):
        results = [d['result'] for d in data]
        manipulation_score = 0
        
        # Alta frequência de empates
        if len(results) > 0 and results.count('E') / len(results) > 0.25:
            manipulation_score += 30
        
        # Padrões previsíveis
        if len(results) >= 6:
            recent6 = results[-6:]
            p1, p2 = recent6[:3], recent6[3:]
            if len(set(p1)) == 1 and len(set(p2)) == 1 and p1[0] != p2[0]:
                manipulation_score += 25

        if manipulation_score >= 40: return 'Alto'
        if manipulation_score >= 20: return 'Médio'
        return 'Baixo'
        
    def make_prediction(self, data, patterns):
        results = [d['result'] for d in data]
        last_result = results[-1]
        prediction = {'color': None, 'confidence': 0}
        
        # Lógica de previsão aprimorada
        streak = next((p for p in patterns if p['type'] == 'streak' and p['color'] != 'E'), None)
        alternating = next((p for p in patterns if p['type'] == 'alternating'), None)
        
        if streak and streak['length'] >= 3:
            other_colors = ['C', 'V']
            other_colors.remove(streak['color'])
            prediction['color'] = other_colors[0]
            prediction['confidence'] = min(95, 50 + streak['length'] * 8)
        elif alternating and last_result in ['C', 'V']:  # Só aplica se não for empate
            prediction['color'] = 'C' if last_result == 'V' else 'V'
            prediction['confidence'] = 75
        else:
            # Previsão padrão baseada no último resultado não-empate
            non_tie_results = [r for r in results if r != 'E']
            if non_tie_results:
                last_non_tie = non_tie_results[-1]
                prediction['color'] = 'C' if last_non_tie == 'V' else 'V'
                prediction['confidence'] = 55
            
        return prediction

    def get_recommendation(self, risk, manipulation, patterns):
        if risk == 'Alto' or manipulation == 'Alto':
            return 'Evitar'
        if patterns and risk == 'Baixo':
            return 'Apostar'
        return 'Observar'

    def verify_previous_prediction(self, current_outcome):
        for i in reversed(range(len(self.signals))):
            signal = self.signals[i]
            if signal.get('correct') is None:
                self.performance['total'] += 1
                if signal['prediction'] == current_outcome:
                    self.performance['hits'] += 1
                    signal['correct'] = "✅"
                else:
                    self.performance['misses'] += 1
                    signal['correct'] = "❌"
                return

    def get_accuracy(self):
        if self.performance['total'] == 0:
            return 0.0
        return (self.performance['hits'] / self.performance['total']) * 100

# --- INTERFACE DO USUÁRIO STREAMLIT ---
st.set_page_config(page_title="Sistema de Análise Preditiva - Versão Corrigida", layout="wide", page_icon="🎰")
st.title("🎰 Sistema de Análise Preditiva - Cassino")
st.markdown("---")

if 'analyzer' not in st.session_state:
    st.session_state.analyzer = PredictiveAnalyzer()

analyzer = st.session_state.analyzer

# --- SEÇÃO DE ENTRADA DE DADOS E CONTROLES ---
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

# --- VISUALIZAÇÃO DE ANÁLISE E RECOMENDAÇÃO ---
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
    </div>
    """, unsafe_allow_html=True)
    
    st.write(f"**Confiança:** {analysis['confidence']}%")
    st.write(f"**Recomendação:** {analysis['recommendation']}")
    st.write(f"**Nível de Risco:** {analysis['riskLevel']}")
    st.write(f"**Possível Manipulação:** {analysis['manipulation']}")

    if analysis['patterns']:
        st.write("### Padrões Detectados:")
        for p in analysis['patterns']:
            st.write(f"- {p['description']}")
else:
    st.info("Nenhum resultado registrado ainda. Adicione resultados para iniciar a análise.")

st.markdown("---")

# --- MÉTRICAS DE DESEMPENHO E HISTÓRICO ---
st.subheader("📊 Métricas de Desempenho")
accuracy = analyzer.get_accuracy()
col_met1, col_met2, col_met3 = st.columns(3)
col_met1.metric("Acurácia", f"{accuracy:.2f}%")
col_met2.metric("Total de Previsões", analyzer.performance['total'])
col_met3.metric("Acertos", analyzer.performance['hits'])

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
            <div><strong>Sinal para aposta em:</strong></div>
            <div style="font-size: 24px; font-weight: bold;">{display}</div>
            <div style="color: {'green' if status == '✅' else 'red' if status == '❌' else 'gray'}; font-weight: bold; font-size: 24px;">
                {status}
            </div>
        </div>
        """, unsafe_allow_html=True)
else:
    st.info("Registre resultados para que as sugestões e seu desempenho apareçam aqui.")
