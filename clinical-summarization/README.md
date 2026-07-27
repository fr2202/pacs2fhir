# Clinical Summarization

> Sumarização automática de relatórios radiológicos em português com avaliação multidimensional — ROUGE, BERTScore, fidelidade clínica e human judgement.

Parte do projeto **[PACS2FHIR — Clinical Intelligence Platform](https://fr2202.github.io/pacs2fhir)** · BLOCKCHAIN.PT WP2 · IPLeiria / ESTG-Leiria

## Resultados

| Modelo | ROUGE-1 F | ROUGE-2 F | BERTScore F | Fidelidade |
|--------|-----------|-----------|-------------|------------|
| **PTT5-FT v2** ⭐ | **0.493** | **0.470** | **0.805** | 0.592 |
| Extractive-PT | 0.349 | 0.301 | 0.699 | 0.538 |
| Gemma 3.1 (local) | 0.341 | 0.288 | 0.762 | 0.571 |
| mT5-XLSum | 0.118 | 0.043 | 0.701 | 0.232 |

*Avaliado sobre 616 relatórios de teste com golden collection criada por 2 radiologistas do CHULN.*

## Estrutura

```
clinical-summarization/
├── evaluate.py                # Avaliar um modelo
├── evaluate_all.py            # Avaliar todos os modelos
├── requirements.txt
├── models/
│   ├── ptt5_model.py          # PTT5 fine-tuned (melhor modelo)
│   ├── mt5_model.py           # mT5-XLSum
│   ├── extractive_model.py    # Extração de frases-chave
│   └── gemma_model.py         # Gemma 3.1 local
├── evaluation/
│   ├── rouge_eval.py
│   ├── bertscore_eval.py
│   ├── faithfulness_eval.py   # Fidelidade clínica
│   └── human_eval.py          # Interface human judgement
├── data/
│   ├── raw/                   # Relatórios FHIR (gitignored)
│   └── processed/             # Tensors, splits (gitignored)
├── results/
│   └── eval_*.json            # Resultados finais (gitignored)
├── examples/
│   ├── sample_input.txt       # Relatório TC exemplo
│   ├── sample_output_ptt5.txt # Resumo PTT5-FT v2
│   └── eval_summary.json      # Métricas exemplo
├── tests/
│   └── test_models.py
└── docs/
    └── evaluation_framework.md
```

## Como executar

```bash
pip install -r requirements.txt

# Avaliar PTT5-FT v2 (melhor modelo)
python evaluate.py --model ptt5 --split test

# Avaliar todos os modelos
python evaluate_all.py

# Gerar resumo para um relatório
python evaluate.py --model ptt5 --input examples/sample_input.txt
```

## Dataset

- **Volume:** 9.921 relatórios de TC do CHULN (anonimizados)
- **Split:** Train 7.937 · Val 992 · Test 992
- **Golden collection:** 616 relatórios com resumos manuais por 2 radiologistas
- **Idioma:** Português (PT-PT)

> Os dados clínicos do CHULN são confidenciais e não estão incluídos.

## Modelos

| Modelo | Tipo | Base |
|--------|------|------|
| PTT5-FT v2 | Generativo (fine-tuned) | neuralmind/ptt5-large-portuguese-vocab |
| mT5-XLSum | Generativo (zero-shot) | google/mt5-base |
| Extractive-PT | Extrativo | spaCy pt_core_news_lg |
| Gemma 3.1 | Generativo local (LLM) | google/gemma-3.1 |

## Publicações

- Villacis Vera L., Malheiro R., Craveiro O. *"LLM-Based Medical Summarization Survey and a Multidimensional Evaluation Framework."* Artificial Intelligence in Medicine · Elsevier · Q1 · Under Review 2026.
- Villacis Vera L., Malheiro R., Craveiro O. *"Multidimensional Evaluation Framework for Local LLM-Based Clinical Summarization: A Cross-Lingual Prototype on Computed Tomography Reports."* MAKE · MDPI · Q1 · Under Review 2026.
