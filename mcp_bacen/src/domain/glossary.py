from typing import Any

BACEN_GLOSSARY: dict[str, dict[str, Any]] = {
    "ranking_reclamacoes": {
        "titulo": "Ranking de Reclamações e Ouvidoria do Banco Central (BCB)",
        "base_legal": "Resolução BCB nº 155/2021 e Resolução CMN nº 4.860/2020 (Ouvidorias)",
        "descricao": (
            "O Ranking de Reclamações do Banco Central avalia trimestralmente o desempenho de atendimento "
            "das instituições financeiras e de pagamento a partir das demandas registradas pelo público e "
            "analisadas pelos servidores do BCB."
        ),
        "formula_indice": (
            "Índice de Reclamações BCB = (Reclamações Reguladas Procedentes × 1.000.000) ÷ Número Total de Clientes da Instituição. "
            "Quanto MENOR o índice, melhor o posicionamento da instituição no atendimento."
        ),
        "escala_selos_ouvidoria": {
            "A": "Excelente (Nota Atendimento >= 88.0 / Índice BCB <= 18.0 por milhão de clientes)",
            "B": "Bom (78.0 <= Nota < 88.0 / Índice BCB entre 18.1 e 30.0)",
            "C": "Regular (68.0 <= Nota < 78.0 / Índice BCB entre 30.1 e 45.0)",
            "D": "Atenção Regulatória (55.0 <= Nota < 68.0 / Índice BCB entre 45.1 e 65.0)",
            "E": "Crítico (Nota < 55.0 / Índice BCB > 65.0 — sujeito a supervisão de conduta intensiva)",
        },
        "periodicidade": "Trimestral (ex.: 2026-Q1, 2026-Q2, 2026-Q3).",
    },
    "indicadores_pix_spi": {
        "titulo": "Indicadores Operacionais do Pix (SPI, DICT e MED)",
        "base_legal": "Resolução BCB nº 1/2020 (Regulamento do Pix) e Manual de Tempos do Pix",
        "indicadores": {
            "disponibilidade_spi_pct": {
                "nome": "Índice de Disponibilidade do Participante no SPI (%)",
                "meta_referencia": 99.90,
                "unidade": "% de uptime",
                "explicacao": "Percentual do tempo em que os sistemas do participante responderam dentro do SLA no Sistema de Pagamentos Instantâneos.",
            },
            "tempo_liquidacao_p95_seg": {
                "nome": "Tempo de Liquidação Pix P95 (segundos)",
                "meta_referencia": 2.00,
                "unidade": "segundos (menor é melhor)",
                "explicacao": "Tempo máximo levado para liquidar 95% das transações Pix iniciadas pelo participante.",
            },
            "tempo_consulta_dict_p99_ms": {
                "nome": "Latência de Consulta de Chave no DICT P99 (ms)",
                "meta_referencia": 500.0,
                "unidade": "ms (menor é melhor)",
                "explicacao": "Tempo de resolução da chave Pix no Diretório de Identificadores de Contas Transacionais.",
            },
            "taxa_sucesso_transacional_pct": {
                "nome": "Taxa de Efetivação Transacional Pix (%)",
                "meta_referencia": 99.50,
                "unidade": "% de transações efetivadas",
                "explicacao": "Fração das ordens de pagamento Pix concluídas sem rejeição técnica ou timeout.",
            },
            "indice_med_contestacao_100k": {
                "nome": "Índice de Acionamento do MED por 100 mil transações",
                "meta_referencia": 3.50,
                "unidade": "ocorrências/100k Pix (menor é melhor)",
                "explicacao": "Acionamentos do Mecanismo Especial de Devolução (suspeita fundada de fraude ou falha operacional).",
            },
        },
    },
    "taxas_juros_credito": {
        "titulo": "Estatísticas de Taxas de Juros de Operações de Crédito (API Olinda / SGS)",
        "base_legal": "Resolução CMN nº 3.517/2007 (Custo Efetivo Total - CET) e Lei nº 14.690/2023 (Teto do Rotativo)",
        "modalidades": {
            "CONSIGNADO_INSS": "Crédito Pessoal Consignado para Beneficiários do INSS (desconto em folha, menor risco e menor taxa).",
            "CREDITO_PESSOAL": "Crédito Pessoal Não-Consignado (livre destinação para Pessoa Física).",
            "CARTAO_ROTATIVO": "Cartão de Crédito Rotativo Regular (sujeito ao limite legal de 100% do valor original da dívida pela Lei 14.690/2023).",
            "FINANCIAMENTO_IMOBILIARIO": "Financiamento Imobiliário com Taxas de Mercado (aquisição de imóveis residenciais).",
            "CAPITAL_GIRO_PJ": "Capital de Giro com Prazo Superior a 365 dias para Pessoas Jurídicas (empresas).",
        },
        "conceito_cet": (
            "CET (Custo Efetivo Total): taxa anual que engloba não apenas os juros nominais, mas também "
            "IOF, tarifas de cadastro (TAC), seguros prestamistas e custos de registro."
        ),
    },
    "tarifas_servicos_essenciais": {
        "titulo": "Tarifas Bancárias, Pacotes Padronizados e Serviços Essenciais",
        "base_legal": "Resolução CMN nº 3.919/2010 e Resolução BCB nº 1/2020 (Gratuidade do Pix PF)",
        "regras_chave": [
            "Serviços Essenciais (Conta Corrente PF): todo cidadão tem direito a conta corrente sem tarifa de manutenção com até 4 saques, 2 transferências entre contas da mesma instituição e 10 folhas de cheque por mês.",
            "Pix Pessoa Física (PF) e MEI/EI: é expressamente vedada a cobrança de tarifa no envio e recebimento de Pix por Pessoas Físicas (salvo hipóteses comerciais específicas previstas pelo BCB).",
            "Pacotes Padronizados I, II, III e IV: cestas definidas pelo CMN para permitir comparação direta de preços entre bancos.",
        ],
    },
    "segmentos_instituicoes": {
        "titulo": "Segmentação Prudencial (S1 a S5) e Tipos de Instituições Supervisionadas pelo BCB",
        "segmentos": {
            "BANCOS_VAREJO": "Grandes bancos múltiplos e comerciais tradicionais (Segmento S1: Itaú, Bradesco, Banco do Brasil, Caixa, Santander).",
            "BANCOS_DIGITAIS": "Bancos digitais e Instituições de Pagamento (IPs) de grande porte (Nubank, Banco Inter, C6 Bank).",
            "COOPERATIVAS_ATACADO": "Sistemas cooperativos de crédito e bancos de investimento/atacado (Sicredi, BTG Pactual).",
        },
    },
}


def get_glossary_content(topico: str | None = None) -> dict[str, Any]:
    """Returns the full BCB regulatory glossary or the entry for one topic."""
    if not topico or topico.strip().lower() in ("geral", "todos", "all", "*"):
        return BACEN_GLOSSARY
    key = topico.strip().lower()
    if key in BACEN_GLOSSARY:
        return {key: BACEN_GLOSSARY[key]}
    matched = {k: v for k, v in BACEN_GLOSSARY.items() if key in k or key in v.get("titulo", "").lower()}
    return matched if matched else BACEN_GLOSSARY
