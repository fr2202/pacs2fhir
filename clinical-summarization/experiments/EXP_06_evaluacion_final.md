# EXP-06 — Evaluación Final Multilingüe Completa

**Estado:** ⏳ Pendiente  
**Dependencias:** EXP-01 ✅, EXP-02 ✅, EXP-03 ⏳, EXP-04 ⏳, EXP-05 ⏳  
**Propósito:** Generar la tabla definitiva para el capítulo de evaluación de la tesis

---

## Objetivo

Consolidar todos los experimentos anteriores en una evaluación unificada sobre el test set completo (n=616), con todas las métricas y todos los modelos. Producir la tabla publicable final y los ejemplos cualitativos comparativos definitivos.

---

## Comando a ejecutar

```bash
cd fhir_transformer

python -m scripts.eval_multilingual \
  --models extractive mt5-xlsum mt5-small results\ptt5_finetuned\best \
  --translate \
  --device auto
```

*(Nota: omitir modelos zero-shot si se quiere solo la comparativa extractivo vs fine-tuned)*

---

## Tabla objetivo para la tesis

| Modelo | ROUGE-1↑ | ROUGE-2↑ | ROUGE-L↑ | BERTScore-F↑ | Faithfulness↑ | Compresión | Avg Len |
|--------|----------|----------|----------|--------------|---------------|------------|---------|
| Extractivo TF-IDF (PT) | 0.378 | 0.319 | 0.340 | — | — | 5.7x | 469 |
| mT5-XLSum zero-shot (PT) | 0.118 | 0.048 | 0.100 | — | — | 24.2x | 124 |
| mT5-small zero-shot (PT) | 0.103 | 0.067 | 0.092 | — | — | 39.0x | 73 |
| **ptt5-base fine-tuned (PT)** | — | — | — | — | — | — | — |
| Extractivo + opus-mt (EN) | — | — | — | — | — | — | — |
| ptt5-base-ft + opus-mt (EN) | — | — | — | — | — | — | — |

*n=616 para extractivo (test set completo); n=100 para zero-shot (subconjunto); n=616 para fine-tuned*

---

## Sección de ejemplos cualitativos finales

*(Seleccionar 3-4 ejemplos representativos que muestren:)*

1. **Caso donde el extractivo es suficiente** (informe corto, conclusión clara)
2. **Caso donde el fine-tuned mejora** (informe largo, extractivo coge frases irrelevantes)
3. **Caso de alucinación mT5-XLSum** (ya documentado en EXP-02)
4. **Ejemplo de traducción EN** (par PT→EN de calidad)

---

## Integración FHIR

Una vez validado el mejor modelo, post-procesar los 5,089 bundles con conclusión:

```bash
# Con ptt5-base fine-tuned + traducción EN:
python -m scripts.run_summarization \
  --abstractive \
  --model results\ptt5_finetuned\best \
  --translate \
  --device auto

# Verificar un bundle de salida:
python verify_bundle.py output\fhir_bundles_summarized\<accession>.fhir.json
```

Salida esperada: `output/fhir_bundles_summarized/` con extensión FHIR:
```json
{
  "url": "http://chuln.pt/fhir/StructureDefinition/radiology-summary",
  "extension": [
    {"url": "extractive_pt", "valueString": "..."},
    {"url": "abstractive_pt", "valueString": "..."},
    {"url": "model_abstractive_pt", "valueString": "ptt5-base"},
    {"url": "translation_en", "valueString": "..."},
    {"url": "model_translation_en", "valueString": "opus-mt-tc-big-pt-en"},
    {"url": "generated_at", "valueDateTime": "2026-..."}
  ]
}
```

---

## Archivos finales a generar

- `results/eval_multilingual_FINAL.json` — métricas completas de todos los modelos
- `results/eval_multilingual_FINAL_table.md` — tabla para copiar en la tesis
- `output/fhir_bundles_summarized/` — 5,089 bundles enriquecidos con resúmenes
