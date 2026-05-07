"""
pages/consulta.py
Tela inicial — lista todos os equipamentos cadastrados.
"""

import streamlit as st
from services.equipamento_service import listar_equipamentos, excluir_equipamento


_STATUS_CORES = {
    "Ativo":          ("🟢", "#1a7a4a"),
    "Em Manutenção":  ("🟡", "#a07800"),
    "Inativo":        ("🔴", "#a02020"),
}


def render():
    st.title("⚙️ Equipamentos Cadastrados")
    st.caption("Selecione um equipamento para ver a ficha técnica ou os dados do sensor.")

    equipamentos = listar_equipamentos()

    # ── Barra de ações ────────────────────────────────────────────────────────
    col_busca, col_novo = st.columns([4, 1])
    with col_busca:
        filtro = st.text_input(
            "🔍 Buscar por TAG, modelo ou fabricante",
            placeholder="ex: MTR-001",
            label_visibility="collapsed",
        )
    with col_novo:
        if st.button("➕ Novo equipamento", use_container_width=True, type="primary"):
            st.session_state["pagina"] = "cadastro"
            st.session_state["equipamento_selecionado"] = None
            st.rerun()

    st.divider()

    # ── Filtragem ─────────────────────────────────────────────────────────────
    if filtro:
        termo = filtro.lower()
        equipamentos = [
            e for e in equipamentos
            if termo in e.get("tag", "").lower()
            or termo in e.get("modelo", "").lower()
            or termo in e.get("fabricante", "").lower()
        ]

    if not equipamentos:
        st.info("Nenhum equipamento encontrado. Cadastre o primeiro!", icon="📋")
        return

    # ── Tabela de equipamentos ────────────────────────────────────────────────
    st.markdown(f"**{len(equipamentos)} equipamento(s) encontrado(s)**")

    # Cabeçalho
    cols = st.columns([1.2, 2.5, 2, 1.5, 1.5, 2.2])
    headers = ["TAG", "Modelo", "Fabricante", "Potência", "Status", "Ações"]
    for col, h in zip(cols, headers):
        col.markdown(f"**{h}**")

    st.divider()

    for eq in equipamentos:
        icone, _ = _STATUS_CORES.get(eq.get("status", "Inativo"), ("⚪", "#555"))
        cols = st.columns([1.2, 2.5, 2, 1.5, 1.5, 2.2])

        cols[0].markdown(f"`{eq.get('tag', '—')}`")
        cols[1].markdown(eq.get("modelo", "—"))
        cols[2].markdown(eq.get("fabricante", "—"))
        cols[3].markdown(f"{eq.get('potencia_kw', '—')} kW")
        cols[4].markdown(f"{icone} {eq.get('status', '—')}")

        with cols[5]:
            a, b, c = st.columns(3)
            if a.button("📋", key=f"ficha_{eq['id']}", help="Ficha técnica"):
                st.session_state["pagina"] = "cadastro"
                st.session_state["equipamento_selecionado"] = eq["id"]
                st.rerun()
            if b.button("📡", key=f"dados_{eq['id']}", help="Dados do sensor"):
                st.session_state["pagina"] = "dados_brutos"
                st.session_state["equipamento_selecionado"] = eq["id"]
                st.rerun()
            if c.button("🗑️", key=f"del_{eq['id']}", help="Excluir"):
                st.session_state[f"confirmar_exclusao_{eq['id']}"] = True

        # Confirmação de exclusão inline
        if st.session_state.get(f"confirmar_exclusao_{eq['id']}"):
            with st.container():
                st.warning(
                    f"Tem certeza que deseja excluir **{eq['tag']}**? Esta ação não pode ser desfeita.",
                    icon="⚠️",
                )
                cc1, cc2, _ = st.columns([1, 1, 4])
                if cc1.button("✅ Confirmar", key=f"conf_{eq['id']}", type="primary"):
                    excluir_equipamento(eq["id"])
                    del st.session_state[f"confirmar_exclusao_{eq['id']}"]
                    st.success("Equipamento excluído.")
                    st.rerun()
                if cc2.button("❌ Cancelar", key=f"canc_{eq['id']}"):
                    del st.session_state[f"confirmar_exclusao_{eq['id']}"]
                    st.rerun()

        st.divider()
