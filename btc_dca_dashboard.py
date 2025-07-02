@lru_cache(maxsize=4)
def load_btc_history(start: datetime.date, end: datetime.date) -> pd.DataFrame:
    """Return daily BTC price (USD) between start and end inclusive."""
    # Convert to UNIX timestamps (midnight UTC)
    start_ts = int(
        datetime.datetime.combine(start, datetime.time.min,
                                  tzinfo=datetime.timezone.utc).timestamp()
    )
    end_ts = int(
        datetime.datetime.combine(end, datetime.time.min,
                                  tzinfo=datetime.timezone.utc).timestamp()
    )

    url = (
        "https://api.coingecko.com/api/v3/coins/bitcoin/market_chart/range"
        f"?vs_currency=usd&from={start_ts}&to={end_ts}"
    )

    # Add a browser-like User-Agent header
    HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (iPad; CPU OS 17_5 like Mac OS X) "
            "AppleWebKit/605.1.15 (KHTML, like Gecko) "
            "Version/17.5 Mobile/15E148 Safari/604.1"
        )
    }

    # Retry up to 5 times if rate-limited (HTTP 429)
    wait = 2  # seconds
    for _ in range(5):
        resp = requests.get(url, headers=HEADERS, timeout=30)
        if resp.status_code == 429:
            time.sleep(wait)
            wait *= 2
            continue
        resp.raise_for_status()
        break
    else:
        resp.raise_for_status()  # Still failed after retries

    # Parse price data
    prices = resp.json()["prices"]
    df = pd.DataFrame(prices, columns=["ms", "price"])
    df["date"] = pd.to_datetime(df["ms"], unit="ms").dt.date

    # Keep first price for each date
    df = df.groupby("date", as_index=False).first()[["date", "price"]]
    return df
