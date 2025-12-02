import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.express as px

# --- 1. รายชื่อหุ้น US แยกตามอุตสาหกรรม (Predefined List) ---
# เน้นกลุ่ม Tech / SaaS ที่นิยมใช้ Rule of 40
US_SECTORS = {
    "Big Tech (M7)": ["AAPL", "MSFT", "GOOGL", "AMZN", "META", "NVDA", "TSLA"],
    "Software & SaaS": ["ADBE", "CRM", "ORCL", "INTU", "NOW", "UBER", "ABNB", "PLTR", "SNOW", "CRWD", "DDOG", "ZM", "TEAM", "WDAY", "PANW", "FTNT", "NET"],
    "Semiconductors": ["AMD", "INTC", "QCOM", "TXN", "AVGO", "MU", "AMAT", "LRCX", "TSM", "ARM"],
    "Fintech & Crypto": ["V", "MA", "PYPL", "SQ", "COIN", "HOOD", "AFRM", "SOFI"],
    "E-commerce & Retail": ["NFLX", "SPOT", "SHOP", "ETSY", "EBAY", "WMT", "COST", "TGT", "HD"],
    "Healthcare & Bio": ["JNJ", "PFE", "MRK", "ABBV", "LLY", "UNH", "TMO"],
    "Consumer & Discretionary": ["DIS", "NKE", "SBUX", "MCD", "KO", "PEP", "PG"]
}

# --- ตั้งค่าหน้าเว็บ ---
st.set_page_config(page_title="US Rule of 40 Analyzer", layout="wide", initial_sidebar_state="collapsed")

st.title("🇺🇸 US Stock: Rule of 40 Analyzer")
st.markdown("""
**Rule of 40** คือสูตรดูหุ้น Tech ที่ดี:  
*(Revenue Growth + Profit Margin) > 40% ถือว่าแข็งแกร่ง*
""")

# --- Sidebar ---
st.sidebar.header("⚙️ Filter Settings")

# 1. เลือกปี
lookback_years = st.sidebar.selectbox("📅 Growth ย้อนหลังกี่ปี (CAGR)?", options=[1, 3, 5, 10], index=1)

# 2. เลือกอุตสาหกรรม
st.sidebar.subheader("🏭 เลือกกลุ่มหุ้น (Sector)")
selected_sector_key = st.sidebar.selectbox("เลือกกลุ่มอุตสาหกรรม:", ["Custom Input (ระบุเอง)"] + list(US_SECTORS.keys()))

tickers_to_process = []
if selected_sector_key == "Custom Input (ระบุเอง)":
    default_custom = "MSFT, GOOGL, NVDA, AMD, PLTR"
    user_input = st.sidebar.text_area("ใส่ชื่อหุ้น (Comma separated)", default_custom, height=100)
    if user_input:
        raw_list = [x.strip().upper() for x in user_input.split(',')]
        tickers_to_process = [x for x in raw_list if x]
else:
    tickers_to_process = US_SECTORS[selected_sector_key]

# 3. Filter พิเศษ
max_rule40 = st.sidebar.number_input("ตัดหุ้นที่ Rule of 40 เกินกว่า (%)", value=200, help="ช่วยกรองหุ้นที่งบกระโดดผิดปกติออก")
min_rule40 = st.sidebar.slider("โชว์เฉพาะที่ Rule of 40 สูงกว่า", -50, 100, 0)

run_button = st.sidebar.button("🚀 Run Analysis", type="primary", use_container_width=True)

# --- Function ดึงข้อมูล ---
@st.cache_data(ttl=3600)
def fetch_us_data(tickers, years):
    data = []
    progress_bar = st.progress(0)
    status_text = st.empty()
    total = len(tickers)
    
    for i, ticker in enumerate(tickers):
        status_text.caption(f"Fetching {i+1}/{total}: {ticker}")
        progress_bar.progress((i + 1) / total)
        try:
            stock = yf.Ticker(ticker)
            # ดึงงบปี (Annual)
            financials = stock.financials.T.sort_index()
            
            if len(financials) > years:
                latest = financials.iloc[-1]
                past = financials.iloc[-(years + 1)]
                
                # 1. Revenue Growth (CAGR)
                rev_now = latest.get('Total Revenue', 0)
                rev_past = past.get('Total Revenue', 0)
                
                # 2. Profit Margin (ใช้ Net Income Margin ของปีล่าสุด)
                # (SaaS บางที่ใช้ FCF หรือ EBITDA แต่ Net Margin หาได้ง่ายสุดใน Free Tier)
                net_income = latest.get('Net Income', 0)
                
                if rev_past > 0 and rev_now > 0:
                    # คำนวณ CAGR
                    rev_growth = ((rev_now / rev_past) ** (1 / years) - 1) * 100
                    
                    # คำนวณ Net Margin
                    net_margin = (net_income / rev_now) * 100
                    
                    # คำนวณ Rule of 40
                    rule_of_40 = rev_growth + net_margin
                    
                    data.append({
                        'Ticker': ticker,
                        'Rule of 40': round(rule_of_40, 2),
                        'Revenue Growth (%)': round(rev_growth, 2),
                        'Net Margin (%)': round(net_margin, 2),
                        'Revenue ($B)': round(rev_now / 1e9, 2) # หน่วยพันล้านเหรียญ
                    })
        except: continue
            
    progress_bar.empty()
    status_text.empty()
    return pd.DataFrame(data)

# --- Main Logic ---
if run_button:
    if not tickers_to_process:
        st.warning("กรุณาระบุชื่อหุ้น")
    else:
        with st.spinner(f'Analyzing {len(tickers_to_process)} US Stocks...'):
            df = fetch_us_data(tickers_to_process, lookback_years)
        
        if not df.empty:
            # --- Filtering Logic ---
            # 1. ตัดค่าเวอร์ (เกิน 200%)
            filtered_df = df[df['Rule of 40'] <= max_rule40]
            # 2. ตัดค่าต่ำเตี้ย (ตาม Slider)
            filtered_df = filtered_df[filtered_df['Rule of 40'] >= min_rule40]
            
            st.success(f"✅ พบ {len(filtered_df)} หุ้น (จาก {len(df)} ตัว)")
            
            # --- Visualization ---
            tab1, tab2 = st.tabs(["📊 Scatter Plot", "📋 Ranking Table"])
            
            with tab1:
                if len(filtered_df) > 0:
                    # สร้างเส้นแบ่งโซน 40%
                    fig = px.scatter(
                        filtered_df,
                        x="Revenue Growth (%)",
                        y="Net Margin (%)",
                        size="Revenue ($B)", # ขนาดวงกลมตามรายได้
                        color="Rule of 40",
                        hover_name="Ticker",
                        text="Ticker",
                        color_continuous_scale="RdYlGn", # แดง-เหลือง-เขียว
                        title=f"Rule of 40 Map (Lookback {lookback_years} Years)",
                        height=600
                    )
                    
                    # เส้นเป้าหมาย Rule of 40 (Growth + Margin = 40)
                    # สร้างเส้นทแยงมุมยากใน Plotly ธรรมดา เลยใช้เส้นแนวนอน/ตั้งช่วยดูแทน
                    # แต่เราวาดเส้นสมมติแบบ Line Shape ได้
                    
                    x_range = [filtered_df['Revenue Growth (%)'].min()-5, filtered_df['Revenue Growth (%)'].max()+5]
                    # y = 40 - x
                    
                    fig.add_shape(
                        type="line",
                        x0=x_range[0], y0=40-x_range[0],
                        x1=x_range[1], y1=40-x_range[1],
                        line=dict(color="Red", width=2, dash="dash"),
                    )
                    fig.add_annotation(
                        x=20, y=25,
                        text="เส้น Rule of 40 (Above line is Good)",
                        showarrow=False,
                        textangle=-45,
                        font=dict(color="red")
                    )

                    # ปรับแต่ง Layout
                    fig.update_layout(
                        margin=dict(l=20, r=20, t=50, b=20),
                        xaxis_title=f"Revenue CAGR ({lookback_years}Y) %",
                        yaxis_title="Net Profit Margin (Latest) %",
                        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
                    )
                    
                    st.plotly_chart(fig, use_container_width=True)
                    st.caption("ℹ️ วงกลมใหญ่ = รายได้เยอะ | เส้นประสีแดงคือเส้นเกณฑ์ 40%")
                else:
                    st.warning("ไม่พบหุ้นที่ผ่านเกณฑ์")

            with tab2:
                st.dataframe(
                    filtered_df.sort_values(by='Rule of 40', ascending=False),
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "Rule of 40": st.column_config.ProgressColumn(
                            "Rule of 40 Score",
                            format="%.2f%%",
                            min_value=-50,
                            max_value=100,
                        ),
                    }
                )

        else:
            st.error("ไม่สามารถดึงข้อมูลได้ (อาจเป็นเพราะ Ticker ผิด หรือ Yahoo บล็อกชั่วคราว)")
else:
    st.info("👈 เลือกกลุ่มอุตสาหกรรม แล้วกดปุ่ม Run Analysis")
