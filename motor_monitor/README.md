# ⚙️ Motor Monitor — Sprint 1 + Sprint 2

Sistema de gestão e monitoramento de ativos industriais desenvolvido com **Streamlit**.

## 🚀 Como rodar

```bash
# 1. Clone o repositório
git clone <seu-repo>
cd motor_monitor

# 2. Instale as dependências
pip install -r requirements.txt

# 3. Rode a aplicação
streamlit run app.py
```

Acesse em `http://localhost:8501`

---

## 📁 Estrutura do projeto

```
motor_monitor/
├── app.py                          # Entry point e roteamento
├── requirements.txt
├── data/
│   ├── equipamentos.json           # Persistência local (substituível por DB)
│   └── historico/                   # Dados históricos por TAG (gerados automaticamente)
│       ├── MTR-001.json
│       └── MTR-002.json
├── assets/                         # Imagens das placas dos motores
│   ├── placa_MTR-001.png
│   └── placa_MTR-002.png
├── pages/
│   ├── consulta.py                 # Lista de equipamentos
│   ├── cadastro.py                 # Formulário de cadastro/edição
│   ├── dados_brutos.py             # Visualização com conversão de sinal
│   ├── dashboard.py                # Dashboard de telemetria (Sprint 2)
│   ├── planta.py                   # Navegação por Planta/Área (Sprint 2)
│   └── historico.py                # Gráficos de séries temporais (Sprint 2)
└── services/
    ├── equipamento_service.py      # CRUD de equipamentos
    ├── sensor_service.py           # Mock de sensores + conversão ADC → unidade física
    └── historico_service.py        # Geração e leitura de dados históricos (Sprint 2)
```

### Por que essa separação?

| Camada | Responsabilidade | Quando mudar |
|--------|-----------------|--------------|
| `pages/` | Interface do usuário | Redesign visual, migração de framework |
| `services/` | Lógica de dados | Trocar mock por sensor real, adicionar ML |
| `data/` | Persistência | Migrar para banco de dados |

---

## 📊 Sprint 2 — Visualização Operacional

### Dashboard de Telemetria
- **Gauges Plotly** para cada grandeza (Temperatura, Vibração, Corrente, Tensão, RPM)
- **Semáforo de saúde global** com indicador colorido (verde/amarelo/vermelho)
- **Sparklines** com evolução das últimas 24h
- **Integração da placa do motor** com dados técnicos extraídos

### Navegação por Planta/Área
- Visão macro por localização com contagem de ativos por status
- Cards individuais de cada motor com badges de telemetria
- Navegação direta para o dashboard do motor selecionado

### Gráficos de Séries Temporais
- Gráficos interativos Plotly com zoom, pan e hover
- **Faixas de limite operacional** (Normal / Atenção / Crítico)
- Gráfico combinado com normalização para comparação entre grandezas
- **Tabela de eventos críticos** com timestamps de anomalias
- **Exportação CSV** dos dados filtrados

---

## 📡 Conversão de sinal bruto (Sprint 1)

Os sensores retornam sinais digitais de **12 bits (0–4095)** via ADC. A conversão aplicada é:

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

## 🎨 Cores semânticas

| Estado | Cor | Significado |
|--------|-----|-------------|
| 🟢 Normal | `#10b981` | Desvio < 5% / Dentro dos limites |
| 🟡 Atenção | `#f59e0b` | Desvio entre 5–12% / Próximo dos limites |
| 🔴 Crítico | `#ef4444` | Desvio > 12% / Acima dos limites |

---

## 🔧 Limites Operacionais (Sprint 2)

| Grandeza | Normal | Atenção | Crítico |
|----------|--------|---------|---------|
| Temperatura | ≤ 75°C | ≤ 90°C | > 90°C |
| Vibração | ≤ 4.5 mm/s | ≤ 7.0 mm/s | > 7.0 mm/s |
| Corrente | < 5% desvio | < 12% desvio | > 12% desvio |
| Tensão | < 5% desvio | < 10% desvio | > 10% desvio |
| RPM | < 3% desvio | < 8% desvio | > 8% desvio |

---

FIAP · Challenge 2026
