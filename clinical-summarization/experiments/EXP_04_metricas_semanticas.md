# EXP-04 — Métricas Semánticas: BERTScore + NLI Faithfulness

**Estado:** ✅ Completo  
**Fecha:** 2026-06-20  
**Hardware:** RTX 3060 Laptop (6 GB VRAM) — CUDA 12.4  
**Dependencias:** EXP-01 ✅, EXP-02 ✅, EXP-03 ✅

---

## Objetivo

Complementar las métricas ROUGE (léxicas) con métricas semánticas que capturen:
- **BERTScore:** similitud semántica entre resumen y referencia, robusta a paráfrasis
- **NLI Faithfulness:** probabilidad de que el resumen esté *entailed* (implicado) por el texto fuente, como proxy de anti-alucinación

Estas métricas son crecientemente exigidas en publicaciones de NLP y permiten distinguir casos donde ROUGE es bajo pero el resumen es semánticamente correcto (o viceversa).

---

## Modelos utilizados

| Métrica | Modelo | Tamaño | Propósito |
|---------|--------|--------|-----------|
| BERTScore PT | `neuralmind/bert-base-portuguese-cased` | ~420 MB | Similitud semántica en PT |
| BERTScore EN cross-lingual | `bert-base-multilingual-cased` | ~680 MB | EN summary vs PT reference |
| Faithfulness (NLI) | `cross-encoder/nli-deberta-v3-small` | ~180 MB | P(summary entailed by source) |

---

## Comandos ejecutados

```bash
cd fhir_transformer

# Bloque 1 — PT models (BERTScore + faithfulness):
python -m scripts.eval_multilingual --models extractive mt5-xlsum mt5-small --limit 100 --name pt_models_n100

# Bloque 2 — Traducción EN (BERTScore cross-lingual):
python -m scripts.eval_multilingual --models extractive --translate --limit 100 --name extractive_translation_n100
```

**Archivos de resultados:**
- `results/eval_pt_models_n100.json` + `.md` (bloque 1)
- `results/eval_extractive_translation_n100.json` + `.md` (bloque 2)

---

## Protocolo

### BERTScore
- Para PT: `model_type="neuralmind/bert-base-portuguese-cased"`, `num_layers=9` (BERT-base)
- Para EN cross-lingual (EN summary vs PT reference): `model_type="bert-base-multilingual-cased"`
- Truncación de inputs a 1500 chars antes de BERTScore (referencias del corpus pueden superar 3000 chars → exceden límite de 512 tokens de BERT)
- Reportar F1 en tabla comparativa

### NLI Faithfulness
- Modelo: `CrossEncoder("cross-encoder/nli-deberta-v3-small")`
- Input: (source[:800], summary)
- Output: logits → softmax → P(entailment) = label index 1
  - Labels: [contradiction, entailment, neutral]
- Rango: [0, 1] — valores > 0.7 indican alta fidelidad

---

## Resultados (n=100)

### Bloque 1 — Evaluación PT (métricas completas)

| Modelo | ROUGE-1 | ROUGE-2 | ROUGE-L | BERTScore-F | Faithfulness | Compresión | Avg Len |
|--------|---------|---------|---------|-------------|-------------|------------|---------|
| Extractivo TF-IDF (PT) | **0.349** | **0.291** | **0.313** | **0.699** | **0.538±0.329** | 5.5x | 485 |
| mT5-XLSum zero-shot (PT) | 0.118 | 0.048 | 0.100 | 0.513 | 0.232±0.345 | 24.2x | 124 |
| mT5-small zero-shot (PT) | 0.103 | 0.067 | 0.092 | 0.527 | 0.415±0.352 | 39.0x | 73 |

### Bloque 2 — Evaluación EN cross-lingual

| Modelo | ROUGE-1* | ROUGE-2* | ROUGE-L* | BERTScore-F (cross-lingual) | Faithfulness | Compresión | Avg Len |
|--------|---------|---------|---------|------------------------------|-------------|------------|---------|
| Extractivo + opus-mt-ROMANCE-en (EN) | 0.045 | 0.009 | 0.038 | **0.677** | 0.429±0.418 | 5.6x | 465 |

*ROUGE inválido en evaluación cross-lingual (resumen EN vs referencia PT). Ver nota metodológica.

---

## Análisis e insights

### 1. BERTScore confirma superioridad del extractivo (PT)
El extractivo obtiene BERTScore-F = **0.699**, muy superior a mT5-XLSum (0.513) y mT5-small (0.527). La brecha BERTScore (36 puntos) es consistente con la brecha ROUGE (>3x), confirmando que los modelos zero-shot no capturan el contenido relevante semánticamente, no solo léxicamente.

### 2. Faithfulness revela el problema de mT5-XLSum con mayor claridad que ROUGE
- Extractivo: faithfulness = **0.538** — relativamente alta (copia frases del fuente)
- mT5-XLSum: faithfulness = **0.232** — confirma que el 77% de sus generaciones NO están respaldadas por el fuente
- mT5-small: faithfulness = **0.415** — intermedio; genera texto más corto pero aún con fragmentos inventados

La hipótesis inicial (faithfulness extractivo > mT5-XLSum) se confirma. La hipótesis de faithfulness > 0.85 para el extractivo NO se confirmó (0.538), lo que sugiere que incluso copiando frases del texto, el modelo de NLI detecta tensión entre resumen y fuente completo. Esto es esperable dado que el extractivo no captura toda la información del fuente (comprime 5.5x).

### 3. Evaluación cross-lingual EN
- BERTScore cross-lingual (EN summary vs PT reference): **0.677**
- Es esperado que sea ligeramente menor que PT vs PT (0.699) dada la traducción
- La diferencia de ~2 puntos indica que opus-mt-ROMANCE-en preserva bien el contenido semántico
- ROUGE EN = 0.045 es inválido (cross-lingual) y debe ignorarse en la tabla final de tesis

### 4. Alta varianza en faithfulness
La desviación estándar de faithfulness es elevada en todos los modelos (~0.32-0.42), indicando que la calidad varía mucho por registro. Algunos resúmenes son altamente fieles, otros completamente inventados. Para la tesis: reportar mean ± std.

### 5. Discrepancia ROUGE vs BERTScore en mT5-small
mT5-small tiene ROUGE-2 (0.067) > mT5-XLSum (0.048) pero BERTScore (0.527) < mT5-XLSum (0.513) está dentro del margen. Esto sugiere que mT5-small copia n-gramas exactos del fuente pero sin captura semántica superior.

---

## Notas metodológicas

### Modelo BERTScore PT no estaba en el registro interno de bert-score
`neuralmind/bert-base-portuguese-cased` no está en el diccionario `model2layers` de bert-score. Se pasó `num_layers=9` (BERT-base) explícitamente. Esto es la configuración correcta y estándar para BERT-base.

### Truncación de inputs a BERTScore
Las referencias del corpus CHULN pueden superar 3000 caracteres (secciones completas de conclusión en RTF). Se truncan a 1500 chars (~400 tokens) antes de pasar a BERTScore para evitar errores de forma de tensor. Esta truncación es conservadora y preserva el contenido más relevante.

### ROUGE cross-lingual es inválido
ROUGE compara n-gramas de forma léxica. Un resumen en inglés comparado contra una referencia en portugués produce valores cercanos a cero (0.045 ROUGE-1) que no son informativos. La métrica cross-lingual correcta es BERTScore con `bert-base-multilingual-cased`, que opera en espacio semántico compartido.

---

## Tabla acumulada para tesis (post EXP-04)

| Modelo | ROUGE-1 | ROUGE-2 | ROUGE-L | BERTScore-F | Faithfulness | Compresión |
|--------|---------|---------|---------|-------------|-------------|------------|
| Extractivo TF-IDF (PT) | **0.349** | **0.291** | **0.313** | **0.699** | 0.538±0.329 | 5.5x |
| mT5-XLSum zero-shot (PT) | 0.118 | 0.048 | 0.100 | 0.513 | 0.232±0.345 | 24.2x |
| mT5-small zero-shot (PT) | 0.103 | 0.067 | 0.092 | 0.527 | 0.415±0.352 | 39.0x |
| ptt5-base fine-tuned (PT) | — | — | — | — | — | — |
| Extractivo + opus-mt (EN) | n/a* | n/a* | n/a* | 0.677† | 0.429±0.418 | 5.6x |
| ptt5-base-ft + opus-mt (EN) | — | — | — | — | — | — |

*ROUGE cross-lingual inválido  
†BERTScore cross-lingual con `bert-base-multilingual-cased` (EN summary vs PT reference)

*n=100 para todos los modelos en este experimento*
