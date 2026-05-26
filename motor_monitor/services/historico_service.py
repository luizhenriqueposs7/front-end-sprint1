"""
services/historico_service.py
Geração, persistência e leitura de dados históricos simulados de telemetria.
Os dados simulam leituras a cada 15 minutos nos últimos N dias, com cenários
realistas: ciclo térmico diurno, picos de vibração e eventos críticos.
"""

import json
import math
import random
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

DATA_DIR = Path(__file__).parent.parent / "data" / "historico"


# ── Limites operacionais ─────────────────────────────────────────────────────

LIMITES = {
    "temperatura": {"normal": 75, "atencao": 90, "critico": 105, "unidade": "°C"},
    "vibracao":    {"normal": 4.5, "atencao": 7.0, "critico": 11.0, "unidade": "mm/s"},
    "corrente":    {"normal_pct": 5, "atencao_pct": 12, "critico_pct": 20},
    "tensao":      {"normal_pct": 5, "atencao_pct": 10, "critico_pct": 15},
    "rpm":         {"normal_pct": 3, "atencao_pct": 8, "critico_pct": 15},
}


def classificar_status(grandeza: str, valor: float, nominal: float = 0) -> str:
    """Classifica o status de uma leitura com base nos limites operacionais.

    Para temperatura e vibração usa limites absolutos; para corrente,
    tensão e RPM usa desvio percentual sobre o valor nominal.
    """
    cfg = LIMITES[grandeza]

    if "normal" in cfg:
        # Limites absolutos (temperatura, vibração)
        if valor <= cfg["normal"]:
            return "normal"
        elif valor <= cfg["atencao"]:
            return "atencao"
        else:
            return "critico"
    else:
        # Limites percentuais (corrente, tensão, rpm)
        if nominal == 0:
            return "normal"
        desvio = abs(valor - nominal) / nominal * 100
        if desvio < cfg["normal_pct"]:
            return "normal"
        elif desvio < cfg["atencao_pct"]:
            return "atencao"
        else:
            return "critico"


def get_limites():
    """Retorna os limites operacionais para uso em gráficos."""
    return LIMITES


# ── Geração de histórico simulado ────────────────────────────────────────────

def gerar_historico(equipamento: dict, dias: int = 30) -> list[dict]:
    """
    Gera leituras simuladas a cada 15 min para os últimos `dias` dias.
    Inclui:
      - Ciclo térmico diurno (aquece 8h–18h, resfria à noite)
      - Picos esporádicos de vibração (simula desgaste)
      - 2–3 eventos críticos pontuais
      - Ruído gaussiano realista
    """
    registros = []
    agora = datetime.now().replace(second=0, microsecond=0)
    inicio = agora - timedelta(days=dias)

    tensao_nom = float(equipamento.get("tensao_v", 380))
    corrente_nom = float(equipamento.get("corrente_nominal_a", 28.5))
    rpm_nom = float(equipamento.get("velocidade_rpm", 1760))
    temp_base = 45.0  # Temperatura ambiente + base do motor
    vib_base = 2.0    # Vibração base em mm/s

    # Sortear dias para eventos críticos (2-3 eventos no período)
    dias_criticos = sorted(random.sample(range(3, dias - 1), min(3, dias - 3)))
    horas_criticas = [random.randint(9, 16) for _ in dias_criticos]

    # Tendência de degradação lenta na vibração (simula desgaste)
    vib_tendencia = random.uniform(0.01, 0.04)  # mm/s por dia

    t = inicio
    while t <= agora:
        hora = t.hour
        dia_idx = (t - inicio).days
        minuto_do_dia = hora * 60 + t.minute

        # ── Ciclo térmico diurno ─────────────────────────────────────────
        # Sobe durante expediente (7h–17h), pico ~14h
        if 7 <= hora <= 17:
            fator_termico = math.sin((hora - 7) / 10 * math.pi) * 25
        else:
            fator_termico = max(0, 5 - abs(hora - 17) * 1.5)

        temperatura = temp_base + fator_termico + random.gauss(0, 1.5)

        # ── Vibração com tendência + picos ───────────────────────────────
        vibracao = vib_base + dia_idx * vib_tendencia + random.gauss(0, 0.3)

        # Picos esporádicos (a cada ~6h de operação)
        if random.random() < 0.008:
            vibracao += random.uniform(2.0, 5.0)

        # ── Corrente / Tensão / RPM ──────────────────────────────────────
        # Variação leve com carga (correlaciona com temperatura)
        fator_carga = 1 + (fator_termico / 25) * 0.08  # Até +8% na carga máxima
        corrente = corrente_nom * fator_carga + random.gauss(0, corrente_nom * 0.02)
        tensao = tensao_nom + random.gauss(0, tensao_nom * 0.015)
        rpm = rpm_nom + random.gauss(0, rpm_nom * 0.01)

        # ── Eventos críticos ─────────────────────────────────────────────
        for dc, hc in zip(dias_criticos, horas_criticas):
            if dia_idx == dc and abs(hora - hc) <= 1:
                # Evento: superaquecimento + vibração alta
                temperatura += random.uniform(20, 35)
                vibracao += random.uniform(4, 8)
                corrente *= random.uniform(1.15, 1.25)

        # Clamp valores
        temperatura = round(max(20, min(130, temperatura)), 1)
        vibracao = round(max(0.1, min(25, vibracao)), 3)
        corrente = round(max(0.1, corrente), 2)
        tensao = round(max(100, tensao), 1)
        rpm = round(max(100, rpm), 0)

        registro = {
            "timestamp": t.strftime("%Y-%m-%dT%H:%M:%S"),
            "temperatura": {
                "valor": temperatura,
                "status": classificar_status("temperatura", temperatura),
            },
            "vibracao": {
                "valor": vibracao,
                "status": classificar_status("vibracao", vibracao),
            },
            "corrente": {
                "valor": corrente,
                "status": classificar_status("corrente", corrente, corrente_nom),
            },
            "tensao": {
                "valor": tensao,
                "status": classificar_status("tensao", tensao, tensao_nom),
            },
            "rpm": {
                "valor": rpm,
                "status": classificar_status("rpm", rpm, rpm_nom),
            },
        }
        registros.append(registro)
        t += timedelta(minutes=15)

    return registros


# ── Persistência ──────────────────────────────────────────────────────────────

def _caminho_historico(tag: str) -> Path:
    return DATA_DIR / f"{tag}.json"


def salvar_historico(tag: str, dados: list[dict]) -> Path:
    """Salva dados históricos em JSON para uma TAG."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    caminho = _caminho_historico(tag)
    with open(caminho, "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False)
    return caminho


def carregar_historico(tag: str) -> list[dict]:
    """Carrega dados históricos de uma TAG. Retorna lista vazia se não existir."""
    caminho = _caminho_historico(tag)
    if not caminho.exists():
        return []
    with open(caminho, "r", encoding="utf-8") as f:
        return json.load(f)


def garantir_historico(equipamento: dict, dias: int = 30) -> list[dict]:
    """
    Carrega histórico existente ou gera novo se não existir.
    Use esta função nas páginas para garantir que sempre há dados.
    """
    tag = equipamento.get("tag", "UNKNOWN")
    dados = carregar_historico(tag)
    if not dados:
        dados = gerar_historico(equipamento, dias)
        salvar_historico(tag, dados)
    return dados


def regenerar_historico(equipamento: dict, dias: int = 30) -> list[dict]:
    """Força regeneração do histórico (descarta o anterior)."""
    tag = equipamento.get("tag", "UNKNOWN")
    dados = gerar_historico(equipamento, dias)
    salvar_historico(tag, dados)
    return dados


def extrair_eventos_criticos(dados: list[dict]) -> list[dict]:
    """Extrai registros onde pelo menos uma grandeza está em status 'critico'."""
    eventos = []
    grandezas = ["temperatura", "vibracao", "corrente", "tensao", "rpm"]
    for reg in dados:
        criticos = [g for g in grandezas if reg.get(g, {}).get("status") == "critico"]
        if criticos:
            eventos.append({
                "timestamp": reg["timestamp"],
                "grandezas": criticos,
                "valores": {g: reg[g]["valor"] for g in criticos},
            })
    return eventos
