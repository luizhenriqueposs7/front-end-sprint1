# ⚙️ Motor Monitor — Sprint 1

Sistema de gestão de ativos industriais desenvolvido com **Streamlit**.

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
│   └── equipamentos.json           # Persistência local (substituível por DB)
├── pages/
│   ├── consulta.py                 # Lista de equipamentos
│   ├── cadastro.py                 # Formulário de cadastro/edição
│   └── dados_brutos.py             # Visualização com conversão de sinal
└── services/
    ├── equipamento_service.py      # CRUD de equipamentos
    └── sensor_service.py           # Mock de sensores + conversão ADC → unidade física
```

### Por que essa separação?

| Camada | Responsabilidade | Quando mudar |
|--------|-----------------|--------------|
| `pages/` | Interface do usuário | Redesign visual, migração de framework |
| `services/` | Lógica de dados | Trocar mock por sensor real, adicionar ML |
| `data/` | Persistência | Migrar para banco de dados |

Nos próximos sprints, a integração com o modelo de ML ocorre **apenas em `services/`**, sem tocar nas páginas.

---

## 📡 Conversão de sinal bruto

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
| 🟢 Normal | `#1a7a4a` | Desvio < 5% do nominal |
| 🟡 Atenção | `#a07800` | Desvio entre 5–12% |
| 🔴 Crítico | `#a02020` | Desvio > 12% |

---

---

FIAP · Challenge 2026
