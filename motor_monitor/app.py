"""
app.py — Entry point do Motor Monitor
Gerencia navegação e sidebar. Não contém lógica de negócio.
"""

import streamlit as st

# ── Configuração da página ────────────────────────────────────────────────────
st.set_page_config(
    page_title="Motor Monitor",
    page_icon="⚙️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── CSS global ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    /* Esconde a navegação padrão do Streamlit (links vazios) */
    [data-testid="stSidebarNav"] { display: none; }

    /* Sidebar */
    [data-testid="stSidebar"] { background-color: #0f1117; }
    [data-testid="stSidebar"] * { color: #e0e0e0 !important; }

    /* Remove padding excessivo no topo */
    .block-container { padding-top: 2rem; }

    /* Botões primários */
    .stButton > button[kind="primary"] {
        background-color: #1a7a4a;
        border-color: #1a7a4a;
    }
    .stButton > button[kind="primary"]:hover {
        background-color: #145f39;
        border-color: #145f39;
    }

    /* Estilo dos botões do menu */
    .stButton > button {
        border-radius: 5px;
        text-align: left;
        padding-left: 15px;
    }

    /* Métricas */
    [data-testid="metric-container"] { background: #f8f9fa; border-radius: 8px; padding: 8px; }
</style>
""", unsafe_allow_html=True)


# ── Estado inicial ────────────────────────────────────────────────────────────
if "pagina" not in st.session_state:
    st.session_state["pagina"] = "dashboard"
if "equipamento_selecionado" not in st.session_state:
    st.session_state["equipamento_selecionado"] = None


# ── Sidebar / Menu ────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## ⚙️ Motor Monitor")
    st.markdown("*Sistema de Gestão de Ativos*")
    st.divider()

    # ── Sprint 2 — Visualização Operacional ──────────────────────────────────
    st.markdown("### 📊 Visualização")

    menu_sprint2 = {
        "dashboard":  ("📊", "Dashboard"),
        "planta":     ("🏭", "Visão por Planta"),
        "historico":  ("📈", "Histórico"),
    }

    for pagina, (icone, label) in menu_sprint2.items():
        ativo = st.session_state["pagina"] == pagina
        if st.button(
            f"{icone}  {label}",
            key=f"menu_{pagina}",
            use_container_width=True,
        ):
            st.session_state["pagina"] = pagina
            st.rerun()

    st.divider()

    # ── Sprint 1 — Gestão de Ativos ─────────────────────────────────────────
    st.markdown("### 📂 Gestão")

    menu_sprint1 = {
        "consulta":     ("🏠", "Equipamentos"),
        "cadastro":     ("➕", "Novo Cadastro"),
        "dados_brutos": ("📡", "Dados do Sensor"),
    }

    for pagina, (icone, label) in menu_sprint1.items():
        ativo = st.session_state["pagina"] == pagina
        if st.button(
            f"{icone}  {label}",
            key=f"menu_{pagina}",
            use_container_width=True,
        ):
            st.session_state["pagina"] = pagina
            if pagina == "cadastro":
                st.session_state["equipamento_selecionado"] = None
            st.rerun()

    st.divider()
    st.caption("FIAP · Challenge 2026 · Sprint 2")


# ── Roteamento de páginas ─────────────────────────────────────────────────────
pagina = st.session_state["pagina"]

if pagina == "dashboard":
    from pages.dashboard import render
    render()

elif pagina == "planta":
    from pages.planta import render
    render()

elif pagina == "historico":
    from pages.historico import render
    render()

elif pagina == "consulta":
    from pages.consulta import render
    render()

elif pagina == "cadastro":
    from pages.cadastro import render
    render()

elif pagina == "dados_brutos":
    from pages.dados_brutos import render
    render()
