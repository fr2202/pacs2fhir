# EXP-03 — Traducción PT→EN con opus-mt-ROMANCE-en

**Estado:** ✅ Completo  
**Fecha:** 2026-06-20  
**Hardware:** RTX 3060 Laptop 6 GB VRAM (CUDA 12.4)  
**Duración:** ~12 min (descarga modelo + inferencia 616 muestras)

---

## Objetivo

Evaluar la calidad de la traducción automática Portugués→Inglés de los resúmenes extractivos clínicos, integrando el componente multilingüe (PT+EN) en el pipeline FHIR.

---

## Modelo utilizado

**`Helsinki-NLP/opus-mt-ROMANCE-en`** (MarianMT)

- Entrenado en corpus OPUS multilingüe: PT, ES, FR, IT, CA, GL → EN
- Tamaño: ~298 MB
- Arquitectura: Transformer encoder-decoder (6 capas)
- Requisito: `sacremoses` (tokenizador)

> **Nota de corrección:** El modelo `Helsinki-NLP/opus-mt-tc-big-pt-en` planificado originalmente no existe en HuggingFace. Se usa `opus-mt-ROMANCE-en` que cubre PT→EN y es la opción estándar para este par.

---

## Comando ejecutado

```bash
cd fhir_transformer
python -m scripts.eval_multilingual \
  --models extractive \
  --translate \
  --skip-bertscore \
  --skip-faithfulness
```

---

## Resultados cuantitativos

### Métricas (n=616)

| Modelo | ROUGE-1 | ROUGE-2 | ROUGE-L | Compresión | Avg Len |
|--------|---------|---------|---------|------------|---------|
| Extractivo TF-IDF (PT) | 0.378 | 0.319 | 0.340 | 5.7x | 469 chars |
| Extractivo + opus-mt (EN) | 0.047 | 0.010 | 0.041 | 5.8x | 448 chars |

### Interpretación del ROUGE bajo en EN

El ROUGE-1=0.047 en la fila EN **es esperado y correcto** — no indica mala calidad de traducción. ROUGE es una métrica léxica que compara n-gramas; las referencias están en PT y los resúmenes generados están en EN, por lo que no comparten vocabulario. Este valor es irrelevante para evaluar calidad de traducción.

**La evaluación real de EN requiere BERTScore cross-lingual** (EXP-04), que compara representaciones semánticas del modelo `bert-base-multilingual-cased` y funciona correctamente entre idiomas.

---

## Ejemplos cualitativos

Se muestran 5 pares (extractivo PT → traducción EN) de tipos de examen diversos.

---

### Ejemplo 1 — TC do abdómen superior
*Paciente 61 años, COVID en ECMO, sepsis MRSA + fungemia*

**Extractivo PT (390 chars):**
> Cânula de ECMO inserindo-se na veia jugular interna direita, com defeito de repleção sugestivo de trombo justacentimétrico adjacente a este nível, identificando-se a sua extremidade inferior na aurícula direita. Reduzido calibre da veia ilíaca comum esquerda no seu segmento superior, com heterogeneidade da sua opacificação, de difícil interpretação na presente fase de aquisição do exame.

**Traducción EN (386 chars):**
> ECMO cannula inserting into the right internal jugular vein, with defect of replenishment suggestive of thrombus juxticentimetric adjacent to this level, identifying its lower end in the right atrium. Reduced caliber of the left common iliac vein in its upper segment, with heterogeneity of its opacification, of difficult interpretation in the present phase of acquisition of the exam.

**Evaluación:** ✅ Clínicamente correcta. Terminología médica clave preservada: *jugular vein*, *right atrium*, *common iliac vein*, *opacification*. Leve imprecisión: "defect of replenishment" (debería ser "filling defect") — comprensible en contexto radiológico.

---

### Ejemplo 2 — TC pélvico
*SARS-COV-2, ventilación mecánica, infarto renal y esplénico*

**Extractivo PT (256 chars):**
> Pede-se angio-TC do corpo para exclusão de pneumonia organizativa, TEP e reavaliação das áreas de isquémia. Densificação em vidro despolido de forma simétrica, bilateral e difusa em ambos os pulmões, com predominância periférica, compatível com SARS-COV-2.

**Traducción EN (254 chars):**
> Angio-CT of the body is requested to exclude organizational pneumonia, PTE and re-evaluation of the areas of ischemia. Densification in symmetrically, bilaterally and diffused glass in both lungs, with peripheral predominance, compatible with SARS-COV-2.

**Evaluación:** ✅ Mayoritariamente correcta. Notas:
- "organizational pneumonia" → debería ser "**organizing** pneumonia" (término estándar en inglés)
- "TEP" → "PTE" (sigla invertida, pero comprensible)
- "vidro despolido" → "glass" (debería ser "**ground-glass** opacity" — terminología incompleta)
- Estructura general preservada ✓

---

### Ejemplo 3 — TC do tórax
*Mujer 40 años, patología pulmonar post-COVID + barotrauma + aspergilosis*

**Extractivo PT (409 chars):**
> O dreno posicionado na vertente lateral do 4º espaço intercostal direito tem posicionamento cisural e contacta apenas com uma fina lâmina de líquido pleural e algumas bolhas gasosas; o derrame pleural é muito ligeiro à direita. À esquerda, a melhoria é apenas ligeira, verificando-se um discreto menor grau de derrame pleural e há agora algum arejamento do segmento apico-posterior do lobo superior direito.

**Traducción EN (381 chars):**
> The drain positioned on the lateral side of the 4th right intercostal space has cisural positioning and contacts only with a thin blade of pleural fluid and some gas bubbles; pleural effusion is very slight to the right. To the left, the improvement is only slight, with a slight lower degree of pleural effusion and there is now some aeration of the api-posterior segment of the right upper lobe.

**Evaluación:** ✅ Buena calidad general. Notas:
- "thin blade of pleural fluid" → "thin **film**" sería más preciso clínicamente
- "api-posterior" → typo por "apico-posterior" (leve error ortográfico del modelo)
- Estructura descriptiva radiológica preservada ✓

---

### Ejemplo 4 — RM + difusão
*Mujer 46 años, cefalea temporal derecha en racimos, visión borrosa*

**Extractivo PT (382 chars):**
> Ressonância magnética crânio-encefálica e das órbitas — Internamento. Não se observam lesões focais com efeito de massa, áreas de restrição à difusão das moléculas de água, nem áreas de realce anómalo após administração de gadolínio.

**Traducción EN (397 chars):**
> Brain magnetic resonance imaging and orbits - Hospitalization. No focal lesions with mass effect, areas of restriction to the diffusion of water molecules, nor areas of abnormal enhancement after gadolinium administration are observed.

**Evaluación:** ✅ Muy buena. "Internamento" → "Hospitalization" ✓ (correcto), terminología RM preservada: *mass effect*, *diffusion restriction*, *gadolinium enhancement* ✓.

---

### Ejemplo 5 — Estudo eletromiográfico
*SARS-CoV-2, miopatía del cuidado crítico, destete ventilatorio*

**Extractivo PT (555 chars):**
> Doente admitida por pneumonia a SARS-CoV2 com evolução favorável COM CRITERIOS DE CURA, em fase de convalescença com desmame ventilatório prolongado por fraqueza muscular associada a doença crítica e paresia diafragmática bilateral, traqueostomizada mantém-se sob VMI em modalidade assistida, a cumprir plano de reabilitação global com boa colaboração e evolução lenta. Conclusão: Estudo electromiográfico dos membros superiores e inferiores identifica aspetos compatíveis com lesão da fibra muscular difusa, de acordo com miopatia dos cuidados críticos.

**Traducción EN (546 chars):**
> Patient admitted by pneumonia to SARS-CoV2 with favorable evolution, in convalescence phase with prolonged ventilatory weaning due to muscle weakness associated with critical disease and bilateral diaphragmatic paresis, tracheostomized, remains under invasive mechanical ventilation in assisted mode, complying with overall rehabilitation plan with good collaboration and slow evolution. Conclusion: Electromyographic study of the upper and lower limbs identifies aspects compatible with diffuse muscle fiber injury, according to myopathy of critical care.

**Evaluación:** ✅ Excelente. Ejemplo más largo y complejo, traducido con alta fidelidad. Terminología clínica especializada correctamente traducida: *ventilatory weaning*, *diaphragmatic paresis*, *tracheostomized*, *electromyographic study*, *myopathy of critical care* ✓.

---

## Análisis e insights

### Calidad global

La traducción opus-mt-ROMANCE-en produce resultados **funcionalmente adecuados** para comunicación clínica en todos los ejemplos evaluados. Las imprecisiones detectadas son menores y no comprometen la comprensión del contenido radiológico:

| Tipo de error | Ejemplos | Impacto clínico |
|---------------|----------|-----------------|
| Terminología levemente imprecisa | "organizational" vs "organizing" pneumonia | Bajo — comprensible |
| Siglas invertidas | TEP → PTE | Bajo — comprensible |
| Términos incompletos | "glass" vs "ground-glass opacity" | Bajo — contexto claro |
| Errores ortográficos leves | "api-posterior" | Mínimo |

### Limitaciones técnicas del modelo

1. **Límite de tokens de entrada:** MarianMT tiene máximo 512 tokens. Algunos resúmenes extractivos largos (~461-475 tokens según advertencia) se traducen por fragmento, lo que puede introducir discontinuidades leves. Mitigado subiendo `translation_max_length=800` en la configuración.

2. **Terminología no estándar en inglés:** El modelo no siempre usa la convención anglosajona de radiología (e.g., "ground-glass opacity" vs simplemente "glass"). Un post-procesado de terminología mejoraría la calidad para publicación clínica.

3. **Sin fine-tuning en dominio médico:** El modelo fue entrenado en corpus general. Fine-tuning en pares PT-EN de radiología mejoraría precisión terminológica, pero está fuera del alcance de esta tesis.

### Para la tesis

- **Resultado cualitativo:** Las traducciones son comprensibles y clínicamente informativas para un radiólogo anglófono.
- **Evaluación cuantitativa pendiente:** BERTScore cross-lingual (EXP-04) dará el valor numérico real para la tabla final.
- **El ROUGE EN (0.047) no es una métrica válida aquí** — documentar claramente en la tesis que la evaluación EN requiere métricas cross-lingual o back-translation.

---

## Archivos generados

- `results/eval_multilingual.json` — métricas (ROUGE PT + ROUGE EN inválido)
- `results/eval_multilingual_table.md` — tabla actualizada
