"""Streamlit entry point for the Financial Market & Stock Portfolio Tracker."""

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

from data_loader import (
    APP_DIR,
    DEFAULT_COMPANY_LIST,
    DEFAULT_DATA_ROOT,
    DEFAULT_OHLC_PATH,
    LOCAL_COMPANY_LIST,
    LOCAL_SOURCE_DATA_ROOT,
    default_data_path,
    load_company_list,
    load_ohlc_csv,
    load_company_table,
    load_company_universe,
    make_illustrative_ohlc,
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
def cached_table(company: str, data_root: str, table_name: str) -> pd.DataFrame:
    return load_company_table(company, data_root, table_name)


def money(value: object) -> str:
    if pd.isna(value):
        return "—"
    return f"₹{float(value):,.2f}"


def metric_value(universe: pd.DataFrame, company: str, field: str) -> float:
    rows = universe.loc[universe["Company"] == company, field]
    return float(rows.iloc[0]) if not rows.empty and pd.notna(rows.iloc[0]) else np.nan


def metric_text(value: object, suffix: str = "", decimals: int = 1) -> str:
    if pd.isna(value):
        return "—"
    return f"{float(value):,.{decimals}f}{suffix}"


def company_value(universe: pd.DataFrame, company: str, field: str) -> object:
    rows = universe.loc[universe["Company"] == company, field]
    return rows.iloc[0] if not rows.empty else np.nan


def latest_metric(table: pd.DataFrame, metric: str) -> float:
    values = table.loc[table["metric"].eq(metric), "value"].dropna()
    return float(values.iloc[-1]) if not values.empty else np.nan


def plot_statement(table: pd.DataFrame, metrics: list[str], title: str) -> None:
    if table.empty:
        st.info("This statement is not available for the selected company.")
        return
    chart = table[table["metric"].isin(metrics)].dropna(subset=["value"]).copy()
    if chart.empty:
        st.info("No numeric values were found for this view.")
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
    "Academic dashboard for exploring the supplied NSE/BSE company dataset. "
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
    ohlc_path = st.text_input(
        "Optional OHLC CSV",
        str(default_data_path(DEFAULT_OHLC_PATH, DEFAULT_OHLC_PATH)),
        help="Long-format CSV with Date, Open, High, Low, Close and optional Company/Symbol.",
    )
    st.divider()
    st.header("Portfolio assumptions")
    starting_value = st.number_input("Illustrative portfolio value (₹)", 1000.0, 1e9, 100000.0, 1000.0)
    st.caption("Portfolio weights below are equal-weight defaults for comparison, not recommendations.")

universe = cached_universe(data_root)
if universe.empty:
    st.error(
        "No company records could be loaded. Check the financials folder path and ensure it "
        "contains company subfolders with *_Basic_Info.csv files."
    )
    st.caption(
        f"Resolved financials path: `{data_root}` · app directory: "
        f"`{APP_DIR}`"
    )
    st.stop()

listed_names = load_company_list(company_list_path)
if listed_names:
    universe["In supplied list"] = universe["Company"].isin(listed_names)
else:
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
    kpi4.metric("Median ROE", f"{filtered['ROE'].median():.1f}%" if filtered["ROE"].notna().any() else "—")
    if filtered.empty:
        st.warning("No companies match the current filters.")
    else:
        sector_counts = filtered["Sector"].value_counts().reset_index()
        sector_counts.columns = ["Sector", "Companies"]
        left, right = st.columns(2)
        with left:
            st.plotly_chart(px.bar(sector_counts.head(15), x="Companies", y="Sector", orientation="h",
                                   title="Companies by sector"), use_container_width=True)
        with right:
            st.plotly_chart(px.scatter(filtered, x="Market Cap", y="ROE", hover_name="Company",
                                       color="Sector", size="Current Price",
                                       title="Market cap vs ROE (descriptive only)"),
                            use_container_width=True)
        st.plotly_chart(
            px.treemap(
                filtered.dropna(subset=["Market Cap"]),
                path=["Sector", "Company"],
                values="Market Cap",
                color="ROE",
                color_continuous_scale="RdYlGn",
                title="Sector market-cap composition (dataset units)",
            ),
            use_container_width=True,
        )
        display_cols = ["Company", "Sector", "NSE", "BSE", "Market Cap", "Current Price", "ROE", "ROCE"]
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
            ("Dividend yield", metric_text(profile.get("Dividend Yield", np.nan), "%")),
            ("NSE", str(profile.get("NSE", "—"))),
            ("BSE", str(profile.get("BSE", "—"))),
        ]
        for index, (label, value) in enumerate(profile_metrics):
            profile_cols[index % 4].metric(label, value)
        st.caption(
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
            st.plotly_chart(px.pie(portfolio, names="Company", values="Weight", hole=0.45,
                                   title=f"Equal weights across first {len(portfolio)} matches"),
                            use_container_width=True)
        with right:
            st.plotly_chart(px.bar(portfolio.sort_values("Illustrative allocation"),
                                   x="Illustrative allocation", y="Company", orientation="h",
                                   title="Illustrative allocation (₹)"),
                            use_container_width=True)
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
        st.plotly_chart(px.bar(compare.sort_values(metric), x=metric, y="Company", color="Sector",
                               orientation="h", title=f"{metric} comparison"),
                        use_container_width=True)
        st.plotly_chart(
            px.scatter(
                compare,
                x="Stock P/E",
                y="ROE",
                size="Market Cap",
                color="Sector",
                hover_name="Company",
                title="Valuation versus profitability (descriptive only)",
                labels={"Stock P/E": "Stock P/E (x)", "ROE": "ROE (%)"},
            ),
            use_container_width=True,
        )
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
    c1, c2 = st.columns(2)
    with c1:
        st.plotly_chart(px.bar(ratios[ratios["metric"].isin(["Current Ratio", "Debt / equity", "ROE", "ROCE"])],
                               x="period", y="value", color="metric", barmode="group",
                               title="Selected ratios") if not ratios.empty else go.Figure(),
                        use_container_width=True)
    with c2:
        plot_statement(profit_loss, ["Sales", "Operating Profit", "Net Profit"], "Profit and loss trend")
    debt_profit = pd.concat(
        [
            balance[balance["metric"].eq("Borrowings")].assign(source="Borrowings"),
            profit_loss[profit_loss["metric"].eq("Net Profit")].assign(source="Net Profit"),
        ],
        ignore_index=True,
    )
    if not debt_profit.empty:
        st.plotly_chart(
            px.bar(
                debt_profit,
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
    price = metric_value(universe, company, "Current Price")
    real_ohlc = load_ohlc_csv(ohlc_path, company)
    schema_error = ohlc_schema_message(ohlc_path)
    if schema_error:
        st.warning(schema_error + " Using the illustrative fallback until it is corrected.")
    if not real_ohlc.empty:
        ohlc = real_ohlc
        st.success(f"Using real OHLC data from `{ohlc_path}` ({len(ohlc):,} rows).")
    else:
        ohlc = make_illustrative_ohlc(price)
        st.info(
            "No usable OHLC rows were found for this company. Showing a clearly labelled "
            "deterministic illustrative path anchored to the dataset's current price."
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
        title=f"{'Historical' if not real_ohlc.empty else 'Illustrative'} OHLC path — {company}",
        xaxis_title="Business date",
        xaxis_rangeslider_visible=False,
        height=650 if has_volume else 520,
    )
    st.plotly_chart(figure, use_container_width=True)
    st.download_button(
        "Download displayed OHLC data (CSV)",
        ohlc.to_csv(index=False).encode("utf-8"),
        f"{company.replace(' ', '_').lower()}_ohlc.csv",
        "text/csv",
    )

st.caption(f"Loaded {len(universe):,} company records. Source files are read-only; no source data is copied or modified.")
