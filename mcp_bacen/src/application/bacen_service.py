from typing import Any

import polars as pl

from src.config import settings
from src.domain.entities import FonteMetadados, RespostaPadraoBacen
from src.domain.glossary import get_glossary_content
from src.domain.normalizer import (
    normalize_credit_modality,
    normalize_institution,
    normalize_pix_indicator,
    normalize_segment,
)
from src.infrastructure.bacen_http_client import bacen_http_client


def _clamp_limit(limite: int | None) -> int:
    if limite is None or limite <= 0:
        return settings.default_max_rows
    return min(limite, settings.max_allowed_rows)


def _records_to_markdown_table(records: list[dict[str, Any]], max_rows: int = 15) -> str:
    if not records:
        return "_Nenhum registro encontrado para os filtros informados._"
    sample = records[:max_rows]
    headers = list(sample[0].keys())
    header_line = "| " + " | ".join(headers) + " |"
    separator_line = "| " + " | ".join(["---"] * len(headers)) + " |"
    body_lines = []
    for row in sample:
        vals = [str(row.get(h, "")) for h in headers]
        body_lines.append("| " + " | ".join(vals) + " |")
    return "\n".join([header_line, separator_line, *body_lines])


class BacenService:
    """Orchestrates in-memory (Polars) queries over Banco Central do Brasil's 4 pillars:

    1. Ranking de Reclamações & Ouvidoria BCB (índice por 1M clientes, nota 0-100, Selo A-E)
    2. Indicadores Operacionais do Pix / SPI / DICT / MED
    3. Taxas de Juros de Operações de Crédito (API Olinda taxaJuros)
    4. Tarifas Bancárias, Pacotes Padronizados & Satisfação Digital
    5. Comparativo Consolidado de Instituições Financeiras (join dos 4 pilares)
    """

    async def consultar_ranking_reclamacoes_bcb(
        self,
        instituicao: str | None = None,
        segmento: str | None = None,
        motivo: str | None = None,
        trimestre: str | None = None,
        limite: int = 25,
    ) -> dict[str, Any]:
        df, origin = await bacen_http_client.get_ranking_reclamacoes_df()
        inst_norm = normalize_institution(instituicao)
        seg_norm = normalize_segment(segmento)
        row_limit = _clamp_limit(limite)

        filtered = df
        if inst_norm:
            filtered = filtered.filter(pl.col("instituicao").str.to_uppercase().str.contains(inst_norm))
        if seg_norm:
            filtered = filtered.filter(pl.col("segmento") == seg_norm)
        if motivo and motivo.strip():
            filtered = filtered.filter(
                pl.col("principal_motivo").str.to_lowercase().str.contains(motivo.strip().lower())
            )
        if trimestre and trimestre.strip():
            filtered = filtered.filter(pl.col("trimestre") == trimestre.strip().upper())

        # Lower indice_reclamacoes_bcb and higher nota_qualidade_atendimento is better
        filtered = filtered.sort(
            ["trimestre", "nota_qualidade_atendimento"], descending=[True, True]
        )
        total_found = filtered.height
        records = filtered.head(row_limit).to_dicts()

        if total_found > 0:
            media_ind = round(float(filtered["indice_reclamacoes_bcb"].mean() or 0.0), 2)
            media_nota = round(float(filtered["nota_qualidade_atendimento"].mean() or 0.0), 2)
            media_res = round(float(filtered["taxa_resolucao_pct"].mean() or 0.0), 2)
            melhor = filtered.row(0, named=True)
            pior = filtered.sort("indice_reclamacoes_bcb", descending=True).row(0, named=True)
            resumo = (
                f"Consultados {total_found} registros do Ranking de Reclamações BCB. "
                f"Índice médio: {media_ind} reclamações procedentes por 1 milhão de clientes | "
                f"Nota média de atendimento: {media_nota}/100 | Resolução média: {media_res}%. "
                f"Melhor avaliação no recorte: {melhor['instituicao']} ({melhor['trimestre']}) com índice {melhor['indice_reclamacoes_bcb']} "
                f"e Nota {melhor['nota_qualidade_atendimento']} (Selo {melhor['selo_ouvidoria_bcb']})."
            )
            stats = {
                "media_indice_reclamacoes_bcb": media_ind,
                "media_nota_qualidade_atendimento": media_nota,
                "media_taxa_resolucao_pct": media_res,
                "melhor_instituicao": {
                    "instituicao": melhor["instituicao"],
                    "trimestre": melhor["trimestre"],
                    "indice_reclamacoes_bcb": melhor["indice_reclamacoes_bcb"],
                    "nota_qualidade_atendimento": melhor["nota_qualidade_atendimento"],
                    "selo_ouvidoria_bcb": melhor["selo_ouvidoria_bcb"],
                },
                "maior_indice_reclamacoes": {
                    "instituicao": pior["instituicao"],
                    "trimestre": pior["trimestre"],
                    "indice_reclamacoes_bcb": pior["indice_reclamacoes_bcb"],
                    "nota_qualidade_atendimento": pior["nota_qualidade_atendimento"],
                },
            }
        else:
            resumo = "Nenhum registro encontrado no Ranking de Reclamações do Banco Central para os filtros informados."
            stats = {"media_indice_reclamacoes_bcb": None}

        resposta = RespostaPadraoBacen(
            resumo_executivo=resumo,
            estatisticas_agregadas=stats,
            registros=records,
            tabela_markdown=_records_to_markdown_table(records),
            metadados_fonte=FonteMetadados(
                pilar="Ranking de Reclamações e Ouvidoria BCB",
                url_oficial_bcb=settings.bcb_ranking_reclamacoes_url,
                origem_leitura=origin,
                filtros_aplicados={
                    "instituicao": inst_norm,
                    "segmento": seg_norm,
                    "motivo": motivo,
                    "trimestre": trimestre,
                },
                total_registros_encontrados=total_found,
                registros_retornados=len(records),
            ),
        )
        return resposta.model_dump()

    async def consultar_indicadores_pix(
        self,
        instituicao: str | None = None,
        segmento: str | None = None,
        indicador: str | None = None,
        trimestre: str | None = None,
        limite: int = 25,
    ) -> dict[str, Any]:
        df, origin = await bacen_http_client.get_indicadores_pix_df()
        inst_norm = normalize_institution(instituicao)
        seg_norm = normalize_segment(segmento)
        ind_norm = normalize_pix_indicator(indicador)
        row_limit = _clamp_limit(limite)

        filtered = df
        if inst_norm:
            filtered = filtered.filter(pl.col("instituicao").str.to_uppercase().str.contains(inst_norm))
        if seg_norm:
            filtered = filtered.filter(pl.col("segmento") == seg_norm)
        if ind_norm:
            filtered = filtered.filter(pl.col("indicador") == ind_norm)
        if trimestre and trimestre.strip():
            filtered = filtered.filter(pl.col("trimestre") == trimestre.strip().upper())

        filtered = filtered.sort(
            ["trimestre", "instituicao", "indicador"], descending=[True, False, False]
        )
        total_found = filtered.height
        records = filtered.head(row_limit).to_dicts()

        if total_found > 0:
            taxa_sla = round(
                float(filtered["cumpriu_sla_bcb"].cast(pl.Float64).mean() or 0.0) * 100.0, 2
            )
            por_indicador = (
                filtered.group_by(["indicador", "unidade", "meta_bcb"])
                .agg(
                    pl.col("valor_medido").mean().round(2).alias("media_valor_medido"),
                    (pl.col("cumpriu_sla_bcb").cast(pl.Float64).mean() * 100.0)
                    .round(1)
                    .alias("pct_cumprimento_sla"),
                )
                .sort("indicador")
                .to_dicts()
            )
            resumo = (
                f"Consultados {total_found} indicadores operacionais do Pix (SPI/DICT/MED). "
                f"Taxa global de conformidade com os SLAs regulatórios do BCB: {taxa_sla}%."
            )
            stats = {
                "taxa_cumprimento_sla_bcb_pct": taxa_sla,
                "medias_por_indicador": por_indicador,
            }
        else:
            resumo = "Nenhum indicador operacional do Pix encontrado para os filtros informados."
            stats = {"taxa_cumprimento_sla_bcb_pct": None, "medias_por_indicador": []}

        resposta = RespostaPadraoBacen(
            resumo_executivo=resumo,
            estatisticas_agregadas=stats,
            registros=records,
            tabela_markdown=_records_to_markdown_table(records),
            metadados_fonte=FonteMetadados(
                pilar="Estatísticas Operacionais do Pix (SPI / DICT / MED)",
                url_oficial_bcb=settings.bcb_pix_estatisticas_url,
                origem_leitura=origin,
                filtros_aplicados={
                    "instituicao": inst_norm,
                    "segmento": seg_norm,
                    "indicador": ind_norm,
                    "trimestre": trimestre,
                },
                total_registros_encontrados=total_found,
                registros_retornados=len(records),
            ),
        )
        return resposta.model_dump()

    async def consultar_taxas_juros_credito(
        self,
        instituicao: str | None = None,
        segmento: str | None = None,
        modalidade: str | None = None,
        ano_mes: str | None = None,
        limite: int = 25,
    ) -> dict[str, Any]:
        df, origin = await bacen_http_client.get_taxas_juros_df()
        inst_norm = normalize_institution(instituicao)
        seg_norm = normalize_segment(segmento)
        mod_norm = normalize_credit_modality(modalidade)
        row_limit = _clamp_limit(limite)

        filtered = df
        if inst_norm:
            filtered = filtered.filter(pl.col("instituicao").str.to_uppercase().str.contains(inst_norm))
        if seg_norm:
            filtered = filtered.filter(pl.col("segmento") == seg_norm)
        if mod_norm:
            filtered = filtered.filter(pl.col("modalidade") == mod_norm)
        if ano_mes and ano_mes.strip():
            filtered = filtered.filter(pl.col("ano_mes") == ano_mes.strip())

        # Lower interest rate is better for borrowers
        filtered = filtered.sort(
            ["modalidade", "taxa_juros_mensal_pct"], descending=[False, False]
        )
        total_found = filtered.height
        records = filtered.head(row_limit).to_dicts()

        if total_found > 0:
            media_am = round(float(filtered["taxa_juros_mensal_pct"].mean() or 0.0), 2)
            media_aa = round(float(filtered["taxa_juros_anual_pct"].mean() or 0.0), 2)
            menor = filtered.sort("taxa_juros_mensal_pct", descending=False).row(0, named=True)
            maior = filtered.sort("taxa_juros_mensal_pct", descending=True).row(0, named=True)
            resumo = (
                f"Consultadas {total_found} taxas de juros na API Olinda BCB. "
                f"Média do recorte: {media_am}% a.m. ({media_aa}% a.a.). "
                f"Menor taxa: {menor['instituicao']} em {menor['modalidade']} ({menor['taxa_juros_mensal_pct']}% a.m. / {menor['taxa_juros_anual_pct']}% a.a.)."
            )
            stats = {
                "media_taxa_mensal_pct": media_am,
                "media_taxa_anual_pct": media_aa,
                "menor_taxa_recorte": {
                    "instituicao": menor["instituicao"],
                    "modalidade": menor["modalidade"],
                    "taxa_juros_mensal_pct": menor["taxa_juros_mensal_pct"],
                    "taxa_juros_anual_pct": menor["taxa_juros_anual_pct"],
                },
                "maior_taxa_recorte": {
                    "instituicao": maior["instituicao"],
                    "modalidade": maior["modalidade"],
                    "taxa_juros_mensal_pct": maior["taxa_juros_mensal_pct"],
                    "taxa_juros_anual_pct": maior["taxa_juros_anual_pct"],
                },
            }
        else:
            resumo = "Nenhum registro de taxa de juros encontrado para os filtros informados."
            stats = {"media_taxa_mensal_pct": None}

        resposta = RespostaPadraoBacen(
            resumo_executivo=resumo,
            estatisticas_agregadas=stats,
            registros=records,
            tabela_markdown=_records_to_markdown_table(records),
            metadados_fonte=FonteMetadados(
                pilar="Taxas de Juros de Operações de Crédito (API Olinda taxaJuros)",
                url_oficial_bcb=settings.bcb_taxas_juros_url,
                origem_leitura=origin,
                filtros_aplicados={
                    "instituicao": inst_norm,
                    "segmento": seg_norm,
                    "modalidade": mod_norm,
                    "ano_mes": ano_mes,
                },
                total_registros_encontrados=total_found,
                registros_retornados=len(records),
            ),
        )
        return resposta.model_dump()

    async def consultar_tarifas_satisfacao_bcb(
        self,
        instituicao: str | None = None,
        segmento: str | None = None,
        ano_referencia: int | None = None,
        limite: int = 25,
    ) -> dict[str, Any]:
        df, origin = await bacen_http_client.get_tarifas_satisfacao_df()
        inst_norm = normalize_institution(instituicao)
        seg_norm = normalize_segment(segmento)
        row_limit = _clamp_limit(limite)

        filtered = df
        if inst_norm:
            filtered = filtered.filter(pl.col("instituicao").str.to_uppercase().str.contains(inst_norm))
        if seg_norm:
            filtered = filtered.filter(pl.col("segmento") == seg_norm)
        if ano_referencia is not None:
            filtered = filtered.filter(pl.col("ano_referencia") == int(ano_referencia))

        filtered = filtered.sort("nota_satisfacao_app_0_10", descending=True)
        total_found = filtered.height
        records = filtered.head(row_limit).to_dicts()

        if total_found > 0:
            media_cesta = round(float(filtered["cesta_servicos_mensal_brl"].mean() or 0.0), 2)
            media_app = round(float(filtered["nota_satisfacao_app_0_10"].mean() or 0.0), 2)
            media_transp = round(float(filtered["nota_transparencia_tarifaria_0_10"].mean() or 0.0), 2)
            lider = filtered.row(0, named=True)
            resumo = (
                f"Consultadas {total_found} instituições para Tarifas Bancárias e Satisfação Digital. "
                f"Cesta mensal média: R$ {media_cesta:.2f} | Satisfação digital média: {media_app}/10 | "
                f"Transparência tarifária média: {media_transp}/10. "
                f"Destaque em experiência digital: {lider['instituicao']} (Nota App {lider['nota_satisfacao_app_0_10']}/10, Cesta R$ {lider['cesta_servicos_mensal_brl']:.2f})."
            )
            stats = {
                "media_cesta_servicos_mensal_brl": media_cesta,
                "media_nota_satisfacao_app_0_10": media_app,
                "media_nota_transparencia_tarifaria_0_10": media_transp,
                "lider_satisfacao_digital": {
                    "instituicao": lider["instituicao"],
                    "cesta_servicos_mensal_brl": lider["cesta_servicos_mensal_brl"],
                    "nota_satisfacao_app_0_10": lider["nota_satisfacao_app_0_10"],
                },
            }
        else:
            resumo = "Nenhum registro de tarifas e satisfação encontrado para os filtros informados."
            stats = {"media_cesta_servicos_mensal_brl": None}

        resposta = RespostaPadraoBacen(
            resumo_executivo=resumo,
            estatisticas_agregadas=stats,
            registros=records,
            tabela_markdown=_records_to_markdown_table(records),
            metadados_fonte=FonteMetadados(
                pilar="Tarifas Bancárias, Pacotes Padronizados & Experiência Digital (Olinda / IF.data)",
                url_oficial_bcb=settings.bcb_tarifas_url,
                origem_leitura=origin,
                filtros_aplicados={
                    "instituicao": inst_norm,
                    "segmento": seg_norm,
                    "ano_referencia": ano_referencia,
                },
                total_registros_encontrados=total_found,
                registros_retornados=len(records),
            ),
        )
        return resposta.model_dump()

    async def comparar_instituicoes_bcb(
        self,
        segmento: str = "TODOS",
        modalidade_credito: str = "CREDITO_PESSOAL",
        instituicoes: list[str] | None = None,
    ) -> dict[str, Any]:
        """Joins the 4 BACEN pillars in memory to rank and compare financial institutions."""
        seg_norm = normalize_segment(segmento)
        mod_norm = normalize_credit_modality(modalidade_credito) or "CREDITO_PESSOAL"
        insts_norm = [
            normalize_institution(i) for i in (instituicoes or []) if normalize_institution(i)
        ]

        df_rec, origin = await bacen_http_client.get_ranking_reclamacoes_df()
        df_pix, _ = await bacen_http_client.get_indicadores_pix_df()
        df_juros, _ = await bacen_http_client.get_taxas_juros_df()
        df_tar, _ = await bacen_http_client.get_tarifas_satisfacao_df()

        # 1. Latest quarter Ranking de Reclamações
        rec_sub = df_rec
        if seg_norm:
            rec_sub = rec_sub.filter(pl.col("segmento") == seg_norm)
        if insts_norm:
            rec_sub = rec_sub.filter(pl.col("instituicao").is_in(insts_norm))

        rec_agg = (
            rec_sub.sort("trimestre", descending=True)
            .group_by("instituicao")
            .agg(
                pl.col("segmento").first().alias("segmento"),
                pl.col("selo_ouvidoria_bcb").first().alias("selo_ouvidoria_bcb"),
                pl.col("indice_reclamacoes_bcb").first().alias("indice_reclamacoes_bcb"),
                pl.col("nota_qualidade_atendimento").first().alias("nota_qualidade_atendimento"),
                pl.col("taxa_resolucao_pct").first().alias("taxa_resolucao_pct"),
            )
        )

        # 2. Pix / SPI operational score (0-10) + key metrics
        pix_agg = (
            df_pix.sort("trimestre", descending=True)
            .group_by("instituicao")
            .agg(
                pl.col("valor_medido")
                .filter(pl.col("indicador") == "disponibilidade_spi_pct")
                .first()
                .alias("pix_disponibilidade_spi_pct"),
                pl.col("valor_medido")
                .filter(pl.col("indicador") == "tempo_liquidacao_p95_seg")
                .first()
                .alias("pix_liquidacao_p95_seg"),
                pl.col("valor_medido")
                .filter(pl.col("indicador") == "indice_med_contestacao_100k")
                .first()
                .alias("pix_med_por_100k"),
            )
            .with_columns(
                (
                    5.0
                    + (pl.col("pix_disponibilidade_spi_pct") - 99.80) * 18.0
                    + (2.00 - pl.col("pix_liquidacao_p95_seg")) * 1.6
                )
                .clip(4.0, 9.9)
                .round(2)
                .alias("nota_estabilidade_pix_0_10")
            )
        )

        # 3. Credit interest rate for the chosen modality
        juros_sub = df_juros.filter(pl.col("modalidade") == mod_norm)
        juros_agg = juros_sub.group_by("instituicao").agg(
            pl.col("taxa_juros_mensal_pct").first().alias("juros_mensal_pct"),
            pl.col("taxa_juros_anual_pct").first().alias("juros_anual_pct"),
            pl.col("nota_competitividade_custo").first().alias("nota_competitividade_custo_0_10"),
        )

        # 4. Fees & digital satisfaction
        tar_agg = df_tar.group_by("instituicao").agg(
            pl.col("cesta_servicos_mensal_brl").first().alias("cesta_mensal_brl"),
            pl.col("nota_satisfacao_app_0_10").first().alias("nota_satisfacao_app_0_10"),
        )

        joined = (
            rec_agg.join(pix_agg, on="instituicao", how="left")
            .join(juros_agg, on="instituicao", how="left")
            .join(tar_agg, on="instituicao", how="left")
            .with_columns(
                (
                    (pl.col("nota_qualidade_atendimento").fill_null(80.0) / 10.0) * 0.35
                    + pl.col("nota_estabilidade_pix_0_10").fill_null(8.5) * 0.25
                    + pl.col("nota_competitividade_custo_0_10").fill_null(7.5) * 0.20
                    + pl.col("nota_satisfacao_app_0_10").fill_null(8.0) * 0.20
                )
                .round(2)
                .alias("score_consolidado_bcb_0_10")
            )
            .sort("score_consolidado_bcb_0_10", descending=True)
        )

        records = joined.to_dicts()
        for idx, row in enumerate(records, start=1):
            row["posicao_ranking"] = idx

        if records:
            top = records[0]
            resumo = (
                f"Comparativo consolidado BCB de {len(records)} instituições "
                f"(Segmento: {seg_norm or 'TODOS'} | Modalidade de Juros: {mod_norm}): "
                f"1º lugar: {top['instituicao']} (Score {top['score_consolidado_bcb_0_10']}/10 | "
                f"Selo Ouvidoria {top['selo_ouvidoria_bcb']} | Índice Reclamações {top['indice_reclamacoes_bcb']} | "
                f"Pix SPI {top.get('pix_disponibilidade_spi_pct')}% | Juros {top.get('juros_mensal_pct')}% a.m.)."
            )
            stats = {
                "segmento_comparado": seg_norm or "TODOS",
                "modalidade_credito_referencia": mod_norm,
                "total_instituicoes_comparadas": len(records),
                "lider_ranking": top,
                "pesos_score_consolidado": {
                    "qualidade_atendimento_ouvidoria": "35%",
                    "estabilidade_pix_spi": "25%",
                    "competitividade_juros_custo": "20%",
                    "satisfacao_digital_tarifas": "20%",
                },
            }
        else:
            resumo = "Nenhuma instituição financeira encontrada para o comparativo solicitado."
            stats = {"total_instituicoes_comparadas": 0}

        resposta = RespostaPadraoBacen(
            resumo_executivo=resumo,
            estatisticas_agregadas=stats,
            registros=records,
            tabela_markdown=_records_to_markdown_table(records),
            metadados_fonte=FonteMetadados(
                pilar="Comparativo Consolidado 4 Pilares BCB (Reclamações + Pix/SPI + Juros Olinda + Tarifas/App)",
                url_oficial_bcb=settings.bcb_olinda_base_url,
                origem_leitura=origin,
                filtros_aplicados={
                    "segmento": seg_norm or "TODOS",
                    "modalidade_credito": mod_norm,
                    "instituicoes": insts_norm,
                },
                total_registros_encontrados=len(records),
                registros_retornados=len(records),
            ),
        )
        return resposta.model_dump()

    async def buscar_datasets_dados_abertos_bcb(
        self,
        termo_busca: str = "pix reclamacoes juros tarifas",
        limite: int = 10,
    ) -> dict[str, Any]:
        row_limit = min(max(1, limite), 25)
        packages, origin = await bacen_http_client.search_bcb_datasets(
            termo_busca=termo_busca, limite=row_limit
        )
        resumo = (
            f"Encontrados {len(packages)} conjuntos de dados abertos no Portal BCB / API Olinda para '{termo_busca}'."
        )
        resposta = RespostaPadraoBacen(
            resumo_executivo=resumo,
            estatisticas_agregadas={"termo_busca": termo_busca, "total_pacotes": len(packages)},
            registros=packages,
            tabela_markdown=_records_to_markdown_table(packages),
            metadados_fonte=FonteMetadados(
                pilar="Catálogo de Dados Abertos BCB (CKAN & API Olinda OData)",
                url_oficial_bcb=settings.bcb_ckan_api_url,
                origem_leitura=origin,
                filtros_aplicados={"termo_busca": termo_busca, "limite": row_limit},
                total_registros_encontrados=len(packages),
                registros_retornados=len(packages),
            ),
        )
        return resposta.model_dump()

    async def consultar_glossario_metodologia_bcb(
        self,
        topico: str | None = "geral",
    ) -> dict[str, Any]:
        conteudo = get_glossary_content(topico)
        topicos_retornados = list(conteudo.keys())
        registros = [{"topico": k, **v} for k, v in conteudo.items()]
        resumo = (
            f"Glossário regulatório do Banco Central carregado para os tópicos: {', '.join(topicos_retornados)}."
        )
        resposta = RespostaPadraoBacen(
            resumo_executivo=resumo,
            estatisticas_agregadas={
                "topico_solicitado": topico or "geral",
                "topicos_retornados": topicos_retornados,
            },
            registros=registros,
            tabela_markdown=_records_to_markdown_table(
                [{"topico": k, "titulo": v.get("titulo", "")} for k, v in conteudo.items()]
            ),
            metadados_fonte=FonteMetadados(
                pilar="Glossário e Metodologia Regulatória Banco Central (BCB / CMN)",
                url_oficial_bcb="https://www.bcb.gov.br/estabilidadefinanceira/ranking",
                origem_leitura="memoria_interna",
                filtros_aplicados={"topico": topico},
                total_registros_encontrados=len(registros),
                registros_retornados=len(registros),
            ),
        )
        return resposta.model_dump()


bacen_service = BacenService()
