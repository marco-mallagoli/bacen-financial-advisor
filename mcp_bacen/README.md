# 🏦 `mcp-bacen` — Servidor MCP de Dados Abertos do Banco Central (Olinda / Pix / Juros / Reclamações)

Servidor **Model Context Protocol (MCP)** escrito em **Python 3.12+ (FastAPI + `MCPServer` + Polars)** que processa e expõe em memória (RAM) os indicadores públicos do **Banco Central do Brasil (BACEN / CMN)**. Compatível com **Google ADK 2.x**, **Cloud Run** e **Gemini Enterprise (Custom MCP Server)** via transporte `StreamableHTTP` (`/mcp`) ou `stdio`.

---

## 🎯 Ferramentas MCP Expostas (7 Tools)

1. **`consultar_ranking_reclamacoes_bcb`**: Índice de reclamações reguladas procedentes por 1 milhão de clientes, Nota de Atendimento (0–100), Selo de Ouvidoria (`A`–`E`), taxa de resolução (%) e motivo principal por trimestre.
2. **`consultar_indicadores_pix`**: SLAs operacionais do Pix aferidos pelo BCB — disponibilidade no SPI (`>= 99,90%`), liquidação P95 (`<= 2,0s`), latência DICT P99 (`<= 500ms`), taxa de sucesso (`>= 99,50%`) e índice de acionamento do **MED** por 100 mil Pix.
3. **`consultar_taxas_juros_credito`**: Taxas médias mensais (`% a.m.`), anuais (`% a.a.`), CET estimado e posição competitiva vs. mercado nas modalidades `CONSIGNADO_INSS`, `CREDITO_PESSOAL`, `CARTAO_ROTATIVO`, `FINANCIAMENTO_IMOBILIARIO` e `CAPITAL_GIRO_PJ` (API Olinda `taxaJuros`).
4. **`consultar_tarifas_satisfacao_bcb`**: Cesta de serviços mensal padronizada (R$), tarifa de saque excedente, gratuidade do Pix PF, nota de app digital (0–10) e transparência tarifária (0–10).
5. **`comparar_instituicoes_bcb`**: Cruzamento em memória Polars dos 4 pilares gerando o `score_consolidado_bcb_0_10` e ranking ordenado.
6. **`buscar_datasets_dados_abertos_bcb`**: Busca de conjuntos de dados no catálogo CKAN (`dadosabertos.bcb.gov.br`) e endpoints OData da API Olinda.
7. **`consultar_glossario_metodologia_bcb`**: Dicionário oficial das normas do BCB e CMN (Res. BCB 1/2020 Pix/MED, Res. CMN 3.919/2010 Serviços Essenciais, Res. CMN 3.517/2007 CET, Segmentação S1–S5 e IPs).

---

## 🚀 Execução Local

```bash
# A partir da raiz do repositório:
PYTHONPATH=mcp_bacen .venv/bin/python3 -m pytest mcp_bacen/tests -v
PYTHONPATH=mcp_bacen .venv/bin/uvicorn src.main:app --host 127.0.0.1 --port 18081
```
