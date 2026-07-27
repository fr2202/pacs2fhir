# Multilingual Summarization Evaluation — CHULN Radiology Test Set

**Test samples (with reference):** 100
**BERTScore model (PT):** neuralmind/bert-base-portuguese-cased
**BERTScore model (EN cross-lingual):** bert-base-multilingual-cased
**Faithfulness:** NLI entailment score (cross-encoder/nli-deberta-v3-small)

| Model | ROUGE-1 | ROUGE-2 | ROUGE-L | BERTScore-F | Faithfulness | Compression | Avg Len (chars) |
|-------|---------|---------|---------|-------------|-------------|-------------|-----------------|
| Extractive TF-IDF (PT) | 0.349 | 0.291 | 0.313 | 0.699 | 0.538 | 5.5 | 485 |
| extractive + opus-mt (EN) | 0.045 | 0.009 | 0.038 | 0.677 | 0.429 | 5.6 | 465 |
