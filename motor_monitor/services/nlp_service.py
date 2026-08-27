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

# Severidade legível: o texto é lido por operador, não por log.
_SEVERIDADE_LEGIVEL = {"normal": "normal", "atencao": "atenção", "critico": "crítico"}

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


def formatar_numero(valor, casas: int = 2, remover_zeros: bool = True) -> str:
    """Número no padrão brasileiro: 1.760 · 32,72 · 28,5.

    Mora aqui porque é a mesma regra de idioma dos resumos; `components.py`
    importa esta função para não existirem dois formatadores divergentes.
    `remover_zeros=False` para casas fixas — é o caso do score de anomalia,
    que precisa sair igual no selo do card e no texto (0,90, não 0,9).
    """
    try:
        v = float(valor)
    except (TypeError, ValueError):
        return str(valor)
    texto = f"{v:,.{casas}f}"
    if remover_zeros:
        texto = texto.rstrip("0").rstrip(".")
    return texto.translate(str.maketrans({",": ".", ".": ","}))


def _comparacao(grandeza: str, valor: float, nominal: float) -> str:
    """Traduz o desvio para a referência que o operador reconhece.

    Temperatura e vibração comparam com o limite absoluto do projeto; as
    demais comparam com o nominal de placa, que é o número da plaqueta.
    """
    cfg = LIMITES.get(grandeza, {})
    un = _UNIDADE.get(grandeza, "")

    if "atencao" in cfg:  # limite absoluto
        limite = cfg["atencao"]
        excesso = (valor - limite) / limite * 100 if limite else 0
        if excesso > 0:
            return (f"{formatar_numero(excesso, 1)}% acima do limite de atenção "
                    f"de {formatar_numero(limite)} {un}")
        return (f"ainda abaixo do limite de atenção de {formatar_numero(limite)} {un}, "
                f"porém fora do padrão histórico")

    if nominal:  # tolerância percentual sobre o nominal
        desvio = (valor - nominal) / nominal * 100
        lado = "acima" if desvio >= 0 else "abaixo"
        return (f"{formatar_numero(abs(desvio), 1)}% {lado} do nominal de "
                f"{formatar_numero(nominal)} {un} "
                f"(tolerância de {cfg.get('atencao_pct', 10)}%)")

    return "fora do padrão histórico"


def resumir_alerta(alerta: dict) -> str:
    """Resumo textual de UM alerta, em linguagem de operação."""
    texto = (alerta.get("resumo_nlp") or "").strip()
    if texto:
        return texto  # o modelo real já escreveu — nada a fazer aqui

    # .get() em toda parte: a grandeza vem do pipeline analítico, que é externo.
    # Um nome fora do contrato tem que degradar o texto, nunca derrubar a tela.
    g = alerta.get("grandeza", "")
    sev = alerta.get("severidade", "atencao")
    try:
        valor = float(alerta.get("valor", 0))
        nominal = float(alerta.get("nominal", 0) or 0)
        score = float(alerta.get("score_anomalia", 0))
    except (TypeError, ValueError):
        valor = nominal = score = 0.0

    hipotese = _HIPOTESE.get(g)
    causa = f" e o padrão é compatível com {hipotese}" if hipotese else ""

    return (
        f"{_ABERTURA.get(sev, 'Desvio detectado')} em **{alerta.get('tag', '—')}**: "
        f"{_NOME.get(g, g or 'grandeza monitorada')} de {formatar_numero(valor)} "
        f"{_UNIDADE.get(g, '')}, {_comparacao(g, valor, nominal)}. "
        f"O modelo classificou o comportamento como *{_SEVERIDADE_LEGIVEL.get(sev, sev)}* "
        f"(score de anomalia {formatar_numero(score, 2, remover_zeros=False)}){causa}. "
        f"{_FECHAMENTO.get(sev, '')}"
    ).replace("  ", " ")


def descrever_estado(tag: str, estado: str, alertas: list[dict]) -> str:
    """Resumo textual do ESTADO de um equipamento (agrega todos os alertas ativos)."""
    if estado == "normal" or not alertas:
        return (
            f"**{tag}** opera dentro da faixa esperada. Nenhum desvio ativo nas "
            f"últimas leituras analisadas pelo modelo."
        )

    # `or "—"` porque um alerta pode chegar com grandeza null; sorted() de uma
    # lista com None e str estoura TypeError.
    grandezas = sorted({_NOME.get(a.get("grandeza")) or a.get("grandeza") or "—" for a in alertas})
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
