# Multilingual Summarization Evaluation — CHULN Radiology Test Set

**Test samples (with reference):** 100
**BERTScore model (PT):** neuralmind/bert-base-portuguese-cased
**BERTScore model (EN cross-lingual):** bert-base-multilingual-cased
**Faithfulness:** NLI entailment score (cross-encoder/nli-deberta-v3-small)

| Model | ROUGE-1 | ROUGE-2 | ROUGE-L | BERTScore-F | Faithfulness | Compression | Avg Len (chars) |
|-------|---------|---------|---------|-------------|-------------|-------------|-----------------|
| Extractive TF-IDF (PT) | 0.349 | 0.291 | 0.313 | 0.699 | 0.538 | 5.5 | 485 |
| mt5-xlsum (PT) | 0.118 | 0.048 | 0.100 | 0.513 | 0.232 | 24.2 | 124 |
| mt5-small (PT) | 0.103 | 0.067 | 0.092 | 0.527 | 0.415 | 39.0 | 73 |
