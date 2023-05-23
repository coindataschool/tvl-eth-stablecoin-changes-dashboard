from defillama2 import DefiLlama
import yfinance as yf
from datetime import date
import pandas as pd
import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots

obj = DefiLlama()

# --- prep a frame of daily BTC & ETH prices and total DeFi TVL --- #

# get historical DeFi TVL of all chains from DefiLlama
df_tvl = obj.get_defi_hist_tvl()
df_tvl.index = df_tvl.index.date # for joining with price frame 
df_tvl = df_tvl.rename(columns={'tvl': 'TVL'})

# download daily prices from Yahoo
start = df_tvl.index[0]
end = df_tvl.index[-1]
tickers_names = {
    'BTC-USD':'BTC', 
    'ETH-USD':'ETH'
}
tickers = list(tickers_names.keys())
# downloads prices since `start` (including `start`) 
df_prices = yf.download(tickers, start, end)['Adj Close'] \
    .rename(tickers_names, axis=1)
df_prices.columns.name = None

# join TVL and Prices 
df_eth_vs_tvl = df_prices.join(df_tvl, how='inner').fillna(method='ffill')

# --- prep a frame of daily MCaps for major fiat stablecoins --- #

# get stablecoin ids
df = obj.get_stablecoins_circulating()
ss = df.loc[:, 'name']

# download historical mcap of USDT, USDC, and BUSD
lst = []
stables = ['Tether', 'USD Coin', 'Binance USD']
for stablecoin in stables:
    stablecoin_id = ss.index[ss == stablecoin].values[0]
    da = obj.get_stablecoin_hist_mcap(stablecoin_id)[['totalCirculatingUSD']]\
        .rename(columns={"totalCirculatingUSD": stablecoin})
    da[stablecoin] = da[stablecoin] / 1e9
    lst.append(da)
df_mcap = pd.concat(lst, axis=1)
df_mcap['All 3'] = df_mcap['Tether'] + df_mcap['USD Coin'] + df_mcap['Binance USD']
df_mcap.index = df_mcap.index.date 

# --- make app --- #

# set_page_config() can only be called once per app, and must be called as the 
# first Streamlit command in your script.
st.set_page_config(page_title='tvl-eth-stablecoin-changes', 
                   layout='wide', page_icon='🔔') 

# 2 cols layout 
c1, c2 = st.columns(2)
with c1:
    # user input 
    base_date_tvl = st.date_input(
        "Start Date", date(2022, 1, 1), min_value=date(2018, 8, 16), 
        max_value=date.today()-pd.Timedelta(1, 'd'))
    
    # calc cumulative pct change from the base date
    df_pct_chng = df_eth_vs_tvl.loc[base_date_tvl:]\
        .apply(lambda x: x.div(x.iloc[0]).subtract(1))

    # plot figure 1 
    fig1 = make_subplots() 
    fig1.add_trace( 
        go.Scatter(x=df_pct_chng.index, y=df_pct_chng.TVL, mode='lines', 
                   name='TVL', line=dict(color='#79e7e7', width=2))
    )
    fig1.add_trace( 
        go.Scatter(x=df_pct_chng.index, y=df_pct_chng.ETH, mode='lines', 
                   name='ETH', line=dict(color='#ecf0f1', width=1.5))
    )
    fig1.add_trace( 
        go.Scatter(x=df_pct_chng.index, y=df_pct_chng.BTC, mode='lines', 
                   name='BTC', line=dict(color='#F7931A', width=1.5))
    )
    # format the axes
    fig1.update_yaxes(title_text=None, showgrid=False, linewidth=2, 
                      zeroline=False, tickformat=".0%")
    fig1.update_xaxes(title_text=None, showgrid=False, linewidth=2)
    # format layout
    fig1.update_layout(paper_bgcolor="#0E1117", plot_bgcolor='#0E1117', 
        yaxis_tickprefix = '', 
        legend=dict(orientation="h"),
        title_text='% Change - BTC & ETH vs. TVL',
        font=dict(size=18),
        autosize=False,
        width=1000,
        height=600,
    )
    # render figure
    st.plotly_chart(fig1, use_container_width=True)

with c2:
    # user input
    base_date_stb = st.date_input(
        "Start Date", date(2022, 1, 1), min_value=date(2020, 12, 31), 
        max_value=date.today()-pd.Timedelta(1, 'd'))

    # calc cumulative $ change from the base date
    df_mcap_chng = df_mcap.loc[base_date_stb:]\
        .apply(lambda x: x.subtract(x.iloc[0]))\
        .rename(columns={'Tether':'USDT', 'USD Coin':'USDC', 'Binance USD':'BUSD'})

    # plot figure 2
    fig2 = make_subplots() 
    fig2.add_trace( 
        go.Scatter(x=df_mcap_chng.index, y=df_mcap_chng['All 3'], mode='lines', 
                   name='All 3', line=dict(color='#E31836', width=2))
    )
    fig2.add_trace(
        go.Scatter(x=df_mcap_chng.index, y=df_mcap_chng['USDT'], mode='lines', 
                   name='USDT', line=dict(color='#26A17B', width=1.5))
    )
    fig2.add_trace(
        go.Scatter(x=df_mcap_chng.index, y=df_mcap_chng['USDC'], mode='lines', 
                   name='USDC', line=dict(color='#2775CA', width=1.5))
    )
    fig2.add_trace(
        go.Scatter(x=df_mcap_chng.index, y=df_mcap_chng['BUSD'], mode='lines', 
                   name='BUSD', line=dict(color='#F0B90B', width=1.5))
    )    
    # format the axes
    fig2.update_yaxes(title_text='Billions of US Dollars', showgrid=False, 
                      linewidth=2, zeroline=False)
    fig2.update_xaxes(title_text=None, showgrid=False, linewidth=2)
    # format layout
    fig2.update_layout(paper_bgcolor="#0E1117", plot_bgcolor='#0E1117', 
        yaxis_tickprefix = '', yaxis_tickformat = ',.2f', 
        legend=dict(orientation="h"),
        title_text='Market Cap $ Change - Top 3 Fiat Stables',
        font=dict(size=18),
        autosize=False,
        width=1000,
        height=600,
    )
    # render figure
    st.plotly_chart(fig2, use_container_width=True)


# about
st.markdown("""---""")
c3, c4 = st.columns(2)
with c3:
    st.subheader('If you want to master the art of LP')
    st.markdown("- Get my [Uniswap V3 LP Book](https://twitter.com/coindataschool/status/1658033627035471872)")

    st.subheader('If you want to trade on chain')
    st.markdown("- Get [5% discount](https://app.gmx.io/#/trade/?ref=coindataschool) when trading on GMX.")
    st.markdown("- Get [2.5%+ discount](https://app.mux.network/#/ref/coindataschool) when trading on MUX.")
    st.markdown("- Get [\$1 for every \$10,000 trading volume](https://app.hyperliquid.xyz/join/COINDATASCHOOL) and qualify for [airdrop](https://app.hyperliquid.xyz/join/CDS) when trading on Hyperliquid.")
with c4:
    st.subheader('Get data-driven insights and Learn DeFi analytics')
    st.markdown("- Subscribe to my free [newsletter](https://coindataschool.substack.com/about)")
    st.markdown("- Follow me on twitter: [@coindataschool](https://twitter.com/coindataschool)")
    st.markdown("- Follow me on github: [@coindataschool](https://github.com/coindataschool)")

    st.subheader("If you'd like to support my work, you can")
    st.markdown("- Send me ETH: `0x783c5546c863f65481bd05fd0e3fd5f26724604e`")
    st.markdown("- Tip me [sat](https://tippin.me/@coindataschool)")
    st.markdown("- Get one of these [membership tiers](https://ko-fi.com/coindataschool/tiers)")
