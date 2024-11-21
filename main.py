import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
import pandas as pd
from statsmodels.tsa.seasonal import seasonal_decompose
import numpy as np
import requests

import streamlit as st
NEWS_API_KEY = st.secrets["NEWS_API_KEY"]


def get_financial_news(query, api_key, max_results=3):
    financial_domains = "bloomberg.com,cnbc.com,reuters.com,wsj.com,marketwatch.com,ft.com"

    url = (f"https://newsapi.org/v2/everything?"
           f"q={query}&apiKey={api_key}&language=en&sortBy=publishedAt&domains={financial_domains}")

    response = requests.get(url)
    if response.status_code == 200:
        articles = response.json().get("articles", [])[:max_results]
        return articles
    else:
        return []

popular_tickers = ["AAPL", "MSFT", "AMZN", "TSLA", "ASML", "NVDA", "QCOM", "QUBT"]

st.title("AI24: Project, team 31")

if "selected_ticker" not in st.session_state:
    st.session_state.selected_ticker = None

st.header("Выберите тикер актива")

cols = st.columns(len(popular_tickers))
for i, ticker in enumerate(popular_tickers):
    if cols[i].button(ticker):
        st.session_state.selected_ticker = ticker

user_ticker = st.text_input("Или введите свой тикер:", "")

if user_ticker:
    st.session_state.selected_ticker = user_ticker

if st.session_state.selected_ticker:
    selected_ticker = st.session_state.selected_ticker
    try:
        stock = yf.Ticker(selected_ticker)

        st.header(f"Основная информация: {selected_ticker}")
        info = stock.info
        st.write(f"**Название:** {info.get('longName', 'Неизвестно')}")
        st.write(f"**Сектор:** {info.get('sector', 'Неизвестно')}")
        st.write(f"**Биржа:** {info.get('exchange', 'Неизвестно')}")

        market_cap = info.get('marketCap', None)
        if market_cap:
            market_cap_bln = market_cap / 1e9
            st.write(f"**Оценочная стоимость:** {market_cap_bln:.2f} млрд долларов")
        else:
            st.write("**Рыночная капитализация:** Неизвестно")

        price = info.get('regularMarketPrice', None)
        if not price:
            data = stock.history(period="1d", interval="1d")
            if not data.empty:
                price = data['Close'].iloc[-1]
        if price:
            st.write(f"**Текущая цена:** ${price:.2f}")
        else:
            st.write("**Текущая цена:** Неизвестно")

        st.header("График цены")
        period = st.selectbox("Выберите период:", ["1mo", "3mo", "6mo", "1y", "5y", "max"], index=2)
        interval = st.selectbox("Выберите интервал:", ["1d", "1wk", "1mo"], index=0)
        data = stock.history(period=period, interval=interval)

        if not data.empty:
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=data.index, y=data['Close'], mode='lines', name='Цена закрытия'))
            fig.update_layout(
                title=f'График цены для {selected_ticker}',
                xaxis_title="Дата",
                yaxis_title="Цена закрытия",
                xaxis_rangeslider_visible=True,
                template="plotly_dark"
            )
            st.plotly_chart(fig)

            st.header("Ключевые численные показатели")
            metrics = {
                "Средняя цена закрытия": [data['Close'].mean()],
                "Медианная цена закрытия": [data['Close'].median()],
                "Максимальная цена закрытия": [data['Close'].max()],
                "Минимальная цена закрытия": [data['Close'].min()],
                "Изменение (с начальной до конечной)": [((data['Close'].iloc[-1] - data['Close'].iloc[0]) / data['Close'].iloc[0]) * 100],
                "Среднее дневное изменение (%)": [data['Close'].pct_change().mean() * 100],
                "Средний объем торгов": [data['Volume'].mean()],
                "Максимальный объем торгов": [data['Volume'].max()],
                "Минимальный объем торгов": [data['Volume'].min()],
            }
            metrics_df = pd.DataFrame(metrics)
            st.dataframe(metrics_df.style.format("{:.2f}"), use_container_width=True)


            st.header("Информация о волатильности")
            data['Daily Return'] = data['Close'].pct_change()
            volatility = np.std(data['Daily Return']) * np.sqrt(len(data))
            st.write(f"**Годовая волатильность:** {volatility:.2%}")

            st.header("Японские свечи")
            candle = go.Figure(data=[go.Candlestick(
                x=data.index,
                open=data['Open'],
                high=data['High'],
                low=data['Low'],
                close=data['Close'],
                name="Candlesticks"
            )])
            candle.update_layout(
                title=f'Японские свечи для {selected_ticker}',
                xaxis_title="Дата",
                yaxis_title="Цена",
                xaxis_rangeslider_visible=False,
                template="plotly_dark"
            )
            st.plotly_chart(candle)

            st.header("Bollinger bands")
            data['Bollinger_Mid'] = data['Close'].rolling(window=20).mean()
            data['Bollinger_Up'] = data['Bollinger_Mid'] + (data['Close'].rolling(window=20).std() * 2)
            data['Bollinger_Low'] = data['Bollinger_Mid'] - (data['Close'].rolling(window=20).std() * 2)

            fig_bollinger = go.Figure()
            fig_bollinger.add_trace(go.Scatter(x=data.index, y=data['Close'], mode='lines', name='Цена закрытия'))
            fig_bollinger.add_trace(go.Scatter(x=data.index, y=data['Bollinger_Up'], mode='lines', name='Bollinger Верхний', line=dict(dash='dot')))
            fig_bollinger.add_trace(go.Scatter(x=data.index, y=data['Bollinger_Low'], mode='lines', name='Bollinger Нижний', line=dict(dash='dot')))
            fig_bollinger.update_layout(
                title=f'Bollinger bands для {selected_ticker}',
                xaxis_title="Дата",
                yaxis_title="Цена закрытия",
                template="plotly_dark"
            )
            st.plotly_chart(fig_bollinger)

            st.header("Финансовые новости")
            st.write(f"Последние новости о {selected_ticker}:")
            news = get_financial_news(selected_ticker, NEWS_API_KEY)

            if news:
                for article in news:
                    st.write(f"**[{article['title']}]({article['url']})**")
                    st.write(f"*{article['source']['name']}* | Опубликовано: {article['publishedAt']}")
                    st.write(f"Описание: {article['description']}")
            else:
                st.write("Нет доступных новостей.")

            st.header("Декомпозиция временного ряда")
            st.write("Декомпозиция выполняется на основе закрывающих цен.")
            data['Close'] = pd.to_numeric(data['Close'], errors='coerce')
            data = data.dropna()

            if len(data) < 60:
                st.warning("Для выполнения декомпозиции временного ряда необходимо как минимум 60 точек данных. Попробуйте выбрать более длительный период.")
            else:
                result = seasonal_decompose(data['Close'], model='additive', period=30)
                st.subheader("Оригинальный ряд")
                fig_observed = go.Figure()
                fig_observed.add_trace(go.Scatter(x=result.observed.index, y=result.observed, mode='lines', name='Оригинальный ряд', line=dict(color='royalblue')))
                st.plotly_chart(fig_observed)

                st.subheader("Тренд")
                fig_trend = go.Figure()
                fig_trend.add_trace(go.Scatter(x=result.trend.index, y=result.trend, mode='lines', name='Тренд', line=dict(color='orange')))
                st.plotly_chart(fig_trend)

                st.subheader("Сезонность")
                fig_seasonal = go.Figure()
                fig_seasonal.add_trace(go.Scatter(x=result.seasonal.index, y=result.seasonal, mode='lines', name='Сезонность', line=dict(color='green')))
                st.plotly_chart(fig_seasonal)

                st.subheader("Остатки")
                fig_resid = go.Figure()
                fig_resid.add_trace(go.Scatter(x=result.resid.index, y=result.resid, mode='lines', name='Остатки', line=dict(color='red')))
                st.plotly_chart(fig_resid)

        else:
            st.write("Нет данных для отображения графика.")
    except Exception as e:
        st.error(f"Ошибка: {e}")
