"""In-memory (RAM) reference snapshot of Banco Central do Brasil (BACEN) open data:
1. Ranking de Reclamações & Ouvidoria BCB (índice por 1 milhão de clientes, nota 0-100 e Selo A-E)
2. Indicadores Operacionais do Pix / SPI / DICT / MED
3. Taxas de Juros de Operações de Crédito (API Olinda taxaJuros)
4. Tarifas Bancárias, Pacotes Padronizados & Satisfação Digital (IF.data / Olinda)
"""

from typing import Any

import polars as pl


def _compute_selo_ouvidoria(nota_atendimento: float) -> str:
    if nota_atendimento >= 88.0:
        return "A"
    if nota_atendimento >= 78.0:
        return "B"
    if nota_atendimento >= 68.0:
        return "C"
    if nota_atendimento >= 55.0:
        return "D"
    return "E"


def build_fallback_ranking_reclamacoes() -> pl.DataFrame:
    """Builds the BCB Ranking de Reclamações DataFrame by institution, segment and quarter."""
    perfis = [
        # (instituicao, conglomerado, segmento, clientes_mi, indice_rec_1m, nota_atend, resolucao_pct, prazo_dias, motivo_principal)
        (
            "NUBANK",
            "NU PAGAMENTOS S.A. - IP",
            "BANCOS_DIGITAIS",
            98.4,
            13.8,
            91.5,
            92.4,
            3.2,
            "Irregularidades relativas a integridade, confiabilidade e segurança de operações Pix/Cartão",
        ),
        (
            "SICREDI",
            "SISTEMA COOPERATIVO SICREDI",
            "COOPERATIVAS_ATACADO",
            8.2,
            12.4,
            92.8,
            93.6,
            2.9,
            "Oferta ou prestação de informação sobre serviços de conta corrente de forma inadequada",
        ),
        (
            "BTG PACTUAL",
            "BANCO BTG PACTUAL S.A.",
            "COOPERATIVAS_ATACADO",
            5.6,
            15.2,
            90.1,
            91.2,
            3.4,
            "Questionamento sobre liquidação de ativos e portabilidade de investimentos",
        ),
        (
            "BANCO DO BRASIL",
            "BB - CONGLOMERADO PRUDENCIAL",
            "BANCOS_VAREJO",
            76.5,
            19.4,
            86.2,
            88.9,
            4.1,
            "Oferta ou prestação de informação sobre crédito consignado de forma inadequada",
        ),
        (
            "ITAU",
            "ITAU UNIBANCO HOLDING S.A.",
            "BANCOS_VAREJO",
            71.2,
            21.6,
            84.5,
            87.8,
            4.3,
            "Irregularidades relativas a integridade e segurança em cartão de crédito",
        ),
        (
            "INTER",
            "BANCO INTER S.A.",
            "BANCOS_DIGITAIS",
            34.1,
            24.8,
            81.4,
            85.6,
            4.6,
            "Contestação de transações Pix (MED) e bloqueio preventivo de segurança",
        ),
        (
            "BRADESCO",
            "BANCO BRADESCO S.A.",
            "BANCOS_VAREJO",
            70.8,
            27.9,
            79.0,
            84.1,
            4.9,
            "Cobrança irregular de tarifa por pacote de serviços não contratado",
        ),
        (
            "CAIXA",
            "CAIXA ECONOMICA FEDERAL",
            "BANCOS_VAREJO",
            152.0,
            29.5,
            77.6,
            82.5,
            5.3,
            "Demora no atendimento de contestação Pix/benefícios e financiamento habitacional",
        ),
        (
            "SANTANDER",
            "BANCO SANTANDER (BRASIL) S.A.",
            "BANCOS_VAREJO",
            66.4,
            32.4,
            74.8,
            81.2,
            5.5,
            "Oferta ou renegociação de dívidas e cartão de crédito em desacordo",
        ),
        (
            "C6 BANK",
            "BANCO C6 S.A.",
            "BANCOS_DIGITAIS",
            28.5,
            38.2,
            70.4,
            79.5,
            5.8,
            "Oferta ou cobrança em operações de crédito consignado e encerramento de conta",
        ),
    ]

    trimestres = [("2026-Q1", 1.05), ("2026-Q2", 1.02), ("2026-Q3", 1.00)]
    rows: list[dict[str, Any]] = []

    for inst, cong, seg, cli_mi, ind_base, nota_base, res_base, prazo_base, motivo in perfis:
        for trim, factor in trimestres:
            ind_val = round(ind_base * factor, 2)
            nota_val = round(min(98.0, max(45.0, nota_base / factor)), 2)
            rec_proc = int(round(cli_mi * ind_val))
            rows.append(
                {
                    "trimestre": trim,
                    "instituicao": inst,
                    "conglomerado": cong,
                    "segmento": seg,
                    "total_clientes_milhoes": cli_mi,
                    "reclamacoes_procedentes": rec_proc,
                    "indice_reclamacoes_bcb": ind_val,
                    "nota_qualidade_atendimento": nota_val,
                    "selo_ouvidoria_bcb": _compute_selo_ouvidoria(nota_val),
                    "taxa_resolucao_pct": round(min(97.5, res_base / factor), 2),
                    "prazo_medio_dias": round(prazo_base * factor, 2),
                    "principal_motivo": motivo,
                }
            )
    return pl.DataFrame(rows)


def build_fallback_indicadores_pix() -> pl.DataFrame:
    """Builds the operational Pix / SPI / DICT / MED indicators DataFrame."""
    perfis_pix = [
        # (instituicao, segmento, disp_spi, liq_p95_s, dict_p99_ms, sucesso_pct, med_100k)
        ("NUBANK", "BANCOS_DIGITAIS", 99.96, 1.12, 240.0, 99.84, 1.85),
        ("ITAU", "BANCOS_VAREJO", 99.95, 1.18, 255.0, 99.81, 1.62),
        ("BANCO DO BRASIL", "BANCOS_VAREJO", 99.94, 1.24, 270.0, 99.79, 1.58),
        ("BTG PACTUAL", "COOPERATIVAS_ATACADO", 99.95, 1.15, 245.0, 99.82, 1.40),
        ("SICREDI", "COOPERATIVAS_ATACADO", 99.93, 1.32, 290.0, 99.76, 1.48),
        ("INTER", "BANCOS_DIGITAIS", 99.92, 1.38, 310.0, 99.71, 2.35),
        ("BRADESCO", "BANCOS_VAREJO", 99.91, 1.45, 325.0, 99.68, 2.10),
        ("SANTANDER", "BANCOS_VAREJO", 99.90, 1.52, 340.0, 99.64, 2.25),
        ("C6 BANK", "BANCOS_DIGITAIS", 99.89, 1.64, 365.0, 99.58, 2.75),
        ("CAIXA", "BANCOS_VAREJO", 99.87, 1.78, 395.0, 99.52, 2.60),
    ]

    trimestres = [("2026-Q1", -0.02), ("2026-Q2", -0.01), ("2026-Q3", 0.0)]
    rows: list[dict[str, Any]] = []

    for inst, seg, disp, liq, dict_ms, suc, med in perfis_pix:
        for trim, adj in trimestres:
            disp_v = round(min(99.99, disp + adj), 2)
            liq_v = round(max(0.80, liq - adj * 3), 2)
            dict_v = round(max(150.0, dict_ms - adj * 400), 1)
            suc_v = round(min(99.95, suc + adj * 2), 2)
            med_v = round(max(0.80, med - adj * 5), 2)

            specs = [
                ("disponibilidade_spi_pct", disp_v, 99.90, "%", disp_v >= 99.90),
                ("tempo_liquidacao_p95_seg", liq_v, 2.00, "s", liq_v <= 2.00),
                ("tempo_consulta_dict_p99_ms", dict_v, 500.0, "ms", dict_v <= 500.0),
                ("taxa_sucesso_transacional_pct", suc_v, 99.50, "%", suc_v >= 99.50),
                ("indice_med_contestacao_100k", med_v, 3.50, "por 100k Pix", med_v <= 3.50),
            ]
            for ind_id, val, meta, unit, cumpriu in specs:
                rows.append(
                    {
                        "trimestre": trim,
                        "instituicao": inst,
                        "segmento": seg,
                        "indicador": ind_id,
                        "valor_medido": val,
                        "meta_bcb": meta,
                        "unidade": unit,
                        "cumpriu_sla_bcb": cumpriu,
                    }
                )
    return pl.DataFrame(rows)


def build_fallback_taxas_juros() -> pl.DataFrame:
    """Builds the credit interest rates DataFrame modeled on BCB Olinda taxaJuros."""
    # (instituicao, segmento, consignado_am, pessoal_am, rotativo_am, imob_am, giro_pj_am)
    perfis_juros = [
        ("SICREDI", "COOPERATIVAS_ATACADO", 1.58, 3.85, 9.40, 0.82, 1.38),
        ("BANCO DO BRASIL", "BANCOS_VAREJO", 1.62, 4.15, 11.20, 0.84, 1.42),
        ("CAIXA", "BANCOS_VAREJO", 1.59, 4.28, 10.95, 0.78, 1.48),
        ("BTG PACTUAL", "COOPERATIVAS_ATACADO", 1.68, 4.35, 11.50, 0.86, 1.32),
        ("INTER", "BANCOS_DIGITAIS", 1.64, 4.60, 12.40, 0.85, 1.49),
        ("ITAU", "BANCOS_VAREJO", 1.71, 4.95, 12.90, 0.88, 1.46),
        ("NUBANK", "BANCOS_DIGITAIS", 1.65, 5.10, 12.60, 0.90, 1.54),
        ("SANTANDER", "BANCOS_VAREJO", 1.76, 5.45, 13.50, 0.91, 1.58),
        ("BRADESCO", "BANCOS_VAREJO", 1.74, 5.38, 13.35, 0.89, 1.55),
        ("C6 BANK", "BANCOS_DIGITAIS", 1.72, 5.65, 13.80, 0.92, 1.62),
    ]

    medias_mensais = {
        "CONSIGNADO_INSS": 1.67,
        "CREDITO_PESSOAL": 4.78,
        "CARTAO_ROTATIVO": 12.16,
        "FINANCIAMENTO_IMOBILIARIO": 0.87,
        "CAPITAL_GIRO_PJ": 1.48,
    }

    rows: list[dict[str, Any]] = []
    for inst, seg, consig, pessoal, rotativo, imob, giro in perfis_juros:
        mod_map = {
            "CONSIGNADO_INSS": consig,
            "CREDITO_PESSOAL": pessoal,
            "CARTAO_ROTATIVO": rotativo,
            "FINANCIAMENTO_IMOBILIARIO": imob,
            "CAPITAL_GIRO_PJ": giro,
        }
        for mod_code, taxa_am in mod_map.items():
            taxa_aa = round(((1.0 + taxa_am / 100.0) ** 12 - 1.0) * 100.0, 2)
            cet_aa = round(taxa_aa + (1.85 if mod_code != "CARTAO_ROTATIVO" else 4.20), 2)
            media_am = medias_mensais[mod_code]
            media_aa = round(((1.0 + media_am / 100.0) ** 12 - 1.0) * 100.0, 2)
            diff_pp = round(taxa_aa - media_aa, 2)
            if diff_pp <= -0.50:
                pos = "Abaixo da Média (Mais Barato)"
            elif diff_pp >= 0.50:
                pos = "Acima da Média (Mais Caro)"
            else:
                pos = "Na Média do Mercado"

            # Score 0-10 where lower interest vs market average gives higher score
            ratio = taxa_am / media_am
            nota_custo = round(min(9.8, max(4.5, 10.0 - (ratio - 0.80) * 8.5)), 2)

            rows.append(
                {
                    "ano_mes": "2026-09",
                    "instituicao": inst,
                    "segmento": seg,
                    "modalidade": mod_code,
                    "taxa_juros_mensal_pct": taxa_am,
                    "taxa_juros_anual_pct": taxa_aa,
                    "cet_estimado_anual_pct": cet_aa,
                    "media_mercado_anual_pct": media_aa,
                    "diferenca_vs_media_pp": diff_pp,
                    "posicao_competitiva": pos,
                    "nota_competitividade_custo": nota_custo,
                }
            )
    return pl.DataFrame(rows)


def build_fallback_tarifas_satisfacao() -> pl.DataFrame:
    """Builds the bank fees, standardized service packages and digital satisfaction DataFrame."""
    perfis_tarifas = [
        # (instituicao, segmento, cesta_mensal_brl, saque_excedente_brl, anuidade_media_brl, nota_app, nota_transp)
        ("NUBANK", "BANCOS_DIGITAIS", 0.00, 6.50, 0.00, 9.15, 9.40),
        ("INTER", "BANCOS_DIGITAIS", 0.00, 0.00, 0.00, 8.85, 9.50),
        ("BTG PACTUAL", "COOPERATIVAS_ATACADO", 0.00, 2.90, 35.00, 8.95, 8.80),
        ("SICREDI", "COOPERATIVAS_ATACADO", 18.50, 2.50, 22.00, 8.70, 8.65),
        ("C6 BANK", "BANCOS_DIGITAIS", 0.00, 6.50, 0.00, 8.10, 8.55),
        ("ITAU", "BANCOS_VAREJO", 34.90, 3.10, 48.00, 8.65, 7.95),
        ("BANCO DO BRASIL", "BANCOS_VAREJO", 32.50, 2.95, 42.00, 8.55, 8.05),
        ("CAIXA", "BANCOS_VAREJO", 28.90, 2.75, 36.00, 7.80, 7.85),
        ("BRADESCO", "BANCOS_VAREJO", 36.20, 3.20, 49.00, 8.15, 7.65),
        ("SANTANDER", "BANCOS_VAREJO", 37.50, 3.30, 52.00, 8.05, 7.50),
    ]

    rows: list[dict[str, Any]] = []
    for inst, seg, cesta, saque, anuidade, app_score, transp_score in perfis_tarifas:
        rows.append(
            {
                "ano_referencia": 2026,
                "instituicao": inst,
                "segmento": seg,
                "cesta_servicos_mensal_brl": cesta,
                "tarifa_pix_pf_brl": 0.00,
                "tarifa_saque_excedente_brl": saque,
                "anuidade_cartao_media_brl": anuidade,
                "nota_satisfacao_app_0_10": app_score,
                "nota_transparencia_tarifaria_0_10": transp_score,
            }
        )
    return pl.DataFrame(rows)


FALLBACK_BCB_DATASETS: list[dict[str, Any]] = [
    {
        "id": "bcb-ranking-reclamacoes",
        "name": "ranking-de-reclamacoes-bcb",
        "title": "Ranking de Reclamações do Banco Central — Bancos, Financeiras e Instituições de Pagamento",
        "notes": "Índice trimestral de reclamações reguladas procedentes por milhão de clientes, volume de demandas, taxa de resolução e motivos principais nas ouvidorias e no BCB.",
        "organization": "Banco Central do Brasil (BCB / Deati)",
        "url": "https://dadosabertos.bcb.gov.br/dataset/ranking-de-reclamacoes",
        "format": "JSON/CSV (API Olinda & CKAN)",
        "frequency": "Trimestral",
    },
    {
        "id": "bcb-pix-estatisticas-spi-dict",
        "name": "pix-estatisticas-transacoes-e-disponibilidade-spi",
        "title": "Estatísticas do Pix — Disponibilidade SPI, Latência DICT, Liquidação e MED",
        "notes": "Indicadores operacionais dos participantes do Pix no Sistema de Pagamentos Instantâneos (SPI), tempos de resposta do DICT e estatísticas de segurança/MED.",
        "organization": "Banco Central do Brasil (BCB / Decem)",
        "url": "https://olinda.bcb.gov.br/olinda/servico/Pix_DadosAbertos/versao/v1/odata",
        "format": "OData JSON / CSV",
        "frequency": "Mensal / Trimestral",
    },
    {
        "id": "bcb-taxas-juros-operacoes-credito",
        "name": "taxas-de-juros-de-operacoes-de-credito",
        "title": "Taxas de Juros de Operações de Crédito por Instituição Financeira (API Olinda taxaJuros)",
        "notes": "Taxas médias mensais e anuais (% a.m. e % a.a.) praticadas pelas instituições financeiras em Crédito Consignado INSS, Crédito Pessoal, Cartão Rotativo, Imobiliário e Capital de Giro PJ.",
        "organization": "Banco Central do Brasil (BCB / Dstat)",
        "url": "https://olinda.bcb.gov.br/olinda/servico/taxaJuros/versao/v2/odata/TaxasJurosMensalPorMes?$format=json",
        "format": "OData JSON",
        "frequency": "Mensal / Semanal",
    },
    {
        "id": "bcb-tarifas-bancarias-ifdata",
        "name": "tarifas-bancarias-e-pacotes-padronizados",
        "title": "Tarifas Bancárias por Instituição e Segmento Prudencial (Olinda Tarifas & IF.data)",
        "notes": "Valores vigentes de pacotes padronizados de conta corrente, saques excedentes, anuidades de cartões e gratuidade regulatória do Pix Pessoa Física.",
        "organization": "Banco Central do Brasil (BCB)",
        "url": "https://olinda.bcb.gov.br/olinda/servico/informes_lista_tarifas_por_instituicao_financeira/versao/v1/odata",
        "format": "OData JSON",
        "frequency": "Mensal",
    },
]
