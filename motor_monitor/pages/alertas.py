"""
pages/alertas.py
Painel de Alertas e Estados — página inicial do sistema (Sprint 3).

Mostra o estado operacional de todos os ativos ANTES de escolher um
equipamento, com os resumos textuais do NLP e o apoio à decisão para a
manutenção.

A página não roda modelo nenhum: só lê `alerta_service` e formata com
`components`. Atualiza por botão ou por timer (st.fragment(run_every=...)),
que é o recurso nativo do Streamlit — sem dependência extra.
"""

import time

import streamlit as st

import components as ui
from services.alerta_service import (
    alerta_mais_severo,
    contar_por_severidade,
    estado_dos_equipamentos,
    listar_alertas,
    reconhecer_alerta,
    reconhecer_todos,
    verificar_novos_alertas,
)
from services.nlp_service import (
    descrever_estado,
    fonte_do_resumo,
    formatar_numero,
    resumir_alerta,
)

INTERVALOS = {"10 segundos": 10, "30 segundos": 30, "1 minuto": 60}


# ── Atualização dos dados ─────────────────────────────────────────────────────

def _consultar_pipeline() -> list[dict]:
    """Pergunta ao pipeline analítico se há alerta novo e notifica na tela."""
    novos = verificar_novos_alertas()
    st.session_state["alertas_ultima_atualizacao"] = time.strftime("%H:%M:%S")
    st.session_state["alertas_ultima_checagem"] = time.monotonic()
    for a in novos:
        emoji = ui.EMOJI.get(a.get("severidade"), "🔔")
        nome = ui.NOME_GRANDEZA.get(a.get("grandeza"), a.get("grandeza", "grandeza"))
        medida = f"{formatar_numero(a.get('valor', '—'))} {a.get('unidade', '')}".strip()
        st.toast(f"{emoji} **{a.get('tag', '—')}** · {nome} em {medida}", icon="🔔")
    return novos


# ── Corpo do painel (roda dentro do fragment) ─────────────────────────────────

def _painel() -> None:
    intervalo = st.session_state.get("alertas_intervalo", 10)
    auto = st.session_state.get("alertas_auto", False)

    # O fragment também roda quando um botão dele é clicado; o relógio abaixo
    # garante que só o TICK do timer dispare uma nova consulta ao pipeline.
    if auto:
        decorrido = time.monotonic() - st.session_state.get("alertas_ultima_checagem", 0)
        if decorrido >= intervalo - 0.5:
            _consultar_pipeline()

    # ── Ações de atualização ──────────────────────────────────────────────────
    c1, c2, c3 = st.columns([1.2, 1.2, 3])
    with c1:
        if st.button("🔄 Atualizar agora", use_container_width=True, type="primary"):
            if not _consultar_pipeline():
                st.toast("Varredura concluída — nenhum desvio novo.", icon="✅")
            st.rerun(scope="fragment")
    with c2:
        if st.button("✅ Reconhecer todos", use_container_width=True,
                     help="Dá baixa em todos os alertas ativos e volta os ativos para Saudável"):
            n = reconhecer_todos()
            st.toast(f"{n} alerta(s) reconhecido(s).", icon="✅")
            st.rerun(scope="fragment")
    with c3:
        ultima = st.session_state.get("alertas_ultima_atualizacao", "—")
        modo = f"automática a cada {intervalo}s" if auto else "manual"
        st.markdown(
            f"<div style='padding-top:8px;color:#6b7280;font-size:0.85em;'>"
            f"Última varredura: <b style='color:#9ca3af;'>{ultima}</b> · Atualização {modo}</div>",
            unsafe_allow_html=True,
        )

    alertas_ativos = listar_alertas(apenas_ativos=True)
    estados = estado_dos_equipamentos()
    contagem_estados = {"normal": 0, "atencao": 0, "critico": 0}
    for e in estados:
        contagem_estados[e["estado"]] = contagem_estados.get(e["estado"], 0) + 1

    # ── KPIs ──────────────────────────────────────────────────────────────────
    st.markdown("")
    cols = st.columns(4)
    contagem_alertas = contar_por_severidade(alertas_ativos)
    kpis = [
        ("Ativos monitorados", len(estados), "⚙️", "#3b82f6"),
        ("Saudáveis", contagem_estados["normal"], ui.EMOJI["normal"], ui.COR["normal"]),
        ("Em atenção", contagem_estados["atencao"], ui.EMOJI["atencao"], ui.COR["atencao"]),
        ("Críticos", contagem_estados["critico"], ui.EMOJI["critico"], ui.COR["critico"]),
    ]
    for col, (label, valor, emoji, cor) in zip(cols, kpis):
        with col:
            ui.metrica(label, valor, emoji, cor)

    # ── Estado operacional por ativo ──────────────────────────────────────────
    st.markdown("### 🩺 Estado Operacional dos Ativos")
    for item in estados:
        eq = item["equipamento"]
        ui.card_estado(
            tag=eq.get("tag", "—"),
            modelo=eq.get("modelo", "—"),
            localizacao=eq.get("localizacao", "—"),
            estado=item["estado"],
            resumo=descrever_estado(eq.get("tag", "—"), item["estado"], item["alertas"]),
            n_alertas=len(item["alertas"]),
        )
        if st.button(f"📊 Abrir dashboard de {eq.get('tag','—')}",
                     key=f"ir_dash_{eq['id']}", use_container_width=True):
            st.session_state["equipamento_selecionado"] = eq["id"]
            st.session_state["pagina"] = "dashboard"
            st.rerun(scope="app")

    # ── Alertas ativos ────────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown(
        f"### 🔔 Alertas Ativos "
        f"<span style='color:#6b7280;font-size:0.6em;'>"
        f"{contagem_alertas['critico']} crítico(s) · {contagem_alertas['atencao']} em atenção</span>",
        unsafe_allow_html=True,
    )

    if not alertas_ativos:
        st.success(
            "Nenhum alerta ativo. Todos os ativos operam dentro da faixa esperada. "
            "Use **Atualizar agora** (ou ligue a atualização automática acima) "
            "para rodar uma nova varredura do modelo.",
            icon="🟢",
        )
    else:
        for a in alertas_ativos:
            ui.card_alerta(a, resumir_alerta(a), fonte_do_resumo(a))
            b1, b2, _ = st.columns([1.1, 1.1, 3])
            with b1:
                if st.button("✅ Reconhecer", key=f"ack_{a.get('id')}", use_container_width=True):
                    reconhecer_alerta(a.get("id"))
                    st.toast(f"Alerta {a.get('id','—')} reconhecido.", icon="✅")
                    st.rerun(scope="fragment")
            with b2:
                if st.button("📈 Ver histórico", key=f"hist_{a.get('id')}", use_container_width=True):
                    st.session_state["equipamento_selecionado"] = a.get("equipamento_id")
                    st.session_state["pagina"] = "historico"
                    st.rerun(scope="app")

    # ── Apoio à decisão ───────────────────────────────────────────────────────
    prioritario = alerta_mais_severo(alertas_ativos)
    if prioritario:
        st.markdown("---")
        st.markdown(
            f"### 🧭 Apoio à Decisão "
            f"<span style='color:#6b7280;font-size:0.6em;'>plano sugerido para "
            f"{ui.escapar(prioritario.get('tag','—'))} · {ui.escapar(prioritario.get('id','—'))}</span>",
            unsafe_allow_html=True,
        )
        recomendacoes = prioritario.get("recomendacoes", [])
        cols_rec = st.columns(max(len(recomendacoes), 1))
        for col, rec in zip(cols_rec, recomendacoes):
            with col:
                ui.card_recomendacao(
                    rec.get("titulo", "Ação sugerida"), rec.get("acao", "—"),
                    rec.get("prazo", "A definir"), prioritario.get("severidade", "atencao"),
                )

    # ── Histórico de eventos ──────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("### 🗂️ Histórico de Eventos")
    ui.historico_eventos(listar_alertas())


# ── Página ────────────────────────────────────────────────────────────────────

def render() -> None:
    st.markdown("""
    <h1 style="margin:0;"><span style="background:linear-gradient(135deg,#ef4444,#f59e0b);
    -webkit-background-clip:text;-webkit-text-fill-color:transparent;">
    🚨 Painel de Alertas e Estados</span></h1>
    <p style="color:#9ca3af;margin-top:4px;">
    Inteligência operacional — anomalias detectadas pelos modelos analíticos,
    resumidas em linguagem natural e traduzidas em ação de manutenção</p>
    """, unsafe_allow_html=True)
    st.markdown("---")

    st.session_state.setdefault("alertas_ultima_checagem", 0.0)

    # O toggle fica FORA do fragment: mudar o intervalo precisa recriar o timer.
    c_auto, c_int, _ = st.columns([1.4, 1.4, 3])
    with c_auto:
        auto = st.toggle("⏱️ Atualização automática", key="alertas_auto")
    with c_int:
        rotulo = st.selectbox("Intervalo", list(INTERVALOS.keys()),
                              disabled=not auto, label_visibility="collapsed")
    st.session_state["alertas_intervalo"] = INTERVALOS[rotulo]

    # run_every=None desliga o timer; o painel continua atualizável pelo botão.
    st.fragment(_painel, run_every=INTERVALOS[rotulo] if auto else None)()
