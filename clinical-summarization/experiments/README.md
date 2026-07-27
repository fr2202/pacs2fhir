# Cuaderno de Experimentos — Sumarización Multilingüe CHULN

**Tesis de Maestría** | CHULN Radiology Reports | Português Europeu (pt-PT)  
**Directorio de trabajo:** `fhir_transformer/`  
**Dataset:** 9,921 registros PACS → 992 test (616 con referencia real)

---

## Objetivo

Desarrollar e integrar un sistema de sumarización automática multilingüe de informes radiológicos en el pipeline FHIR R4 del CHULN, evaluando distintos enfoques (extractivo, abstractivo zero-shot, abstractivo fine-tuned, traducción) con métricas de calidad publicables.

---

## Tabla de experimentos

| ID | Experimento | Estado | ROUGE-1 F | Fecha |
|----|-------------|--------|-----------|-------|
| [EXP-01](EXP_01_baseline_extractivo.md) | Baseline extractivo TF-IDF | ✅ Completo | 0.378 | 2026-06-20 |
| [EXP-02](EXP_02_ablacion_zero_shot.md) | Ablación zero-shot (mT5-XLSum, mT5-small) | ✅ Completo | 0.118 / 0.103 | 2026-06-20 |
| [EXP-03](EXP_03_traduccion_pt_en.md) | Traducción PT→EN (opus-mt-ROMANCE-en) | ✅ Completo | — (cross-lingual) | 2026-06-20 |
| [EXP-04](EXP_04_metricas_semanticas.md) | BERTScore + NLI Faithfulness | ✅ Completo | 0.699 (BS-F PT) / 0.677 (BS-F EN) | 2026-06-20 |
| [EXP-05](EXP_05_finetuning_ptt5.md) | Fine-tuning ptt5-base | 🔄 En ejecución | — | 2026-06-20 |
| [EXP-06](EXP_06_evaluacion_final.md) | Evaluación final multilingüe completa | ⏳ Pendiente | — | — |

---

## Resultados parciales acumulados

| Modelo | ROUGE-1 | ROUGE-2 | ROUGE-L | n | Notas |
|--------|---------|---------|---------|---|-------|
| Extractivo TF-IDF (PT) | **0.378** | **0.319** | **0.340** | 616 | Baseline sólido; BERTScore-F=0.699, Faith=0.538 |
| mT5-XLSum zero-shot (PT) | 0.118 | 0.048 | 0.100 | 100 | Alucinaciones: Faith=0.232, BERTScore-F=0.513 |
| mT5-small zero-shot (PT) | 0.103 | 0.067 | 0.092 | 100 | BERTScore-F=0.527, Faith=0.415 |
| ptt5-base fine-tuned (PT) | — | — | — | — | Pendiente (EXP-05) |
| Extractivo + opus-mt-ROMANCE-en (EN) | n/a* | n/a* | n/a* | 100 | BERTScore cross-lingual F=0.677, Faith=0.429 |
| ptt5-base-ft + opus-mt (EN) | — | — | — | — | Pendiente (EXP-06) |

---

## Entorno técnico

| Componente | Versión |
|------------|---------|
| Python | 3.13.7 |
| torch | 2.6.0+cu124 |
| transformers | 4.57.6 |
| GPU | NVIDIA RTX 3060 Laptop (6 GB VRAM) |
| OS | Windows 10 |

> **Nota importante:** `transformers>=5.0` eliminó los pipelines `summarization` y `text2text-generation`. Usar `transformers<5.0.0`. Para Python 3.13, PyTorch CUDA requiere `cu124` (no `cu121`).

---

## Estructura de archivos relacionados

```
fhir_transformer/
├── summarization/           ← módulo Python (config, extractive, abstractive, translation, evaluation)
├── agents/summarization_agent.py
├── scripts/
│   ├── eval_multilingual.py ← script de evaluación
│   └── run_summarization.py ← post-procesado de bundles FHIR
├── results/
│   ├── eval_multilingual.json
│   └── eval_multilingual_table.md
└── experimentos/            ← este cuaderno
```
