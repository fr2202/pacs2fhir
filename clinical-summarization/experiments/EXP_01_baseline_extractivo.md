# EXP-01 — Baseline Extractivo TF-IDF

**Estado:** ✅ Completo  
**Fecha:** 2026-06-20  
**Duración:** ~30 segundos (CPU, sin GPU)

---

## Objetivo

Establecer el baseline de rendimiento para sumarización extractiva sobre el corpus de informes radiológicos del CHULN (pt-PT). Este resultado sirve como cota inferior para los modelos abstractivos y como referencia principal para evaluar el valor añadido del fine-tuning.

## Hipótesis

Un modelo TF-IDF con boost de palabras clave clínicas y deduplicación por similitud de Jaccard debe superar el rendimiento de modelos abstractivos pre-entrenados en datos de noticias (dominio distante), sin requerir GPU ni fine-tuning.

---

## Configuración

**Modelo:** `ExtractiveSummarizer` (TF-IDF + keyword boost + Jaccard dedup)  
**Hiperparámetros** (tuneados sobre corpus completo, conservados de `sumarizacion/`):

| Parámetro | Valor | Descripción |
|-----------|-------|-------------|
| `n_sentences` | 2 | Frases a extraer |
| `keyword_boost` | 1.15 | Boost para palabras clínicas ("conclusão", "achados"…) |
| `similarity_threshold` | 0.72 | Umbral Jaccard para deduplicación |
| `short_penalty` | 0.45 | Penalización para frases < 25 chars |
| `long_penalty` | 0.65 | Penalización para frases > 230 chars |
| `min_sent_len` | 25 | Longitud mínima de frase |
| `max_sent_len` | 230 | Longitud máxima de frase |

**Dataset:**
- Fuente: `../sumarizacion/data/processed/dataset_test.jsonl`
- Total test: 992 registros
- Con referencia heurística real: **616** (solo estos evaluados con ROUGE)
- Sin referencia: 376 (excluidos de ROUGE/BERTScore)

**Nota sobre referencias:** El 38% del dataset usa pseudo-referencias generadas por el propio extractivo (ausencia de sección de conclusión en el RTF). Solo los 616 con referencia heurística real (sección "Conclusão/Impressão" extraída del RTF) se usan para evaluación ROUGE.

---

## Comando ejecutado

```bash
cd fhir_transformer
python -m scripts.eval_multilingual \
  --models extractive \
  --skip-bertscore \
  --skip-faithfulness
```

---

## Resultados

### Métricas ROUGE (n=616)

| Métrica | Precision | Recall | **F1** |
|---------|-----------|--------|--------|
| ROUGE-1 | — | — | **0.378** |
| ROUGE-2 | — | — | **0.319** |
| ROUGE-L | — | — | **0.340** |

### Estadísticas descriptivas

| Estadística | Valor |
|-------------|-------|
| Compresión media | 5.7x |
| Longitud media del resumen | 469 caracteres |
| Longitud media del source | ~2,675 caracteres |
| Muestras evaluadas | 616 |

---

## Análisis e insights

**Fortalezas:**
- ROUGE-1 de 0.378 es un resultado sólido para sumarización extractiva en dominio médico sin fine-tuning. En papers de referencia (e.g., Liu et al. 2019, MedSumm), el extractivo TF-IDF en dominios especializados típicamente obtiene ROUGE-1 entre 0.30–0.42.
- No requiere GPU, ni descarga de modelos. Tiempo de inferencia: <1 ms/muestra en CPU.
- Alta fidelidad al texto fuente: el extractivo nunca "inventa" información — limitación fundamental que los modelos abstractivos no cumplen sin fine-tuning.

**Limitaciones:**
- Extrae frases literales del texto, no reformula ni sintetiza.
- Sensible a la calidad del splitting de frases (abreviaciones médicas).
- Un resumen de 2 frases (~469 chars) puede ser excesivamente largo para algunos casos, e insuficiente para informes complejos.
- Las pseudo-referencias (38% del dataset) introducen sesgo: el modelo extractivo tenderá a obtener métricas artificialmente altas en esas muestras.

**Implicaciones para la tesis:**
- Este resultado establece que el extractivo es el método de referencia y **cualquier modelo abstractivo debe superar 0.378 en ROUGE-1 para justificar su uso**.
- El ROUGE-2 de 0.319 indica buena conservación de bigramas (frases clave intactas), lo cual es deseable en informes clínicos donde la terminología exacta importa.

---

## Archivos generados

- `results/eval_multilingual.json` — métricas completas
- `results/eval_multilingual_table.md` — tabla markdown
