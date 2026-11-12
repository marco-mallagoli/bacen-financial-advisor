import pytest
from fastapi.testclient import TestClient
from src.application.bacen_service import bacen_service
from src.main import create_app


@pytest.mark.asyncio
async def test_ranking_reclamacoes_bcb():
    res = await bacen_service.consultar_ranking_reclamacoes_bcb(segmento="digitais", trimestre="2026-Q3")
    assert res["metadados_fonte"]["total_registros_encontrados"] >= 3
    assert res["registros"][0]["instituicao"] == "NUBANK"
    assert res["registros"][0]["selo_ouvidoria_bcb"] == "A"


@pytest.mark.asyncio
async def test_indicadores_pix_sla():
    res = await bacen_service.consultar_indicadores_pix(instituicao="Itaú", trimestre="2026-Q3")
    assert len(res["registros"]) == 5
    assert res["estatisticas_agregadas"]["taxa_cumprimento_sla_bcb_pct"] == 100.0


@pytest.mark.asyncio
async def test_taxas_juros_consignado():
    res = await bacen_service.consultar_taxas_juros_credito(modalidade="consignado")
    assert len(res["registros"]) == 10
    # Sorted ascending by monthly interest rate (cheapest first)
    assert res["registros"][0]["taxa_juros_mensal_pct"] <= res["registros"][-1]["taxa_juros_mensal_pct"]


@pytest.mark.asyncio
async def test_comparar_instituicoes_bcb():
    res = await bacen_service.comparar_instituicoes_bcb(
        segmento="TODOS", modalidade_credito="CREDITO_PESSOAL"
    )
    assert len(res["registros"]) == 10
    assert res["registros"][0]["posicao_ranking"] == 1
    assert 0 <= res["registros"][0]["score_consolidado_bcb_0_10"] <= 10


def test_mcp_http_health_and_tools():
    with TestClient(create_app()) as client:
        r = client.get("/healthz")
        assert r.status_code == 200
        rpc = client.post(
            "/mcp",
            headers={"Accept": "application/json, text/event-stream"},
            json={"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}},
        )
        assert rpc.status_code == 200
        tools = [t["name"] for t in rpc.json()["result"]["tools"]]
        assert "comparar_instituicoes_bcb" in tools
        assert "consultar_indicadores_pix" in tools
        assert "consultar_taxas_juros_credito" in tools
