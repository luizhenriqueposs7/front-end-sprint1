"""
pages/historico.py
Gráficos de Séries Temporais — Análise de tendências históricas
com faixas de limite operacional e tabela de eventos críticos.
"""

import streamlit as st
import plotly.graph_objects as go
from datetime import datetime, timedelta
from services.equipamento_service import buscar_por_id, listar_equipamentos
from services.historico_service import (
    garantir_historico, regenerar_historico, extrair_eventos_criticos, LIMITES,
)

_COR_GRANDEZA = {
    "temperatura": "#ef4444",
    "vibracao":    "#f59e0b",
    "corrente":    "#3b82f6",
    "tensao":      "#8b5cf6",
    "rpm":         "#10b981",
}

_LABEL = {
    "temperatura": "Temperatura (°C)",
    "vibracao":    "Vibração (mm/s)",
    "corrente":    "Corrente (A)",
    "tensao":      "Tensão (V)",
    "rpm":         "Velocidade (RPM)",
}


def _grafico_serie(dados, grandeza, eq, periodo_dias):
    """Cria gráfico de série temporal com faixas de limite."""
    agora = datetime.now()
    inicio = agora - timedelta(days=periodo_dias)
    filtrado = [r for r in dados if datetime.fromisoformat(r["timestamp"]) >= inicio]

    if not filtrado:
        st.info("Sem dados para o período selecionado.")
        return

    timestamps = [r["timestamp"] for r in filtrado]
    valores = [r[grandeza]["valor"] for r in filtrado]
    cor = _COR_GRANDEZA[grandeza]

    fig = go.Figure()

    # Faixas de limite (só para temperatura e vibração com limites absolutos)
    lim = LIMITES.get(grandeza, {})
    if "normal" in lim:
        y_max = max(valores) * 1.2 if valores else 100
        fig.add_hrect(y0=0, y1=lim["normal"], fillcolor="rgba(16,185,129,0.08)",
                      line_width=0, annotation_text="Normal", annotation_position="top left",
                      annotation_font_color="#10b981")
        fig.add_hrect(y0=lim["normal"], y1=lim["atencao"], fillcolor="rgba(245,158,11,0.08)",
                      line_width=0, annotation_text="Atenção", annotation_position="top left",
                      annotation_font_color="#f59e0b")
        fig.add_hrect(y0=lim["atencao"], y1=y_max, fillcolor="rgba(239,68,68,0.08)",
                      line_width=0, annotation_text="Crítico", annotation_position="top left",
                      annotation_font_color="#ef4444")
        fig.add_hline(y=lim["normal"], line_dash="dash", line_color="rgba(16,185,129,0.4)", line_width=1)
        fig.add_hline(y=lim["atencao"], line_dash="dash", line_color="rgba(245,158,11,0.4)", line_width=1)
    else:
        # Para grandezas com limites percentuais, mostrar faixa nominal
        nome_campo = {"corrente": "corrente_nominal_a", "tensao": "tensao_v", "rpm": "velocidade_rpm"}
        nominal = float(eq.get(nome_campo.get(grandeza, ""), 0))
        if nominal > 0:
            pct_n = lim.get("normal_pct", 5)
            pct_a = lim.get("atencao_pct", 12)
            fig.add_hrect(y0=nominal * (1 - pct_n/100), y1=nominal * (1 + pct_n/100),
                          fillcolor="rgba(16,185,129,0.06)", line_width=0)
            fig.add_hline(y=nominal, line_dash="dot", line_color="#6b7280", line_width=1,
                          annotation_text=f"Nominal: {nominal}", annotation_font_color="#9ca3af")

    # Linha principal
    fig.add_trace(go.Scatter(
        x=timestamps, y=valores, mode="lines",
        line={"color": cor, "width": 2},
        fill="tozeroy", fillcolor=f"rgba({int(cor[1:3],16)},{int(cor[3:5],16)},{int(cor[5:7],16)},0.06)",
        name=_LABEL[grandeza],
        hovertemplate="%{x}<br>%{y:.2f}<extra></extra>",
    ))

    fig.update_layout(
        height=350,
        margin=dict(l=10, r=10, t=40, b=10),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="#0f172a",
        font={"color": "#e5e7eb"},
        xaxis={"gridcolor": "#1e293b", "title": None, "showgrid": True},
        yaxis={"gridcolor": "#1e293b", "title": _LABEL[grandeza], "showgrid": True},
        hovermode="x unified",
        showlegend=False,
    )
    return fig


def _grafico_combinado(dados, grandezas_sel, periodo_dias):
    """Gráfico overlay com múltiplas grandezas normalizadas (0-100%)."""
    agora = datetime.now()
    inicio = agora - timedelta(days=periodo_dias)
    filtrado = [r for r in dados if datetime.fromisoformat(r["timestamp"]) >= inicio]

    if not filtrado:
        st.info("Sem dados para o período selecionado.")
        return None

    fig = go.Figure()
    timestamps = [r["timestamp"] for r in filtrado]

    for g in grandezas_sel:
        valores = [r[g]["valor"] for r in filtrado]
        v_min, v_max = min(valores), max(valores)
        rng = v_max - v_min if v_max != v_min else 1
        normalizados = [(v - v_min) / rng * 100 for v in valores]

        fig.add_trace(go.Scatter(
            x=timestamps, y=normalizados, mode="lines",
            line={"color": _COR_GRANDEZA[g], "width": 2},
            name=_LABEL[g],
            hovertemplate=f"{_LABEL[g]}: %{{customdata:.2f}}<extra></extra>",
            customdata=valores,
        ))

    fig.update_layout(
        height=350,
        margin=dict(l=10, r=10, t=40, b=10),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="#0f172a",
        font={"color": "#e5e7eb"},
        xaxis={"gridcolor": "#1e293b", "showgrid": True},
        yaxis={"gridcolor": "#1e293b", "title": "Valor Normalizado (%)", "showgrid": True},
        hovermode="x unified",
        legend={"orientation": "h", "y": -0.15, "font": {"size": 11}},
    )
    return fig


def render():
    st.markdown("""
    <h1 style="margin:0;"><span style="background:linear-gradient(135deg,#f59e0b,#ef4444);
    -webkit-background-clip:text;-webkit-text-fill-color:transparent;">
    📈 Histórico de Telemetria</span></h1>
    <p style="color:#9ca3af;margin-top:4px;">Análise de tendências e detecção de anomalias</p>
    """, unsafe_allow_html=True)
    st.markdown("---")

    equipamentos = listar_equipamentos()
    if not equipamentos:
        st.warning("Nenhum equipamento cadastrado.", icon="⚠️")
        return

    # ── Controles ─────────────────────────────────────────────────────────────
    c1, c2, c3 = st.columns([2, 1.5, 1])
    with c1:
        eq_id = st.session_state.get("equipamento_selecionado")
        opcoes = {f"{e['tag']} — {e['modelo']}": e["id"] for e in equipamentos}
        sel = next((k for k, v in opcoes.items() if v == eq_id), list(opcoes.keys())[0])
        escolha = st.selectbox("Equipamento", list(opcoes.keys()),
                               index=list(opcoes.keys()).index(sel))
        eq_id = opcoes[escolha]
        eq = buscar_por_id(eq_id)
        st.session_state["equipamento_selecionado"] = eq_id

    with c2:
        periodo = st.selectbox("Período", ["7 dias", "15 dias", "30 dias"], index=2)
        periodo_dias = int(periodo.split()[0])

    with c3:
        st.markdown("")
        if st.button("🔄 Regenerar Dados", use_container_width=True, help="Gera novo histórico simulado"):
            regenerar_historico(eq)
            st.rerun()

    dados = garantir_historico(eq)
    if not dados:
        st.info("Nenhum dado histórico disponível.", icon="📊")
        return

    st.markdown("---")

    # ── Gráficos individuais ──────────────────────────────────────────────────
    tabs = st.tabs(["🌡️ Temperatura", "📳 Vibração", "〰️ Corrente", "⚡ Tensão", "🔄 RPM", "📊 Combinado"])

    grandezas_keys = ["temperatura", "vibracao", "corrente", "tensao", "rpm"]

    for i, g in enumerate(grandezas_keys):
        with tabs[i]:
            fig = _grafico_serie(dados, g, eq, periodo_dias)
            if fig:
                st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": True})

    # Tab combinado
    with tabs[5]:
        grandezas_sel = st.multiselect(
            "Grandezas para comparar",
            grandezas_keys,
            default=["temperatura", "vibracao", "corrente"],
            format_func=lambda x: _LABEL[x],
        )
        if grandezas_sel:
            fig_c = _grafico_combinado(dados, grandezas_sel, periodo_dias)
            if fig_c:
                st.plotly_chart(fig_c, use_container_width=True, config={"displayModeBar": True})

    # ── Eventos críticos ──────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("### 🚨 Eventos Críticos Detectados")

    agora = datetime.now()
    inicio_filtro = agora - timedelta(days=periodo_dias)
    eventos = extrair_eventos_criticos(dados)
    eventos_filtrados = [
        e for e in eventos
        if datetime.fromisoformat(e["timestamp"]) >= inicio_filtro
    ]

    if not eventos_filtrados:
        st.success("Nenhum evento crítico no período selecionado! ✅", icon="🎉")
    else:
        st.markdown(f"""
        <div style="background:#450a0a;border:1px solid #ef444444;border-radius:10px;padding:12px 16px;margin-bottom:12px;">
            <span style="color:#ef4444;font-weight:700;font-size:1.1em;">⚠️ {len(eventos_filtrados)} evento(s) crítico(s)</span>
            <span style="color:#9ca3af;margin-left:8px;">nos últimos {periodo_dias} dias</span>
        </div>
        """, unsafe_allow_html=True)

        # Tabela de eventos
        for ev in eventos_filtrados[-20:]:  # Mostrar os 20 mais recentes
            ts = ev["timestamp"]
            gs = ", ".join(ev["grandezas"])
            vals = " · ".join(f"{g}: {v}" for g, v in ev["valores"].items())
            st.markdown(f"""
            <div style="background:#0f172a;border:1px solid #1e293b;border-radius:8px;
            padding:8px 14px;margin-bottom:4px;display:flex;align-items:center;gap:12px;">
                <span style="color:#ef4444;">🔴</span>
                <span style="color:#6b7280;font-size:0.85em;min-width:140px;">{ts}</span>
                <span style="color:#d1d5db;font-size:0.85em;">{gs}</span>
                <span style="color:#9ca3af;font-size:0.78em;margin-left:auto;">{vals}</span>
            </div>""", unsafe_allow_html=True)

    # ── Exportação CSV ────────────────────────────────────────────────────────
    st.markdown("---")
    dados_filtrados = [
        r for r in dados
        if datetime.fromisoformat(r["timestamp"]) >= inicio_filtro
    ]

    csv_lines = ["timestamp,temperatura,vibracao,corrente,tensao,rpm"]
    for r in dados_filtrados:
        csv_lines.append(
            f"{r['timestamp']},{r['temperatura']['valor']},{r['vibracao']['valor']},"
            f"{r['corrente']['valor']},{r['tensao']['valor']},{r['rpm']['valor']}"
        )
    csv_str = "\n".join(csv_lines)

    st.download_button(
        "📥 Exportar dados (CSV)",
        data=csv_str,
        file_name=f"historico_{eq.get('tag','MOTOR')}_{periodo_dias}d.csv",
        mime="text/csv",
        use_container_width=False,
    )
