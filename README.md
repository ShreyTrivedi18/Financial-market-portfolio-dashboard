# Financial Market & Stock Portfolio Tracker

An academic-project-friendly Streamlit dashboard for exploring the supplied NSE/BSE company financial exports. It provides:

- Searchable and filterable market overview with sector and market-cap visuals.
- Company profile cards, sector market-cap treemap, and descriptive valuation/profitability scatter views.
- An illustrative equal-weight portfolio allocation view.
- Company comparison across market-cap, valuation, growth, and return metrics.
- Financial-health KPI cards and visuals from the supplied ratios, profit/loss, and balance-sheet exports.
- A candlestick section with optional date filtering, 3/5-period moving averages, volume when available, and CSV download.
- Downloadable filtered, comparison, portfolio, financial-health, and displayed OHLC tables.

The app is descriptive and educational; it does not provide investment advice or recommendations.

## Run locally

From this folder:

```powershell
python -m pip install -r requirements.txt
streamlit run app.py
```

The sidebar defaults to:

- `D:\Semester-5\DV\Detailed-Financials-Data-Of-4456-NSE-And-BSE-Company-20231230T233228Z-001`
- `C:\Users\hp\.copilot\attachments\4e86504f-47ca-47aa-b12b-0b3fe7ff5e89-List-Of-All-Companies.csv`

Both paths can be changed in the sidebar. The financials archive may contain an additional nested directory; the loader detects that layout automatically. The original dataset is never written to.

## Data notes

`data_loader.py` discovers `*_Basic_Info.csv` files for the company universe and loads `Ratios.csv`, `Yearly_Profit_Loss.csv`, and `Yearly_Balance_Sheet.csv` only for the company currently shown. Numeric values are normalized from the wide CSV exports into tidy metric/period/value tables. Missing or malformed files are handled as empty views with user-facing messages.

### Historical OHLC CSV schema

Use the included `data/ohlc_template.csv` as a starting point. The required columns are:

| Column | Type | Description |
| --- | --- | --- |
| `Date` | date | Trading date, such as `2024-01-02` |
| `Open` | number | Opening price |
| `High` | number | Intraday high; must be at least Open and Close |
| `Low` | number | Intraday low; must be at most Open and Close |
| `Close` | number | Closing price |

`Volume` is optional. `Company`, `Symbol`, or `Ticker` is optional but recommended when one file contains multiple companies; its value must match the company name selected in the dashboard. Enter the file path in the **Optional OHLC CSV** sidebar field. The dashboard validates dates, numeric values, and high/low bounds before plotting.

## Streamlit Community Cloud deployment

1. Create a GitHub repository and push `app.py`, `data_loader.py`, `requirements.txt`, `README.md`, and the `data/ohlc_template.csv` template. Do not commit the original financial archive or any private attachment files.
2. In [Streamlit Community Cloud](https://share.streamlit.io/), choose **Deploy an app**, select the repository and branch, and set the main file to `app.py`.
3. Streamlit Cloud installs the pinned dependency families from `requirements.txt`. In the deployed app, use repository-relative paths such as `data/financials` and `data/ohlc.csv`, or provide another accessible path in the sidebar.
4. If the full financial archive is too large for GitHub, upload a smaller academic sample under `data/financials` or connect the app to an external storage workflow. The app will start with a clear error rather than modifying or copying source data.

The repository includes a reduced subset of identifiable companies from the supplied archive so the deployed app renders immediately without exposing the full archive or private attachments: 3M India Ltd, ABB India Ltd, ACC Ltd, AAVAS Financiers Ltd, and 5Paisa Capital Ltd. Relative defaults are resolved from the directory containing `app.py`/`data_loader.py`, not Streamlit's process working directory. On the original local machine it automatically falls back to the supplied absolute full archive when the repository subset is absent or when you enter that path in the sidebar.

## V3 market-data provenance

The mapped NSE tickers are:

| Company | Yahoo Finance symbol |
| --- | --- |
| 3M India Ltd | `3MINDIA.NS` |
| ABB India Ltd | `ABB.NS` |
| ACC Ltd | `ACC.NS` |
| AAVAS Financiers Ltd | `AAVAS.NS` |
| 5Paisa Capital Ltd | `5PAISA.NS` |

The Price/OHLC tab attempts a cached `yfinance` download using these `.NS` symbols. It displays the retrieval time and source. If Yahoo Finance is unavailable, it loads `data/ohlc.csv`, a dated real Yahoo Finance snapshot committed for reproducible deployment. If neither source has rows, the app displays an explicit no-data message; v3 does not generate synthetic prices. Yahoo Finance availability, licensing, delayed quotes, corporate actions, and data completeness may vary. This dashboard is descriptive and is not investment advice.

## V2 interpretation notes

The richer visuals remain descriptive: the treemap uses dataset market-cap fields as area, the valuation/profitability scatter places Stock P/E against ROE, and the equal-weight portfolio is an arithmetic illustration. The OHLC moving averages are rolling summaries of whichever rows are loaded; they are not forecasts. The reduced real-company sample and dated snapshot should not be interpreted as a live, complete market feed.
