# Multilingual Summarization Evaluation — CHULN Radiology Test Set

**Test samples (with reference):** 100
**BERTScore model (PT):** neuralmind/bert-base-portuguese-cased
**BERTScore model (EN cross-lingual):** bert-base-multilingual-cased
**Faithfulness:** NLI entailment score (cross-encoder/nli-deberta-v3-small)

| Model | ROUGE-1 | ROUGE-2 | ROUGE-L | BERTScore-F | Faithfulness | Compression | Avg Len (chars) |
|-------|---------|---------|---------|-------------|-------------|-------------|-----------------|
| Extractive TF-IDF (PT) | 0.349 | 0.291 | 0.313 | 0.699 | 0.538 | 5.5 | 485 |
| results/ptt5_finetuned/checkpoint-2219 (PT) | 0.470 | 0.448 | 0.460 | 0.791 | 0.592 | 8.3 | 345 |
| results/ptt5_finetuned/checkpoint-6657 (PT) | 0.490 | 0.466 | 0.480 | 0.803 | 0.585 | 8.2 | 351 |
