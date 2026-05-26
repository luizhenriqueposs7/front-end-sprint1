"""
pages/dashboard.py
Dashboard de Telemetria — Visão operacional do ativo com gauges,
indicadores de saúde e integração da placa do motor.
"""

import streamlit as st
import plotly.graph_objects as go
from pathlib import Path
from services.equipamento_service import buscar_por_id, listar_equipamentos
from services.sensor_service import gerar_leitura, avaliar_status
from services.historico_service import garantir_historico, classificar_status


def _hex_para_rgba(hex_cor: str, alpha: float = 0.1) -> str:
    h = hex_cor.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r},{g},{b},{alpha})"

ASSETS_DIR = Path(__file__).parent.parent / "assets"

_GRANDEZAS = {
    "temperatura": {"label": "Temperatura", "icone": "🌡️", "unidade": "°C",  "max_range": 130, "decimais": 1},
    "vibracao":    {"label": "Vibração",    "icone": "📳", "unidade": "mm/s", "max_range": 20,  "decimais": 2},
    "corrente":    {"label": "Corrente",    "icone": "〰️", "unidade": "A",    "max_range": 50,  "decimais": 1},
    "tensao":      {"label": "Tensão",      "icone": "⚡", "unidade": "V",    "max_range": 500, "decimais": 0},
    "rpm":         {"label": "Velocidade",  "icone": "🔄", "unidade": "RPM",  "max_range": 4000, "decimais": 0},
}

_STATUS_CONFIG = {
    "normal":  {"label": "SAUDÁVEL",  "cor": "#10b981", "bg": "#052e16", "emoji": "🟢"},
    "atencao": {"label": "ATENÇÃO",   "cor": "#f59e0b", "bg": "#451a03", "emoji": "🟡"},
    "critico": {"label": "CRÍTICO",   "cor": "#ef4444", "bg": "#450a0a", "emoji": "🔴"},
}

_COR_STATUS = {"normal": "#10b981", "atencao": "#f59e0b", "critico": "#ef4444"}


def _criar_gauge(valor, maximo, unidade, status):
    cor = _COR_STATUS.get(status, "#6b7280")
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=valor,
        number={"suffix": f" {unidade}", "font": {"size": 22, "color": "#e5e7eb"}},
        gauge={
            "axis": {"range": [0, maximo], "tickcolor": "#4b5563", "tickfont": {"color": "#9ca3af", "size": 10}},
            "bar": {"color": cor, "thickness": 0.75},
            "bgcolor": "#1f2937",
            "borderwidth": 0,
            "steps": [
                {"range": [0, maximo * 0.6], "color": "rgba(6,78,59,0.13)"},
                {"range": [maximo * 0.6, maximo * 0.8], "color": "rgba(120,53,15,0.13)"},
                {"range": [maximo * 0.8, maximo], "color": "rgba(127,29,29,0.13)"},
            ],
        },
    ))
    fig.update_layout(
        height=180, margin=dict(l=20, r=20, t=30, b=10),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font={"color": "#e5e7eb"},
    )
    return fig


def _criar_sparkline(dados_hist, grandeza, cor):
    ultimas = dados_hist[-96:] if len(dados_hist) >= 96 else dados_hist
    valores = [r[grandeza]["valor"] for r in ultimas]
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=list(range(len(valores))), y=valores,
        mode="lines", line={"color": cor, "width": 2},
        fill="tozeroy", fillcolor=_hex_para_rgba(cor, 0.1),
        hoverinfo="skip",
    ))
    fig.update_layout(
        height=60, margin=dict(l=0, r=0, t=0, b=0),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        xaxis={"visible": False}, yaxis={"visible": False}, showlegend=False,
    )
    return fig


def render():
    equipamentos = listar_equipamentos()
    if not equipamentos:
        st.warning("Nenhum equipamento cadastrado.", icon="⚠️")
        return

    col_titulo, col_sel = st.columns([3, 2])
    with col_titulo:
        st.markdown("""
        <h1 style="margin:0;"><span style="background:linear-gradient(135deg,#10b981,#3b82f6);
        -webkit-background-clip:text;-webkit-text-fill-color:transparent;">
        📊 Dashboard de Telemetria</span></h1>
        <p style="color:#9ca3af;margin-top:4px;">Monitoramento em tempo real do ativo</p>
        """, unsafe_allow_html=True)

    with col_sel:
        eq_id = st.session_state.get("equipamento_selecionado")
        opcoes = {f"{e['tag']} — {e['modelo']}": e["id"] for e in equipamentos}
        sel_label = next((k for k, v in opcoes.items() if v == eq_id), list(opcoes.keys())[0])
        escolha = st.selectbox("Equipamento", list(opcoes.keys()),
                               index=list(opcoes.keys()).index(sel_label), label_visibility="collapsed")
        eq_id = opcoes[escolha]
        eq = buscar_por_id(eq_id)
        st.session_state["equipamento_selecionado"] = eq_id

    st.markdown("---")

    leitura = gerar_leitura(eq)
    status_global = avaliar_status(leitura)
    cfg_s = _STATUS_CONFIG[status_global]
    dados_hist = garantir_historico(eq)

    # ── Semáforo global ───────────────────────────────────────────────────────
    st.markdown(f"""
    <div style="background:linear-gradient(135deg,{cfg_s['bg']},#111827);
    border:1px solid {cfg_s['cor']}44;border-left:4px solid {cfg_s['cor']};
    border-radius:12px;padding:16px 24px;margin-bottom:20px;display:flex;align-items:center;gap:16px;">
        <div style="font-size:2.5em;">{cfg_s['emoji']}</div>
        <div>
            <div style="font-size:1.4em;font-weight:700;color:{cfg_s['cor']};">Status: {cfg_s['label']}</div>
            <div style="color:#9ca3af;font-size:0.9em;">Motor <strong style="color:#e5e7eb">{eq.get('tag','—')}</strong> · {eq.get('modelo','—')} · {eq.get('localizacao','—')}</div>
        </div>
        <div style="margin-left:auto;text-align:right;">
            <div style="color:#6b7280;font-size:0.75em;">POTÊNCIA</div>
            <div style="color:#e5e7eb;font-size:1.1em;font-weight:600;">{eq.get('potencia_kw','—')} kW</div>
        </div>
        <div style="text-align:right;">
            <div style="color:#6b7280;font-size:0.75em;">FREQUÊNCIA</div>
            <div style="color:#e5e7eb;font-size:1.1em;font-weight:600;">{eq.get('frequencia_hz','—')} Hz</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Gauges ────────────────────────────────────────────────────────────────
    colunas = st.columns(5)
    for col, (chave, cfg) in zip(colunas, _GRANDEZAS.items()):
        with col:
            dado = leitura.get(chave)
            valor = dado["valor"] if dado else 0
            nominal = dado.get("nominal", 0) if dado else 0
            status_g = classificar_status(chave, valor, nominal)

            st.markdown(f"""<div style="background:#111827;border:1px solid #1f2937;
            border-top:3px solid {_COR_STATUS[status_g]};border-radius:10px;padding:12px 8px 4px;text-align:center;">
            <div style="font-size:0.8em;color:#9ca3af;">{cfg['icone']} {cfg['label']}</div></div>""",
            unsafe_allow_html=True)

            st.plotly_chart(_criar_gauge(valor, cfg["max_range"], cfg["unidade"], status_g),
                           use_container_width=True, config={"displayModeBar": False})

            if dados_hist:
                st.plotly_chart(_criar_sparkline(dados_hist, chave, _COR_STATUS[status_g]),
                               use_container_width=True, config={"displayModeBar": False})

    # ── Placa do motor ────────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("### 🏭 Identificação do Ativo")
    col_placa, col_dados = st.columns([1, 2])

    with col_placa:
        tag = eq.get("tag", "UNKNOWN")
        img_path = ASSETS_DIR / f"placa_{tag}.png"
        if img_path.exists():
            st.image(str(img_path), caption=f"Placa — {tag}", use_container_width=True)
        else:
            st.markdown(f"""
            <div style="background:linear-gradient(145deg,#d4d4d8,#a1a1aa);border:3px solid #71717a;
            border-radius:8px;padding:20px;font-family:'Courier New',monospace;color:#18181b;
            box-shadow:inset 0 2px 4px rgba(0,0,0,0.3);">
                <div style="text-align:center;font-size:1.2em;font-weight:bold;border-bottom:2px solid #52525b;padding-bottom:6px;margin-bottom:10px;">{eq.get('fabricante','—')}</div>
                <table style="width:100%;font-size:0.85em;color:#27272a;">
                    <tr><td style="padding:3px 0;"><b>MODELO:</b></td><td>{eq.get('modelo','—')}</td></tr>
                    <tr><td style="padding:3px 0;"><b>TAG:</b></td><td>{tag}</td></tr>
                    <tr><td style="padding:3px 0;"><b>POTÊNCIA:</b></td><td>{eq.get('potencia_kw','—')} kW</td></tr>
                    <tr><td style="padding:3px 0;"><b>TENSÃO:</b></td><td>{eq.get('tensao_v','—')} V</td></tr>
                    <tr><td style="padding:3px 0;"><b>CORRENTE:</b></td><td>{eq.get('corrente_nominal_a','—')} A</td></tr>
                    <tr><td style="padding:3px 0;"><b>FREQ:</b></td><td>{eq.get('frequencia_hz','—')} Hz</td></tr>
                    <tr><td style="padding:3px 0;"><b>POLOS:</b></td><td>{eq.get('n_polos','—')}</td></tr>
                    <tr><td style="padding:3px 0;"><b>RPM:</b></td><td>{eq.get('velocidade_rpm','—')}</td></tr>
                </table>
                <div style="text-align:center;margin-top:10px;font-size:0.7em;color:#52525b;">Cadastro: {eq.get('data_cadastro','—')}</div>
            </div>""", unsafe_allow_html=True)

    with col_dados:
        rows = [
            ("Identificação (TAG)", eq.get('tag','—')),
            ("Fabricante / Modelo", f"{eq.get('fabricante','—')} · {eq.get('modelo','—')}"),
            ("Potência Nominal", f"{eq.get('potencia_kw','—')} kW"),
            ("Tensão / Corrente", f"{eq.get('tensao_v','—')} V · {eq.get('corrente_nominal_a','—')} A"),
            ("Frequência / Polos", f"{eq.get('frequencia_hz','—')} Hz · {eq.get('n_polos','—')} polos"),
            ("Velocidade Nominal", f"{eq.get('velocidade_rpm','—')} RPM"),
            ("Localização", eq.get('localizacao','—')),
            ("Status Operacional", eq.get('status','—')),
        ]
        trs = "".join(f'<tr style="border-bottom:1px solid #1f2937;"><td style="padding:8px 0;color:#9ca3af;">{l}</td><td style="padding:8px 0;font-weight:600;">{v}</td></tr>' for l, v in rows)
        st.markdown(f"""<div style="background:#111827;border:1px solid #1f2937;border-radius:10px;padding:20px;">
        <h4 style="color:#e5e7eb;margin-top:0;">📋 Dados Técnicos Extraídos</h4>
        <table style="width:100%;color:#d1d5db;font-size:0.95em;">{trs}</table></div>""", unsafe_allow_html=True)

    st.markdown("")
    c1, c2, c3, _ = st.columns([1, 1, 1, 3])
    with c1:
        if st.button("📈 Ver Histórico", use_container_width=True, type="primary"):
            st.session_state["pagina"] = "historico"
            st.rerun()
    with c2:
        if st.button("📡 Dados Brutos", use_container_width=True):
            st.session_state["pagina"] = "dados_brutos"
            st.rerun()
    with c3:
        if st.button("📋 Ficha Técnica", use_container_width=True):
            st.session_state["pagina"] = "cadastro"
            st.rerun()
