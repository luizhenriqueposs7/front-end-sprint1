"""
test_alertas.py — checagem mínima da camada de alertas da Sprint 3.

Roda sem framework:   python test_alertas.py   (a partir da pasta motor_monitor)

ponytail: cobre só o que quebra silenciosamente na tela — consolidação de
estado, baixa de alerta e coerência do resumo do NLP. O resto é HTML.
"""

import tempfile
from pathlib import Path

from services import alerta_service as al
from services.nlp_service import descrever_estado, fonte_do_resumo, resumir_alerta

# Isola a "caixa de entrada" para não sujar os dados da aplicação.
al.ALERTAS_PATH = Path(tempfile.mkdtemp()) / "alertas.json"

EQ_ID = al.listar_equipamentos()[0]["id"]
TAG = al.listar_equipamentos()[0]["tag"]


def _alerta(severidade, grandeza="vibracao", valor=9.0):
    return al.registrar_alerta({
        "equipamento_id": EQ_ID, "tag": TAG, "grandeza": grandeza,
        "valor": valor, "unidade": "mm/s", "nominal": 2.5,
        "severidade": severidade, "score_anomalia": 0.9,
        "modelo_analitico": "teste", "recomendacoes": [],
    })


def test_sem_alerta_o_ativo_fica_saudavel():
    estado = next(e for e in al.estado_dos_equipamentos() if e["equipamento"]["id"] == EQ_ID)
    assert estado["estado"] == "normal", estado["estado"]


def test_estado_sobe_para_a_pior_severidade():
    _alerta("atencao")
    estado = next(e for e in al.estado_dos_equipamentos() if e["equipamento"]["id"] == EQ_ID)
    assert estado["estado"] == "atencao", estado["estado"]

    critico = _alerta("critico")
    estado = next(e for e in al.estado_dos_equipamentos() if e["equipamento"]["id"] == EQ_ID)
    assert estado["estado"] == "critico", "crítico tem que sobrepor atenção"

    # O apoio à decisão sempre aponta para o alerta mais grave.
    assert al.alerta_mais_severo(al.listar_alertas(apenas_ativos=True))["id"] == critico["id"]


def test_reconhecer_baixa_o_alerta_e_volta_o_estado():
    assert al.reconhecer_todos() >= 1
    assert al.listar_alertas(apenas_ativos=True) == []
    estado = next(e for e in al.estado_dos_equipamentos() if e["equipamento"]["id"] == EQ_ID)
    assert estado["estado"] == "normal", "sem alerta ativo o ativo volta a saudável"
    # Histórico preserva os eventos já reconhecidos.
    assert len(al.listar_alertas()) >= 2


def test_reconhecer_alerta_inexistente_nao_quebra():
    assert al.reconhecer_alerta("ALM-9999") is False


def test_resumo_usa_o_texto_do_nlp_quando_existir():
    a = _alerta("critico")
    assert TAG in resumir_alerta(a) and "template" in fonte_do_resumo(a).lower()

    a["resumo_nlp"] = "Texto vindo do modelo de NLP."
    assert resumir_alerta(a) == "Texto vindo do modelo de NLP."
    assert fonte_do_resumo(a) == "Resumo gerado por NLP"
    al.reconhecer_todos()


def test_descricao_de_estado_acompanha_a_severidade():
    assert "dentro da faixa esperada" in descrever_estado(TAG, "normal", [])
    assert "crítico" in descrever_estado(TAG, "critico", [_alerta("critico")])
    al.reconhecer_todos()


def test_detector_gera_alerta_no_formato_esperado():
    campos = {"equipamento_id", "tag", "grandeza", "valor", "unidade", "severidade",
              "score_anomalia", "recomendacoes"}
    # O detector é probabilístico; algumas varreduras não acham nada.
    for _ in range(50):
        for novo in al.verificar_novos_alertas():
            assert campos <= set(novo), campos - set(novo)
            assert novo["severidade"] in ("atencao", "critico")
            assert novo["recomendacoes"], "todo alerta traz apoio à decisão"
            return
    raise AssertionError("50 varreduras sem nenhum alerta — detector provavelmente quebrado")


if __name__ == "__main__":
    for nome, func in list(globals().items()):
        if nome.startswith("test_"):
            func()
            print(f"ok  {nome}")
    print("\nTodos os testes passaram.")
