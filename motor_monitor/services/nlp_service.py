"""
services/nlp_service.py
Camada de linguagem natural — resumos textuais dos alertas e descrição do
estado operacional dos ativos.

STATUS: mock por template. O CONTRATO já é o definitivo:

    resumir_alerta(alerta)                 -> str
    descrever_estado(tag, estado, alertas) -> str

Quando o time de NLP entregar o modelo, há dois caminhos e nenhum deles
toca as páginas:

  1. O pipeline analítico grava o texto no campo `resumo_nlp` do alerta.
     resumir_alerta() devolve esse texto e ignora o template.
  2. Ou troca-se o corpo das funções abaixo pela chamada ao modelo.

ponytail: template determinístico em vez de modelo de verdade — é o mock
pedido pela sprint. Trocar quando o NLP existir; a interface não muda.
"""

from services.historico_service import LIMITES

# Fonte do texto exibido na interface. Vira "modelo-nlp" quando o modelo real
# passar a preencher `resumo_nlp`.
FONTE_TEMPLATE = "Resumo automático (template)"
FONTE_MODELO = "Resumo gerado por NLP"

_UNIDADE = {
    "temperatura": "°C",
    "vibracao": "mm/s",
    "corrente": "A",
    "tensao": "V",
    "rpm": "RPM",
}

_NOME = {
    "temperatura": "temperatura",
    "vibracao": "vibração",
    "corrente": "corrente",
    "tensao": "tensão",
    "rpm": "velocidade",
}

# Hipótese técnica mais provável por grandeza — o que o modelo de ML "viu".
_HIPOTESE = {
    "temperatura": "sobrecarga térmica, ventilação obstruída ou carga acima da nominal",
    "vibracao": "desbalanceamento, desalinhamento ou folga em mancal",
    "corrente": "variação de carga no eixo ou degradação do isolamento",
    "tensao": "instabilidade na alimentação do barramento",
    "rpm": "escorregamento fora do esperado ou perda de torque",
}

_ABERTURA = {
    "atencao": "Desvio moderado detectado",
    "critico": "Anomalia severa detectada",
}

_FECHAMENTO = {
    "atencao": "Sem impacto imediato na produção, mas a tendência é de piora — acompanhar no próximo turno.",
    "critico": "Risco de falha em curto prazo. Recomenda-se inspeção antes de manter o ativo em operação.",
}


def fonte_do_resumo(alerta: dict) -> str:
    """Diz na interface de onde veio o texto: modelo real ou template."""
    return FONTE_MODELO if (alerta.get("resumo_nlp") or "").strip() else FONTE_TEMPLATE


def _limite_de_referencia(grandeza: str, nominal: float) -> tuple[float, str]:
    """Retorna (limite de atenção, descrição) para a grandeza.

    Temperatura e vibração têm limite absoluto; as demais são percentuais
    sobre o valor nominal do equipamento.
    """
    cfg = LIMITES.get(grandeza, {})
    if "atencao" in cfg:
        return cfg["atencao"], f"limite de atenção de {cfg['atencao']} {_UNIDADE[grandeza]}"
    pct = cfg.get("atencao_pct", 10)
    return nominal * (1 + pct / 100), f"tolerância de {pct}% sobre o nominal de {nominal:g} {_UNIDADE[grandeza]}"


def resumir_alerta(alerta: dict) -> str:
    """Resumo textual de UM alerta, em linguagem de operação."""
    texto = (alerta.get("resumo_nlp") or "").strip()
    if texto:
        return texto  # o modelo real já escreveu — nada a fazer aqui

    g = alerta.get("grandeza", "vibracao")
    sev = alerta.get("severidade", "atencao")
    valor = float(alerta.get("valor", 0))
    nominal = float(alerta.get("nominal", 0) or 0)
    limite, descricao_limite = _limite_de_referencia(g, nominal)
    score = float(alerta.get("score_anomalia", 0))

    if limite > 0:
        excedente = (valor - limite) / limite * 100
        comparacao = (
            f"{excedente:.0f}% acima da {descricao_limite}"
            if excedente > 0
            else f"dentro da {descricao_limite}, porém fora do padrão histórico"
        )
    else:
        comparacao = "fora do padrão histórico"

    return (
        f"{_ABERTURA.get(sev, 'Desvio detectado')} em **{alerta.get('tag', '—')}**: "
        f"{_NOME[g]} de {valor:g} {_UNIDADE[g]}, {comparacao}. "
        f"O modelo classificou o comportamento como *{sev}* "
        f"(score de anomalia {score:.2f}) e o padrão é compatível com {_HIPOTESE[g]}. "
        f"{_FECHAMENTO.get(sev, '')}"
    )


def descrever_estado(tag: str, estado: str, alertas: list[dict]) -> str:
    """Resumo textual do ESTADO de um equipamento (agrega todos os alertas ativos)."""
    if estado == "normal" or not alertas:
        return (
            f"**{tag}** opera dentro da faixa esperada. Nenhum desvio ativo nas "
            f"últimas leituras analisadas pelo modelo."
        )

    grandezas = sorted({_NOME[a["grandeza"]] for a in alertas})
    lista = grandezas[0] if len(grandezas) == 1 else ", ".join(grandezas[:-1]) + f" e {grandezas[-1]}"
    n = len(alertas)
    plural = "desvio ativo" if n == 1 else "desvios ativos"

    if estado == "critico":
        return (
            f"**{tag}** está em estado **crítico**: {n} {plural} em {lista}. "
            f"O comportamento saiu da faixa operável e há risco de falha em curto prazo. "
            f"Priorizar inspeção e considerar parada programada."
        )
    return (
        f"**{tag}** está em **atenção**: {n} {plural} em {lista}. "
        f"O ativo segue operável, mas o modelo identificou afastamento do baseline. "
        f"Acompanhar a tendência e programar verificação preventiva."
    )
