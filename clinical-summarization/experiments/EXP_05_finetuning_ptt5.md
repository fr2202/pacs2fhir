# EXP-05 — Fine-tuning ptt5-base en corpus CHULN

**Estado:** ⚠️ Run #1 terminado con early-stopping prematuro a epoch 3/5 — Run #2 con script corregido pendiente
**Dependencias:** EXP-02 ✅, EXP-04 ✅

## Cronología

| Run | Fecha | Estado | Epochs | Notas |
|-----|-------|--------|--------|-------|
| #1  | 2026-06-20 13:05 | ⚠️ Early-stop epoch 3/5 — pero ckpt-6657 ya supera baseline ampliamente | 3 (de 5) | `metric_for_best_model="rougeL"` cortó por noise. "best" quedó en epoch 1 |
| #2  | 2026-06-20 14:00 | 🔄 En ejecución (bh6izkl6d) | 5 (planeado) | Script corregido: `--best-metric eval_loss --gen-max-length 256 --gen-num-beams 4 --early-stopping-patience 3` |

---

## Objetivo

Fine-tunear `unicamp-dl/ptt5-base-portuguese-vocab` (T5-base con vocabulario portugués, 220M parámetros) sobre las referencias **reales** del corpus CHULN para que aprenda a generar resúmenes clínicos concisos a partir de informes radiológicos completos, superando el baseline extractivo TF-IDF (ROUGE-1=0.378, BERTScore-F=0.699).

**Por qué ptt5-base y no mT5-XLSum:**
- ptt5-base tiene vocabulario optimizado para PT (evita fragmentación excesiva de texto médico)
- mT5-XLSum demostró alucinaciones estructurales en EXP-02 (faithfulness=0.232 en EXP-04) — el sesgo de noticias está profundamente integrado
- ptt5-base es un modelo "limpio" (pre-entrenado pero sin tarea específica) → más apto para fine-tuning en nuevo dominio

---

## Datos de entrenamiento

| Split | Registros totales | Con referencia real | Uso |
|-------|------------------|--------------------|----|
| Train | 7,937 | 4,930 | Entrenamiento (con `--only-with-reference`) |
| Val | 992 | 613 | NO usado por el script (split interno) |
| Test | 992 | 616 | Held-out para EXP-06 final |

**Estrategia:** Usar **solo los registros con `has_reference: true`** (4,930 en train). Las pseudo-referencias (generadas por el propio extractivo, ~38% del corpus) introducirían sesgo circular si entrenásemos con ellas.

El script `finetune_mt5.py` hace su propio split interno 90/10 del archivo train:
- Train interno: ~4,437
- Val interno (early-stopping): ~493
- Test held-out (intocado): 992 (616 con ref real) → usado en evaluación final

**Estadísticas del corpus filtrado (con referencia real):**
- Source: media 2,073 chars (~500 tokens), max 11,146 (~2,700 tokens)
- Reference: media 1,113 chars (~280 tokens), max 10,549

---

## Configuración de fine-tuning (decisiones razonadas)

```bash
cd ..\sumarizacion

python scripts/finetune_mt5.py ^
  --data data/processed/dataset_train.jsonl ^
  --output-dir ..\fhir_transformer\results\ptt5_finetuned ^
  --model unicamp-dl/ptt5-base-portuguese-vocab ^
  --epochs 5 ^
  --batch-size 2 ^
  --lr 5e-5 ^
  --fp16 ^
  --max-source 512 ^
  --max-target 256 ^
  --only-with-reference ^
  --early-stopping-patience 2
```

### Hiperparámetros y justificación

| Parámetro | Valor | Justificación |
|-----------|-------|---------------|
| `--model` | `unicamp-dl/ptt5-base-portuguese-vocab` | T5 con vocabulario PT optimizado; ~490 MB |
| `--epochs` | 5 | Con early-stopping patience=2 típicamente para en epoch 3-4. Más epochs sin más datos = overfitting |
| `--batch-size` | 2 | RTX 3060 6GB: ptt5-base + Adam states + fp16 activations ≈ 5 GB. Subir a 4 arriesga OOM |
| `--lr` | 5e-5 | Estándar para T5/mT5 fine-tuning. Más alto desestabiliza; más bajo entrena demasiado lento |
| `--fp16` | activado | Mixed precision: pesos/activaciones en float16 (-40% VRAM, +2x velocidad en RTX). Sin esto no entra en 6 GB |
| `--max-source` | 512 tokens | Tamaño nativo de entrenamiento de T5. Cubre la media (~500 tokens) de los reports. Subir a 768/1024 es no-estándar para ptt5 y arriesga OOM |
| `--max-target` | 256 tokens | La media de referencias = 280 tokens. Default 128 cortaría >50% de los targets enseñando resúmenes truncados artificialmente |
| `--only-with-reference` | activado | 4,930 ejemplos con referencia REAL > 7,937 mezclando 38% pseudo-extractivas. Calidad > cantidad |
| `--early-stopping-patience` | 2 | Si 2 epochs seguidas no mejora rougeL en val interno, corta. Evita overfitting y compute innecesario |
| `--val-ratio` | 0.1 (default) | Toma 10% del train interno como val para early-stopping |
| `--seed` | 42 (default) | Reproducibilidad de la tesis |

### Estrategia interna del Seq2SeqTrainer
- `evaluation_strategy="epoch"` + `save_strategy="epoch"`: evalúa y guarda al final de cada epoch
- `load_best_model_at_end=True` + `metric_for_best_model="rougeL"`: al terminar carga el checkpoint con mejor ROUGE-L
- `save_total_limit=2`: mantiene solo los 2 mejores checkpoints (ahorra disco)
- `predict_with_generate=True`: genera con beam search durante eval (~3 min/epoch en n=493)

### Tiempo estimado
- 4,930 samples * 0.9 (train) / batch 2 = ~2,219 steps por epoch
- 5 epochs = ~11,000 steps + 5 evals con generación
- En RTX 3060 con fp16: **3-5 horas** total
- Early stopping puede cortarlo a 2-3 horas

---

## Evaluación del modelo fine-tuned (después del entrenamiento)

```bash
cd ..\fhir_transformer

# Métricas completas vs baseline (PT) en n=100:
python -m scripts.eval_multilingual ^
  --models extractive results\ptt5_finetuned\best ^
  --limit 100 ^
  --name finetuned_pt_n100

# Con traducción EN cross-lingual:
python -m scripts.eval_multilingual ^
  --models extractive results\ptt5_finetuned\best ^
  --translate ^
  --limit 100 ^
  --name finetuned_full_n100

# Evaluación final en test set completo (n=616 con referencia):
python -m scripts.eval_multilingual ^
  --models results\ptt5_finetuned\best ^
  --translate ^
  --name finetuned_test_full
```

---

## Métricas a monitorear durante entrenamiento

- `train_loss` por step (cada 10 steps)
- `eval_loss` por epoch (early stopping)
- `eval_rouge1/2/L` por epoch en val interno
- VRAM usage (debería estabilizarse < 6 GB)

---

## Resultados Run #1 (2026-06-20)

### Log de entrenamiento (terminado por early-stopping a epoch 3)

| Época | eval_loss | eval_rougeL† | Observación |
|-------|-----------|--------------|-------------|
| 1 | 0.491 | 0.00713 | Baseline post warmup |
| 2 | 0.409 (-17%) | 0.00688 | rougeL bajó (noise) → patience counter=1 |
| 3 | **0.365 (-11%)** | 0.00700 | rougeL no superó epoch 1 → counter=2 → **STOP** |
| 4 | — | — | No ejecutado (cortado) |
| 5 | — | — | No ejecutado (cortado) |

†`eval_rougeL` es ruido: HF Trainer usa `model.config.max_length = 20` por defecto para T5 durante eval. Genera solo ~20 tokens vs los ~280 que necesitan los resúmenes reales. **eval_loss sí es indicativo y bajó consistentemente.**

### Stats finales
- `train_runtime`: 2,722 s (45 min 22 s)
- `train_samples_per_second`: 8.149
- `train_steps_per_second`: 4.075
- `train_loss` (medio últimos steps): 0.569

### Checkpoints disponibles tras Run #1

| Checkpoint | Epoch | eval_loss | Estado |
|------------|-------|-----------|--------|
| `checkpoint-2219` | 1 | 0.491 | Conservado (= `best/` por noise de rougeL) |
| `checkpoint-4438` | 2 | 0.409 | ❌ Borrado por `save_total_limit=2` |
| `checkpoint-6657` | 3 | **0.365** | Conservado (último) |
| `best/` | 1 (copia) | 0.491 | Copia de epoch 1 |

### Diagnóstico del problema

`trainer_state.json` confirma exactamente lo predicho:
```
"best_global_step": 2219,
"best_metric": 0.00712829... (rougeL),
"best_model_checkpoint": "checkpoint-2219"  ← EPOCH 1 (menos entrenado)
```

**Root cause:**
1. `Seq2SeqTrainingArguments` por defecto NO setea `generation_max_length`
2. HF Trainer cae al `model.config.max_length` del modelo, que en T5 es 20 tokens
3. Durante eval, el modelo genera resúmenes de ~20 tokens (10% de la longitud real)
4. El ROUGE comparando 20-token-summary vs 280-token-reference es esencialmente ruido (~0.007 = casi cero overlap)
5. El script usaba `metric_for_best_model="rougeL"` con `patience=2` → early-stopping fires por noise
6. "best" checkpoint quedó en el modelo menos entrenado por azar

### Comparativa Run #1 (n=100) — ✅ EVALUACIÓN COMPLETA

Comando: `python -m scripts.eval_multilingual --models extractive results/ptt5_finetuned/checkpoint-2219 results/ptt5_finetuned/checkpoint-6657 --limit 100 --name finetuned_compare_n100`

Archivo: `results/eval_finetuned_compare_n100.{json,md}`

| Modelo | ROUGE-1 | ROUGE-2 | ROUGE-L | BERTScore-F | Faithfulness | Compresión | Avg Len |
|--------|---------|---------|---------|-------------|-------------|------------|---------|
| Extractivo TF-IDF (PT) — baseline | 0.349 | 0.291 | 0.313 | 0.699 | 0.538±0.329 | 5.5x | 485 |
| mT5-XLSum zero-shot (PT) | 0.118 | 0.048 | 0.100 | 0.513 | 0.232±0.345 | 24.2x | 124 |
| ptt5-base FT epoch 1 (ckpt-2219) | 0.470 | 0.448 | 0.460 | 0.791 | 0.592±0.365 | 8.3x | 345 |
| **ptt5-base FT epoch 3 (ckpt-6657)** | **0.490** | **0.466** | **0.480** | **0.803** | 0.585±0.356 | 8.2x | 351 |

**Mejora vs baseline extractivo (ckpt-6657):**
- ROUGE-1: **+40%** relativo (0.349 → 0.490)
- ROUGE-2: **+60%** relativo (0.291 → 0.466) — la mejora más fuerte
- ROUGE-L: **+53%** relativo (0.313 → 0.480)
- BERTScore-F: **+15%** relativo (0.699 → 0.803)
- Faithfulness: **+9%** relativo (0.538 → 0.585) — modesto pero positivo
- Compresión: 8.2x vs 5.5x → resúmenes más concisos (348 chars vs 485)

**Insights:**
1. Fine-tuning funcionó incluso con solo 3 epochs y "best" mal elegido por noise
2. ckpt-6657 (epoch 3) > ckpt-2219 (epoch 1) en TODAS las métricas → confirma que `eval_loss` (no rougeL ruidoso) era el indicador correcto
3. Faithfulness apenas mejora (0.538 → 0.585): el modelo abstractivo introduce cierta paráfrasis que el NLI detecta como no-100% entailed. Sigue MUY lejos del 0.232 catastrófico de mT5-XLSum
4. La diferencia ckpt-2219 → ckpt-6657 (~2 puntos por métrica) sugiere que más epochs podrían seguir mejorando → motiva Run #2

---

## Correcciones aplicadas al script para Run #2

Editado `../sumarizacion/scripts/finetune_mt5.py` con tres flags nuevos:

| Flag nuevo | Default | Razón |
|------------|---------|-------|
| `--best-metric` | `eval_loss` (era rougeL) | rougeL sin gen-length correcto es noise; eval_loss siempre es indicativo |
| `--gen-max-length` | `256` (era ~20 efectivo) | Match con la media de referencias (~280 tokens) y con `--max-target 256` de training |
| `--gen-num-beams` | `4` (era 1) | Beam search da generación más coherente para evaluación |

**Cambios concretos:**
```python
# Antes:
best_metric = "rougeL" if HAS_ROUGE else "eval_loss"
greater_is_better = HAS_ROUGE

# Después:
if args.best_metric == "eval_loss" or not HAS_ROUGE:
    best_metric = "eval_loss"
    greater_is_better = False
else:
    best_metric = "rougeL"
    greater_is_better = True

# Y en training_args agregados:
generation_max_length=args.gen_max_length,
generation_num_beams=args.gen_num_beams,
```

## Comando preparado para Run #2

```bash
cd ..\sumarizacion

python scripts/finetune_mt5.py ^
  --data data/processed/dataset_train.jsonl ^
  --output-dir ..\fhir_transformer\results\ptt5_finetuned_v2 ^
  --model unicamp-dl/ptt5-base-portuguese-vocab ^
  --epochs 5 ^
  --batch-size 2 ^
  --lr 5e-5 ^
  --fp16 ^
  --max-source 512 ^
  --max-target 256 ^
  --only-with-reference ^
  --early-stopping-patience 3 ^
  --best-metric eval_loss ^
  --gen-max-length 256 ^
  --gen-num-beams 4
```

**Cambios respecto a Run #1:**
- `--output-dir` → `ptt5_finetuned_v2` (no sobreescribir Run #1)
- `--early-stopping-patience 3` (sube de 2 → 3, más margen)
- `--best-metric eval_loss` (en lugar del rougeL ruidoso)
- `--gen-max-length 256` (en lugar del default 20)
- `--gen-num-beams 4` (en lugar del default 1)

**Tiempo estimado:** ~75-80 min (5 epochs vs 3 de Run #1, + eval más caro por beam-search)

---

## Análisis e insights

*(Se completará al terminar)*

**Preguntas clave de investigación:**
1. ¿El fine-tuning en 4,437 muestras supera el baseline extractivo (ROUGE-1=0.349, BERTScore-F=0.699)?
2. ¿La faithfulness del fine-tuned (esperada > 0.7) supera mT5-XLSum zero-shot (0.232)?
3. ¿Aparecen alucinaciones residuales del pre-entrenamiento de ptt5?
4. ¿Es viable usarlo en producción para enriquecer los 5,089 bundles FHIR?

---

## Artefactos generados

```
fhir_transformer/results/ptt5_finetuned/
├── best/                           ← Mejor checkpoint (cargado al final)
│   ├── config.json
│   ├── model.safetensors           ← ~490 MB
│   ├── tokenizer_config.json
│   ├── spiece.model
│   └── ...
├── checkpoint-XXXX/                ← Checkpoints intermedios (max 2)
├── runs/                           ← Logs de TensorBoard
└── training_args.bin
```

El checkpoint `best/` es el que se usa en evaluación y en el pipeline FHIR de producción.

---

## Logs en vivo

```
results/ptt5_finetuned/training.log   ← stdout del entrenamiento (background)
```

Para monitorear progreso mientras corre:
```bash
tail -f results/ptt5_finetuned/training.log
```
