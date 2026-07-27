# PACS2FHIR — Clinical Intelligence Platform

> Transformação semântica e sumarização automática de relatórios radiológicos PACS para FHIR R4, com avaliação multilíngue por modelos de linguagem.

**🌐 [Ver página do projeto](https://fr2202.github.io/pacs2fhir)** · **📄 [Artigo publicado (ScienceDirect)](https://www.sciencedirect.com/science/article/pii/S1877050926007131)**

---

## Sobre o projeto

Este projeto nasceu quando o **Centro Hospitalar Universitário de Lisboa Norte (CHULN)** disponibilizou 10.001 relatórios radiológicos anonimizados no âmbito da agenda do projeto **BLOCKCHAIN.PT** (WP2 – Saúde e Bem-estar). A questão central era: como transformar dados clínicos não estruturados — exportados em JSON aninhado com narrativas em RTF — no padrão universal **HL7 FHIR R4**?

O resultado é uma plataforma com dois módulos integrados:

1. **Pipeline PACS → FHIR R4** — transformação multi-agente com 100% de conformidade HAPI-FHIR, 1.173 ficheiros/segundo, zero erros em 10.001 relatórios de TC.
2. **Sumarização clínica com LLMs** — avaliação multidimensional (ROUGE, BERTScore, fidelidade, human judgement) de modelos PTT5, mT5, Extractive e Gemma 3.1 em português e inglês.

---

## Repositórios

| Projeto | Descrição | Repo |
|---------|-----------|------|
| **Página do projeto** | GitHub Pages — documentação, resultados, demos | [`fr2202/pacs2fhir`](https://github.com/fr2202/pacs2fhir) |
| **Pipeline FHIR** | Transformação PACS→FHIR R4 multi-agente em Python | [`fr2202/fhir-transformer`](https://github.com/fr2202/fhir-transformer) |
| **API FHIR** | API Flask original de conversão PACS→FHIR (v1) | [`fr2202/APIFHIR`](https://github.com/fr2202/APIFHIR) |
| **Sumarização** | Sumarização clínica com LLMs — PTT5, mT5, Gemma, avaliação multilíngue | [`fr2202/clinical-summarization`](https://github.com/fr2202/clinical-summarization) |
| **Projeto Sumarização (EI)** | Projeto de licenciatura — sumarização clínica integrada | [`fr2202/proyecto51`](https://github.com/fr2202/proyecto51) |
| **Projeto EI 2024/2025** | Dashboard web com integração FHIR e resumo clínico (Flask + MongoDB) | [`rsmal-ipl/Dashboard-Medico-Web-com-Integracao-de-Sistema-de-Resumo-Clinico`](https://github.com/rsmal-ipl/Dashboard-Medico-Web-com-Integracao-de-Sistema-de-Resumo-Clinico) |
| **Projeto EI 2025/2026 — 52** | Dashboard médico com sumarização clínica integrada + VM Ubuntu | *(em publicação)* |

---

## Resultados principais

### Pipeline FHIR
| Métrica | Valor |
|---------|-------|
| Registos processados | **10.001** |
| Conformidade HAPI-FHIR R4 | **100%** |
| Throughput | **1.173 ficheiros/segundo** |
| Tempo total (10.001 relatórios) | **8,5 segundos** |
| Latência por Bundle | **~0,41 ms** |
| Erros de validação | **0** |

### Sumarização Clínica
| Modelo | ROUGE-1 F | ROUGE-2 F | BERTScore F | Fidelidade |
|--------|-----------|-----------|-------------|------------|
| **PTT5-FT v2** ⭐ | **0.493** | **0.470** | **0.805** | 0.592 |
| Extractive-PT | 0.349 | 0.301 | 0.699 | 0.538 |
| Gemma 3.1 (local) | 0.341 | 0.288 | 0.762 | 0.571 |
| mT5-XLSum | 0.118 | 0.043 | 0.701 | 0.232 |

*Avaliado sobre 616 relatórios de teste com golden collection criada por 2 radiologistas do CHULN.*

---

## Arquitetura

```
PACS JSON (RTF aninhado)
        │
        ▼
┌─────────────────┐
│  RTF Parser     │  Remove escapes hex, control words, extrai texto limpo
│  Agent          │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Mapper Agents  │  Patient · Encounter · ImagingStudy · DiagnosticReport
│  (LOINC codes)  │  IDs determinísticos UUID5 para reruns idempotentes
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Validator      │  Pydantic R4 (interno) + HAPI-FHIR (externo)
│  Agent          │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  FHIR Bundle    │  Transaction Bundle R4 · ProcessPoolExecutor (cpu-1 workers)
│  Generator      │  Batch size: 500 · Output: .fhir.json por relatório
└─────────────────┘
```

---

## Publicações

1. **[Publicado]** Villacis Vera L., Malheiro R., Craveiro O. *"PACS-to-FHIR Transformation and Clinical Text: a Case Study with Computed Tomography."* Procedia Computer Science (ScienceDirect) · HCIST 2025. DOI: [10.1016/j.procs.2026...](https://www.sciencedirect.com/science/article/pii/S1877050926007131)

2. **[Under Review]** Villacis Vera L., Malheiro R., Craveiro O. *"LLM-Based Medical Summarization Survey and a Multidimensional Evaluation Framework."* Artificial Intelligence in Medicine · Elsevier · Q1 · Submetido Jun 2026.

3. **[Under Review]** Villacis Vera L., Malheiro R., Craveiro O. *"Multidimensional Evaluation Framework for Local LLM-Based Clinical Summarization: A Cross-Lingual Prototype on Computed Tomography Reports."* Machine Learning and Knowledge Extraction · MDPI · Q1 · Submetido Jun 2026.

4. **[Em preparação]** Villacis Vera L., Malheiro R., Craveiro O., Távora V. *"Governance, Compliance, and Cross-Border Interoperability in Clinical Data Platforms."* Capítulo de livro · BLOCKCHAIN.PT · Jul 2026.

---

## Dataset

- **Fonte:** Centro Hospitalar Universitário de Lisboa Norte (CHULN) — dados anonimizados
- **Tipo:** Relatórios de Tomografia Computadorizada (TC)
- **Volume:** 10.001 relatórios PACS (9.921 para sumarização)
- **Split sumarização:** Train 7.937 · Val 992 · Test 992 (616 com referências manuais)
- **Especialidades TC:** 37 tipos de procedimento — tórax (24,49%), abdómen superior (15,92%), pélvico (15,47%)
- **Idioma:** Português (PT-PT)

> ⚠️ Os dados clínicos do CHULN são confidenciais e não estão incluídos neste repositório.

---

## Como executar

### Pipeline FHIR

```bash
cd fhir_transformer
pip install -r requirements.txt

# Processar todos os ficheiros
python main.py

# Testar com N ficheiros
python main.py --limit 10

# Workers customizados
python main.py --workers 4
```

Output em `output/fhir_bundles/` · Log em `logs/coordinator.log` · Resumo em `logs/transformation_summary.json`

### Sumarização

```bash
cd summarization
pip install -r requirements.txt

# Avaliar PTT5-FT v2
python evaluate.py --model ptt5 --split test

# Avaliar todos os modelos
python evaluate_all.py
```

---

## Equipa

| Nome | Papel | Instituição |
|------|-------|-------------|
| **Luís Alfredo Villacis Vera** | Bolseiro de Investigação / Mestrando | ESTG · IPLeiria |
| **Prof. Ricardo Manuel da Silva Malheiro** | Orientador Científico | ESTG · IPLeiria |
| **Prof. Olga Marina Freitas Craveiro** | Orientadora Científica | ESTG · IPLeiria |
| **Prof. Vítor M. de Oliveira Pegado de Noronha e Távora** | Coordenador do Projeto | IPLeiria |

---

## Financiamento

Este trabalho foi desenvolvido no âmbito da **Bolsa de Investigação BLOCKCHAIN.PT** — Agenda "Descentralizar Portugal com Blockchain" (WP2 – Saúde e Bem-estar).

**Ref.:** `02/C05-i01.01/2022.PC644918095-00000033`  
**Financiamento:** PRR – Plano de Recuperação e Resiliência · Next Generation EU · 2021–2026  
**Instituição de acolhimento:** Escola Superior de Tecnologia e Gestão (ESTG) · Instituto Politécnico de Leiria

---

## Licença

Código disponibilizado sob licença **MIT**. Os dados clínicos do CHULN são propriedade do hospital e não estão incluídos.
