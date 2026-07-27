# Multilingual Summarization Evaluation — CHULN Radiology Test Set

**Test samples (with reference):** 100
**BERTScore model (PT):** neuralmind/bert-base-portuguese-cased
**BERTScore model (EN cross-lingual):** bert-base-multilingual-cased
**Faithfulness:** NLI entailment score (cross-encoder/nli-deberta-v3-small)

| Model | ROUGE-1 | ROUGE-2 | ROUGE-L | BERTScore-F | Faithfulness | Compression | Avg Len (chars) |
|-------|---------|---------|---------|-------------|-------------|-------------|-----------------|
| Extractive TF-IDF (PT) | 0.349 | 0.291 | 0.313 | 0.699 | 0.538 | 5.5 | 485 |
| extractive + opus-mt (EN) | 0.045 | 0.009 | 0.038 | 0.677 | 0.429 | 5.6 | 465 |
| results/ptt5_finetuned/checkpoint-6657 (PT) | 0.490 | 0.466 | 0.480 | 0.803 | 0.585 | 8.2 | 351 |
| results/ptt5_finetuned/checkpoint-6657 + opus-mt (EN) | 0.068 | 0.018 | 0.062 | 0.722 | 0.410 | 8.7 | 335 |
| results/ptt5_finetuned_v2/best (PT) | 0.493 | 0.470 | 0.484 | 0.805 | 0.592 | 8.2 | 348 |
| results/ptt5_finetuned_v2/best + opus-mt (EN) | 0.069 | 0.017 | 0.063 | 0.724 | 0.432 | 8.6 | 333 |
