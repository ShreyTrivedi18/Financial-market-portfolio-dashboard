"""Streamlit entry point for the Financial Market & Stock Portfolio Tracker."""

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timezone
import streamlit as st

from data_loader import (
    APP_DIR,
    DEFAULT_COMPANY_LIST,
    DEFAULT_DATA_ROOT,
    DEFAULT_OHLC_PATH,
    DEFAULT_REAL_UNIVERSE,
    LOCAL_COMPANY_LIST,
    LOCAL_SOURCE_DATA_ROOT,
    default_data_path,
    load_company_list,
    load_ohlc_csv,
    load_yfinance_ohlc,
    load_company_table,
    load_company_universe,
    load_real_universe,
    REAL_TICKER_MAP,
    ohlc_schema_message,
)


st.set_page_config(
    page_title="Financial Market & Portfolio Tracker",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)


@st.cache_data(show_spinner=False)
def cached_universe(data_root: str) -> pd.DataFrame:
    return load_company_universe(data_root)


@st.cache_data(show_spinner=False)
def cached_real_universe(path: str, data_root: str) -> pd.DataFrame:
    return load_real_universe(path, data_root)


@st.cache_data(show_spinner=False)
def cached_table(company: str, data_root: str, table_name: str) -> pd.DataFrame:
    return load_company_table(company, data_root, table_name)


@st.cache_data(ttl=900, show_spinner=False)
def cached_yfinance_ohlc(ticker: str) -> pd.DataFrame:
    return load_yfinance_ohlc(ticker)


def money(value: object) -> str:
    if pd.isna(value):
        return "Not available from supplied source"
    return f"₹{float(value):,.2f}"


def metric_value(universe: pd.DataFrame, company: str, field: str) -> float:
    rows = universe.loc[universe["Company"] == company, field]
    return float(rows.iloc[0]) if not rows.empty and pd.notna(rows.iloc[0]) else np.nan


def metric_text(value: object, suffix: str = "", decimals: int = 1) -> str:
    if pd.isna(value):
        return "Not available from supplied source"
    return f"{float(value):,.{decimals}f}{suffix}"


def company_value(universe: pd.DataFrame, company: str, field: str) -> object:
    rows = universe.loc[universe["Company"] == company, field]
    return rows.iloc[0] if not rows.empty else np.nan


def sanitize_numeric_columns(frame: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    """Return a chart-only copy with numeric columns coerced and non-finite values removed."""
    clean = frame.copy()
    for column in columns:
        if column in clean.columns:
            clean[column] = pd.to_numeric(clean[column], errors="coerce")
            clean[column] = clean[column].replace([np.inf, -np.inf], np.nan)
    return clean


def chart_rows(
    frame: pd.DataFrame,
    required_columns: list[str],
    chart_name: str,
    minimum_rows: int = 1,
) -> pd.DataFrame:
    """Keep only finite rows needed by a chart and explain when it cannot be drawn."""
    clean = sanitize_numeric_columns(frame, required_columns)
    if not set(required_columns).issubset(clean.columns):
        st.info(f"{chart_name} is unavailable because required numeric fields are missing.")
        return clean.iloc[0:0]
    clean = clean.dropna(subset=required_columns)
    if len(clean) < minimum_rows:
        st.info(f"{chart_name} needs at least {minimum_rows} valid data row(s) to be shown.")
        return clean.iloc[0:0]
    return clean


def bounded_marker_sizes(values: pd.Series) -> pd.Series:
    """Keep Plotly bubble sizes finite and positive without changing displayed table values."""
    return pd.to_numeric(values, errors="coerce").replace([np.inf, -np.inf], np.nan).clip(1.0, 100.0)


def latest_metric(table: pd.DataFrame, metric: str) -> float:
    values = table.loc[table["metric"].eq(metric), "value"].dropna()
    return float(values.iloc[-1]) if not values.empty else np.nan


def plot_statement(table: pd.DataFrame, metrics: list[str], title: str) -> None:
    if table.empty:
        st.info("This statement is not available for the selected company.")
        return
    chart = chart_rows(
        table[table["metric"].isin(metrics)],
        ["value"],
        title,
    )
    if chart.empty:
        return
    chart["period"] = pd.Categorical(
        chart["period"], categories=list(dict.fromkeys(chart["period"])), ordered=True
    )
    st.plotly_chart(
        px.line(chart, x="period", y="value", color="metric", markers=True, title=title),
        use_container_width=True,
    )


st.title("Financial Market & Stock Portfolio Tracker")
st.caption(
    "Academic dashboard using identifiable Indian NSE companies and Yahoo Finance market data. "
    "It is descriptive only and is not investment advice."
)

with st.sidebar:
    st.header("Data sources")
    data_root = st.text_input(
        "Financials folder",
        str(default_data_path(DEFAULT_DATA_ROOT, LOCAL_SOURCE_DATA_ROOT)),
        help="Use a repository-relative folder on Streamlit Cloud, or paste a local archive path.",
    )
    company_list_path = st.text_input(
        "Optional company list",
        str(default_data_path(DEFAULT_COMPANY_LIST, LOCAL_COMPANY_LIST)),
        help="CSV containing company names; leave the default if unavailable.",
    )
    real_universe_path = st.text_input(
        "Curated NSE universe",
        str(DEFAULT_REAL_UNIVERSE),
        help="Repository-contained real-company mapping; expand this CSV to add tickers.",
    )
    ohlc_path = st.text_input(
        "Optional OHLC CSV",
        str(default_data_path(DEFAULT_OHLC_PATH, DEFAULT_OHLC_PATH)),
        help="Long-format CSV with Date, Open, High, Low, Close and optional Company/Symbol.",
    )
    use_live_data = st.checkbox(
        "Try Yahoo Finance live/historical data",
        value=True,
        help="Uses a cached Yahoo Finance download; bundled real snapshot is used if unavailable.",
    )
    company_limit = st.slider("Companies shown", 5, 50, 30, 5)
    st.divider()
    st.header("Portfolio assumptions")
    starting_value = st.number_input("Illustrative portfolio value (₹)", 1000.0, 1e9, 100000.0, 1000.0)
    st.caption("Portfolio weights below are equal-weight defaults for comparison, not recommendations.")

universe = cached_real_universe(real_universe_path, data_root).head(company_limit).copy()
if universe.empty:
    st.error(
        "No company records could be loaded. Check the financials folder path and ensure it "
        "contains company subfolders with *_Basic_Info.csv files."
    )
    st.caption(
        f"Resolved universe path: `{real_universe_path}` · app directory: "
        f"`{APP_DIR}`"
    )
    st.stop()

# The public view is driven by the curated real NSE mapping. The optional
# company-list input remains available for local workflows but never hides
# mapped real companies in the cloud view.
universe["In supplied list"] = True

with st.sidebar:
    sectors = sorted(value for value in universe["Sector"].dropna().unique() if value)
    chosen_sectors = st.multiselect("Sector", sectors)
    search = st.text_input("Search company", placeholder="e.g. Reliance")
    min_market_cap = st.number_input("Minimum market cap (dataset units)", min_value=0.0, value=0.0)

filtered = universe[universe["In supplied list"]].copy()
if chosen_sectors:
    filtered = filtered[filtered["Sector"].isin(chosen_sectors)]
if search:
    filtered = filtered[filtered["Company"].str.contains(search, case=False, na=False)]
filtered = filtered[filtered["Market Cap"].fillna(0) >= min_market_cap]

tab_overview, tab_portfolio, tab_compare, tab_health, tab_price = st.tabs(
    ["Market overview", "Portfolio allocation", "Company comparison", "Financial health", "Price view"]
)

with tab_overview:
    st.subheader("Filtered market universe")
    kpi1, kpi2, kpi3, kpi4 = st.columns(4)
    kpi1.metric("Companies", f"{len(filtered):,}")
    kpi2.metric("Sectors", f"{filtered['Sector'].nunique():,}")
    kpi3.metric("Median market cap", money(filtered["Market Cap"].median()))
    kpi4.metric("Median ROE", f"{filtered['ROE'].median():.1f}%" if filtered["ROE"].notna().any() else "Not available from supplied source")
    if filtered.empty:
        st.warning("No companies match the current filters.")
    else:
        archive_matches = int((universe["Fundamentals source"] == "Supplied archive").sum())
        st.caption(
            f"Two-tier sources: prices use Yahoo Finance with the bundled snapshot fallback; "
            f"fundamentals use the supplied archive. Archive fundamentals matched for "
            f"{archive_matches}/{len(universe)} mapped companies."
        )
        sector_counts = filtered["Sector"].value_counts().reset_index()
        sector_counts.columns = ["Sector", "Companies"]
        left, right = st.columns(2)
        with left:
            sector_chart = chart_rows(sector_counts.head(15), ["Companies"], "Companies by sector")
            if not sector_chart.empty:
                st.plotly_chart(px.bar(sector_chart, x="Companies", y="Sector", orientation="h",
                                       title="Companies by sector"), use_container_width=True)
        with right:
            overview_scatter = chart_rows(
                filtered, ["Market Cap", "ROE", "Current Price"],
                "Market cap vs ROE", minimum_rows=2,
            )
            if not overview_scatter.empty:
                overview_scatter["Marker Size"] = bounded_marker_sizes(
                    overview_scatter["Current Price"]
                )
                st.plotly_chart(px.scatter(
                    overview_scatter, x="Market Cap", y="ROE", hover_name="Company",
                    color="Sector", size="Marker Size",
                    title="Market cap vs ROE (descriptive only)",
                ), use_container_width=True)
        treemap_data = chart_rows(
            filtered, ["Market Cap", "ROE"], "Sector market-cap composition"
        )
        if not treemap_data.empty:
            st.plotly_chart(
                px.treemap(
                    treemap_data,
                    path=["Sector", "Company"],
                    values="Market Cap",
                    color="ROE",
                    color_continuous_scale="RdYlGn",
                    title="Sector market-cap composition (dataset units)",
                ),
                use_container_width=True,
            )
        display_cols = [
            "Company", "Sector", "NSE", "BSE", "Yahoo Symbol", "Market Cap",
            "Current Price", "ROE", "ROCE", "Fundamentals source",
            "Fundamentals coverage", "Fundamentals files",
        ]
        overview_table = filtered[[c for c in display_cols if c in filtered.columns]].head(100)
        st.dataframe(overview_table, use_container_width=True, hide_index=True)
        st.download_button(
            "Download filtered companies (CSV)",
            overview_table.to_csv(index=False).encode("utf-8"),
            "filtered_companies.csv",
            "text/csv",
        )
        st.markdown("#### Company profile")
        profile_company = st.selectbox(
            "Select a company for key metrics", filtered["Company"].tolist(), key="profile_company"
        )
        profile = filtered.loc[filtered["Company"].eq(profile_company)].iloc[0]
        profile_cols = st.columns(4)
        profile_metrics = [
            ("Current price", money(profile.get("Current Price", np.nan))),
            ("Market cap", money(profile.get("Market Cap", np.nan))),
            ("Stock P/E", metric_text(profile.get("Stock P/E", np.nan), "x")),
            ("Price / sales", metric_text(profile.get("Price to Sales", np.nan), "x")),
            ("ROE", metric_text(profile.get("ROE", np.nan), "%")),
            ("ROCE", metric_text(profile.get("ROCE", np.nan), "%")),
            ("Sales growth", metric_text(profile.get("Sales growth", np.nan), "%")),
            ("Profit growth", metric_text(profile.get("Profit growth", np.nan), "%")),
            ("Debt", money(profile.get("Debt", np.nan))),
            ("Debt / equity", metric_text(profile.get("Debt / equity", np.nan), "x")),
            ("Profit margin", metric_text(profile.get("Profit margin", np.nan), "%")),
            ("Dividend yield", metric_text(profile.get("Dividend Yield", np.nan), "%")),
            ("NSE", str(profile.get("NSE", "—"))),
            ("BSE", str(profile.get("BSE", "—"))),
            ("Yahoo symbol", REAL_TICKER_MAP.get(profile_company, "—")),
        ]
        for index, (label, value) in enumerate(profile_metrics):
            profile_cols[index % 4].metric(label, value)
        available_count = sum(
            pd.notna(profile.get(field, np.nan))
            for field in (
                "Market Cap", "Current Price", "Stock P/E", "Price to Sales", "ROE",
                "ROCE", "Sales growth", "Profit growth", "Debt", "Dividend Yield",
                "Profit margin", "Debt / equity",
            )
        )
        st.info(
            f"Fundamentals coverage: {available_count}/12 profile metrics. "
            f"Source: {profile.get('Fundamentals source', 'Not available')}. "
            f"Files: {profile.get('Fundamentals files', 0)}/4 expected. "
            f"{profile.get('Fundamentals freshness', '')}"
        )
        st.caption(
            f"Price source: Yahoo Finance ({profile.get('Yahoo Symbol', '—')}) with bundled snapshot fallback · "
            f"Sector: {profile.get('Sector', 'Unknown')} · profile values are descriptive "
            "dataset fields, not recommendations."
        )

with tab_portfolio:
    st.subheader("Illustrative equal-weight portfolio")
    if filtered.empty:
        st.info("Apply less restrictive filters to create a portfolio view.")
    else:
        portfolio = filtered.head(20).copy()
        portfolio["Weight"] = 1 / len(portfolio)
        portfolio["Illustrative allocation"] = portfolio["Weight"] * starting_value
        left, right = st.columns([1, 1])
        with left:
            portfolio_pie = chart_rows(portfolio, ["Weight"], "Portfolio allocation")
            if not portfolio_pie.empty:
                st.plotly_chart(px.pie(
                    portfolio_pie, names="Company", values="Weight", hole=0.45,
                    title=f"Equal weights across first {len(portfolio)} matches",
                ), use_container_width=True)
        with right:
            portfolio_bar = chart_rows(
                portfolio, ["Illustrative allocation"], "Illustrative allocation"
            )
            if not portfolio_bar.empty:
                st.plotly_chart(px.bar(
                    portfolio_bar.sort_values("Illustrative allocation"),
                    x="Illustrative allocation", y="Company", orientation="h",
                    title="Illustrative allocation (₹)",
                ), use_container_width=True)
        st.dataframe(portfolio[["Company", "Sector", "Weight", "Illustrative allocation"]],
                     use_container_width=True, hide_index=True)
        st.download_button(
            "Download illustrative portfolio (CSV)",
            portfolio[["Company", "Sector", "Weight", "Illustrative allocation"]].to_csv(index=False).encode("utf-8"),
            "illustrative_portfolio.csv",
            "text/csv",
        )

with tab_compare:
    st.subheader("Compare companies")
    names = filtered["Company"].tolist()
    selected = st.multiselect("Select up to five companies", names, default=names[:3], max_selections=5)
    if selected:
        compare = filtered[filtered["Company"].isin(selected)].copy()
        metric_options = ["Market Cap", "Current Price", "Stock P/E", "ROE", "ROCE", "Sales growth", "Profit growth"]
        metric = st.selectbox("Comparison metric", [m for m in metric_options if m in compare.columns])
        comparison_bar = chart_rows(compare, [metric], f"{metric} comparison")
        if not comparison_bar.empty:
            st.plotly_chart(px.bar(
                comparison_bar.sort_values(metric), x=metric, y="Company", color="Sector",
                orientation="h", title=f"{metric} comparison",
            ), use_container_width=True)
        comparison_scatter = chart_rows(
            compare, ["Stock P/E", "ROE", "Market Cap"],
            "Valuation versus profitability", minimum_rows=2,
        )
        if not comparison_scatter.empty:
            comparison_scatter["Marker Size"] = bounded_marker_sizes(
                comparison_scatter["Market Cap"]
            )
            st.plotly_chart(px.scatter(
                comparison_scatter, x="Stock P/E", y="ROE", size="Marker Size",
                color="Sector", hover_name="Company",
                title="Valuation versus profitability (descriptive only)",
                labels={"Stock P/E": "Stock P/E (x)", "ROE": "ROE (%)"},
            ), use_container_width=True)
        st.dataframe(compare[["Company", "Sector"] + [m for m in metric_options if m in compare.columns]],
                     use_container_width=True, hide_index=True)
        st.download_button(
            "Download comparison (CSV)",
            compare[["Company", "Sector"] + [m for m in metric_options if m in compare.columns]]
            .to_csv(index=False)
            .encode("utf-8"),
            "company_comparison.csv",
            "text/csv",
        )
    else:
        st.info("Select at least one company.")

with tab_health:
    st.subheader("Financial health visuals")
    company = st.selectbox("Company", filtered["Company"].tolist() or universe["Company"].tolist(), key="health_company")
    ratios = cached_table(company, data_root, "Ratios.csv")
    profit_loss = cached_table(company, data_root, "Yearly_Profit_Loss.csv")
    balance = cached_table(company, data_root, "Yearly_Balance_Sheet.csv")
    health_cards = st.columns(4)
    health_cards[0].metric("Latest ROE", metric_text(latest_metric(ratios, "ROE"), "%"))
    health_cards[1].metric("Latest ROCE", metric_text(latest_metric(ratios, "ROCE"), "%"))
    health_cards[2].metric("Current ratio", metric_text(latest_metric(ratios, "Current Ratio"), "x"))
    health_cards[3].metric("Debt / equity", metric_text(latest_metric(ratios, "Debt / equity"), "x"))
    health_profile = universe.loc[universe["Company"].eq(company)].iloc[0]
    st.caption(
        f"Fundamentals source: {health_profile.get('Fundamentals source', 'Not available')} · "
        f"coverage: {health_profile.get('Fundamentals coverage', '0/0 metrics')} · "
        f"files: {health_profile.get('Fundamentals files', 0)}/4 expected · "
        f"{health_profile.get('Fundamentals freshness', '')}"
    )
    if ratios.empty and profit_loss.empty and balance.empty:
        st.info(
            "No supplied-archive fundamentals are available for this company. "
            "Price/OHLC data remains available independently from Yahoo Finance or the bundled snapshot."
        )
    c1, c2 = st.columns(2)
    with c1:
        ratio_chart = chart_rows(
            ratios[ratios["metric"].isin(["Current Ratio", "Debt / equity", "ROE", "ROCE"])],
            ["value"], "Selected ratios",
        )
        if not ratio_chart.empty:
            st.plotly_chart(px.bar(
                ratio_chart, x="period", y="value", color="metric", barmode="group",
                title="Selected ratios",
            ), use_container_width=True)
    with c2:
        plot_statement(profit_loss, ["Sales", "Operating Profit", "Net Profit"], "Profit and loss trend")
    debt_profit = pd.concat(
        [
            balance[balance["metric"].eq("Borrowings")].assign(source="Borrowings"),
            profit_loss[profit_loss["metric"].eq("Net Profit")].assign(source="Net Profit"),
        ],
        ignore_index=True,
    )
    debt_profit_chart = chart_rows(debt_profit, ["value"], "Borrowings and net profit")
    if not debt_profit_chart.empty:
        st.plotly_chart(
            px.bar(
                debt_profit_chart,
                x="period",
                y="value",
                color="source",
                barmode="group",
                title="Borrowings and net profit (statement units)",
            ),
            use_container_width=True,
        )
    plot_statement(balance, ["Borrowings", "Cash & Bank", "Total Assets", "Total Liabilities"],
                   "Balance-sheet trend")
    st.download_button(
        "Download selected financial tables (CSV)",
        pd.concat(
            [
                ratios.assign(statement="Ratios"),
                profit_loss.assign(statement="Yearly_Profit_Loss"),
                balance.assign(statement="Yearly_Balance_Sheet"),
            ],
            ignore_index=True,
        ).to_csv(index=False).encode("utf-8"),
        "financial_health_tables.csv",
        "text/csv",
    )

with tab_price:
    st.subheader("Price / OHLC view")
    company = st.selectbox("Company", filtered["Company"].tolist() or universe["Company"].tolist(), key="price_company")
    ticker = REAL_TICKER_MAP.get(company)
    if use_live_data and ticker:
        with st.spinner(f"Loading cached Yahoo Finance history for {ticker}..."):
            live_ohlc = cached_yfinance_ohlc(ticker)
    else:
        live_ohlc = pd.DataFrame()
    snapshot_ohlc = load_ohlc_csv(ohlc_path, company)
    schema_error = ohlc_schema_message(ohlc_path)
    if schema_error:
        st.warning(schema_error + " Trying Yahoo Finance, then the bundled real snapshot.")
    if not live_ohlc.empty:
        ohlc = live_ohlc
        source_label = f"Yahoo Finance ({ticker})"
        st.success(
            f"Using cached Yahoo Finance data for `{ticker}` ({len(ohlc):,} rows). "
            f"Retrieved {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}."
        )
    elif not snapshot_ohlc.empty:
        ohlc = snapshot_ohlc
        source_label = f"Bundled real snapshot ({ticker or 'mapped symbol unavailable'})"
        st.warning(
            f"Yahoo Finance data was unavailable. Using the bundled real snapshot from "
            f"`{ohlc_path}` ({len(ohlc):,} rows); coverage ends {ohlc['Date'].max().date()}."
        )
    else:
        ohlc = pd.DataFrame()
        source_label = "No real OHLC data"
        st.info(
            "No real OHLC rows are available for this company. Add a valid OHLC CSV or "
            "restore network access; no synthetic price path is shown in v3."
        )
    ohlc = chart_rows(
        ohlc,
        ["Open", "High", "Low", "Close"],
        "Historical OHLC chart",
    )
    if ohlc.empty:
        st.stop()
    ohlc = ohlc.sort_values("Date").copy()
    if "Volume" in ohlc.columns:
        ohlc["Volume"] = pd.to_numeric(ohlc["Volume"], errors="coerce")
        ohlc["Volume"] = ohlc["Volume"].replace([np.inf, -np.inf], np.nan)
        if ohlc["Volume"].notna().any():
            ohlc = ohlc.dropna(subset=["Volume"]).copy()
    st.caption(
        f"Data source: {source_label}. Historical observations are not forecasts or investment advice."
    )
    if len(ohlc) > 1:
        min_date = ohlc["Date"].min().date()
        max_date = ohlc["Date"].max().date()
        date_range = st.date_input(
            "Date range",
            value=(min_date, max_date),
            min_value=min_date,
            max_value=max_date,
            key="ohlc_date_range",
        )
        if isinstance(date_range, tuple) and len(date_range) == 2:
            ohlc = ohlc[
                ohlc["Date"].dt.date.between(date_range[0], date_range[1])
            ].copy()
    for window in (3, 5):
        ohlc[f"MA{window}"] = ohlc["Close"].rolling(window, min_periods=1).mean()
    has_volume = "Volume" in ohlc.columns and ohlc["Volume"].notna().any()
    rows = 2 if has_volume else 1
    figure = make_subplots(
        rows=rows,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.06,
        row_heights=[0.72, 0.28] if has_volume else [1],
    )
    figure.add_trace(
        go.Candlestick(
            x=ohlc["Date"], open=ohlc["Open"], high=ohlc["High"],
            low=ohlc["Low"], close=ohlc["Close"], name="OHLC"
        ),
        row=1,
        col=1,
    )
    for window, color in ((3, "#1f77b4"), (5, "#ff7f0e")):
        figure.add_trace(
            go.Scatter(x=ohlc["Date"], y=ohlc[f"MA{window}"], mode="lines",
                       name=f"{window}-period MA", line={"color": color}),
            row=1,
            col=1,
        )
    if has_volume:
        figure.add_trace(
            go.Bar(x=ohlc["Date"], y=ohlc["Volume"], name="Volume", marker_color="#9aa5b1"),
            row=2,
            col=1,
        )
        figure.update_yaxes(title_text="Volume", row=2, col=1)
    figure.update_yaxes(title_text="Price (₹)", row=1, col=1)
    figure.update_layout(
        title=f"Historical OHLC path — {company}",
        xaxis_title="Business date",
        xaxis_rangeslider_visible=True,
        height=650 if has_volume else 520,
    )
    figure.update_xaxes(
        rangeselector={
            "buttons": [
                {"count": 1, "label": "1m", "step": "month", "stepmode": "backward"},
                {"count": 3, "label": "3m", "step": "month", "stepmode": "backward"},
                {"count": 6, "label": "6m", "step": "month", "stepmode": "backward"},
                {"step": "all", "label": "All"},
            ]
        },
        row=1,
        col=1,
    )
    st.plotly_chart(figure, use_container_width=True)
    st.download_button(
        "Download displayed OHLC data (CSV)",
        ohlc.to_csv(index=False).encode("utf-8"),
        f"{company.replace(' ', '_').lower()}_ohlc.csv",
        "text/csv",
    )

st.caption(f"Loaded {len(universe):,} company records. Source files are read-only; no source data is copied or modified.")
