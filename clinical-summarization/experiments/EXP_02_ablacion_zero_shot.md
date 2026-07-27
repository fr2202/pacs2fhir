# EXP-02 — Ablación Zero-Shot: mT5-XLSum y mT5-small

**Estado:** ✅ Completo  
**Fecha:** 2026-06-20  
**Hardware:** RTX 3060 Laptop 6 GB VRAM (CUDA 12.4)  
**Duración:** ~7 min (mT5-XLSum descarga + inferencia 100 samples) + ~4 min (mT5-small)

---

## Objetivo

Cuantificar el rendimiento de modelos seq2seq multilingüe pre-entrenados **sin fine-tuning** sobre informes radiológicos en pt-PT. El propósito es doble:
1. Demostrar que el dominio médico requiere adaptación específica (motivación del fine-tuning).
2. Documentar el tipo de fallos (alucinaciones, tokens de pre-entrenamiento) para el capítulo de análisis cualitativo de la tesis.

## Hipótesis

Los modelos zero-shot obtendrán ROUGE significativamente inferior al extractivo baseline (EXP-01, ROUGE-1=0.378) debido al desajuste de dominio: fueron entrenados en noticias (BBC XLSum) o como modelos de lenguaje general (mT5-small), no en texto clínico.

---

## Modelos evaluados

### mT5-XLSum (`csebuetnlp/mT5_multilingual_XLSum`)
- **Arquitectura:** mT5-base encoder-decoder (582M parámetros)
- **Entrenamiento:** BBC XLSum — 1.35M pares artículo-resumen de noticias en 45 idiomas, incluyendo portugués
- **Tamaño:** ~1.2 GB
- **Prefix de entrada:** `<pt> {texto}` (token de idioma requerido)
- **Razón de incluir:** Es el modelo multilingüe más usado para sumarización; su fallo en dominio médico es un resultado publicable

### mT5-small (`google/mt5-small`)
- **Arquitectura:** mT5-small encoder-decoder (300M parámetros)
- **Entrenamiento:** mC4 — pre-entrenamiento de lenguaje general (sin tarea de sumarización)
- **Tamaño:** ~300 MB
- **Prefix de entrada:** `summarize: {texto}`
- **Razón de incluir:** Modelo ligero alternativo; permite separar el efecto del tamaño del modelo vs. el ajuste de tarea

---

## Configuración

**Parámetros de generación:**

| Parámetro | Valor |
|-----------|-------|
| `max_new_tokens` | 128 |
| `min_length` | 20 |
| `num_beams` | 4 |
| `no_repeat_ngram_size` | 3 |
| `do_sample` | False |
| `device` | CUDA:0 |

**Dataset:** 100 primeros registros del test set con referencia real (subconjunto para rapidez).

---

## Comandos ejecutados

```bash
# Ablación completa (ambos modelos + baseline):
cd fhir_transformer
python -m scripts.eval_multilingual \
  --models extractive mt5-xlsum mt5-small \
  --skip-bertscore \
  --skip-faithfulness \
  --limit 100
```

---

## Resultados cuantitativos

### Métricas ROUGE (n=100)

| Modelo | ROUGE-1 F | ROUGE-2 F | ROUGE-L F | Compresión | Avg Len |
|--------|-----------|-----------|-----------|------------|---------|
| Extractivo TF-IDF | **0.349** | **0.291** | **0.313** | 5.5x | 485 chars |
| mT5-XLSum zero-shot | 0.118 | 0.048 | 0.100 | 24.2x | 124 chars |
| mT5-small zero-shot | 0.103 | 0.067 | 0.092 | 39.0x | 73 chars |

**Degradación vs. extractivo:**

| Modelo | Δ ROUGE-1 | Δ ROUGE-2 | Δ ROUGE-L |
|--------|-----------|-----------|-----------|
| mT5-XLSum | **−66%** | **−83%** | **−68%** |
| mT5-small | **−70%** | **−77%** | **−71%** |

---

## Ejemplos cualitativos

Los siguientes ejemplos fueron generados con los 4 primeros registros válidos del test set. Se muestran fragmentos para ilustrar los patrones de fallo.

---

### Ejemplo 1 — TC do abdómen superior
**Paciente:** 61 años, COVID curada en ECMO, sepsis MRSA + fungemia

**Source (extracto):**
> Doente de 61 anos COVID curada em ECMO há 60 dias complicação de sepsis a MRSA e fungemia pelo que se pede TC corpo + cervical para exclusão de complicações infecciosas locais (inserção da cânula jugular vs coleção) com contraste...

**Referencia heurística (sección Conclusão del RTF):**
> Cânula de ECMO com defeito de repleção sugestivo de trombo justacentimétrico adjacente [...] Reduzido calibre da veia ilíaca comum esquerda no seu segmento superior, com heterogeneidade da sua opacificação...

**Extractivo TF-IDF:**
> Cânula de ECMO inserindo-se na veia jugular interna direita, com defeito de repleção sugestivo de trombo justacentimétrico adjacente a este nível, identificando-se a sua extremidade inferior na aurícula direita. Reduzido calibre da veia ilíaca comum esquerda no seu segmento superior, com heterogeneidade da sua opacificação, de difícil interpretação na presente fase de aquisição do exame.

**mT5-XLSum zero-shot:** ⚠️ ALUCINACIÓN
> Confira abaixo a primeira reportagem sobre a doença causada pelo novo coronavírus.

**mT5-small zero-shot:** ⚠️ TOKEN DE PRE-ENTRENAMIENTO
> `<extra_id_0>` e com maior sensibilidade à direita. ) `<extra_id_10>`..

---

### Ejemplo 2 — TC pélvico
**Paciente:** SARS-COV-2 con ventilación mecánica invasiva, infarto renal y esplénico

**Source (extracto):**
> Doente com pneumonia a SARS-COV-2 e suspeita de sobreinfecção bacteriana. Encontra-se sob ventilação mecânica invasiva há 7 dias. Já terminou 10 dias de dexametasona...

**Extractivo TF-IDF:**
> Pede-se angio-TC do corpo para exclusão de pneumonia organizativa, TEP e reavaliação das áreas de isquémia. Densificação em vidro despolido de forma simétrica, bilateral e difusa em ambos os pulmões, com predominância periférica, compatível com SARS-COV-2.

**mT5-XLSum zero-shot:** ⚠️ ALUCINACIÓN PLAUSIBLE
> O paciente com pneumonia a SARS-COV-2 e suspeita de sobreinfecção bacteriana foi submetido a tratamento intensivo com antibióticos e dexametasona.

> *(Nota: superficialmente coherente, pero INVENTADO — el texto original no menciona el tratamiento como conclusión, y el modelo añade detalles no presentes.)*

**mT5-small zero-shot:** ⚠️ COPIA FRAGMENTADA
> `<extra_id_0>` e segmentar. Relatório validado por: José Hugo Luz (No Ordem dos Médicos: 65169)

---

### Ejemplo 3 — TC do tórax
**Paciente:** Mujer 40 años, patología pulmonar post-COVID + barotrauma + neumonía necrotizante + aspergilosis

**Extractivo TF-IDF:**
> O dreno posicionado na vertente lateral do 4º espaço intercostal direito tem posicionamento cisural e contacta apenas com uma fina lâmina de líquido pleural e algumas bolhas gasosas [...] À esquerda, a melhoria é apenas ligeira, verificando-se um discreto menor grau de derrame pleural...

**mT5-XLSum zero-shot:** ⚠️ INSTITUCIÓN INVENTADA
> O paciente com pneumonia necrotizante bacteriana e aspergilose é a primeira pessoa a desenvolver a doença após a pandemia de coronavírus, segundo o **Instituto de Pesquisas Clínicas de Londres (LSE)**.

> *(Nota: el "Instituto de Pesquisas Clínicas de Londres (LSE)" no existe — alucinación de institución.)*

**mT5-small zero-shot:** ⚠️ TOKEN + COPIA
> `<extra_id_0>` a nível torácico: Mulher 40 anos, patologia pulmonar pós covid+ barotrauma+

---

### Ejemplo 4 — RM + difusão
**Paciente:** Mujer 46 años, cefalea temporal derecha, visión borrosa

**Extractivo TF-IDF:**
> Ressonância magnética crânio-encefálica e das órbitas [...] Nomeadamente, não se observam lesões focais com efeito de massa, áreas de restrição à difusão das moléculas de água, nem áreas de realce anómalo após administração de gadolínio.

**mT5-XLSum zero-shot:** ⚠️ ALUCINACIÓN MEDIÁTICA
> A partir desta quarta-feira, a **BBC News Brasil** enviará o seu depoimento a uma mulher com quadro de cefaleia temporal direita em salvas e sensação de visão segura.

> *(Nota: "BBC News Brasil" — el modelo revierte al patrón de sus datos de entrenamiento (noticias BBC).)*

**mT5-small zero-shot:** ⚠️ FRAGMENTO IRRELEVANTE
> `<extra_id_0>` ao longo da linha média centrada. - Sagital: T1 3D antes e após administração de gadolínio.

---

## Análisis e insights

### Patrones de fallo identificados

**mT5-XLSum — Alucinaciones de dominio:**
- El modelo genera texto con estilo periodístico ("Confira abaixo", "BBC News Brasil", "Instituto de Pesquisas Clínicas de Londres") porque fue entrenado exclusivamente en artículos de noticias de la BBC.
- En los 4 ejemplos: **4/4 alucinaciones** — no extrajo información clínica relevante en ningún caso.
- La compresión de 24.2x (124 chars vs 485 del extractivo) indica que genera resúmenes muy cortos y genéricos.
- ROUGE-2 de 0.048 (vs 0.291 del extractivo) = **83% de degradación** — los bigramas no se conservan porque el texto generado es completamente distinto al fuente.

**mT5-small — Tokens de pre-entrenamiento:**
- El modelo no fue fine-tuned para sumarización — fue pre-entrenado como modelo de lenguaje con objetivos de span masking (similar a BERT pero seq2seq).
- Los tokens `<extra_id_N>` son los placeholders de los spans enmascarados durante el pre-entrenamiento. Aparecen en la salida porque el modelo intenta "completar máscaras" en lugar de "resumir".
- Compresión de 39.0x (73 chars): genera apenas 1-2 frases sin coherencia.
- **Conclusión:** mT5-small sin fine-tuning es inutilizable para esta tarea.

### Implicación central para la tesis

> **La gran brecha entre extractivo (ROUGE-1=0.349) y los mejores modelos zero-shot (ROUGE-1=0.118) — una degradación del 66% — demuestra empíricamente que los modelos abstractivos pre-entrenados en noticias no son transferibles al dominio radiológico sin adaptación específica.**

Esta brecha motiva y justifica el EXP-05 (fine-tuning de ptt5-base sobre las 6,159 referencias reales del corpus).

### Sobre el tamaño de la muestra (n=100)

La evaluación se realizó sobre 100 muestras por restricciones de tiempo. Para resultados finales publicables, EXP-06 repetirá la evaluación sobre el test set completo (n=616) con todos los modelos (incluyendo el fine-tuned).

---

## Archivos generados

- `results/eval_multilingual.json` — métricas de los 3 modelos
- `results/eval_multilingual_table.md` — tabla comparativa
