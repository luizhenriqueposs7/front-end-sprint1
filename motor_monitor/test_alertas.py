"""
test_alertas.py — checagem mínima da camada de alertas da Sprint 3.

Roda sem framework:   python test_alertas.py   (a partir da pasta motor_monitor)

ponytail: cobre só o que quebra silenciosamente na tela — consolidação de
estado, baixa de alerta e coerência do resumo do NLP. O resto é HTML.
"""

import tempfile
import threading
from pathlib import Path

from services import alerta_service as al
from services.nlp_service import (
    descrever_estado,
    fonte_do_resumo,
    formatar_numero,
    resumir_alerta,
)

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


def test_ids_nao_colidem_com_abas_gravando_juntas():
    """Duas abas com o timer ligado gravam em threads diferentes."""
    al.reconhecer_todos()
    antes = {a["id"] for a in al.listar_alertas()}

    threads = [threading.Thread(target=_alerta, args=("atencao",)) for _ in range(12)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    ids = [a["id"] for a in al.listar_alertas()]
    assert len(ids) == len(set(ids)), "id repetido derruba a página com DuplicateWidgetID"
    assert len(set(ids) - antes) == 12, "gravação concorrente perdeu alertas"
    al.reconhecer_todos()


def test_poda_do_historico_nunca_descarta_alerta_em_aberto():
    original = al.MAX_HISTORICO
    al.MAX_HISTORICO = 10
    try:
        aberto = _alerta("critico")
        for _ in range(20):
            reconhecido = _alerta("atencao")
            al.reconhecer_alerta(reconhecido["id"])
        todos = al.listar_alertas()
        assert len(todos) <= 10, f"histórico passou do teto: {len(todos)}"
        assert aberto["id"] in {a["id"] for a in todos}, "alerta em aberto sumiu na poda"
    finally:
        al.MAX_HISTORICO = original
    al.reconhecer_todos()


def test_alerta_fora_do_contrato_nao_derruba_o_resumo():
    """O pipeline é externo: grandeza/severidade novas não podem quebrar a tela."""
    estranho = {"tag": "MTR-X", "grandeza": "fluxo_magnetico", "severidade": "desconhecida",
                "valor": "n/d", "nominal": None, "score_anomalia": None}
    texto = resumir_alerta(estranho)
    assert "MTR-X" in texto and "fluxo_magnetico" in texto

    al.registrar_alerta(dict(estranho, equipamento_id=EQ_ID))
    estado = next(e for e in al.estado_dos_equipamentos() if e["equipamento"]["id"] == EQ_ID)
    assert estado["estado"] == "normal", "severidade desconhecida não pode virar crítico"
    assert al.alerta_mais_severo(al.listar_alertas(apenas_ativos=True)) is not None
    al.reconhecer_todos()


def test_texto_do_cadastro_nao_vira_html():
    from components import _md, escapar
    assert escapar('<script>alert(1)</script>') == "&lt;script&gt;alert(1)&lt;/script&gt;"
    # markdown do NLP continua virando tag; HTML de fora, não.
    assert _md("**WEG <b>W22</b>**") == "<b>WEG &lt;b&gt;W22&lt;/b&gt;</b>"


def test_numero_sai_no_padrao_brasileiro():
    assert formatar_numero(32.72) == "32,72"
    assert formatar_numero(1760) == "1.760"
    assert formatar_numero(28.50) == "28,5"
    assert formatar_numero("n/d") == "n/d"


if __name__ == "__main__":
    for nome, func in list(globals().items()):
        if nome.startswith("test_"):
            func()
            print(f"ok  {nome}")
    print("\nTodos os testes passaram.")
