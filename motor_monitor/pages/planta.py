"""
pages/planta.py
Navegação por Planta/Área — Visão macro dos ativos por localização,
com cards de status e contagem de saúde por área.
"""

import streamlit as st
from services.equipamento_service import listar_equipamentos, listar_localizacoes, buscar_por_localizacao
from services.sensor_service import gerar_leitura, avaliar_status

_COR = {"normal": "#10b981", "atencao": "#f59e0b", "critico": "#ef4444"}
_EMOJI = {"normal": "🟢", "atencao": "🟡", "critico": "🔴"}
_LABEL = {"normal": "Saudável", "atencao": "Atenção", "critico": "Crítico"}
_ICONE_AREA = {"Linha de Produção": "🏭", "Compressor": "🔧", "Bomba": "💧", "Utilidades": "⚙️"}


def _icone_para_area(nome_area: str) -> str:
    for chave, icone in _ICONE_AREA.items():
        if chave.lower() in nome_area.lower():
            return icone
    return "📍"


def render():
    st.markdown("""
    <h1 style="margin:0;"><span style="background:linear-gradient(135deg,#8b5cf6,#3b82f6);
    -webkit-background-clip:text;-webkit-text-fill-color:transparent;">
    🏭 Visão por Planta / Área</span></h1>
    <p style="color:#9ca3af;margin-top:4px;">Navegue pelas localizações e identifique o estado dos motores</p>
    """, unsafe_allow_html=True)
    st.markdown("---")

    equipamentos = listar_equipamentos()
    if not equipamentos:
        st.info("Nenhum equipamento cadastrado.", icon="📋")
        return

    localizacoes = listar_localizacoes()
    if not localizacoes:
        st.info("Nenhuma localização cadastrada nos equipamentos.", icon="📍")
        return

    # ── Resumo geral ──────────────────────────────────────────────────────────
    total = len(equipamentos)
    contagem = {"normal": 0, "atencao": 0, "critico": 0}
    status_por_eq = {}
    for eq in equipamentos:
        leitura = gerar_leitura(eq)
        s = avaliar_status(leitura)
        contagem[s] += 1
        status_por_eq[eq["id"]] = {"status": s, "leitura": leitura}

    cols = st.columns(4)
    metricas = [
        ("Total de Ativos", total, "⚙️", "#3b82f6"),
        ("Saudáveis", contagem["normal"], "🟢", "#10b981"),
        ("Em Atenção", contagem["atencao"], "🟡", "#f59e0b"),
        ("Críticos", contagem["critico"], "🔴", "#ef4444"),
    ]
    for col, (label, val, emoji, cor) in zip(cols, metricas):
        col.markdown(f"""
        <div style="background:#111827;border:1px solid #1f2937;border-top:3px solid {cor};
        border-radius:10px;padding:16px;text-align:center;">
            <div style="font-size:2em;">{emoji}</div>
            <div style="font-size:2em;font-weight:700;color:{cor};">{val}</div>
            <div style="color:#9ca3af;font-size:0.85em;">{label}</div>
        </div>""", unsafe_allow_html=True)

    st.markdown("---")

    # ── Filtro por área ───────────────────────────────────────────────────────
    filtro_area = st.selectbox(
        "🔍 Filtrar por Área",
        ["Todas as Áreas"] + localizacoes,
    )

    areas_exibir = localizacoes if filtro_area == "Todas as Áreas" else [filtro_area]

    # ── Cards por área ────────────────────────────────────────────────────────
    for area in areas_exibir:
        eqs_area = buscar_por_localizacao(area)
        if not eqs_area:
            continue

        icone = _icone_para_area(area)
        cont_area = {"normal": 0, "atencao": 0, "critico": 0}
        for eq in eqs_area:
            s = status_por_eq.get(eq["id"], {}).get("status", "normal")
            cont_area[s] += 1

        pior = "critico" if cont_area["critico"] > 0 else ("atencao" if cont_area["atencao"] > 0 else "normal")
        cor_area = _COR[pior]

        st.markdown(f"""
        <div style="background:#111827;border:1px solid {cor_area}44;border-left:4px solid {cor_area};
        border-radius:10px;padding:16px 20px;margin-bottom:8px;">
            <div style="display:flex;align-items:center;gap:12px;">
                <span style="font-size:1.5em;">{icone}</span>
                <div>
                    <div style="font-size:1.1em;font-weight:600;color:#e5e7eb;">{area}</div>
                    <div style="color:#6b7280;font-size:0.8em;">{len(eqs_area)} motor(es)</div>
                </div>
                <div style="margin-left:auto;display:flex;gap:12px;">
                    <span style="color:#10b981;">🟢 {cont_area['normal']}</span>
                    <span style="color:#f59e0b;">🟡 {cont_area['atencao']}</span>
                    <span style="color:#ef4444;">🔴 {cont_area['critico']}</span>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Cards dos motores nessa área
        cols_motores = st.columns(min(len(eqs_area), 3))
        for i, eq in enumerate(eqs_area):
            info = status_por_eq.get(eq["id"], {})
            s = info.get("status", "normal")
            leit = info.get("leitura", {})
            cor = _COR[s]
            emoji = _EMOJI[s]
            label_s = _LABEL[s]

            temp = leit.get("temperatura", {}).get("valor", "—")
            vib = leit.get("vibracao", {}).get("valor", "—")
            corr = leit.get("corrente", {}).get("valor", "—")

            with cols_motores[i % len(cols_motores)]:
                st.markdown(f"""
                <div style="background:#0f172a;border:1px solid {cor}44;border-radius:10px;
                padding:16px;margin-bottom:8px;">
                    <div style="display:flex;justify-content:space-between;align-items:center;">
                        <span style="font-weight:700;color:#e5e7eb;font-size:1.05em;">{eq.get('tag','—')}</span>
                        <span style="color:{cor};font-size:0.85em;font-weight:600;">{emoji} {label_s}</span>
                    </div>
                    <div style="color:#6b7280;font-size:0.8em;margin:4px 0 8px;">{eq.get('modelo','—')}</div>
                    <div style="display:flex;gap:8px;flex-wrap:wrap;">
                        <span style="background:#1e293b;padding:4px 8px;border-radius:6px;font-size:0.78em;color:#d1d5db;">🌡️ {temp}°C</span>
                        <span style="background:#1e293b;padding:4px 8px;border-radius:6px;font-size:0.78em;color:#d1d5db;">📳 {vib} mm/s</span>
                        <span style="background:#1e293b;padding:4px 8px;border-radius:6px;font-size:0.78em;color:#d1d5db;">〰️ {corr} A</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)

                if st.button(f"📊 Dashboard", key=f"dash_{eq['id']}", use_container_width=True):
                    st.session_state["equipamento_selecionado"] = eq["id"]
                    st.session_state["pagina"] = "dashboard"
                    st.rerun()

        st.markdown("")
