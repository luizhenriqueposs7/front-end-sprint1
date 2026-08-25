"""
services/alerta_service.py
Camada de alertas — o front-end lê alertas PRONTOS daqui e nunca executa o modelo.

ARQUITETURA DESACOPLADA
    data/alertas.json é uma CAIXA DE ENTRADA. Quem escreve nela é o pipeline
    analítico (detecção de anomalia + NLP), que roda fora do Streamlit.
    A interface só chama:

        listar_alertas()            -> alertas já classificados
        estado_dos_equipamentos()   -> estado consolidado por ativo
        reconhecer_alerta(id)       -> baixa operacional do alerta

    Trocar o simulador `_detectar()` por um consumidor de API, fila ou banco
    não muda uma linha das páginas.

ponytail: a "fila" é um JSON no disco, não um broker. Sobe para MQTT/REST
quando o modelo passar a rodar em outro processo.
"""

import json
import random
from datetime import datetime
from pathlib import Path
from typing import Optional

from services.equipamento_service import listar_equipamentos
from services.historico_service import LIMITES

ALERTAS_PATH = Path(__file__).parent.parent / "data" / "alertas.json"

# Ordem de severidade — usada para consolidar o estado do ativo.
ORDEM_SEVERIDADE = {"normal": 0, "atencao": 1, "critico": 2}

MODELO_ANALITICO = "IsolationForest v0.1 (mock)"

_GRANDEZAS_MONITORADAS = ["temperatura", "vibracao", "corrente", "tensao", "rpm"]

_UNIDADE = {"temperatura": "°C", "vibracao": "mm/s", "corrente": "A", "tensao": "V", "rpm": "RPM"}

# Campo do cadastro que guarda o valor nominal de cada grandeza.
# Temperatura e vibração não têm nominal de placa — usam o baseline do mock.
_CAMPO_NOMINAL = {"corrente": "corrente_nominal_a", "tensao": "tensao_v", "rpm": "velocidade_rpm"}
_BASELINE = {"temperatura": 65.0, "vibracao": 2.5}

# Apoio à decisão: o que a equipe de manutenção deve fazer para cada desvio.
# Vem junto do alerta para que a página não decida nada — só exiba.
_RECOMENDACOES = {
    "temperatura": [
        ("Verificar ventilação e trocador", "Inspecionar grelhas, aletas e filtro do motor por obstrução.", "Turno atual"),
        ("Conferir carga no eixo", "Comparar corrente medida com a nominal — sobrecarga aquece.", "24 h"),
    ],
    "vibracao": [
        ("Análise de vibração em campo", "Coletar espectro FFT no mancal dianteiro e traseiro.", "Turno atual"),
        ("Checar alinhamento e fixação", "Verificar acoplamento, chumbadores e balanceamento do rotor.", "48 h"),
    ],
    "corrente": [
        ("Medir corrente nas três fases", "Desequilíbrio entre fases indica problema de enrolamento.", "Turno atual"),
        ("Avaliar carga do processo", "Confirmar se a demanda do processo aumentou.", "24 h"),
    ],
    "tensao": [
        ("Inspecionar barramento", "Medir tensão na entrada do painel e conferir conexões.", "Turno atual"),
        ("Acionar equipe elétrica", "Instabilidade de alimentação afeta todos os ativos da área.", "24 h"),
    ],
    "rpm": [
        ("Verificar escorregamento", "Comparar RPM medido com o nominal de placa sob carga.", "24 h"),
        ("Checar transmissão", "Correias, polias e acoplamento com folga alteram a rotação.", "48 h"),
    ],
}

_ACAO_POR_SEVERIDADE = {
    "critico": ("Abrir OS corretiva imediata", "Registrar ordem de serviço e avaliar parada programada do ativo.", "Imediato"),
    "atencao": ("Programar inspeção preventiva", "Incluir o ativo na rota de inspeção do próximo turno.", "Próximo turno"),
}


# ── Persistência ──────────────────────────────────────────────────────────────

def _load() -> list[dict]:
    if not ALERTAS_PATH.exists():
        return []
    with open(ALERTAS_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def _save(alertas: list[dict]) -> None:
    ALERTAS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(ALERTAS_PATH, "w", encoding="utf-8") as f:
        json.dump(alertas, f, ensure_ascii=False, indent=2)


# ── Leitura (o que a interface usa) ───────────────────────────────────────────

def listar_alertas(apenas_ativos: bool = False) -> list[dict]:
    """Alertas do mais recente para o mais antigo."""
    alertas = _load()
    if apenas_ativos:
        alertas = [a for a in alertas if not a.get("reconhecido")]
    return sorted(alertas, key=lambda a: a["timestamp"], reverse=True)


def contar_por_severidade(alertas: list[dict]) -> dict:
    contagem = {"normal": 0, "atencao": 0, "critico": 0}
    for a in alertas:
        sev = a.get("severidade", "normal")
        contagem[sev] = contagem.get(sev, 0) + 1
    return contagem


def estado_dos_equipamentos() -> list[dict]:
    """Consolida o estado operacional de cada ativo a partir dos alertas ativos.

    O estado é a PIOR severidade entre os alertas não reconhecidos — é assim
    que o card muda de Saudável para Atenção ou Crítico sem a página precisar
    saber como o modelo chegou lá.
    """
    ativos = listar_alertas(apenas_ativos=True)
    estados = []
    for eq in listar_equipamentos():
        do_ativo = [a for a in ativos if a["equipamento_id"] == eq["id"]]
        estado = "normal"
        for a in do_ativo:
            if ORDEM_SEVERIDADE[a["severidade"]] > ORDEM_SEVERIDADE[estado]:
                estado = a["severidade"]
        estados.append({"equipamento": eq, "estado": estado, "alertas": do_ativo})
    # Piores primeiro — quem precisa de ação aparece no topo.
    return sorted(estados, key=lambda e: -ORDEM_SEVERIDADE[e["estado"]])


def alerta_mais_severo(alertas: list[dict]) -> Optional[dict]:
    """Alerta que deve puxar o painel de apoio à decisão."""
    if not alertas:
        return None
    return max(alertas, key=lambda a: (ORDEM_SEVERIDADE[a["severidade"]], a.get("score_anomalia", 0)))


# ── Escrita (baixa operacional) ───────────────────────────────────────────────

def reconhecer_alerta(alerta_id: str) -> bool:
    alertas = _load()
    for a in alertas:
        if a["id"] == alerta_id and not a.get("reconhecido"):
            a["reconhecido"] = True
            a["reconhecido_em"] = datetime.now().isoformat(timespec="seconds")
            _save(alertas)
            return True
    return False


def reconhecer_todos() -> int:
    """Zera o painel — usado para voltar a demonstração ao estado saudável."""
    alertas = _load()
    n = 0
    for a in alertas:
        if not a.get("reconhecido"):
            a["reconhecido"] = True
            a["reconhecido_em"] = datetime.now().isoformat(timespec="seconds")
            n += 1
    if n:
        _save(alertas)
    return n


def registrar_alerta(alerta: dict) -> dict:
    """Ponto de entrada do pipeline analítico. Hoje só o simulador usa;
    amanhã o consumidor da fila do modelo chama esta mesma função."""
    alertas = _load()
    alerta.setdefault("id", f"ALM-{len(alertas) + 1:04d}")
    alerta.setdefault("timestamp", datetime.now().isoformat(timespec="seconds"))
    alerta.setdefault("reconhecido", False)
    alerta.setdefault("resumo_nlp", None)  # preenchido pelo NLP quando existir
    alertas.append(alerta)
    _save(alertas)
    return alerta


# ── Simulador do modelo analítico (substituível) ──────────────────────────────

def _nominal(eq: dict, grandeza: str) -> float:
    campo = _CAMPO_NOMINAL.get(grandeza)
    if campo:
        return float(eq.get(campo, 0) or 0)
    return _BASELINE[grandeza]


def _valor_anomalo(eq: dict, grandeza: str, severidade: str) -> float:
    """Sorteia um valor coerente com a severidade e com os limites do projeto."""
    cfg = LIMITES[grandeza]
    if "atencao" in cfg:  # limite absoluto (temperatura, vibração)
        if severidade == "atencao":
            return round(random.uniform(cfg["normal"] + 0.1, cfg["atencao"]), 2)
        return round(random.uniform(cfg["atencao"] + 0.1, cfg["critico"] * 1.15), 2)
    nominal = _nominal(eq, grandeza)  # limite percentual (corrente, tensão, rpm)
    if severidade == "atencao":
        pct = random.uniform(cfg["normal_pct"] + 1, cfg["atencao_pct"]) / 100
    else:
        pct = random.uniform(cfg["atencao_pct"] + 1, cfg["atencao_pct"] * 2) / 100
    return round(nominal * (1 + pct), 2)


def _recomendacoes(grandeza: str, severidade: str) -> list[dict]:
    itens = [_ACAO_POR_SEVERIDADE[severidade]] + _RECOMENDACOES[grandeza]
    return [{"titulo": t, "acao": a, "prazo": p} for t, a, p in itens]


def _detectar() -> list[dict]:
    """Stand-in do modelo de detecção de anomalias.

    Substituir pelo consumo do resultado real (API/fila/banco). O formato de
    saída é o contrato: a interface já sabe ler exatamente estes campos.
    """
    equipamentos = listar_equipamentos()
    if not equipamentos:
        return []

    # ~75% das varreduras encontram algo — o suficiente para a demonstração
    # mostrar a transição de estado sem virar ruído contínuo.
    severidade = random.choices(["normal", "atencao", "critico"], weights=[25, 45, 30])[0]
    if severidade == "normal":
        return []

    eq = random.choice(equipamentos)
    grandeza = random.choice(_GRANDEZAS_MONITORADAS)
    valor = _valor_anomalo(eq, grandeza, severidade)
    score = round(random.uniform(0.55, 0.79) if severidade == "atencao" else random.uniform(0.80, 0.98), 2)

    return [{
        "equipamento_id": eq["id"],
        "tag": eq.get("tag", "—"),
        "modelo_equipamento": eq.get("modelo", "—"),
        "localizacao": eq.get("localizacao", "—"),
        "grandeza": grandeza,
        "valor": valor,
        "unidade": _UNIDADE[grandeza],
        "nominal": _nominal(eq, grandeza),
        "severidade": severidade,
        "score_anomalia": score,
        "modelo_analitico": MODELO_ANALITICO,
        "resumo_nlp": None,
        "recomendacoes": _recomendacoes(grandeza, severidade),
    }]


def verificar_novos_alertas() -> list[dict]:
    """Chamado pelo botão 'Atualizar' e pelo timer da página.

    Consulta a fonte analítica e persiste o que vier de novo. Retorna só os
    alertas novos, para a interface notificar o usuário.
    """
    return [registrar_alerta(a) for a in _detectar()]
