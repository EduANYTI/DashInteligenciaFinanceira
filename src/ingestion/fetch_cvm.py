"""
Módulo de ingestão de dados da CVM (Comissão de Valores Mobiliários).

Fonte: https://dados.cvm.gov.br/
Dados: Demonstrações Financeiras Padronizadas (DFP)
  - Demonstração de Resultado (DRE)
  - Balanço Patrimonial Ativo/Passivo

Documentação da API: https://dados.cvm.gov.br/swagger-ui.html
"""

import io
import zipfile
from pathlib import Path

import pandas as pd
import requests

from src.utils.config import DATA_RAW_DIR
from src.utils.logger import logger

CVM_BASE_URL = "https://dados.cvm.gov.br/dados/CIA_ABERTA/DOC/DFP/DADOS"

# Códigos das linhas contábeis relevantes
CONTAS_INTERESSE = {
    # DRE
    "3.01": "receita_liquida",
    "3.02": "custo_bens_servicos",
    "3.03": "resultado_bruto",
    "3.05": "ebit",
    "3.06": "resultado_financeiro",
    "3.08": "ebt",
    "3.09": "imposto_renda",
    "3.11": "lucro_liquido",
    # Balanço
    "1":    "ativo_total",
    "2":    "passivo_total",
    "2.03": "patrimonio_liquido",
}


def fetch_dfp_year(year: int, save_raw: bool = True) -> pd.DataFrame | None:
    """
    Baixa o arquivo ZIP da DFP de um ano e extrai a DRE consolidada.

    Args:
        year: Ano de referência (ex: 2023).
        save_raw: Se True, salva arquivo bruto em data/raw/.

    Returns:
        DataFrame com DRE/Balanço do ano ou None em caso de falha.
    """
    url = f"{CVM_BASE_URL}/dfp_cia_aberta_{year}.zip"
    logger.info(f"Baixando DFP CVM {year}: {url}")

    try:
        resp = requests.get(url, timeout=60)
        resp.raise_for_status()
    except requests.exceptions.RequestException as e:
        logger.error(f"Erro ao baixar DFP {year}: {e}")
        return None

    try:
        with zipfile.ZipFile(io.BytesIO(resp.content)) as z:
            # Arquivo de interesse: DRE consolidada
            target_files = [
                f for f in z.namelist()
                if "con" in f.lower() and f.endswith(".csv")
            ]

            if not target_files:
                logger.warning(f"Nenhum arquivo consolidado encontrado no ZIP de {year}")
                return None

            frames = []
            for fname in target_files:
                with z.open(fname) as f:
                    df = pd.read_csv(
                        f,
                        sep=";",
                        encoding="latin-1",
                        dtype=str,
                        low_memory=False,
                    )
                    frames.append(df)

            result = pd.concat(frames, ignore_index=True)

            if save_raw:
                path = DATA_RAW_DIR / f"cvm_dfp_{year}_raw.csv"
                result.to_csv(path, index=False)
                logger.info(f"DFP {year} bruta salva: {path} ({len(result):,} linhas)")

            return result

    except Exception as e:
        logger.error(f"Erro ao processar ZIP DFP {year}: {e}")
        return None


def process_dfp(df_raw: pd.DataFrame, year: int) -> pd.DataFrame:
    """
    Filtra e transforma os dados brutos da DFP.

    Args:
        df_raw: DataFrame bruto da CVM.
        year: Ano de referência.

    Returns:
        DataFrame limpo com indicadores financeiros por empresa.
    """
    required_cols = {"CD_CVM", "DENOM_CIA", "DT_REFER", "CD_CONTA", "DS_CONTA", "VL_CONTA"}
    available = set(df_raw.columns)

    if not required_cols.issubset(available):
        missing = required_cols - available
        logger.warning(f"Colunas ausentes na DFP {year}: {missing}")
        return pd.DataFrame()

    df = df_raw[list(required_cols)].copy()
    df.columns = ["cd_cvm", "empresa", "dt_refer", "cd_conta", "ds_conta", "valor"]

    # Filtra apenas contas de interesse
    df = df[df["cd_conta"].isin(CONTAS_INTERESSE.keys())].copy()

    # Converte valor
    df["valor"] = (
        df["valor"]
        .str.replace(",", ".", regex=False)
        .pipe(pd.to_numeric, errors="coerce")
    )

    # Renomeia contas para nomes legíveis
    df["indicador"] = df["cd_conta"].map(CONTAS_INTERESSE)
    df["ano"] = year

    df = df.dropna(subset=["valor"])
    df = df[["cd_cvm", "empresa", "ano", "dt_refer", "indicador", "valor"]]

    logger.info(f"DFP {year} processada: {df['empresa'].nunique()} empresas, {len(df):,} linhas")
    return df


def fetch_cvm_multi_year(
    years: list[int] | None = None,
    save_csv: bool = True,
) -> pd.DataFrame:
    """
    Baixa e consolida DFPs de múltiplos anos.

    Args:
        years: Lista de anos. Se None, usa os últimos 4 anos.
        save_csv: Se True, salva resultado consolidado.

    Returns:
        DataFrame consolidado com todos os anos.
    """
    from datetime import date
    current_year = date.today().year
    years = years or list(range(current_year - 4, current_year))

    frames = []
    for year in years:
        raw = fetch_dfp_year(year)
        if raw is not None:
            processed = process_dfp(raw, year)
            if not processed.empty:
                frames.append(processed)

    if not frames:
        logger.error("Nenhum dado CVM coletado.")
        return pd.DataFrame()

    result = pd.concat(frames, ignore_index=True)

    if save_csv:
        from src.utils.config import DATA_PROCESSED_DIR
        path = DATA_PROCESSED_DIR / "cvm_financials.csv"
        result.to_csv(path, index=False)
        logger.info(f"DFP consolidada salva: {path} ({len(result):,} linhas)")

    return result


if __name__ == "__main__":
    fetch_cvm_multi_year()
