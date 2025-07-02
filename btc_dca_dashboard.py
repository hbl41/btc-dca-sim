import streamlit as st
import pandas as pd
import datetime
import requests
from functools import lru_cache

st.set_page_config(page_title="Bitcoin DCA Simulator", layout="centered")

st.title("📈 Bitcoin Dollar-Cost Averaging (DCA) Simulator")

st.markdown(
    """
Interactively explore how a steady Bitcoin stacking habit would have done.

**How it works**

* Every day you “buy” a fixed USD amount of BTC at that day's average price (from CoinGecko).
* Your position is valued using Bitcoin’s average USD price on **July 1 2025**.
* Data is pulled on-demand from the free CoinGecko API. One call covers the full period you select.
"""
)

# ─────────── Widgets ─────────── #
dca_usd = st.slider(
    "Daily purchase amount (USD)",
    min_value=1,
    max_value=1000,
    value=10,
    step=1,
)

default_start = datetime.date(2022, 1, 1)
start_date = st.date_input(
    "Start accumulating on…",
    value=default_start,
    min_value=datetime.date(2010, 7, 18),  # roughly first BTC market price
    max_value=datetime.date(2025, 6, 30),  # must be before valuation date
)

valuation_date = datetime.date(2025, 7, 1)

if start_date >= valuation_date:
    st.error("Start date must be **before** July 1 2025.")
    st.stop()


@lru_cache(maxsize=4)
def load_btc_history(start: datetime.date, end: datetime.date) -> pd.DataFrame:
    """Return daily BTC price (USD) between start and end inclusive."""
    # Convert to UNIX seconds (midnight UTC)
    start_ts = int(
        datetime.datetime.combine(
            start, datetime.time.min, tzinfo=datetime.timezone.utc
        ).timestamp()
    )
    end_ts = int(
        datetime.datetime.combine(
            end, datetime.time.min, tzinfo=datetime.timezone.utc
        ).timestamp()
    )
    url = (
        f"https://api.coingecko.com/api/v3/coins/bitcoin/market_chart/range"
        f"?vs_currency=usd&from={start_ts}&to={end_ts}"
    )
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    prices = resp.json()["prices"]
    df = pd.DataFrame(prices, columns=["ms", "price"])
    df["date"] = pd.to_datetime(df["ms"], unit="ms").dt.date
    # Keep the first price for each day (they’re sorted oldest→newest)
    df = df.groupby("date", as_index=False).first()[["date", "price"]]
    return df


with st.spinner("Fetching historical prices…"):
    price_df = load_btc_history(start_date, valuation_date)

if price_df.empty:
    st.error("Couldn't load price data. Try again later.")
    st.stop()

# Daily buys
buy_dates = pd.date_range(start=start_date, end=valuation_date, freq="D")
daily_df = pd.DataFrame({"date": buy_dates.date})
daily_df = daily_df.merge(price_df, on="date", how="left").dropna()

daily_df["usd_spent"] = dca_usd
daily_df["btc_bought"] = daily_df["usd_spent"] / daily_df["price"]

total_btc = daily_df["btc_bought"].sum()
total_usd_invested = daily_df["usd_spent"].sum()

# Price on valuation date (use first row that matches valuation_date)
valuation_price = price_df.loc[
    price_df["date"] == valuation_date, "price"
].iloc[0]
current_value = total_btc * valuation_price
return_pct = (current_value / total_usd_invested - 1) * 100

# ─────────── Results ─────────── #
st.subheader("Results")
col1, col2 = st.columns(2)
col1.metric("Total BTC accumulated", f"{total_btc:.6f} BTC")
col2.metric("Total USD invested", f"${total_usd_invested:,.0f}")

col1.metric("Value on 1 Jul 2025", f"${current_value:,.0f}")
col2.metric("Total return", f"{return_pct:,.1f}%")

with st.expander("See calculation details"):
    st.dataframe(
        daily_df[["date", "price", "btc_bought"]],
        hide_index=True,
        use_container_width=True,
    )

st.caption("Price data © CoinGecko (open-source, free API). App by ChatGPT.")
