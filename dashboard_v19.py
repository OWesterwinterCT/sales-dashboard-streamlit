import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np



import streamlit as st
import hashlib

# ---------------------------
# Simple user database
# ---------------------------
USERS = {
    "alice": hashlib.sha256("password1".encode()).hexdigest(),
    "bob": hashlib.sha256("password2".encode()).hexdigest(),
}

# ---------------------------
# Auth functions
# ---------------------------
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def check_login(username, password):
    return USERS.get(username) == hash_password(password)

def login_ui():
    st.title("🔐 Login")

    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        if check_login(username, password):
            st.session_state["authenticated"] = True
            st.session_state["user"] = username
        else:
            st.error("Invalid username or password")

# ---------------------------
# Gate the app
# ---------------------------
if "authenticated" not in st.session_state:
    login_ui()
    st.stop()



st.set_page_config(layout="wide")

# ---------------------------------------------------
# KPI styling
# ---------------------------------------------------

st.markdown("""
<style>
[data-testid="stMetricValue"] {
    font-size: 20px;
}
[data-testid="stMetricLabel"] {
    font-size: 14px;
}
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------
# Load data
# ---------------------------------------------------

@st.cache_data
def load_orders():

    df = pd.read_csv("orders.csv")

    df["OrderDate"] = pd.to_datetime(df["OrderDate"], utc=True)
    df["OrderDate"] = df["OrderDate"].dt.tz_localize(None)

    df["Month"] = df["OrderDate"].dt.to_period("M").dt.to_timestamp()
    df["Week"] = df["OrderDate"].dt.to_period("W").dt.to_timestamp()

    return df

@st.cache_data
def load_customers():
    df = pd.read_csv("customers.csv")
    return df

customers_df = load_customers()

@st.cache_data
def load_receipts():

    df = pd.read_csv("receipts.csv")

    df["ReceiptDate"] = pd.to_datetime(df["ReceiptDate"], utc=True)
    df["ReceiptDate"] = df["ReceiptDate"].dt.tz_localize(None)

    df["Month"] = df["ReceiptDate"].dt.to_period("M").dt.to_timestamp()
    df["Week"] = df["ReceiptDate"].dt.to_period("W").dt.to_timestamp()

    return df


orders_df = load_orders()
receipts_df = load_receipts()

customers_df = customers_df[
    customers_df["CustomerName"].isin(orders_df["CustomerName"].unique())
]

state_counts = (
    customers_df.groupby("State")["CustomerName"]
    .count()
    .reset_index(name="Customers")
)

# ---------------------------------------------------
# Sidebar filters
# ---------------------------------------------------

st.sidebar.title("Filters")

date_range = st.sidebar.date_input(
    "Date range",
    [
        orders_df["OrderDate"].min(),
        orders_df["OrderDate"].max()
    ]
)

orders_df = orders_df[
    (orders_df["OrderDate"] >= pd.to_datetime(date_range[0])) &
    (orders_df["OrderDate"] <= pd.to_datetime(date_range[1]))
]

division_filter = st.sidebar.multiselect(
    "Division",
    sorted(orders_df["Division"].dropna().unique())
)

if division_filter:
    orders_df = orders_df[orders_df["Division"].isin(division_filter)]

customer_filter = st.sidebar.multiselect(
    "Customer",
    sorted(orders_df["CustomerName"].dropna().unique())
)

if customer_filter:
    orders_df = orders_df[orders_df["CustomerName"].isin(customer_filter)]

time_unit = st.sidebar.radio("Aggregation", ["Month", "Week"])

zoom_option = st.sidebar.selectbox(
    "Date Zoom",
    ["Full Range", "Last 12 Months", "Last 26 Weeks"]
)

latest_date = orders_df["OrderDate"].max()

if zoom_option == "Last 12 Months":
    orders_df = orders_df[
        orders_df["OrderDate"] >= latest_date - pd.DateOffset(months=12)
    ]

if zoom_option == "Last 26 Weeks":
    orders_df = orders_df[
        orders_df["OrderDate"] >= latest_date - pd.DateOffset(weeks=26)
    ]

time_col = "Month" if time_unit == "Month" else "Week"

if st.sidebar.button("Logout"):
    st.session_state.clear()
    st.rerun()

# ---------------------------------------------------
# Tabs
# ---------------------------------------------------

sales_tab, purchase_tab, profit_tab = st.tabs(
    ["Sales Dashboard", "Purchasing Dashboard", "Profitability Dashboard"]
)

# ===================================================
# SALES DASHBOARD
# ===================================================

with sales_tab:

    # ---------------------------------------------------
    # Aggregations
    # ---------------------------------------------------

    revenue_ts = (
        orders_df.groupby(time_col)["Amount"]
        .sum()
        .reset_index()
        .sort_values(time_col)
    )

    orders_ts = (
        orders_df.groupby(time_col)["OrderNumber"]
        .nunique()
        .reset_index()
        .sort_values(time_col)
    )

    monthly_sales = (
        orders_df.groupby("Month")["Amount"]
        .sum()
        .reset_index()
    )

    weekly_sales = (
        orders_df.groupby("Week")["Amount"]
        .sum()
        .reset_index()
    )

    # ---------------------------------------------------
    # KPI calculations
    # ---------------------------------------------------

    total_revenue = orders_df["Amount"].sum()
    n_orders = orders_df["OrderNumber"].nunique()

    unique_customers = orders_df["CustomerName"].nunique()

    avg_revenue_per_order = orders_df["Amount"].mean()

    avg_monthly_revenue = monthly_sales["Amount"].mean()
    avg_weekly_revenue = weekly_sales["Amount"].mean()

    monthly_change = monthly_sales["Amount"].pct_change().iloc[-1] * 100
    weekly_change = weekly_sales["Amount"].pct_change().iloc[-1] * 100

    # ---------------------------------------------------
    # Dashboard header
    # ---------------------------------------------------

    st.title("📊 Sales Dashboard")

    col1, col2, col3, col4, col5, col6 = st.columns(6)
    
    col1.metric("Total Revenue", f"${total_revenue:,.0f}")
    col2.metric("Orders", f"{n_orders:,}")
    col3.metric("Customers", f"{unique_customers:,}")

    col4.metric(
       "Avg Monthly Revenue",
       f"${avg_monthly_revenue:,.0f}",
       f"{monthly_change:+.1f}%"
    )

    col5.metric(
       "Avg Weekly Revenue",
       f"${avg_weekly_revenue:,.0f}",
       f"{weekly_change:+.1f}%"
    )

    col6.metric(
       "Avg Revenue per Order",
       f"${avg_revenue_per_order:,.0f}"
    )    

    st.divider()

    # ---------------------------------------------------
    # Revenue over time
    # ---------------------------------------------------

    fig = px.line(
        revenue_ts,
        x=time_col,
        y="Amount",
        markers=True,
        title=f"Revenue Over Time ({time_unit})"
    )

    st.plotly_chart(fig, width="stretch")

    # ---------------------------------------------------
    # Period summary table
    # ---------------------------------------------------

    st.subheader(f"{time_unit} Summary")

    summary_table = (
        orders_df.groupby(time_col)
        .agg(
            Orders=("OrderNumber", "nunique"),
            Revenue=("Amount", "sum")
        )
        .reset_index()
        .sort_values(time_col)
    )

    summary_table["Revenue"] = summary_table["Revenue"].map("${:,.0f}".format)

    st.dataframe(summary_table, use_container_width=True)

    # ---------------------------------------------------
    # Top customers
    # ---------------------------------------------------

    col1, col2 = st.columns(2)

    TOP_N = 10

    customer_rev = (
        orders_df.groupby("CustomerName")["Amount"]
        .sum()
        .reset_index()
        .sort_values("Amount", ascending=False)
    )

    fig_top = px.bar(
        customer_rev.head(TOP_N),
        x="Amount",
        y="CustomerName",
        orientation="h",
        title="Top Customers"
    )

    col1.plotly_chart(fig_top, width="stretch")

    # ---------------------------------------------------
    # Customer State Distribution
    # ---------------------------------------------------

    st.subheader("Customer Distribution by State")

    fig_states = px.pie(
        state_counts,
        names="State",
        values="Customers",
        title="Customers by State"
    )

    st.plotly_chart(fig_states, width="stretch")


    # ---------------------------------------------------
    # Order status
    # ---------------------------------------------------

    status_counts = (
        orders_df.groupby("OrderStatus")["OrderNumber"]
        .count()
        .reset_index()
    )

    fig_status = px.pie(
        status_counts,
        names="OrderStatus",
        values="OrderNumber",
        title="Order Status Breakdown"
    )

    col2.plotly_chart(fig_status, width="stretch")

    # ---------------------------------------------------
    # Pareto chart
    # ---------------------------------------------------

    st.subheader("Customer Revenue Pareto")

    pareto = (
        orders_df.groupby("CustomerName")["Amount"]
        .sum()
        .sort_values(ascending=False)
        .reset_index()
    )

    pareto["CumRevenue"] = pareto["Amount"].cumsum()
    pareto["CumShare"] = pareto["CumRevenue"] / pareto["Amount"].sum()

    fig_pareto = px.bar(
        pareto.head(20),
        x="CustomerName",
        y="Amount"
    )

    fig_pareto.add_scatter(
        x=pareto.head(20)["CustomerName"],
        y=pareto.head(20)["CumShare"],
        mode="lines+markers",
        name="Cumulative %",
        yaxis="y2"
    )

    fig_pareto.update_layout(
        yaxis2=dict(
            overlaying="y",
            side="right",
            tickformat=".0%"
        )
    )

    st.plotly_chart(fig_pareto, width="stretch")

    # ---------------------------------------------------
    # Revenue by Division
    # ---------------------------------------------------

    st.subheader("Revenue by Division")

    division_rev = (
        orders_df.groupby("Division")["Amount"]
        .sum()
        .reset_index()
        .sort_values("Amount", ascending=False)
    )

    fig_div = px.bar(
        division_rev,
        x="Division",
        y="Amount"
    )

    st.plotly_chart(fig_div, width="stretch")

    # ---------------------------------------------------
    # Sales Agent Analytics
    # ---------------------------------------------------

    st.subheader("Sales Agent Performance")

    agent_table = (
        orders_df.groupby("SalesAgent")
        .agg(
            Revenue=("Amount", "sum"),
            Orders=("OrderNumber", "nunique")
        )
        .reset_index()
    )

    agent_table["AvgDeal"] = agent_table["Revenue"] / agent_table["Orders"]

    agent_table = agent_table.sort_values("AvgDeal", ascending=False)

    median_rev = agent_table["Revenue"].median()

    agent_table["Performance"] = np.where(
        agent_table["Revenue"] >= median_rev,
        "Top Performer",
        "Underperformer"
    )

    display_table = agent_table.copy()

    display_table["Revenue"] = display_table["Revenue"].map("${:,.0f}".format)
    display_table["AvgDeal"] = display_table["AvgDeal"].map("${:,.0f}".format)

    st.dataframe(display_table, use_container_width=True)

    fig_agents = px.scatter(
        agent_table,
        x="Orders",
        y="Revenue",
        size="AvgDeal",
        color="Performance",
        hover_name="SalesAgent",
        title="Sales Agent Performance"
    )

    st.plotly_chart(fig_agents, width="stretch")

    # ---------------------------------------------------
    # Revenue Forecast
    # ---------------------------------------------------

    st.subheader("Revenue Forecast")

    forecast_df = revenue_ts.copy()
    forecast_df["t"] = range(len(forecast_df))

    coef = np.polyfit(forecast_df["t"], forecast_df["Amount"], 1)
    trend = np.poly1d(coef)

    future_periods = 6
    future_t = np.arange(len(forecast_df), len(forecast_df) + future_periods)

    freq = "MS" if time_unit == "Month" else "W"

    future_dates = pd.date_range(
        start=forecast_df[time_col].max(),
        periods=future_periods + 1,
        freq=freq
    )[1:]

    future_values = trend(future_t)

    future_df = pd.DataFrame({
        time_col: future_dates,
        "Forecast": future_values
    })

    fig_forecast = px.line(
        forecast_df,
        x=time_col,
        y="Amount",
        title=f"Revenue Forecast ({time_unit})"
    )

    fig_forecast.add_scatter(
        x=future_df[time_col],
        y=future_df["Forecast"],
        mode="lines+markers",
        name="Forecast"
    )

    st.plotly_chart(fig_forecast, width="stretch")

    # ---------------------------------------------------
    # Order Forecast
    # ---------------------------------------------------

    st.subheader("Order Forecast")

    orders_forecast = orders_ts.copy()
    orders_forecast["t"] = range(len(orders_forecast))

    coef_o = np.polyfit(orders_forecast["t"], orders_forecast["OrderNumber"], 1)
    trend_o = np.poly1d(coef_o)

    future_orders = trend_o(future_t)

    future_orders_df = pd.DataFrame({
        time_col: future_dates,
        "ForecastOrders": future_orders
    })

    fig_orders = px.line(
        orders_forecast,
        x=time_col,
        y="OrderNumber",
        title=f"Order Forecast ({time_unit})"
    )

    fig_orders.add_scatter(
        x=future_orders_df[time_col],
        y=future_orders_df["ForecastOrders"],
        mode="lines+markers",
        name="Forecast"
    )

    st.plotly_chart(fig_orders, width="stretch")

# ===================================================
# PURCHASING DASHBOARD
# ===================================================

with purchase_tab:

    st.title("📦 Purchasing Dashboard")

    purchases_ts = (
        receipts_df.groupby(time_col)
        .agg(
            PurchaseOrders=("PurchaseOrderNumber", "nunique"),
            Cost=("ReceiptCost", "sum")
        )
        .reset_index()
        .sort_values(time_col)
    )

    total_pos = receipts_df["PurchaseOrderNumber"].nunique()
    total_cost = receipts_df["ReceiptCost"].sum()

    avg_cost_po = total_cost / total_pos

    avg_monthly_cost = receipts_df.groupby("Month")["ReceiptCost"].sum().mean()
    avg_weekly_cost = receipts_df.groupby("Week")["ReceiptCost"].sum().mean()

    col1, col2, col3, col4, col5 = st.columns(5)

    col1.metric("Total Purchase Orders", f"{total_pos:,}")
    col2.metric("Total Cost", f"${total_cost:,.0f}")
    col3.metric("Avg Cost per Purchase Order", f"${avg_cost_po:,.0f}")
    col4.metric("Avg Monthly Cost", f"${avg_monthly_cost:,.0f}")
    col5.metric("Avg Weekly Cost", f"${avg_weekly_cost:,.0f}")

    st.divider()

    fig_cost = px.line(
        purchases_ts,
        x=time_col,
        y="Cost",
        markers=True,
        title=f"Procurement Cost Over Time ({time_unit})"
    )

    st.plotly_chart(fig_cost, width="stretch")

    st.subheader("Purchasing Summary")

    display = purchases_ts.copy()
    display["Cost"] = display["Cost"].map("${:,.0f}".format)

    st.dataframe(display, use_container_width=True)

    st.subheader("Vendor Analysis")

    TOP_N = 10

    vendor_cost = (
    receipts_df.groupby("SupplierNumber")["ReceiptCost"]
    .sum()
    .reset_index()
    .sort_values("ReceiptCost", ascending=False)
    )

    # treat vendor number as categorical
    vendor_cost["SupplierNumber"] = vendor_cost["SupplierNumber"].astype(str)

    fig_vendor = px.bar(
    vendor_cost.head(TOP_N),
    x="ReceiptCost",
    y="SupplierNumber",
    orientation="h",
    category_orders={
        "SupplierNumber": vendor_cost.head(TOP_N)["SupplierNumber"].tolist()
    },
    title="Top Vendors"
    )

    fig_vendor.update_yaxes(type="category")

    st.plotly_chart(fig_vendor, width="stretch")

    # ---------------------------------------------------
    # Cost Forecast
    # ---------------------------------------------------

    st.subheader("Cost Forecast")

    forecast_df = purchases_ts.copy()
    forecast_df["t"] = range(len(forecast_df))

    # linear trend model
    coef = np.polyfit(forecast_df["t"], forecast_df["Cost"], 1)
    trend = np.poly1d(coef)

    future_periods = 6
    future_t = np.arange(len(forecast_df), len(forecast_df) + future_periods)

    freq = "MS" if time_unit == "Month" else "W"

    future_dates = pd.date_range(
        start=forecast_df[time_col].max(),
        periods=future_periods + 1,
       freq=freq
    )[1:]

    future_values = trend(future_t)

    future_df = pd.DataFrame({
       time_col: future_dates,
       "Forecast": future_values
    })

    fig_forecast = px.line(
    forecast_df,
    x=time_col,
    y="Cost",
    title=f"Cost Forecast ({time_unit})"
    )

    fig_forecast.add_scatter(
    x=future_df[time_col],
    y=future_df["Forecast"],
    mode="lines+markers",
    name="Forecast"
    )

    st.plotly_chart(fig_forecast, width="stretch")


# ===================================================
# PROFITABILITY DASHBOARD
# ===================================================

with profit_tab:

    st.title("💰 Profitability Dashboard")

    # ---------------------------------------------------
    # Combine revenue and cost
    # ---------------------------------------------------

    revenue_ts = (
        orders_df.groupby(time_col)["Amount"]
        .sum()
        .reset_index()
    )

    cost_ts = (
        receipts_df.groupby(time_col)["ReceiptCost"]
        .sum()
        .reset_index()
    )

    profit_df = pd.merge(
        revenue_ts,
        cost_ts,
        on=time_col,
        how="outer"
    ).fillna(0)

    profit_df["Profit"] = profit_df["Amount"] - profit_df["ReceiptCost"]

    profit_df["Margin"] = np.where(
        profit_df["Amount"] > 0,
        profit_df["Profit"] / profit_df["Amount"],
        0
    )

    profit_df = profit_df.sort_values(time_col)

    # ---------------------------------------------------
    # KPI metrics
    # ---------------------------------------------------

    total_revenue = profit_df["Amount"].sum()
    total_cost = profit_df["ReceiptCost"].sum()
    total_profit = profit_df["Profit"].sum()

    margin = total_profit / total_revenue if total_revenue > 0 else 0

    avg_month_profit = (
        profit_df.groupby(
            profit_df[time_col].dt.to_period("M")
        )["Profit"].sum().mean()
    )

    avg_week_profit = (
        profit_df.groupby(
            profit_df[time_col].dt.to_period("W")
        )["Profit"].sum().mean()
    )

    col1, col2, col3, col4, col5, col6 = st.columns(6)

    col1.metric("Total Revenue", f"${total_revenue:,.0f}")
    col2.metric("Total Cost", f"${total_cost:,.0f}")
    col3.metric("Total Profit", f"${total_profit:,.0f}")
    col4.metric("Margin", f"{margin:.1%}")
    col5.metric("Avg Monthly Profit", f"${avg_month_profit:,.0f}")
    col6.metric("Avg Weekly Profit", f"${avg_week_profit:,.0f}")

    st.divider()

    # ---------------------------------------------------
    # Profit table
    # ---------------------------------------------------

    st.subheader("Profit Summary")

    display = profit_df.copy()

    display["Amount"] = display["Amount"].map("${:,.0f}".format)
    display["ReceiptCost"] = display["ReceiptCost"].map("${:,.0f}".format)
    display["Profit"] = display["Profit"].map("${:,.0f}".format)
    display["Margin"] = display["Margin"].map("{:.1%}".format)

    st.dataframe(display, use_container_width=True)

    # ---------------------------------------------------
    # Revenue / Cost / Profit plot
    # ---------------------------------------------------

    st.subheader("Revenue vs Cost vs Profit")

    fig_profit = px.line(
        profit_df,
        x=time_col,
        y=["Amount", "ReceiptCost", "Profit"],
        markers=True
    )

    st.plotly_chart(fig_profit, width="stretch")

    # ---------------------------------------------------
    # Margin plot
    # ---------------------------------------------------

    st.subheader("Margin Over Time")

    fig_margin = px.line(
        profit_df,
        x=time_col,
        y="Margin",
        markers=True
    )

    st.plotly_chart(fig_margin, width="stretch")

    # ---------------------------------------------------
    # Profit Forecast
    # ---------------------------------------------------

    st.subheader("Profit Forecast")

    forecast_df = profit_df.copy()
    forecast_df["t"] = range(len(forecast_df))

    coef = np.polyfit(forecast_df["t"], forecast_df["Profit"], 1)
    trend = np.poly1d(coef)

    future_periods = 6
    future_t = np.arange(len(forecast_df), len(forecast_df) + future_periods)

    freq = "MS" if time_unit == "Month" else "W"

    future_dates = pd.date_range(
        start=forecast_df[time_col].max(),
        periods=future_periods + 1,
        freq=freq
    )[1:]

    future_values = trend(future_t)

    future_df = pd.DataFrame({
        time_col: future_dates,
        "Forecast": future_values
    })

    fig_forecast = px.line(
        forecast_df,
        x=time_col,
        y="Profit",
        title=f"Profit Forecast ({time_unit})"
    )

    fig_forecast.add_scatter(
        x=future_df[time_col],
        y=future_df["Forecast"],
        mode="lines+markers",
        name="Forecast"
    )

    st.plotly_chart(fig_forecast, width="stretch")







