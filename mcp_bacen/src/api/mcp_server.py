import json
from typing import Any

from mcp.server.mcpserver import MCPServer

from src.application.bacen_service import bacen_service
from src.core.observability import ObservabilityMiddleware
from src.domain.glossary import get_glossary_content
from src.infrastructure.fallback_seed import FALLBACK_BCB_DATASETS

mcp = MCPServer(
    name="mcp-bacen",
    instructions=(
        "Servidor MCP especialista em Dados Abertos do Banco Central do Brasil (BACEN / API Olinda): "
        "Ranking de Reclamações e Ouvidorias (índice por 1 milhão de clientes e Selo A-E), "
        "Indicadores Operacionais do Pix (SPI, DICT e MED), "
        "Taxas de Juros de Operações de Crédito (Consignado INSS, Pessoal, Rotativo, Imobiliário e Giro PJ) "
        "e Tarifas Bancárias / Experiência Digital."
    ),
    middleware=[ObservabilityMiddleware()],
)


@mcp.tool(
    name="consultar_ranking_reclamacoes_bcb",
    description=(
        "Consulta o Ranking de Reclamações do Banco Central (BCB): índice de reclamações reguladas "
        "procedentes por 1 milhão de clientes (menor é melhor), nota de qualidade de atendimento (0-100), "
        "Selo de Ouvidoria (A a E), taxa de resolução (%), prazo médio e principal motivo de queixa. "
        "Filtra por instituição (ex: Itaú, Nubank, Banco do Brasil, Bradesco, Caixa, Santander, Inter, BTG, C6, Sicredi), "
        "segmento (BANCOS_VAREJO, BANCOS_DIGITAIS, COOPERATIVAS_ATACADO) e trimestre (ex: 2026-Q3)."
    ),
)
async def consultar_ranking_reclamacoes_bcb(
    instituicao: str | None = None,
    segmento: str | None = None,
    motivo: str | None = None,
    trimestre: str | None = None,
    limite: int = 25,
) -> dict[str, Any]:
    return await bacen_service.consultar_ranking_reclamacoes_bcb(
        instituicao=instituicao,
        segmento=segmento,
        motivo=motivo,
        trimestre=trimestre,
        limite=limite,
    )


@mcp.tool(
    name="consultar_indicadores_pix",
    description=(
        "Consulta os indicadores operacionais do Pix aferidos pelo Banco Central (SPI, DICT e MED): "
        "disponibilidade_spi_pct (meta >= 99.90%), tempo_liquidacao_p95_seg (meta <= 2.00s), "
        "tempo_consulta_dict_p99_ms (meta <= 500ms), taxa_sucesso_transacional_pct (meta >= 99.50%) e "
        "indice_med_contestacao_100k (acionamentos do Mecanismo Especial de Devolução por 100k Pix)."
    ),
)
async def consultar_indicadores_pix(
    instituicao: str | None = None,
    segmento: str | None = None,
    indicador: str | None = None,
    trimestre: str | None = None,
    limite: int = 25,
) -> dict[str, Any]:
    return await bacen_service.consultar_indicadores_pix(
        instituicao=instituicao,
        segmento=segmento,
        indicador=indicador,
        trimestre=trimestre,
        limite=limite,
    )


@mcp.tool(
    name="consultar_taxas_juros_credito",
    description=(
        "Consulta as taxas médias de juros de operações de crédito por instituição financeira na API Olinda BCB "
        "(% ao mês, % ao ano, CET estimado e posição vs. média do mercado). "
        "Modalidades aceitas: CONSIGNADO_INSS, CREDITO_PESSOAL, CARTAO_ROTATIVO, FINANCIAMENTO_IMOBILIARIO e CAPITAL_GIRO_PJ."
    ),
)
async def consultar_taxas_juros_credito(
    instituicao: str | None = None,
    segmento: str | None = None,
    modalidade: str | None = None,
    ano_mes: str | None = None,
    limite: int = 25,
) -> dict[str, Any]:
    return await bacen_service.consultar_taxas_juros_credito(
        instituicao=instituicao,
        segmento=segmento,
        modalidade=modalidade,
        ano_mes=ano_mes,
        limite=limite,
    )


@mcp.tool(
    name="consultar_tarifas_satisfacao_bcb",
    description=(
        "Consulta valores de tarifas bancárias (cesta mensal padronizada, saque excedente, anuidade média de cartão, "
        "gratuidade Pix PF) e notas de satisfação digital/aplicativo e transparência tarifária (0 a 10)."
    ),
)
async def consultar_tarifas_satisfacao_bcb(
    instituicao: str | None = None,
    segmento: str | None = None,
    ano_referencia: int | None = None,
    limite: int = 25,
) -> dict[str, Any]:
    return await bacen_service.consultar_tarifas_satisfacao_bcb(
        instituicao=instituicao,
        segmento=segmento,
        ano_referencia=ano_referencia,
        limite=limite,
    )


@mcp.tool(
    name="comparar_instituicoes_bcb",
    description=(
        "Compara bancos, fintechs e cooperativas lado a lado cruzando automaticamente os 4 pilares do Banco Central: "
        "Ranking de Reclamações/Ouvidoria + Estabilidade Operacional do Pix (SPI) + Competitividade de Juros na modalidade "
        "escolhida + Tarifas e Satisfação Digital, gerando um Score Consolidado BCB de 0 a 10."
    ),
)
async def comparar_instituicoes_bcb(
    segmento: str = "TODOS",
    modalidade_credito: str = "CREDITO_PESSOAL",
    instituicoes: list[str] | None = None,
) -> dict[str, Any]:
    return await bacen_service.comparar_instituicoes_bcb(
        segmento=segmento,
        modalidade_credito=modalidade_credito,
        instituicoes=instituicoes,
    )


@mcp.tool(
    name="buscar_datasets_dados_abertos_bcb",
    description=(
        "Busca conjuntos de dados abertos, endpoints OData da API Olinda e arquivos CSV oficiais "
        "no Portal de Dados Abertos do Banco Central do Brasil (dadosabertos.bcb.gov.br)."
    ),
)
async def buscar_datasets_dados_abertos_bcb(
    termo_busca: str = "pix reclamacoes juros tarifas",
    limite: int = 10,
) -> dict[str, Any]:
    return await bacen_service.buscar_datasets_dados_abertos_bcb(
        termo_busca=termo_busca,
        limite=limite,
    )


@mcp.tool(
    name="consultar_glossario_metodologia_bcb",
    description=(
        "Consulta o glossário regulatório e a metodologia oficial do Banco Central (BCB e CMN): "
        "cálculo do Índice de Reclamações por milhão de clientes, SLAs do Pix (SPI, DICT, MED), "
        "CET (Custo Efetivo Total), Serviços Essenciais gratuitos e Segmentação Prudencial (S1-S5, IP). "
        "Tópicos aceitos: 'geral', 'ranking_reclamacoes', 'indicadores_pix_spi', 'taxas_juros_credito', "
        "'tarifas_servicos_essenciais', 'segmentos_instituicoes'."
    ),
)
async def consultar_glossario_metodologia_bcb(
    topico: str | None = "geral",
) -> dict[str, Any]:
    return await bacen_service.consultar_glossario_metodologia_bcb(topico=topico)


@mcp.resource(
    "bacen://glossario/regulatorio",
    name="Glossário Regulatório Banco Central (Reclamações, Pix/SPI, Juros e Tarifas)",
    description="Dicionário completo de indicadores, SLAs do Pix, fórmulas do Ranking BCB e normas do CMN.",
    mime_type="application/json",
)
def resource_glossario_bacen() -> str:
    return json.dumps(get_glossary_content("geral"), ensure_ascii=False, indent=2)


@mcp.resource(
    "bacen://catalogo/datasets",
    name="Catálogo de Dados Abertos do Banco Central (Olinda & CKAN)",
    description="Endpoints oficiais da API Olinda e pacotes de dados abertos do Banco Central do Brasil.",
    mime_type="application/json",
)
def resource_catalogo_bcb() -> str:
    return json.dumps(FALLBACK_BCB_DATASETS, ensure_ascii=False, indent=2)
