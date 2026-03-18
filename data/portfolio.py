"""
data/portfolio.py — CSV portfolio loader.
Supports file upload + default path /data/portfolio.csv.
Validates columns, handles errors, returns clean DataFrame.
"""
import io
import logging
import pathlib
import pandas as pd

logger = logging.getLogger(__name__)

DEFAULT_PATH = pathlib.Path("data/portfolio.csv")

REQUIRED_COLS_OPTIONS = [
    ["symbol"],
    ["Symbol"],
    ["SYMBOL"],
    ["ticker"],
    ["Ticker"],
]

OPTIONAL_COLS = {
    "symbol":    str,
    "qty":       float,
    "avg_price": float,
    "buy_date":  str,
}

SAMPLE_CSV = """symbol,qty,avg_price,buy_date
RELIANCE,10,2500.00,2023-01-15
TCS,5,3400.00,2023-03-10
INFY,8,1500.00,2023-06-01
HDFCBANK,15,1600.00,2022-11-20
ICICIBANK,20,950.00,2023-02-28
"""


def _normalise_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Lowercase + strip column names."""
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]
    return df


def load_csv(file_obj=None) -> tuple:
    """
    Load portfolio CSV.
    file_obj: Streamlit UploadedFile or None (use default path).
    Returns (DataFrame, error_message).
    """
    try:
        if file_obj is not None:
            content = file_obj.read()
            df = pd.read_csv(io.BytesIO(content))
        elif DEFAULT_PATH.exists():
            df = pd.read_csv(DEFAULT_PATH)
        else:
            return pd.DataFrame(), (
                f"Portfolio file not found at {DEFAULT_PATH}. "
                "Please upload a CSV or create data/portfolio.csv."
            )
    except Exception as e:
        return pd.DataFrame(), f"Could not read portfolio file: {e}"

    df = _normalise_columns(df)

    # Find symbol column
    sym_col = None
    for candidate in ["symbol", "ticker", "scrip", "stock", "name"]:
        if candidate in df.columns:
            sym_col = candidate
            break

    if sym_col is None:
        return pd.DataFrame(), (
            "Portfolio file missing 'symbol' column. "
            f"Found columns: {list(df.columns)}. "
            "Expected format: symbol, qty, avg_price, buy_date"
        )

    # Rename to standard
    if sym_col != "symbol":
        df.rename(columns={sym_col: "symbol"}, inplace=True)

    # Clean symbols — add .NS if missing
    df["symbol"] = df["symbol"].astype(str).str.strip().str.upper()
    df["symbol"] = df["symbol"].apply(lambda s: s if "." in s else s + ".NS")

    # Numeric coercion
    for col in ["qty", "avg_price"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    # Drop empty symbols
    df = df[df["symbol"].str.len() > 0].reset_index(drop=True)

    if df.empty:
        return pd.DataFrame(), "Portfolio file has no valid rows after parsing."

    return df, None


def get_symbols(df: pd.DataFrame) -> list:
    """Extract clean symbol list from portfolio DataFrame."""
    if df is None or df.empty:
        return []
    return df["symbol"].dropna().unique().tolist()


def create_sample_file():
    """Create the default data/portfolio.csv if it doesn't exist."""
    DEFAULT_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not DEFAULT_PATH.exists():
        DEFAULT_PATH.write_text(SAMPLE_CSV)
        logger.info(f"Created sample portfolio at {DEFAULT_PATH}")
