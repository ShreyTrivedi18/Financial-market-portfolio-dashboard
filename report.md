# Financial Market & Stock Portfolio Tracker

## An Academic Case Study of a Streamlit-Based Exploratory Dashboard

**Project type:** Data Visualization / Financial Analytics  
**Application:** [Financial Market & Stock Portfolio Tracker](https://financial-market-portfolio-dashboard-igrhbznnwtvxqhokjtfgaq.streamlit.app/)  
**Repository:** `ShreyTrivedi18/Financial-market-portfolio-dashboard`  
**Prepared for:** Academic project submission  
**Date:** 02 October 2026

> **Data and interpretation notice.** This report describes an educational dashboard. It is not investment advice, a trading recommendation, or a claim about future performance. The deployed demonstration uses a curated real-company NSE universe and dated Yahoo Finance history. The supplied local archive provides the broader financial-data context, but it is not published with the cloud application.

---

## Abstract

The Financial Market & Stock Portfolio Tracker is an interactive Streamlit dashboard designed to help students explore company-level financial information, compare issuers, construct an illustrative portfolio allocation, and inspect selected financial-health indicators. The dashboard addresses a practical data-visualization problem: financial information is often distributed across many company folders and wide CSV statements, making direct comparison difficult without normalization and a consistent visual interface.

The system combines a Python data-loading layer with a Plotly-based Streamlit interface. The loader discovers company folders, reads basic information, reshapes wide statements into tidy metric-period-value tables, validates optional historical OHLC data, and provides explicit handling for missing files. The interface contains five views: Market overview, Portfolio allocation, Company comparison, Financial health, and Price/OHLC. Filters for sector, company name, and minimum market capitalization connect the views to a common filtered universe.

For deployment safety, the public application contains a curated universe of 31 identifiable NSE companies mapped to Yahoo Finance `.NS` symbols, including 3M India, ABB India, ACC, AAVAS Financiers, 5Paisa, Reliance Industries, Infosys, TCS, ICICI Bank, and other listed names. Only a reduced fundamentals subset is published; the full archive and private attachment CSV remain excluded. The OHLC view attempts on-demand Yahoo Finance history through `yfinance`, cached for 15 minutes, and falls back to a dated real snapshot when network retrieval is unavailable. Findings in this report therefore describe interface behavior and available data, not investment conclusions.

**Keywords:** financial visualization, Streamlit, Plotly, portfolio allocation, OHLC, data normalization, exploratory analytics

---

## 1. Introduction and Problem Statement

Financial-market datasets are useful for teaching data analysis because they combine categorical information (sector, exchange, company), numeric indicators (market capitalization, price, return ratios), time series (annual statements and ratios), and market-price records (OHLC). They are also difficult to work with in their raw form. In the supplied local context, each company is represented by a directory containing separate CSV files for basic information, ratios, profit and loss, balance sheet, cash flow, and shareholding patterns. The same metric is often stored across columns representing periods rather than rows representing observations.

This structure creates three educational problems:

1. **Discovery problem:** A user must locate a company and then remember which file contains each metric.
2. **Comparison problem:** Company records are not immediately aligned into a common table for filtering and comparison.
3. **Communication problem:** Static tables do not make it easy to explain how market size, growth, profitability, leverage, and price history relate to one another.

The project addresses these problems with a maintainable dashboard rather than a one-off notebook. The application reads the source files without modifying them, normalizes only what is required for a selected view, and exposes interactive charts that support exploratory questions. Examples include: “Which sectors are represented in the current universe?”, “How do selected companies compare on ROE or market capitalization?”, and “What does the selected company’s annual operating trend look like?”

The case study focuses on the implementation and analytical affordances of the dashboard. It deliberately avoids presenting a company as “good,” “bad,” “safe,” or “recommended.” Such judgments would require a broader investment methodology, current market data, and suitability information that are outside the scope of this academic prototype.

---

## 2. Objectives

The project objectives were:

- Build a usable Streamlit dashboard for company and portfolio exploration.
- Create a reusable data-loading and normalization layer rather than embedding CSV logic in the UI.
- Support search, sector filtering, and a minimum market-cap filter.
- Visualize market composition and basic cross-company relationships.
- Provide an illustrative equal-weight portfolio allocation view.
- Compare companies across size, valuation, growth, and return-related fields.
- Visualize selected ratios, profit-and-loss trends, and balance-sheet trends.
- Support a real historical OHLC CSV workflow with schema validation.
- Provide a clearly labeled fallback when daily OHLC data is unavailable.
- Keep the public deployment safe by using a reduced real-company subset instead of private or oversized source files.
- Document local execution and Streamlit Community Cloud deployment.

The objectives were implemented as an academic exploratory tool. The dashboard is not intended to execute trades, predict prices, or replace financial due diligence.

---

## 3. Dataset and Data Governance

### 3.1 Supplied local financial archive

The local project context includes a financial archive described as containing detailed information for NSE and BSE companies. Its folder structure contains company directories with files such as:

- `*_Basic_Info.csv`
- `Ratios.csv`
- `Yearly_Profit_Loss.csv`
- `Yearly_Balance_Sheet.csv`
- `Yearly_Cash_flow.csv`
- `Quarterly_Profit_Loss.csv`
- shareholding-pattern files

The application’s loader is designed for this layout and detects an additional nested archive directory when present. In the development environment, the basic-info discovery process successfully loaded a readable subset of 52 company records from the supplied local directory. This observation is a validation detail, not a claim that the local archive is complete or current.

The original archive is not copied, transformed in place, or committed to GitHub. The application reads it as an external input when the user enters the local path or when the local fallback path exists.

### 3.2 Public curated real-company universe

Streamlit Community Cloud cannot access a developer’s `D:\` drive. The repository therefore includes a curated real-company mapping under `data/real_universe.csv` and a reduced fundamentals subset under `data/financials`:

| Real company subset | Identifier | Basic info | Ratios | Profit/loss | Balance sheet |
| --- | --- |:---:|:---:|:---:|:---:|
| 3M India Ltd | `3MINDIA.NS` | Yes | Yes | Yes | Yes |
| ABB India Ltd | `ABB.NS` | Yes | Yes | Yes | Yes |
| ACC Ltd | `ACC.NS` | Yes | Yes | Yes | Yes |
| AAVAS Financiers Ltd | `AAVAS.NS` | Yes | Yes | Yes | Yes |
| 5Paisa Capital Ltd | `5PAISA.NS` | Yes | Yes | Yes | Yes |

The mapped names are real listed Indian companies. The curated universe contains 31 mappings, is intentionally limited, and is not statistically representative of the Indian equity market. Fundamentals are shown only where the reduced archive subset contains the relevant company files; unavailable metrics are left unavailable.

The repository also contains `data/ohlc.csv`, a dated Yahoo Finance snapshot with `Date`, `Company`, `Symbol`, `Open`, `High`, `Low`, `Close`, and `Volume`. The loader checks date parsing, numeric conversion, and the logical high/low bounds before a row is plotted.

### 3.3 Data-loading architecture

`data_loader.py` separates source handling from presentation:

1. `load_real_universe()` loads the repository-contained 31-company mapping used by the public dashboard. The legacy `load_company_universe()` path remains available for local archive discovery.
2. `load_company_table()` reshapes wide statements into `metric`, `period`, and `value` columns.
3. `load_ohlc_csv()` validates and filters a long-format OHLC file, including optional company filtering.
4. `load_yfinance_ohlc()` retrieves on-demand Yahoo Finance history for the selected `.NS` ticker; the Streamlit wrapper caches the result for 15 minutes, and the dated bundled snapshot is used when network retrieval fails.
5. Relative paths are resolved from the directory containing `data_loader.py`, rather than from the process working directory. This makes the default `data/financials` path reliable on Streamlit Cloud.

Malformed or missing files produce empty views and user-facing messages instead of modifying source data or silently presenting an invalid success state.

---

## 4. Methodology

The dashboard follows a simple exploratory-analysis workflow:

1. **Load:** Read basic-info files to create the company universe.
2. **Normalize:** Convert wide CSV statement exports into tidy rows. Numeric fields are cleaned of commas, percentage signs, and common missing-value markers.
3. **Filter:** Apply the optional supplied-list filter, sector selection, name search, and minimum market-cap threshold.
4. **Explore:** Use charts and tables to inspect market composition, comparisons, financial trends, and OHLC records.
5. **Allocate illustratively:** Select the first 20 filtered companies and assign equal weights. With the default illustrative portfolio value of ₹100,000, each selected company receives an equal notional allocation. This is a visualization convention, not a recommendation.
6. **Validate:** Display Yahoo Finance history when available, otherwise the dated bundled real snapshot. If neither is available, show an explicit no-data state rather than inventing prices.

Plotly is used for bar charts, scatter plots, pie charts, line charts, and candlesticks. Streamlit caching reduces repeated reads of the same universe and selected statement files. The implementation keeps the source archive read-only and loads detailed tables on demand for the selected company.

---

## 5. Dashboard Design and Interactivity

### 5.1 Market overview

The Market overview tab reports the number of filtered companies, the number of sectors, median market capitalization, and median ROE when values are available. It includes:

- A sector-count bar chart.
- A market-cap-versus-ROE scatter plot with company hover labels.
- A tabular view containing company, sector, exchange identifiers, market cap, current price, ROE, and ROCE.

The sidebar controls are intentionally simple. A student can search for a company, select one or more sectors, and set a minimum market-cap threshold without editing code.

**Figure slot A — Market overview**  
`report_assets/01_market_overview.png`  
*Insert a screenshot showing the KPI row, sector bar chart, scatter plot, and filtered company table. Recommended capture: default curated NSE universe with no restrictive filters.*

### 5.2 Portfolio allocation

The Portfolio allocation tab turns the filtered universe into an illustrative equal-weight view. At most the first 20 filtered companies are used so that the chart remains readable. A donut chart communicates relative weights, while a horizontal bar chart communicates the corresponding notional allocation from the user-entered portfolio value.

This view is a teaching device for allocation arithmetic. It does not account for risk tolerance, liquidity, taxes, transaction costs, concentration limits, or suitability. The UI labels the weights as illustrative and the report preserves that distinction.

**Figure slot B — Portfolio allocation**  
`report_assets/02_portfolio_allocation.png`  
*Insert a screenshot showing the equal-weight donut and illustrative allocation bar chart. Keep the default ₹100,000 value visible if possible.*

### 5.3 Company comparison

The Company comparison tab permits up to five selections and offers a comparison metric such as Market Cap, Current Price, Stock P/E, ROE, ROCE, Sales growth, or Profit growth. A colored horizontal bar chart and a supporting table make the comparison inspectable rather than relying on chart labels alone.

The comparison is descriptive. A higher or lower metric is not automatically interpreted as better because the appropriate interpretation depends on industry, period, accounting definitions, and the user’s question.

**Figure slot C — Company comparison**  
`report_assets/03_company_comparison.png`  
*Insert a screenshot with three or four mapped NSE companies selected and the ROE or Market Cap comparison metric visible.*

### 5.4 Financial health

The Financial health tab combines three sources for the selected company:

- Selected ratio history, including current ratio, debt/equity, ROE, and ROCE when present.
- Profit-and-loss trends for sales, operating profit, and net profit.
- Balance-sheet trends for borrowings, cash and bank, total assets, and total liabilities.

This layout encourages a multi-dimensional reading. For example, a user can inspect profitability together with borrowing and liquidity-related measures instead of viewing a single metric in isolation. The app does not calculate a proprietary health score; it exposes the underlying supplied values where available and leaves missing metrics unavailable.

**Figure slot D — Financial health**  
`report_assets/04_financial_health.png`  
*Insert a screenshot of one selected company with the ratio chart and at least one statement trend visible.*

### 5.5 Price and OHLC

The Price/OHLC tab supports the expected historical CSV schema:

`Date, Open, High, Low, Close`  
Optional fields: `Company`, `Symbol`, `Ticker`, and `Volume`.

The bundled snapshot contains dated OHLC rows for the curated NSE symbols and therefore exercises the real-data path. The app first attempts cached Yahoo Finance history, then filters the bundled snapshot or an external local file to the selected company. If no usable rows are found, it shows an explicit no-data message and does not invent a price path.

The Plotly view supports hover details, legend toggles, zoom/pan, date filtering, range buttons, a range slider, 3/5-period moving averages, and volume when present. Relevant filtered/company tables and displayed OHLC rows can be downloaded as CSV. The captured snapshot has rows for 30 symbols; Tata Motors (`TATAMOTORS.NS`) had no rows and may show no data when live retrieval also fails.

**Figure slot E — Price/OHLC**  
`report_assets/05_price_ohlc.png`  
*Insert a screenshot showing the Yahoo Finance or bundled real-snapshot source message and candlestick chart for one mapped NSE company. If the network is unavailable, retain the dated-snapshot warning in the caption.*

---

## 6. Results and Findings

### 6.1 Verified implementation results

The repository sample produces a usable initial dashboard state:

- **5 company records** load from the reduced archive-derived `data/financials` subset.
- **31 mapped real NSE companies** are available in the curated universe; the default sidebar display limit is 30.
- The default equal-weight portfolio can allocate the illustrative ₹100,000 across the filtered sample.
- Statement files load into tidy metric-period-value tables for the selected company.
- The bundled OHLC snapshot contains one year of validated rows for 30 mapped tickers except any Yahoo symbol with no returned rows.
- Streamlit starts successfully and responds to its health endpoint in local validation.

These are software and data-coverage findings. They demonstrate that the application is deployable and interactive; they do not establish market or investment performance.

### 6.2 Interpretive opportunities

The sample supports classroom questions without pretending to answer them conclusively:

- How does sector composition change when a sector filter is applied?
- How does an equal-weight portfolio differ visually from a market-cap-oriented discussion?
- Which metrics are directly comparable across companies, and which require sector context?
- How do annual profit and balance-sheet trends complement a point-in-time basic-info record?
- What changes in the chart when real OHLC data is available versus when the fallback is used?

The dashboard is particularly useful for demonstrating the difference between **data availability** and **analytical validity**. A chart can render successfully while still being delayed, incomplete, or unsuitable for a financial decision. The explicit source, timestamp, and no-data labels are therefore part of the result, not just interface decoration.

### 6.3 Reproducibility

The application can be reproduced with:

```powershell
python -m pip install -r requirements.txt
streamlit run app.py
```

The public deployment is available at:

<https://financial-market-portfolio-dashboard-igrhbznnwtvxqhokjtfgaq.streamlit.app/>

For local full-archive exploration, enter the supplied archive path in the sidebar. For cloud or repository-only use, retain the default `data/financials` path. The original source files are not required for the public sample.

---

## 7. Limitations and Ethical Considerations

1. **Curated public sample:** The deployed 31-company mapping is real but intentionally limited. It cannot support claims about market-wide sector leadership, diversification quality, or investment performance.
2. **Local archive boundary:** The supplied local archive is external to the repository and may contain a broader or different set of records than the sample. The report does not claim that the public sample represents the full archive.
3. **Yahoo Finance dependency:** The app attempts on-demand Yahoo Finance history through `yfinance`, cached for 15 minutes. Basic-info fields such as price and market capitalization are not guaranteed to be current, and Yahoo Finance may be delayed, incomplete, or unavailable.
4. **OHLC coverage:** The bundled snapshot contains rows for 30 symbols; Tata Motors (`TATAMOTORS.NS`) had no rows in the captured snapshot. Yahoo Finance availability, delays, corporate actions, and completeness can vary. If both sources fail, no chart is shown.
5. **Equal-weight allocation:** The portfolio tab uses an arbitrary equal-weight convention and does not model risk, costs, liquidity, taxes, rebalancing, or investor suitability.
6. **Accounting comparability:** Ratios and statement labels can vary by company, sector, period, and source convention. The app exposes values but does not harmonize every accounting definition.
7. **Missingness:** A missing file or malformed row can reduce the available visual evidence. The app reports empty views, but users should inspect data quality before drawing conclusions.
8. **No predictive model:** The project does not forecast returns, estimate volatility, optimize weights, or issue buy/sell/hold signals.
9. **Privacy and governance:** The private attachment CSV and original local archive are intentionally excluded from GitHub. Any future data addition should be checked for licensing, privacy, size, and reproducibility before publication.

These limitations are appropriate for an academic visualization prototype. A production financial application would require stronger provenance, access controls, data refresh monitoring, testing, audit trails, and domain review.

---

## 8. Conclusion

The Financial Market & Stock Portfolio Tracker demonstrates how a messy collection of company-level CSV exports can be turned into a maintainable exploratory dashboard. The central contribution is not a trading strategy; it is a reproducible interface that links normalized data loading, filtering, comparison, allocation arithmetic, financial-health visuals, and validated OHLC display.

The curated real-company cloud universe ensures that the public application opens with meaningful content while protecting the original archive and private attachment. The local path fallback preserves a route for deeper academic exploration when the full archive is available. Source/timestamp labels, cache behavior, and no-data handling distinguish on-demand Yahoo Finance history from the dated bundled snapshot without implying guaranteed live coverage.

Future academic extensions could add a documented real historical data source, sector-specific normalization, return and volatility calculations, date-range controls, downloadable filtered tables, automated data-quality tests, and a formal evaluation with student users. Those extensions should preserve the current principle: descriptive analytics must be clearly separated from investment advice.

---

## References

1. Streamlit. *Streamlit Documentation*. <https://docs.streamlit.io/>
2. Plotly. *Plotly Python Graphing Library Documentation*. <https://plotly.com/python/>
3. pandas. *pandas User Guide*. <https://pandas.pydata.org/docs/>
4. Python Software Foundation. *Python Documentation*. <https://docs.python.org/3/>
5. GitHub. *GitHub Documentation*. <https://docs.github.com/>
6. Project repository and implementation files: `app.py`, `data_loader.py`, `requirements.txt`, `data/real_universe.csv`, and the reduced archive subset under `data/`.

---

## Screenshot Checklist and Fast Completion Guide

Complete these steps immediately before submission:

1. Open the deployed URL and confirm the app is using the latest `main` revision.
2. Capture the five views listed below at a readable browser width.
3. Save the images with the exact filenames in `report_assets/`.
4. Replace the corresponding image-slot text in this report with Markdown image links, for example:

   ```markdown
   ![Market overview](report_assets/01_market_overview.png)
   ```

5. Keep each caption under the image and preserve the real-source/timestamp labels.
6. Export to PDF using the browser’s **Print → Save as PDF** from a Markdown preview or rendered HTML.
7. Verify that the title page, figures, references, and limitations are present.

| File | Required view | Suggested state |
| --- | --- | --- |
| `01_market_overview.png` | Market overview | Default sample, no restrictive filters |
| `02_portfolio_allocation.png` | Portfolio allocation | ₹100,000 illustrative value |
| `03_company_comparison.png` | Company comparison | Three companies, ROE or Market Cap |
| `04_financial_health.png` | Financial health | 3M India Ltd, ABB India Ltd, ACC Ltd, AAVAS Financiers Ltd, or 5Paisa Capital Ltd |
| `05_price_ohlc.png` | Price/OHLC | Yahoo Finance history or dated bundled real snapshot |

### Dependency-free rendering options

- **VS Code:** Open `report.md` and use Markdown Preview, then print the preview to PDF.
- **GitHub:** Push the report and use GitHub’s rendered Markdown as a quick review.
- **Browser:** Use a Markdown preview extension or a local Markdown viewer, then choose **Print → Save as PDF**.
- **Optional Pandoc:** If Pandoc is already installed on the submission machine, run:

  ```powershell
  pandoc report.md -o report.html --standalone --metadata title="Financial Market & Stock Portfolio Tracker"
  ```

No extra rendering dependency is required by the dashboard itself.
