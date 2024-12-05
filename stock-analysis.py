import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from ta.volatility import BollingerBands, AverageTrueRange
from ta.momentum import RSIIndicator, StochasticOscillator
from ta.trend import MACD, ADXIndicator

st.set_page_config(layout="wide")
st.title("Stock Market Analyzer")

try:
    col1, col2, col3 = st.columns([2, 2, 2])

    with col1:
        symbol = st.text_input("Enter Stock Symbol", "AAPL").upper()
        period = st.selectbox(
            "Time Period", ["1mo", "3mo", "6mo", "1y", "2y", "5y", "max"]
        )
        interval = st.selectbox("Interval", ["1d"])

    with col2:
        ma_periods = st.multiselect(
            "Moving Averages", [5, 10, 20, 50, 100, 200], default=[20, 50]
        )
        bb_period = st.slider("Bollinger Period", 5, 50, 20)
        bb_std = st.slider("Bollinger StdDev", 1.0, 4.0, 2.0, 0.1)

    with col3:
        vol_ma = st.slider("Volatility Period", 5, 50, 20)
        rsi_period = st.slider("RSI Period", 5, 30, 14)
        macd_fast = st.slider("MACD Fast", 5, 20, 12)
        macd_slow = st.slider("MACD Slow", 20, 40, 26)

    comparison = st.multiselect("Compare With", ["SPY", "QQQ", "DIA"])

    stock = yf.Ticker(symbol)
    df = stock.history(period=period, interval=interval)

    if comparison:
        comp_data = {}
        for comp in comparison:
            comp_data[comp] = yf.Ticker(comp).history(period=period, interval=interval)[
                "Close"
            ]
        df_comp = pd.DataFrame(comp_data)
        df_comp = (df_comp / df_comp.iloc[0] * 100) - 100

    if df.empty:
        st.error(f"No data found for {symbol}")
        st.stop()

    for ma in ma_periods:
        df[f"MA_{ma}"] = df["Close"].rolling(window=ma).mean()

    indicator_bb = BollingerBands(df["Close"], window=bb_period, window_dev=bb_std)
    df["BB_upper"] = indicator_bb.bollinger_hband()
    df["BB_lower"] = indicator_bb.bollinger_lband()

    df["ATR"] = AverageTrueRange(
        df["High"], df["Low"], df["Close"]
    ).average_true_range()
    df["RSI"] = RSIIndicator(df["Close"], window=rsi_period).rsi()

    macd = MACD(df["Close"], window_fast=macd_fast, window_slow=macd_slow)
    df["MACD"] = macd.macd()
    df["MACD_Signal"] = macd.macd_signal()

    df["Daily_Return"] = df["Close"].pct_change()
    df["Volatility"] = (
        df["Daily_Return"].rolling(window=vol_ma).std() * np.sqrt(252) * 100
    )

    tabs = st.tabs(
        ["Price Analysis", "Technical Indicators", "Volatility", "Comparison"]
    )

    with tabs[0]:
        fig = go.Figure()
        fig.add_trace(
            go.Candlestick(
                x=df.index,
                open=df["Open"],
                high=df["High"],
                low=df["Low"],
                close=df["Close"],
                name="OHLC",
            )
        )
        for ma in ma_periods:
            fig.add_trace(go.Scatter(x=df.index, y=df[f"MA_{ma}"], name=f"MA_{ma}"))
        fig.add_trace(
            go.Scatter(
                x=df.index, y=df["BB_upper"], name="BB Upper", line=dict(dash="dash")
            )
        )
        fig.add_trace(
            go.Scatter(
                x=df.index, y=df["BB_lower"], name="BB Lower", line=dict(dash="dash")
            )
        )
        st.plotly_chart(fig, use_container_width=True)

        metrics = {
            "Current": f"${df['Close'].iloc[-1]:.2f}",
            "Change": f"{((df['Close'].iloc[-1]/df['Close'].iloc[0])-1)*100:.1f}%",
            "Volatility": f"{df['Volatility'].iloc[-1]:.1f}%",
            "RSI": f"{df['RSI'].iloc[-1]:.1f}",
            "ATR": f"{df['ATR'].iloc[-1]:.2f}",
        }
        # st.write(metrics)
        st.markdown("### Key Metrics")
        st_metrics = {
            k: v.replace("$", "").replace("%", "") if isinstance(v, str) else v
            for k, v in metrics.items()
        }
        st.metric(label="Current", value=f"${st_metrics['Current']}")
        st.metric(label="Change", value=f"{st_metrics['Change']}%")
        st.metric(label="Volatility", value=f"{st_metrics['Volatility']}%")
        st.metric(label="RSI", value=f"{st_metrics['RSI']}")
        st.metric(label="ATR", value=f"{st_metrics['ATR']}")

    with tabs[1]:
        col4, col5 = st.columns(2)
        with col4:
            fig_rsi = go.Figure()
            fig_rsi.add_trace(go.Scatter(x=df.index, y=df["RSI"], name="RSI"))
            fig_rsi.add_hline(y=70, line_dash="dash")
            fig_rsi.add_hline(y=30, line_dash="dash")
            st.plotly_chart(fig_rsi, use_container_width=True)

        with col5:
            fig_macd = go.Figure()
            fig_macd.add_trace(go.Scatter(x=df.index, y=df["MACD"], name="MACD"))
            fig_macd.add_trace(
                go.Scatter(x=df.index, y=df["MACD_Signal"], name="Signal")
            )
            st.plotly_chart(fig_macd, use_container_width=True)

    with tabs[3]:
        if comparison:
            df_norm = pd.DataFrame(
                {"Base": (df["Close"] / df["Close"].iloc[0] * 100) - 100}
            )
            df_comp_all = pd.concat([df_norm, df_comp], axis=1)
            st.line_chart(df_comp_all)

    with tabs[2]:
        col6, col7 = st.columns(2)
        with col6:
            st.line_chart(df["Volatility"])
        with col7:
            fig_ret = px.histogram(df, x="Daily_Return", nbins=50)
            fig_ret.add_vline(x=df["Daily_Return"].mean())
            st.plotly_chart(fig_ret, use_container_width=True)

except Exception as e:
    st.error(f"An error occurred: {str(e)}")
