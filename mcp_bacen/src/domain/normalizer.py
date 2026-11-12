import unicodedata


def _strip_accents(text: str) -> str:
    """Strips accents, trims and upper-cases ``text``."""
    normalized = unicodedata.normalize("NFKD", text.strip())
    return "".join(c for c in normalized if not unicodedata.combining(c)).upper()


SEGMENT_ALIASES: dict[str, str] = {
    "S1": "BANCOS_VAREJO",
    "VAREJO": "BANCOS_VAREJO",
    "BANCOS_VAREJO": "BANCOS_VAREJO",
    "BANCOS TRADICIONAIS": "BANCOS_VAREJO",
    "TRADICIONAIS": "BANCOS_VAREJO",
    "GRANDES BANCOS": "BANCOS_VAREJO",
    "INCUMBENTES": "BANCOS_VAREJO",
    "DIGITAIS": "BANCOS_DIGITAIS",
    "BANCOS_DIGITAIS": "BANCOS_DIGITAIS",
    "BANCOS DIGITAIS": "BANCOS_DIGITAIS",
    "FINTECH": "BANCOS_DIGITAIS",
    "FINTECHS": "BANCOS_DIGITAIS",
    "IP": "BANCOS_DIGITAIS",
    "INSTITUICOES DE PAGAMENTO": "BANCOS_DIGITAIS",
    "COOPERATIVAS": "COOPERATIVAS_ATACADO",
    "COOPERATIVA": "COOPERATIVAS_ATACADO",
    "COOPERATIVAS_ATACADO": "COOPERATIVAS_ATACADO",
    "ATACADO": "COOPERATIVAS_ATACADO",
    "INVESTIMENTO": "COOPERATIVAS_ATACADO",
    "TODOS": "TODOS",
    "TODAS": "TODOS",
    "GERAL": "TODOS",
    "ALL": "TODOS",
}

INSTITUTION_ALIASES: dict[str, str] = {
    "ITAU": "ITAU",
    "ITAU UNIBANCO": "ITAU",
    "ITAÚ": "ITAU",
    "BRADESCO": "BRADESCO",
    "BANCO BRADESCO": "BRADESCO",
    "BB": "BANCO DO BRASIL",
    "BANCO DO BRASIL": "BANCO DO BRASIL",
    "CAIXA": "CAIXA",
    "CEF": "CAIXA",
    "CAIXA ECONOMICA": "CAIXA",
    "CAIXA ECONOMICA FEDERAL": "CAIXA",
    "SANTANDER": "SANTANDER",
    "BANCO SANTANDER": "SANTANDER",
    "NUBANK": "NUBANK",
    "NU PAGAMENTOS": "NUBANK",
    "NU": "NUBANK",
    "INTER": "INTER",
    "BANCO INTER": "INTER",
    "C6": "C6 BANK",
    "C6 BANK": "C6 BANK",
    "BANCO C6": "C6 BANK",
    "BTG": "BTG PACTUAL",
    "BTG PACTUAL": "BTG PACTUAL",
    "BANCO BTG": "BTG PACTUAL",
    "SICREDI": "SICREDI",
    "COOPERATIVA SICREDI": "SICREDI",
}

CREDIT_MODALITY_ALIASES: dict[str, str] = {
    "CONSIGNADO": "CONSIGNADO_INSS",
    "CONSIGNADO_INSS": "CONSIGNADO_INSS",
    "CONSIGNADO INSS": "CONSIGNADO_INSS",
    "INSS": "CONSIGNADO_INSS",
    "APOSENTADO": "CONSIGNADO_INSS",
    "CREDITO_PESSOAL": "CREDITO_PESSOAL",
    "CREDITO PESSOAL": "CREDITO_PESSOAL",
    "EMPRESTIMO PESSOAL": "CREDITO_PESSOAL",
    "PESSOAL": "CREDITO_PESSOAL",
    "ROTATIVO": "CARTAO_ROTATIVO",
    "CARTAO_ROTATIVO": "CARTAO_ROTATIVO",
    "CARTAO DE CREDITO": "CARTAO_ROTATIVO",
    "CARTAO": "CARTAO_ROTATIVO",
    "IMOBILIARIO": "FINANCIAMENTO_IMOBILIARIO",
    "FINANCIAMENTO_IMOBILIARIO": "FINANCIAMENTO_IMOBILIARIO",
    "FINANCIAMENTO IMOBILIARIO": "FINANCIAMENTO_IMOBILIARIO",
    "CASA PROPRIA": "FINANCIAMENTO_IMOBILIARIO",
    "CAPITAL_GIRO_PJ": "CAPITAL_GIRO_PJ",
    "CAPITAL DE GIRO": "CAPITAL_GIRO_PJ",
    "PJ": "CAPITAL_GIRO_PJ",
    "EMPRESARIAL": "CAPITAL_GIRO_PJ",
}

PIX_INDICATOR_ALIASES: dict[str, str] = {
    "DISPONIBILIDADE": "disponibilidade_spi_pct",
    "DISPONIBILIDADE_SPI_PCT": "disponibilidade_spi_pct",
    "SPI": "disponibilidade_spi_pct",
    "UPTIME": "disponibilidade_spi_pct",
    "LATENCIA": "tempo_liquidacao_p95_seg",
    "TEMPO": "tempo_liquidacao_p95_seg",
    "LIQUIDACAO": "tempo_liquidacao_p95_seg",
    "TEMPO_LIQUIDACAO_P95_SEG": "tempo_liquidacao_p95_seg",
    "DICT": "tempo_consulta_dict_p99_ms",
    "CHAVE": "tempo_consulta_dict_p99_ms",
    "TEMPO_CONSULTA_DICT_P99_MS": "tempo_consulta_dict_p99_ms",
    "SUCESSO": "taxa_sucesso_transacional_pct",
    "TAXA_SUCESSO_TRANSACIONAL_PCT": "taxa_sucesso_transacional_pct",
    "APROVACAO": "taxa_sucesso_transacional_pct",
    "MED": "indice_med_contestacao_100k",
    "FRAUDE": "indice_med_contestacao_100k",
    "GOLPE": "indice_med_contestacao_100k",
    "INDICE_MED_CONTESTACAO_100K": "indice_med_contestacao_100k",
}


def normalize_segment(segmento: str | None) -> str | None:
    if not segmento or not segmento.strip():
        return None
    cleaned = _strip_accents(segmento)
    if cleaned in ("TODOS", "TODAS", "GERAL", "ALL", "*"):
        return None
    if cleaned in SEGMENT_ALIASES:
        target = SEGMENT_ALIASES[cleaned]
        return None if target == "TODOS" else target
    for alias, code in SEGMENT_ALIASES.items():
        if alias in cleaned:
            return None if code == "TODOS" else code
    return cleaned


def normalize_institution(instituicao: str | None) -> str | None:
    if not instituicao or not instituicao.strip():
        return None
    cleaned = _strip_accents(instituicao)
    if cleaned in ("TODAS", "TODOS", "ALL", "*"):
        return None
    if cleaned in INSTITUTION_ALIASES:
        return INSTITUTION_ALIASES[cleaned]
    for alias, canonical in INSTITUTION_ALIASES.items():
        if alias in cleaned:
            return canonical
    return cleaned


def normalize_credit_modality(modalidade: str | None) -> str | None:
    if not modalidade or not modalidade.strip():
        return None
    cleaned = _strip_accents(modalidade)
    if cleaned in ("TODAS", "TODOS", "ALL", "*"):
        return None
    if cleaned in CREDIT_MODALITY_ALIASES:
        return CREDIT_MODALITY_ALIASES[cleaned]
    for alias, canonical in CREDIT_MODALITY_ALIASES.items():
        if alias in cleaned:
            return canonical
    return cleaned


def normalize_pix_indicator(indicador: str | None) -> str | None:
    if not indicador or not indicador.strip():
        return None
    cleaned = _strip_accents(indicador)
    if cleaned in ("TODOS", "TODAS", "ALL", "*"):
        return None
    if cleaned in PIX_INDICATOR_ALIASES:
        return PIX_INDICATOR_ALIASES[cleaned]
    for alias, canonical in PIX_INDICATOR_ALIASES.items():
        if alias in cleaned:
            return canonical
    return cleaned.lower()
