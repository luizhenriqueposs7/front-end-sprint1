"""
components.py
Componentes visuais reutilizáveis do Motor Monitor.

Só desenham — não leem arquivo, não chamam modelo, não decidem severidade.
Recebem o dicionário já pronto do `alerta_service` e o texto já pronto do
`nlp_service`. É o que mantém a página fina e permite usar o mesmo card de
alerta no painel, no dashboard ou em qualquer tela futura.
"""

import re

import streamlit as st

# ── Cores semânticas (as mesmas das Sprints 1 e 2) ────────────────────────────
COR = {"normal": "#10b981", "atencao": "#f59e0b", "critico": "#ef4444"}
BG = {"normal": "#052e16", "atencao": "#451a03", "critico": "#450a0a"}
EMOJI = {"normal": "🟢", "atencao": "🟡", "critico": "🔴"}
LABEL = {"normal": "SAUDÁVEL", "atencao": "ATENÇÃO", "critico": "CRÍTICO"}

ICONE_GRANDEZA = {
    "temperatura": "🌡️", "vibracao": "📳", "corrente": "〰️", "tensao": "⚡", "rpm": "🔄",
}
NOME_GRANDEZA = {
    "temperatura": "Temperatura", "vibracao": "Vibração", "corrente": "Corrente",
    "tensao": "Tensão", "rpm": "Velocidade",
}


# O texto do NLP chega em markdown, mas os cards são HTML puro (markdown não
# é interpretado dentro de tags). Converte os dois marcadores que os resumos usam.
_MD_NEGRITO = re.compile(r"\*\*(.+?)\*\*")
_MD_ITALICO = re.compile(r"\*(.+?)\*")


def _md(texto: str) -> str:
    return _MD_ITALICO.sub(r"<i>\1</i>", _MD_NEGRITO.sub(r"<b>\1</b>", texto or ""))


def _hora(timestamp: str) -> str:
    """'2026-08-25T14:03:11' -> '25/08 14:03'. Nunca quebra a tela por formato."""
    try:
        data, hora = timestamp.split("T")
        a, m, d = data.split("-")
        return f"{d}/{m} {hora[:5]}"
    except (ValueError, AttributeError):
        return str(timestamp)


# ── Componentes ───────────────────────────────────────────────────────────────

def metrica(label: str, valor, emoji: str, cor: str) -> None:
    """Cartão de KPI do topo do painel."""
    st.markdown(f"""
    <div style="background:#111827;border:1px solid #1f2937;border-top:3px solid {cor};
    border-radius:10px;padding:16px;text-align:center;">
        <div style="font-size:1.8em;">{emoji}</div>
        <div style="font-size:2em;font-weight:700;color:{cor};">{valor}</div>
        <div style="color:#9ca3af;font-size:0.85em;">{label}</div>
    </div>""", unsafe_allow_html=True)


def card_estado(tag: str, modelo: str, localizacao: str, estado: str,
                resumo: str, n_alertas: int) -> None:
    """Card de ESTADO OPERACIONAL de um ativo, com o resumo do NLP embutido."""
    cor, bg = COR[estado], BG[estado]
    st.markdown(f"""
    <div style="background:linear-gradient(135deg,{bg},#111827);
    border:1px solid {cor}44;border-left:4px solid {cor};border-radius:12px;
    padding:16px 20px;margin-bottom:8px;">
        <div style="display:flex;align-items:center;gap:12px;">
            <span style="font-size:1.6em;">{EMOJI[estado]}</span>
            <div>
                <div style="font-size:1.15em;font-weight:700;color:#e5e7eb;">{tag}</div>
                <div style="color:#6b7280;font-size:0.8em;">{modelo} · {localizacao}</div>
            </div>
            <div style="margin-left:auto;text-align:right;">
                <div style="color:{cor};font-weight:700;font-size:0.95em;">{LABEL[estado]}</div>
                <div style="color:#6b7280;font-size:0.75em;">{n_alertas} alerta(s) ativo(s)</div>
            </div>
        </div>
        <div style="margin-top:12px;padding:10px 12px;background:#0b1220;border-radius:8px;
        border-left:2px solid #3b82f6;color:#d1d5db;font-size:0.88em;line-height:1.5;">
            <span style="color:#60a5fa;font-size:0.8em;font-weight:600;">🧠 RESUMO OPERACIONAL</span><br>
            {_md(resumo)}
        </div>
    </div>""", unsafe_allow_html=True)


def card_alerta(alerta: dict, resumo: str, fonte_resumo: str) -> None:
    """Card de UM alerta: cabeçalho semântico + medição + resumo textual do NLP."""
    sev = alerta.get("severidade", "atencao")
    cor, bg = COR[sev], BG[sev]
    g = alerta.get("grandeza", "vibracao")
    score = float(alerta.get("score_anomalia", 0))

    st.markdown(f"""
    <div style="background:linear-gradient(135deg,{bg},#0f172a);border:1px solid {cor}55;
    border-left:4px solid {cor};border-radius:12px;padding:16px 20px;margin-bottom:6px;">
        <div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap;">
            <span style="background:{cor};color:#0b1220;font-weight:700;font-size:0.72em;
            padding:3px 10px;border-radius:20px;letter-spacing:0.5px;">{LABEL[sev]}</span>
            <span style="color:#e5e7eb;font-weight:700;">{alerta.get('tag','—')}</span>
            <span style="color:#6b7280;font-size:0.82em;">{ICONE_GRANDEZA.get(g,'📊')} {NOME_GRANDEZA.get(g,g)}</span>
            <span style="margin-left:auto;color:#6b7280;font-size:0.78em;">
                {alerta.get('id','—')} · {_hora(alerta.get('timestamp',''))}
            </span>
        </div>
        <div style="display:flex;gap:10px;flex-wrap:wrap;margin:12px 0 0;">
            <span style="background:#1e293b;padding:5px 10px;border-radius:6px;font-size:0.82em;color:#e5e7eb;">
                Medido: <b style="color:{cor};">{alerta.get('valor','—')} {alerta.get('unidade','')}</b></span>
            <span style="background:#1e293b;padding:5px 10px;border-radius:6px;font-size:0.82em;color:#d1d5db;">
                Nominal/base: {alerta.get('nominal','—')} {alerta.get('unidade','')}</span>
            <span style="background:#1e293b;padding:5px 10px;border-radius:6px;font-size:0.82em;color:#d1d5db;">
                Score de anomalia: <b>{score:.2f}</b></span>
            <span style="background:#1e293b;padding:5px 10px;border-radius:6px;font-size:0.82em;color:#9ca3af;">
                {alerta.get('modelo_analitico','—')}</span>
        </div>
        <div style="margin-top:12px;padding:10px 12px;background:#0b1220;border-radius:8px;
        border-left:2px solid #3b82f6;color:#d1d5db;font-size:0.88em;line-height:1.55;">
            <span style="color:#60a5fa;font-size:0.78em;font-weight:600;">🧠 {fonte_resumo.upper()}</span><br>
            {_md(resumo)}
        </div>
    </div>""", unsafe_allow_html=True)


def card_recomendacao(titulo: str, acao: str, prazo: str, severidade: str) -> None:
    """Card de apoio à decisão — o que a manutenção faz com o alerta."""
    cor = COR[severidade]
    st.markdown(f"""
    <div style="background:#0f172a;border:1px solid #1f2937;border-top:3px solid {cor};
    border-radius:10px;padding:14px 16px;height:100%;">
        <div style="color:#e5e7eb;font-weight:700;font-size:0.95em;margin-bottom:6px;">{titulo}</div>
        <div style="color:#9ca3af;font-size:0.85em;line-height:1.5;">{acao}</div>
        <div style="margin-top:10px;">
            <span style="background:{cor}22;color:{cor};padding:3px 10px;border-radius:20px;
            font-size:0.75em;font-weight:600;">⏱ {prazo}</span>
        </div>
    </div>""", unsafe_allow_html=True)


def historico_eventos(alertas: list, limite: int = 20) -> None:
    """Histórico de eventos — lista compacta dos alertas já registrados."""
    if not alertas:
        st.caption("Nenhum evento registrado até agora.")
        return

    linhas = []
    for a in alertas[:limite]:
        sev = a.get("severidade", "atencao")
        g = a.get("grandeza", "")
        estado = ("✅ Reconhecido" if a.get("reconhecido") else "🔔 Em aberto")
        cor_estado = "#6b7280" if a.get("reconhecido") else COR[sev]
        linhas.append(f"""
        <tr style="border-bottom:1px solid #1f2937;">
            <td style="padding:8px 6px;color:#6b7280;font-size:0.8em;white-space:nowrap;">{_hora(a.get('timestamp',''))}</td>
            <td style="padding:8px 6px;color:#9ca3af;font-size:0.8em;">{a.get('id','—')}</td>
            <td style="padding:8px 6px;color:#e5e7eb;font-weight:600;">{a.get('tag','—')}</td>
            <td style="padding:8px 6px;color:#d1d5db;">{ICONE_GRANDEZA.get(g,'📊')} {NOME_GRANDEZA.get(g,g)}</td>
            <td style="padding:8px 6px;color:{COR[sev]};font-weight:600;">{EMOJI[sev]} {LABEL[sev]}</td>
            <td style="padding:8px 6px;color:#d1d5db;">{a.get('valor','—')} {a.get('unidade','')}</td>
            <td style="padding:8px 6px;color:{cor_estado};font-size:0.85em;">{estado}</td>
        </tr>""")

    st.markdown(f"""
    <div style="background:#111827;border:1px solid #1f2937;border-radius:10px;padding:8px 16px 16px;overflow-x:auto;">
    <table style="width:100%;color:#d1d5db;font-size:0.9em;border-collapse:collapse;">
        <thead><tr style="border-bottom:2px solid #1f2937;color:#6b7280;font-size:0.78em;text-align:left;">
            <th style="padding:8px 6px;">QUANDO</th><th style="padding:8px 6px;">ID</th>
            <th style="padding:8px 6px;">ATIVO</th><th style="padding:8px 6px;">GRANDEZA</th>
            <th style="padding:8px 6px;">SEVERIDADE</th><th style="padding:8px 6px;">VALOR</th>
            <th style="padding:8px 6px;">SITUAÇÃO</th>
        </tr></thead>
        <tbody>{''.join(linhas)}</tbody>
    </table></div>""", unsafe_allow_html=True)
