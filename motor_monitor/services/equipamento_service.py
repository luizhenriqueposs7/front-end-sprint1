"""
services/equipamento_service.py
Camada de serviço para gerenciamento de equipamentos.
Toda a lógica de dados fica aqui — troque a fonte de dados
sem tocar nas páginas.
"""

import json
import uuid
from pathlib import Path
from datetime import date
from typing import Optional

DATA_PATH = Path(__file__).parent.parent / "data" / "equipamentos.json"


def _load() -> list[dict]:
    if not DATA_PATH.exists():
        return []
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def _save(data: list[dict]) -> None:
    with open(DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def listar_equipamentos() -> list[dict]:
    return _load()


def buscar_por_id(equipamento_id: str) -> Optional[dict]:
    return next((e for e in _load() if e["id"] == equipamento_id), None)


def salvar_equipamento(dados: dict) -> dict:
    equipamentos = _load()
    dados["id"] = str(uuid.uuid4())[:8]
    dados["data_cadastro"] = str(date.today())
    equipamentos.append(dados)
    _save(equipamentos)
    return dados


def atualizar_equipamento(equipamento_id: str, dados: dict) -> bool:
    equipamentos = _load()
    for i, e in enumerate(equipamentos):
        if e["id"] == equipamento_id:
            equipamentos[i] = {**e, **dados, "id": equipamento_id}
            _save(equipamentos)
            return True
    return False


def excluir_equipamento(equipamento_id: str) -> bool:
    equipamentos = _load()
    novos = [e for e in equipamentos if e["id"] != equipamento_id]
    if len(novos) == len(equipamentos):
        return False
    _save(novos)
    return True


def tag_existe(tag: str, ignorar_id: str = "") -> bool:
    return any(
        e["tag"].upper() == tag.upper() and e["id"] != ignorar_id
        for e in _load()
    )


def listar_localizacoes() -> list[str]:
    """Retorna lista única de localizações cadastradas."""
    locs = set()
    for e in _load():
        loc = e.get("localizacao", "").strip()
        if loc:
            locs.add(loc)
    return sorted(locs)


def buscar_por_localizacao(localizacao: str) -> list[dict]:
    """Retorna equipamentos que pertencem a uma localização específica."""
    return [
        e for e in _load()
        if e.get("localizacao", "").strip().lower() == localizacao.strip().lower()
    ]
