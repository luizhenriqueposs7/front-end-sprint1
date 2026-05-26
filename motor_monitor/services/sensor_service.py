"""
services/sensor_service.py
Mock de dados de sensores com conversão de sinal bruto → unidade física.
Nas próximas sprints, substitua _gerar_sinal_bruto() pela leitura real do sensor.
"""

import random
import math
from typing import Optional

from services.historico_service import classificar_status


# ── Constantes de conversão ──────────────────────────────────────────────────
# Simulam os parâmetros do circuito de condicionamento de sinal

TENSAO_OFFSET = 0.0        # V
TENSAO_ESCALA = 380.0 / 4095   # full-scale 380 V em 12 bits ADC

CORRENTE_OFFSET = 0.0
CORRENTE_ESCALA = 30.0 / 4095  # full-scale 30 A

RPM_OFFSET = 0.0
RPM_ESCALA = 3600.0 / 4095     # full-scale 3600 RPM

TEMPERATURA_OFFSET = 0.0
TEMPERATURA_ESCALA = 120.0 / 4095  # full-scale 120 °C

VIBRACAO_OFFSET = 0.0
VIBRACAO_ESCALA = 50.0 / 4095  # full-scale 50 mm/s


# ── Conversores ───────────────────────────────────────────────────────────────

def raw_para_tensao(raw: int) -> float:
    return round(raw * TENSAO_ESCALA + TENSAO_OFFSET, 2)

def raw_para_corrente(raw: int) -> float:
    return round(raw * CORRENTE_ESCALA + CORRENTE_OFFSET, 2)

def raw_para_rpm(raw: int) -> float:
    return round(raw * RPM_ESCALA + RPM_OFFSET, 1)

def raw_para_temperatura(raw: int) -> float:
    return round(raw * TEMPERATURA_ESCALA + TEMPERATURA_OFFSET, 1)

def raw_para_vibracao(raw: int) -> float:
    return round(raw * VIBRACAO_ESCALA + VIBRACAO_OFFSET, 3)


# ── Gerador de leitura ────────────────────────────────────────────────────────

def _gerar_sinal_bruto(nominal: float, escala: float, variacao_pct: float = 0.05) -> int:
    """Simula um ADC de 12 bits com ruído gaussiano em torno do nominal."""
    raw_nominal = int(nominal / escala)
    ruido = int(random.gauss(0, raw_nominal * variacao_pct))
    return max(0, min(4095, raw_nominal + ruido))


def gerar_leitura(equipamento: Optional[dict] = None) -> dict:
    """
    Retorna uma leitura instantânea com sinal bruto e valor convertido.
    Se um equipamento for fornecido, usa seus parâmetros nominais.
    """
    tensao_nominal  = float(equipamento.get("tensao_v", 380))      if equipamento else 380.0
    corrente_nominal = float(equipamento.get("corrente_nominal_a", 28.5)) if equipamento else 28.5
    rpm_nominal     = float(equipamento.get("velocidade_rpm", 1760)) if equipamento else 1760.0

    raw_t  = _gerar_sinal_bruto(tensao_nominal,   TENSAO_ESCALA)
    raw_c  = _gerar_sinal_bruto(corrente_nominal,  CORRENTE_ESCALA)
    raw_r  = _gerar_sinal_bruto(rpm_nominal,       RPM_ESCALA)
    raw_tp = _gerar_sinal_bruto(65.0,              TEMPERATURA_ESCALA, variacao_pct=0.08)
    raw_v  = _gerar_sinal_bruto(2.5,               VIBRACAO_ESCALA, variacao_pct=0.15)

    return {
        "tensao":      {"raw": raw_t,  "valor": raw_para_tensao(raw_t),      "unidade": "V",    "nominal": tensao_nominal},
        "corrente":    {"raw": raw_c,  "valor": raw_para_corrente(raw_c),    "unidade": "A",    "nominal": corrente_nominal},
        "rpm":         {"raw": raw_r,  "valor": raw_para_rpm(raw_r),         "unidade": "RPM",  "nominal": rpm_nominal},
        "temperatura": {"raw": raw_tp, "valor": raw_para_temperatura(raw_tp),"unidade": "°C",   "nominal": 65.0},
        "vibracao":    {"raw": raw_v,  "valor": raw_para_vibracao(raw_v),    "unidade": "mm/s", "nominal": 2.5},
    }


def avaliar_status(leitura: dict) -> str:
    """Retorna o pior status entre as grandezas usando os limites operacionais.

    Mantém coerência entre o semáforo global, os cards individuais e os
    eventos críticos do histórico, todos passando pela mesma função
    classificar_status() do historico_service.
    """
    ordem = {"normal": 0, "atencao": 1, "critico": 2}
    pior = "normal"
    for grandeza, dados in leitura.items():
        s = classificar_status(grandeza, dados["valor"], dados.get("nominal", 0))
        if ordem[s] > ordem[pior]:
            pior = s
    return pior
