"""
pages/dados_brutos.py
Visualização em tempo real dos dados do sensor com conversão sinal bruto → unidade física.
"""

import time
import streamlit as st
from services.equipamento_service import buscar_por_id, listar_equipamentos
from services.sensor_service import gerar_leitura, avaliar_status


# Configuração de cada grandeza: label, ícone, cor semântica, limites de alerta
_CONFIG = {
    "tensao":      {"label": "Tensão",       "icone": "⚡", "decimais": 1},
    "corrente":    {"label": "Corrente",      "icone": "〰️", "decimais": 2},
    "rpm":         {"label": "Velocidade",    "icone": "🔄", "decimais": 0},
    "temperatura": {"label": "Temperatura",  "icone": "🌡️", "decimais": 1},
    "vibracao":    {"label": "Vibração",      "icone": "📳", "decimais": 3},
}

_STATUS_UI = {
    "normal":   ("🟢 Normal",    "#1a7a4a", "#e6f4ee"),
    "atencao":  ("🟡 Atenção",   "#a07800", "#fdf8e6"),
    "critico":  ("🔴 Crítico",   "#a02020", "#fdeaea"),
}


def _desvio_pct(valor: float, nominal: float) -> float:
    if nominal == 0:
        return 0.0
    return (valor - nominal) / nominal * 100


def _cor_desvio(desvio_pct: float) -> str:
    abs_d = abs(desvio_pct)
    if abs_d < 5:
        return "#1a7a4a"
    elif abs_d < 12:
        return "#a07800"
    else:
        return "#a02020"


def render():
    # ── Seleção de equipamento ────────────────────────────────────────────────
    eq_id = st.session_state.get("equipamento_selecionado")
    eq    = buscar_por_id(eq_id) if eq_id else None

    col_titulo, col_voltar = st.columns([5, 1])
    with col_titulo:
        st.title("📡 Dados do Sensor")
    with col_voltar:
        st.write("")
        if st.button("← Voltar", use_container_width=True):
            st.session_state["pagina"] = "consulta"
            st.rerun()

    # Seletor de equipamento
    equipamentos = listar_equipamentos()
    if not equipamentos:
        st.warning("Nenhum equipamento cadastrado.", icon="⚠️")
        return

    opcoes = {f"{e['tag']} — {e['modelo']}": e["id"] for e in equipamentos}
    selecionado_label = next(
        (k for k, v in opcoes.items() if v == eq_id), list(opcoes.keys())[0]
    )
    escolha = st.selectbox("Equipamento monitorado", list(opcoes.keys()),
                           index=list(opcoes.keys()).index(selecionado_label))
    eq_id = opcoes[escolha]
    eq    = buscar_por_id(eq_id)
    st.session_state["equipamento_selecionado"] = eq_id

    st.divider()

    # ── Controles de simulação ────────────────────────────────────────────────
    c1, c2, c3 = st.columns([2, 2, 3])
    auto_refresh = c1.toggle("▶️ Atualização automática", value=False)
    intervalo    = c2.slider("Intervalo (s)", 1, 10, 3, disabled=not auto_refresh)
    atualizar    = c3.button("🔄 Atualizar agora", use_container_width=True)

    st.divider()

    # ── Leitura ───────────────────────────────────────────────────────────────
    leitura = gerar_leitura(eq)
    status  = avaliar_status(leitura)
    status_label, status_cor, status_bg = _STATUS_UI[status]

    # Badge de status global
    st.markdown(
        f"""
        <div style="
            background:{status_bg};
            border-left: 4px solid {status_cor};
            padding: 10px 16px;
            border-radius: 6px;
            margin-bottom: 16px;
        ">
            <span style="color:{status_cor}; font-weight:700; font-size:1.1em">
                {status_label}
            </span>
            <span style="color:#555; margin-left:12px;">
                Leitura em tempo real · equipamento <strong>{eq.get('tag','—')}</strong>
            </span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ── Cards de grandezas ────────────────────────────────────────────────────
    colunas = st.columns(len(_CONFIG))
    for col, (chave, cfg) in zip(colunas, _CONFIG.items()):
        dado = leitura[chave]
        desvio = _desvio_pct(dado["valor"], dado["nominal"])
        cor    = _cor_desvio(desvio)
        fmt    = f"{{:.{cfg['decimais']}f}}"

        col.markdown(
            f"""
            <div style="
                border:1px solid #ddd;
                border-radius:10px;
                padding:14px 10px;
                text-align:center;
                background:#fafafa;
            ">
                <div style="font-size:1.6em">{cfg['icone']}</div>
                <div style="font-size:0.75em; color:#777; margin:4px 0">{cfg['label']}</div>
                <div style="font-size:1.5em; font-weight:700; color:{cor}">
                    {fmt.format(dado['valor'])}
                </div>
                <div style="font-size:0.8em; color:#999">{dado['unidade']}</div>
                <div style="font-size:0.72em; color:{cor}; margin-top:4px">
                    {'+' if desvio >= 0 else ''}{desvio:.1f}% do nominal
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.write("")

    # ── Tabela de conversão bruto → físico ────────────────────────────────────
    with st.expander("🔬 Ver conversão de sinal bruto → unidade física", expanded=False):
        st.markdown("""
        > Os valores abaixo mostram o sinal **ADC de 12 bits (0–4095)** lido do sensor
        > e a conversão aplicada para obter a grandeza física.
        """)

        header = st.columns([2, 1.2, 1.5, 1.5, 1.5])
        for col, h in zip(header, ["Grandeza", "Sinal Bruto (RAW)", "Valor Convertido", "Nominal", "Desvio"]):
            col.markdown(f"**{h}**")
        st.divider()

        for chave, cfg in _CONFIG.items():
            dado   = leitura[chave]
            desvio = _desvio_pct(dado["valor"], dado["nominal"])
            cor    = _cor_desvio(desvio)
            fmt    = f"{{:.{cfg['decimais']}f}}"
            row    = st.columns([2, 1.2, 1.5, 1.5, 1.5])
            row[0].markdown(f"{cfg['icone']} {cfg['label']}")
            row[1].markdown(f"`{dado['raw']}`")
            row[2].markdown(f"**{fmt.format(dado['valor'])} {dado['unidade']}**")
            row[3].markdown(f"{fmt.format(dado['nominal'])} {dado['unidade']}")
            row[4].markdown(
                f"<span style='color:{cor}'>{'+' if desvio >= 0 else ''}{desvio:.1f}%</span>",
                unsafe_allow_html=True,
            )

    # ── Auto-refresh ──────────────────────────────────────────────────────────
    if auto_refresh:
        time.sleep(intervalo)
        st.rerun()
