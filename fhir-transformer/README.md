# FHIR Transformer

> Pipeline multi-agente em Python para conversão de relatórios PACS (JSON + RTF) para FHIR R4 Bundles.

Parte do projeto **[PACS2FHIR — Clinical Intelligence Platform](https://fr2202.github.io/pacs2fhir)** · BLOCKCHAIN.PT WP2 · IPLeiria / ESTG-Leiria

## Resultados

| Métrica | Valor |
|---------|-------|
| Registos processados | **10.001** |
| Conformidade HAPI-FHIR R4 | **100%** |
| Throughput | **1.173 ficheiros/segundo** |
| Tempo total | **8,5 segundos** |
| Erros de validação | **0** |

## Estrutura

```
fhir-transformer/
├── main.py                    # Entry point
├── requirements.txt
├── config/
│   └── code_mappings.py       # Mapeamentos LOINC e DICOM
├── agents/
│   ├── coordinator_agent.py   # ProcessPoolExecutor, batching
│   ├── rtf_parser_agent.py    # Limpeza RTF → texto clínico
│   ├── patient_mapper_agent.py
│   ├── encounter_mapper_agent.py
│   ├── imaging_study_mapper_agent.py
│   ├── diagnostic_report_mapper_agent.py
│   ├── validator_agent.py     # Pydantic R4 + HAPI-FHIR
│   └── bundle_generator_agent.py
├── output/
│   └── fhir_bundles/          # .fhir.json por relatório (gitignored)
├── logs/
│   ├── coordinator.log        # Log de runtime (gitignored)
│   └── transformation_summary.json
├── tests/
│   └── test_pipeline.py
├── examples/
│   └── sample_bundle.fhir.json   # Bundle exemplo anonimizado
└── docs/
    └── architecture.md
```

## Como executar

```bash
pip install -r requirements.txt

# Processar todos os ficheiros
python main.py

# Testar com N ficheiros
python main.py --limit 10

# Workers customizados
python main.py --workers 4
```

Output em `output/fhir_bundles/` · Resumo em `logs/transformation_summary.json`

## Arquitetura

```
PACS JSON → RTFParserAgent → MapperAgents → ValidatorAgent → BundleGeneratorAgent
                                                  │
                                            Pydantic R4
                                            + HAPI-FHIR
```

- IDs determinísticos **UUID5** (idempotentes em reruns)
- **ProcessPoolExecutor** com `cpu_count - 1` workers, batches de 500
- Status `final` se `Validation_Timestamp` presente, `preliminary` caso contrário

## Dataset

> Os dados clínicos do CHULN são confidenciais e não estão incluídos. Coloca os ficheiros `.txt` em `../JSON/`.

## Publicação

Villacis Vera L., Malheiro R., Craveiro O. *"PACS-to-FHIR Transformation and Clinical Text: a Case Study with Computed Tomography."* Procedia Computer Science · HCIST 2025. [→ ScienceDirect](https://www.sciencedirect.com/science/article/pii/S1877050926007131)
