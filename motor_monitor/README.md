# ⚙️ Motor Monitor

Sistema de gestão e monitoramento de ativos industriais (motores elétricos) desenvolvido em **Python + Streamlit**.

> Challenge FIAP 2026 · Sprint 1 + Sprint 2 + Sprint 3

---

## 👥 Integrantes do grupo

| Nome | RM |
|------|----|
| Lucca Phelipe Masini | 564121 |
| Luiz Henrique Poss | 562177 |
| Igor Paixão Sarak | 563726 |
| Bernardo Braga Perobeli | 562468 |
| Felipe Stefani Honorato | 563380 |

---

## 🚀 Como rodar

> ⚠️ Este é um projeto **Python**, não Node.js. Não use `npm` — não há `package.json`.

### Pré-requisitos

- Python 3.10 ou superior ([download](https://www.python.org/downloads/))
- `pip` (vem junto com o Python)

### Passo a passo (Windows / PowerShell)

```powershell
# 1. Entre na pasta do projeto
cd motor_monitor

# 2. Instale as dependências
pip install -r requirements.txt

# 3. Inicie a aplicação
streamlit run app.py
```

A aplicação abre automaticamente em `http://localhost:8501`.

Para encerrar: pressione `Ctrl+C` no terminal.

### Porta ocupada?

Se a 8501 já estiver em uso, rode em outra porta:

```powershell
streamlit run app.py --server.port 8502
```

### Linux / macOS

Mesma sequência, trocando o terminal:

```bash
cd motor_monitor
pip install -r requirements.txt
streamlit run app.py
```

---

## 📁 Estrutura do projeto

```
motor_monitor/
├── app.py                          # Entry point e roteamento
├── components.py                   # Cards reutilizáveis (alerta, estado, evento)
├── requirements.txt
├── test_alertas.py                 # Checagem da camada de alertas
├── data/
│   ├── equipamentos.json           # Persistência local
│   ├── alertas.json                # Caixa de entrada dos alertas (gerada em runtime)
│   └── historico/                  # Histórico por TAG (gerado automaticamente)
│       ├── MTR-001.json
│       └── MTR-002.json
├── assets/                         # Imagens das placas dos motores
│   ├── placa_MTR-001.png
│   └── placa_MTR-002.png
├── pages/
│   ├── alertas.py                  # Painel de alertas e estados        (Sprint 3)
│   ├── consulta.py                 # Lista de equipamentos          (Sprint 1)
│   ├── cadastro.py                 # Formulário de cadastro/edição  (Sprint 1)
│   ├── dados_brutos.py             # Sinal ADC → unidade física     (Sprint 1)
│   ├── dashboard.py                # Dashboard de telemetria        (Sprint 2)
│   ├── planta.py                   # Navegação por planta/área      (Sprint 2)
│   └── historico.py                # Séries temporais e eventos     (Sprint 2)
└── services/
    ├── equipamento_service.py      # CRUD de equipamentos
    ├── sensor_service.py           # Mock de sensores + conversão ADC
    ├── historico_service.py        # Geração e leitura de histórico + classificação de status
    ├── alerta_service.py           # Alertas do pipeline analítico       (Sprint 3)
    └── nlp_service.py              # Resumos em linguagem natural        (Sprint 3)
```

### Por que essa separação?

| Camada | Responsabilidade | Quando mudar |
|--------|-----------------|--------------|
| `pages/` | Interface do usuário | Redesign visual, migração de framework |
| `components.py` | Cards reutilizáveis | Ajuste de identidade visual |
| `services/` | Lógica de dados | Trocar mock por sensor real, adicionar ML |
| `data/` | Persistência | Migrar para banco de dados |

---

## 📊 Funcionalidades

### Sprint 1 — Cadastro técnico e leitura de sensores

- Cadastro de equipamentos com TAG única, fabricante, modelo, parâmetros elétricos e mecânicos
- Leitura simulada de 5 grandezas (Tensão, Corrente, RPM, Temperatura, Vibração)
- Conversão de sinal ADC 12 bits (0–4095) para unidade física
- Página de dados brutos com tabela de conversão visível ao operador
- Persistência em JSON local

### Sprint 2 — Visualização operacional

- **Dashboard de telemetria** — semáforo global de saúde, 5 gauges Plotly com cor por status e sparklines das últimas 24h
- **Navegação por planta/área** — visão macro com contagem de motores por estado de saúde e drill-down direto pro dashboard
- **Séries temporais** — gráficos por grandeza com faixas de limite (normal/atenção/crítico) sombreadas, gráfico combinado normalizado e seletor de período (7/15/30 dias)
- **Eventos críticos** — tabela com timestamps dos momentos em que pelo menos uma grandeza ficou crítica
- **Exportação CSV** — download dos dados filtrados pelo período
- **Placa do motor** — imagem da placa associada aos dados técnicos extraídos via visão computacional

### Sprint 3 — Inteligência operacional e apoio à decisão

- **Painel de Alertas e Estados** — página inicial do sistema, antes de escolher qualquer equipamento: mostra de uma vez o estado de todos os ativos monitorados
- **Estado dinâmico do ativo** — o card muda de 🟢 Saudável para 🟡 Atenção ou 🔴 Crítico conforme os alertas chegam, e volta a Saudável quando são reconhecidos
- **Resumos em linguagem natural** — cada alerta e cada estado vem com um texto explicando o desvio, a hipótese técnica e o que fazer (ver *Integração com NLP* abaixo)
- **Apoio à decisão** — cards de recomendação com ação concreta e prazo, sempre voltados ao alerta mais severo em aberto
- **Atualização por botão ou timer** — `🔄 Atualizar agora` roda uma varredura sob demanda; o toggle de atualização automática dispara a varredura a cada 10 s, 30 s ou 1 min
- **Notificação de alerta novo** — cada anomalia detectada aparece como toast na tela, além de entrar nos cards
- **Histórico de eventos** — tabela com todos os alertas registrados, em aberto ou já reconhecidos
- **Baixa operacional** — `✅ Reconhecer` por alerta ou `✅ Reconhecer todos` para voltar o painel ao estado saudável

---

## 🧠 Integração com NLP

Os resumos textuais são gerados hoje por **template determinístico** em `services/nlp_service.py`. O contrato já é o definitivo:

```python
resumir_alerta(alerta)                 -> str   # resumo de um alerta
descrever_estado(tag, estado, alertas) -> str   # resumo do estado do ativo
```

Quando o modelo de NLP ficar pronto, há dois caminhos — nenhum deles toca as páginas:

1. O pipeline analítico grava o texto no campo `resumo_nlp` do alerta. `resumir_alerta()` devolve esse texto e ignora o template.
2. Ou troca-se o corpo das duas funções pela chamada ao modelo.

A interface mostra a procedência do texto no próprio card (`RESUMO AUTOMÁTICO (TEMPLATE)` vs `RESUMO GERADO POR NLP`), então dá para plugar o modelo aos poucos, alerta por alerta.

---

## 🔌 De onde vêm os alertas

O front-end **não executa modelo nenhum**. `data/alertas.json` é uma caixa de entrada: quem escreve é o pipeline analítico (detecção de anomalia + NLP), que roda fora do Streamlit. A interface só consome:

```python
listar_alertas()            # alertas já classificados
estado_dos_equipamentos()   # estado consolidado por ativo
reconhecer_alerta(id)       # baixa operacional
```

Enquanto o modelo real não existe, `_detectar()` em `services/alerta_service.py` simula a detecção. Trocar essa função por um consumidor de API, fila MQTT ou banco **não muda uma linha das páginas** — o formato do alerta é o contrato:

```json
{
  "id": "ALM-0001",
  "tag": "MTR-001",
  "equipamento_id": "1",
  "grandeza": "vibracao",
  "valor": 8.4,
  "unidade": "mm/s",
  "nominal": 2.5,
  "severidade": "critico",
  "score_anomalia": 0.92,
  "modelo_analitico": "IsolationForest v0.1",
  "resumo_nlp": null,
  "recomendacoes": [{ "titulo": "...", "acao": "...", "prazo": "Imediato" }],
  "reconhecido": false
}
```

O estado do equipamento é sempre a **pior severidade entre os alertas não reconhecidos** — é o que faz o card mudar de cor sem a página precisar saber como o modelo chegou lá.

---

## ✅ Testes

```powershell
cd motor_monitor
python test_alertas.py
```

Cobre a consolidação de estado, a baixa de alerta, o fallback do resumo do NLP e o formato de saída do detector.

---

## 🎨 Cores semânticas

| Estado | Cor | Significado |
|--------|-----|-------------|
| 🟢 Normal | `#10b981` | Dentro dos limites operacionais |
| 🟡 Atenção | `#f59e0b` | Próximo dos limites |
| 🔴 Crítico | `#ef4444` | Acima dos limites |

---

## 🔧 Limites operacionais

| Grandeza | Normal | Atenção | Crítico |
|----------|--------|---------|---------|
| Temperatura | ≤ 75°C | ≤ 90°C | > 90°C |
| Vibração | ≤ 4,5 mm/s | ≤ 7,0 mm/s | > 7,0 mm/s |
| Corrente | desvio < 5% | < 12% | > 12% |
| Tensão | desvio < 5% | < 10% | > 10% |
| RPM | desvio < 3% | < 8% | > 8% |

Toda a classificação passa por `services/historico_service.classificar_status`, garantindo que o semáforo global, os cards individuais e a tabela de eventos críticos usem exatamente os mesmos limites.

---

## 📡 Conversão de sinal ADC

Os sensores retornam sinais digitais de **12 bits (0–4095)**. A conversão aplicada é linear:

```
valor_físico = raw × escala + offset
```

| Grandeza | Escala | Full-scale |
|----------|--------|------------|
| Tensão | 380 V / 4095 | 380 V |
| Corrente | 30 A / 4095 | 30 A |
| Velocidade | 3600 RPM / 4095 | 3600 RPM |
| Temperatura | 120 °C / 4095 | 120 °C |
| Vibração | 50 mm/s / 4095 | 50 mm/s |

---

## 🏗️ Arquitetura

Separação em três camadas independentes:

- **`pages/`** — interface Streamlit, sem regra de negócio
- **`services/`** — lógica de dados (CRUD, mock de sensores, geração de histórico, classificação de status)
- **`data/`** — persistência local em JSON, substituível por banco de dados sem tocar nas demais camadas

A lógica de classificação de status (normal/atenção/crítico) é centralizada em uma função única e usada por todas as páginas, garantindo coerência entre o semáforo global do dashboard, os cards da visão por planta e a extração de eventos críticos no histórico.

---

## 🔗 Links

- 📦 [Repositório no GitHub](https://github.com/luizhenriqueposs7/front-end-sprint1)
- 🎥 Vídeo de demonstração — _(adicionar link após upload)_

---

FIAP · Challenge 2026
