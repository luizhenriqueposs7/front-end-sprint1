"""
pages/cadastro.py
Formulário de cadastro e edição de equipamento.
"""

import streamlit as st
from services.equipamento_service import (
    buscar_por_id,
    salvar_equipamento,
    atualizar_equipamento,
    tag_existe,
)


_STATUS_OPCOES = ["Ativo", "Em Manutenção", "Inativo"]
_FABRICANTES   = ["WEG", "Siemens", "ABB", "Schneider Electric", "Bosch", "Outro"]


def render():
    eq_id = st.session_state.get("equipamento_selecionado")
    eq    = buscar_por_id(eq_id) if eq_id else None
    modo  = "Editar" if eq else "Novo"

    # ── Cabeçalho ─────────────────────────────────────────────────────────────
    col_titulo, col_voltar = st.columns([5, 1])
    with col_titulo:
        st.title(f"{'✏️ Editar' if eq else '➕ Cadastrar'} Equipamento")
        if eq:
            st.caption(f"TAG: `{eq['tag']}` · Cadastrado em {eq.get('data_cadastro', '—')}")
    with col_voltar:
        st.write("")
        if st.button("← Voltar", use_container_width=True):
            st.session_state["pagina"] = "consulta"
            st.rerun()

    st.divider()

    # ── Formulário ────────────────────────────────────────────────────────────
    with st.form("form_equipamento", clear_on_submit=False):

        st.subheader("🏷️ Identificação")
        c1, c2 = st.columns(2)
        tag = c1.text_input(
            "TAG de Identificação *",
            value=eq.get("tag", "") if eq else "",
            placeholder="ex: MTR-001",
            help="Identificador único do equipamento na planta",
        )
        status = c2.selectbox(
            "Status Operacional *",
            _STATUS_OPCOES,
            index=_STATUS_OPCOES.index(eq["status"]) if eq and eq.get("status") in _STATUS_OPCOES else 0,
        )
        localizacao = st.text_input(
            "Localização / Área",
            value=eq.get("localizacao", "") if eq else "",
            placeholder="ex: Linha de Produção A",
        )

        st.subheader("🔧 Dados do Fabricante")
        c3, c4 = st.columns(2)

        fab_valor = eq.get("fabricante", "") if eq else ""
        fab_opcoes = _FABRICANTES if fab_valor in _FABRICANTES else _FABRICANTES + [fab_valor]
        fabricante = c3.selectbox(
            "Fabricante *",
            fab_opcoes,
            index=fab_opcoes.index(fab_valor) if fab_valor in fab_opcoes else 0,
        )
        modelo = c4.text_input(
            "Modelo *",
            value=eq.get("modelo", "") if eq else "",
            placeholder="ex: WEG W22",
        )

        st.subheader("⚡ Parâmetros Elétricos")
        c5, c6, c7 = st.columns(3)
        potencia = c5.number_input(
            "Potência (kW) *",
            min_value=0.1, max_value=10000.0, step=0.1,
            value=float(eq.get("potencia_kw", 1.0)) if eq else 1.0,
        )
        tensao = c6.selectbox(
            "Tensão Nominal (V) *",
            [110, 127, 220, 380, 440, 480, 690, 4160, 13800],
            index=[110, 127, 220, 380, 440, 480, 690, 4160, 13800].index(eq.get("tensao_v", 380)) if eq else 3,
        )
        corrente = c7.number_input(
            "Corrente Nominal (A) *",
            min_value=0.1, max_value=5000.0, step=0.1,
            value=float(eq.get("corrente_nominal_a", 1.0)) if eq else 1.0,
        )

        st.subheader("🔄 Parâmetros Mecânicos")
        c8, c9, c10 = st.columns(3)
        frequencia = c8.selectbox(
            "Frequência (Hz)",
            [50, 60],
            index=[50, 60].index(eq.get("frequencia_hz", 60)) if eq else 1,
        )
        n_polos = c9.selectbox(
            "Nº de Polos",
            [2, 4, 6, 8, 10, 12],
            index=[2, 4, 6, 8, 10, 12].index(eq.get("n_polos", 4)) if eq else 1,
        )
        rpm = c10.number_input(
            "Velocidade Nominal (RPM)",
            min_value=1, max_value=20000, step=10,
            value=int(eq.get("velocidade_rpm", 1760)) if eq else 1760,
        )

        st.write("")
        col_salvar, col_cancelar, _ = st.columns([1.5, 1.5, 4])
        salvar   = col_salvar.form_submit_button("💾 Salvar", type="primary", use_container_width=True)
        cancelar = col_cancelar.form_submit_button("Cancelar", use_container_width=True)

    # ── Validação e persistência ──────────────────────────────────────────────
    if cancelar:
        st.session_state["pagina"] = "consulta"
        st.rerun()

    if salvar:
        erros = []
        if not tag.strip():
            erros.append("TAG é obrigatória.")
        elif tag_existe(tag.strip(), ignorar_id=eq_id or ""):
            erros.append(f"A TAG **{tag}** já está em uso por outro equipamento.")
        if not modelo.strip():
            erros.append("Modelo é obrigatório.")

        if erros:
            for e in erros:
                st.error(e, icon="❌")
        else:
            dados = {
                "tag":              tag.strip().upper(),
                "status":           status,
                "localizacao":      localizacao.strip(),
                "fabricante":       fabricante,
                "modelo":           modelo.strip(),
                "potencia_kw":      potencia,
                "tensao_v":         tensao,
                "corrente_nominal_a": corrente,
                "frequencia_hz":    frequencia,
                "n_polos":          n_polos,
                "velocidade_rpm":   rpm,
            }

            if eq:
                atualizar_equipamento(eq_id, dados)
                st.success("✅ Equipamento atualizado com sucesso!")
            else:
                novo = salvar_equipamento(dados)
                st.success(f"✅ Equipamento **{novo['tag']}** cadastrado com sucesso!")
                st.session_state["equipamento_selecionado"] = novo["id"]

            st.rerun()
