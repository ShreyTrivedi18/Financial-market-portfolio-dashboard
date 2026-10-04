"""Data loading and normalization helpers for the portfolio dashboard.

The source dataset is intentionally read-only. This module discovers files,
normalizes the wide CSV exports, and returns tidy DataFrames for the UI.
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd
import yfinance as yf


APP_DIR = Path(__file__).resolve().parent
LOCAL_SOURCE_DATA_ROOT = (
    Path(r"D:\Semester-5\DV")
    / "Detailed-Financials-Data-Of-4456-NSE-And-BSE-Company-20231230T233228Z-001"
)
LOCAL_COMPANY_LIST = Path(
    r"C:\Users\hp\.copilot\attachments\4e86504f-47ca-47aa-b12b-0b3fe7ff5e89-List-Of-All-Companies.csv"
)
DEFAULT_DATA_ROOT = APP_DIR / "data" / "financials"
DEFAULT_COMPANY_LIST = APP_DIR / "data" / "company_list.csv"
DEFAULT_OHLC_PATH = APP_DIR / "data" / "ohlc.csv"
DEFAULT_REAL_UNIVERSE = APP_DIR / "data" / "real_universe.csv"
OHLC_REQUIRED_COLUMNS = ("Date", "Open", "High", "Low", "Close")
REAL_TICKER_MAP = {
    "3M India Ltd": "3MINDIA.NS",
    "ABB India Ltd": "ABB.NS",
    "ACC Ltd": "ACC.NS",
    "AAVAS Financiers Ltd": "AAVAS.NS",
    "5Paisa Capital Ltd": "5PAISA.NS",
    "Asian Paints Ltd": "ASIANPAINT.NS",
    "Axis Bank Ltd": "AXISBANK.NS",
    "Bajaj Finance Ltd": "BAJFINANCE.NS",
    "Bharti Airtel Ltd": "BHARTIARTL.NS",
    "Britannia Industries Ltd": "BRITANNIA.NS",
    "Cipla Ltd": "CIPLA.NS",
    "Coal India Ltd": "COALINDIA.NS",
    "Eicher Motors Ltd": "EICHERMOT.NS",
    "HCL Technologies Ltd": "HCLTECH.NS",
    "Hindalco Industries Ltd": "HINDALCO.NS",
    "Hindustan Unilever Ltd": "HINDUNILVR.NS",
    "ICICI Bank Ltd": "ICICIBANK.NS",
    "Infosys Ltd": "INFY.NS",
    "ITC Ltd": "ITC.NS",
    "JSW Steel Ltd": "JSWSTEEL.NS",
    "Kotak Mahindra Bank Ltd": "KOTAKBANK.NS",
    "Larsen & Toubro Ltd": "LT.NS",
    "Maruti Suzuki India Ltd": "MARUTI.NS",
    "NTPC Ltd": "NTPC.NS",
    "Power Grid Corporation of India Ltd": "POWERGRID.NS",
    "Reliance Industries Ltd": "RELIANCE.NS",
    "State Bank of India": "SBIN.NS",
    "Tata Consultancy Services Ltd": "TCS.NS",
    "Tata Motors Ltd": "TATAMOTORS.NS",
    "Titan Company Ltd": "TITAN.NS",
    "Wipro Ltd": "WIPRO.NS",
}


def default_data_path(relative_path: Path, local_path: Path) -> Path:
    """Prefer a repository-relative path, with a local-machine fallback when present."""
    resolved_relative = resolve_input_path(relative_path)
    if resolved_relative.exists():
        return resolved_relative
    return local_path if local_path.exists() else relative_path


def resolve_input_path(path: str | Path) -> Path:
    """Resolve relative data paths from the application directory, not process cwd."""
    candidate = Path(path).expanduser()
    return candidate if candidate.is_absolute() else APP_DIR / candidate


def resolve_company_root(data_root: str | Path) -> Path:
    """Find the directory containing company folders in either archive layout."""
    root = resolve_input_path(data_root)
    nested = root / "Detailed-Financials-Data-Of-4456-NSE-_-BSE-Company"
    if nested.is_dir():
        return nested
    return root


def _clean_number(value: object) -> float:
    if pd.isna(value):
        return np.nan
    text = str(value).strip().replace(",", "").replace("%", "")
    if text in {"", "-", "--", "nan", "None"}:
        return np.nan
    try:
        return float(text)
    except ValueError:
        return np.nan


def _read_wide_csv(path: Path) -> pd.DataFrame:
    frame = pd.read_csv(path)
    if frame.empty:
        return pd.DataFrame(columns=["metric", "period", "value"])
    frame = frame.rename(columns={frame.columns[0]: "metric"})
    frame["metric"] = frame["metric"].astype(str).str.strip()
    tidy = frame.melt(id_vars=["metric"], var_name="period", value_name="value")
    tidy["value"] = tidy["value"].map(_clean_number)
    tidy["period"] = tidy["period"].astype(str).str.strip()
    return tidy.dropna(subset=["metric"]).reset_index(drop=True)


def _read_basic_info(path: Path) -> dict[str, object]:
    frame = pd.read_csv(path)
    if frame.empty:
        return {}
    row = frame.iloc[0].to_dict()
    result: dict[str, object] = {}
    for key, value in row.items():
        clean_key = str(key).strip()
        if clean_key and clean_key != "nan":
            result[clean_key] = value
    result["Company"] = str(result.get("Company_name", path.parent.name)).strip()
    result["Data folder"] = str(path.parent)
    numeric_fields = {
        "Market Cap",
        "Current Price",
        "Stock P/E",
        "Book Value",
        "Dividend Yield",
        "ROCE",
        "ROE",
        "Price to Sales",
        "Sales growth",
        "Profit growth",
        "EPS",
        "Debt",
    }
    for field in numeric_fields:
        if field in result:
            result[field] = _clean_number(result[field])
    return result


def load_company_universe(data_root: str | Path) -> pd.DataFrame:
    """Discover and normalize all available company basic-info records."""
    company_root = resolve_company_root(data_root)
    records: list[dict[str, object]] = []
    if not company_root.is_dir():
        return pd.DataFrame()
    for basic_info in sorted(company_root.glob("*/*_Basic_Info.csv")):
        try:
            record = _read_basic_info(basic_info)
            if record:
                records.append(record)
        except (OSError, pd.errors.ParserError, UnicodeDecodeError):
            continue
    universe = pd.DataFrame(records)
    if universe.empty:
        return universe
    for column in ("Sector", "BSE", "NSE"):
        if column not in universe:
            universe[column] = "Unknown"
        universe[column] = universe[column].fillna("Unknown").astype(str).str.strip()
    return universe.sort_values("Company").reset_index(drop=True)


def load_real_universe(path: str | Path) -> pd.DataFrame:
    """Load the curated real NSE universe used by the public dashboard."""
    universe_path = resolve_input_path(path)
    if not universe_path.is_file():
        return pd.DataFrame()
    try:
        frame = pd.read_csv(universe_path)
    except (OSError, pd.errors.ParserError, UnicodeDecodeError):
        return pd.DataFrame()
    required = {"Company", "Sector", "NSE", "Yahoo Symbol"}
    if not required.issubset(frame.columns):
        return pd.DataFrame()
    for column in ("Market Cap", "Current Price", "Stock P/E", "ROE", "ROCE",
                   "Sales growth", "Profit growth", "Dividend Yield", "Debt"):
        if column not in frame:
            frame[column] = np.nan
        frame[column] = frame[column].map(_clean_number)
    frame["BSE"] = frame.get("BSE", "—")
    return frame.sort_values("Company").reset_index(drop=True)


def load_company_table(
    company: str, data_root: str | Path, table_name: str
) -> pd.DataFrame:
    """Load a company's wide statement/ratio CSV as tidy metric-period-value data."""
    company_root = resolve_company_root(data_root)
    folder = company_root / company
    matches = list(folder.glob(table_name))
    if not matches:
        return pd.DataFrame(columns=["metric", "period", "value"])
    try:
        return _read_wide_csv(matches[0])
    except (OSError, pd.errors.ParserError, UnicodeDecodeError):
        return pd.DataFrame(columns=["metric", "period", "value"])


def load_company_list(path: str | Path) -> set[str]:
    """Read the optional supplied company list without requiring a header format."""
    list_path = resolve_input_path(path)
    if not list_path.is_file():
        return set()
    try:
        frame = pd.read_csv(list_path, header=None)
    except (OSError, pd.errors.ParserError, UnicodeDecodeError):
        return set()
    values = frame.iloc[:, -1].dropna().astype(str).str.strip()
    return {value for value in values if value and value.lower() != "company"}


def load_ohlc_csv(path: str | Path, company: str | None = None) -> pd.DataFrame:
    """Load and validate a long-format OHLC CSV.

    Required columns are Date, Open, High, Low, and Close. An optional Company
    or Symbol column lets one file hold data for multiple companies.
    """
    ohlc_path = resolve_input_path(path)
    if not ohlc_path.is_file():
        return pd.DataFrame()
    try:
        frame = pd.read_csv(ohlc_path)
    except (OSError, pd.errors.ParserError, UnicodeDecodeError):
        return pd.DataFrame()
    frame.columns = [str(column).strip() for column in frame.columns]
    aliases = {column.lower(): column for column in frame.columns}
    missing = [column for column in OHLC_REQUIRED_COLUMNS if column.lower() not in aliases]
    if missing:
        return pd.DataFrame()
    frame = frame.rename(columns={aliases[column.lower()]: column for column in OHLC_REQUIRED_COLUMNS})
    company_column = next(
        (aliases[key] for key in ("company", "symbol", "ticker") if key in aliases),
        None,
    )
    if company and company_column:
        frame = frame[
            frame[company_column].astype(str).str.strip().str.casefold() == company.strip().casefold()
        ]
    frame["Date"] = pd.to_datetime(frame["Date"], errors="coerce")
    for column in ("Open", "High", "Low", "Close"):
        frame[column] = frame[column].map(_clean_number)
    frame = frame.dropna(subset=list(OHLC_REQUIRED_COLUMNS))
    frame = frame[
        (frame["High"] >= frame[["Open", "Close"]].max(axis=1))
        & (frame["Low"] <= frame[["Open", "Close"]].min(axis=1))
    ]
    return frame.sort_values("Date").reset_index(drop=True)


def load_yfinance_ohlc(
    ticker: str, period: str = "2y", interval: str = "1d"
) -> pd.DataFrame:
    """Fetch Yahoo Finance OHLC data and normalize it for the price view."""
    try:
        frame = yf.download(
            ticker,
            period=period,
            interval=interval,
            auto_adjust=False,
            progress=False,
            group_by="column",
            threads=False,
        )
    except Exception:
        return pd.DataFrame()
    if frame.empty:
        return pd.DataFrame()
    if isinstance(frame.columns, pd.MultiIndex):
        frame.columns = frame.columns.get_level_values(0)
    frame = frame.reset_index()
    date_column = "Date" if "Date" in frame.columns else "Datetime"
    if date_column not in frame.columns:
        return pd.DataFrame()
    result = pd.DataFrame(
        {
            "Date": pd.to_datetime(frame[date_column], errors="coerce"),
            "Open": frame.get("Open"),
            "High": frame.get("High"),
            "Low": frame.get("Low"),
            "Close": frame.get("Close"),
            "Volume": frame.get("Volume"),
        }
    )
    for column in ("Open", "High", "Low", "Close", "Volume"):
        result[column] = pd.to_numeric(result[column], errors="coerce")
    result = result.dropna(subset=list(OHLC_REQUIRED_COLUMNS))
    return result[
        (result["High"] >= result[["Open", "Close"]].max(axis=1))
        & (result["Low"] <= result[["Open", "Close"]].min(axis=1))
    ].sort_values("Date").reset_index(drop=True)


def ohlc_schema_message(path: str | Path) -> str | None:
    """Return a user-facing validation message, or None when the file is valid."""
    ohlc_path = resolve_input_path(path)
    if not ohlc_path.is_file():
        return None
    try:
        columns = {str(column).strip().lower() for column in pd.read_csv(ohlc_path, nrows=0).columns}
    except (OSError, pd.errors.ParserError, UnicodeDecodeError):
        return "The OHLC file could not be read as CSV."
    missing = [column for column in OHLC_REQUIRED_COLUMNS if column.lower() not in columns]
    if missing:
        return f"OHLC file is missing required columns: {', '.join(missing)}."
    return None


def make_illustrative_ohlc(
    current_price: float | int | None, periods: int = 30
) -> pd.DataFrame:
    """Create a deterministic sample OHLC path for UI demonstration only."""
    price = _clean_number(current_price)
    if np.isnan(price) or price <= 0:
        price = 100.0
    dates = pd.date_range(end=pd.Timestamp.today().normalize(), periods=periods, freq="B")
    trend = np.linspace(-0.04, 0.04, periods)
    cycle = np.sin(np.arange(periods) / 2.8) * 0.018
    close = price * (1 + trend + cycle)
    open_price = np.roll(close, 1)
    open_price[0] = close[0] * 0.99
    spread = np.maximum(close * 0.012, 0.25)
    return pd.DataFrame(
        {
            "Date": dates,
            "Open": open_price,
            "High": np.maximum(open_price, close) + spread,
            "Low": np.minimum(open_price, close) - spread,
            "Close": close,
        }
    )


def available_table_names(company: str, data_root: str | Path) -> Iterable[str]:
    folder = resolve_company_root(data_root) / company
    return sorted(path.name for path in folder.glob("*.csv"))
