import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.express as px

# --- 1. รายชื่อหุ้น (SET50/100 แบบ Hardcoded เพื่อความเร็ว) ---
# (อ้างอิงข้อมูลล่าสุด ตัด CRC ออกตามคำขอ)
SET50 = [
    "ADVANC", "AOT", "AWC", "BANPU", "BBL", "BDMS", "BEM", "BGRIM", "BH", "BTS",
    "CBG", "CENTEL", "COM7", "CPALL", "CPF", "CPN", "DELTA", "EA", "EGCO",
    "GLOBAL", "GPSC", "GULF", "HMPRO", "INTUCH", "IVL", "KBANK", "KCE", "KTB", "KTC",
    "LH", "MINT", "MTC", "OR", "OSP", "PTT", "PTTEP", "PTTGC", "RATCH", "SAWAD",
    "SCB", "SCC", "SCGP", "TISCO", "TOP", "TRUE", "TTB", "TU", "WHA"
]

SET100 = SET50 + [
    "AMATA", "AP", "BAM", "BCH", "BCP", "BCPG", "BYD", "CK", "CKP", "DOHOME",
    "EPG", "ERW", "ESSO", "FORTH", "GUNKUL", "HANA", "JMART", "JMT", "KEX", "KKP",
    "MAJOR", "MEGA", "ONEE", "ORI", "PLANB", "PRM", "PTG", "QH", "RBF", "RCL",
    "S", "SABUY", "SINGER", "SIRI", "SPALI", "SPRC", "STA", "STARK", "STEC", "STGT",
    "TASCO", "THANI", "TIPH", "TQM", "VGI", "WHAUP"
]

# --- ตั้งค่าหน้าเว็บ ---
st.set_page_config(page_title="Thai Stock Growth Filter", layout="wide")
st.title("📈 Thai Stock Growth Analyzer (All Market)")

# --- Sidebar: ตั้งค่าการค้นหา ---
st.sidebar.header("⚙️ Filter Settings")
lookback_years = st.sidebar.selectbox("ย้อนหลังกี่ปี?", options=[1, 3, 5, 7, 10], index=1)

# --- ส่วนเลือกหุ้น ---
st.sidebar.subheader("🗂️ เลือกกลุ่มหุ้น")
stock_source = st.sidebar.radio(
    "แหล่งข้อมูลหุ้น:",
    ("SET50 (เร็ว)", "SET100 (แนะนำ)", "ระบุเอง (Custom / All Market)")
)

tickers_to_process = []

if stock_source == "SET50 (เร็ว)":
    tickers_to_process = [s + ".BK" for s in SET50]
elif stock_source == "SET100 (แนะนำ)":
    tickers_to_process = [s + ".BK" for s in SET100]
else:
    # Custom List input
    default_custom = "AOT, PTT, CPALL, DELTA"
    user_input = st.sidebar.text_area("ใส่ชื่อหุ้น (คั่นด้วย comma)", default_custom, height=150)
    st.sidebar.caption("💡 ทิป: หากต้องการหุ้นทั้งตลาด ให้ก๊อปปี้รายชื่อหุ้นทั้งหมดมาวางที่นี่")
    
    if user_input:
        raw_list = [x.strip() for x in user_input.split(',')]
        tickers_to_process = [x + ".BK" if not x.upper().endswith(".BK") else x for x in raw_list if x.strip()]

# Filter อื่นๆ
min_rev_cagr = st.sidebar.slider("รายได้โตขั้นต่ำ (%)", 0, 50, 5)
show_only_profit_growth = st.sidebar.checkbox("โชว์เฉพาะตัวที่กำไรโต", value=True)

# ปุ่ม Run
st.sidebar.markdown("---")
st.sidebar.markdown(f"**จำนวนหุ้นที่จะวิเคราะห์:** `{len(tickers_to_process)}` ตัว")
run_button = st.sidebar.button("🚀 เริ่มวิเคราะห์", type="primary")

# --- Function ดึงข้อมูล ---
@st.cache_data(ttl=3600)
def fetch_data(tickers, years):
    data = []
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    total = len(tickers)
    
    for i, ticker in enumerate(tickers):
        status_text.text(f"กำลังดึงข้อมูล ({i+1}/{total}): {ticker}")
        progress_bar.progress((i + 1) / total)
        
        try:
            stock = yf.Ticker(ticker)
            financials = stock.financials.T.sort_index()
            
            if len(financials) > years:
                latest = financials.iloc[-1]
                past = financials.iloc[-(years + 1)]
                
                rev_now = latest.get('Total Revenue', 0)
                rev_past = past.get('Total Revenue', 0)
                profit_now = latest.get('Net Income', 0)
                profit_past = past.get('Net Income', 0)

                if rev_past > 0 and rev_now > 0:
                    rev_cagr = ((rev_now / rev_past) ** (1 / years) - 1) * 100
                    
                    if profit_past != 0:
                        profit_growth = ((profit_now - profit_past) / abs(profit_past)) * 100
                    else:
                        profit_growth = 0
                    
                    net_margin = (profit_now / rev_now) * 100 if rev_now else 0
                    
                    data.append({
                        'Ticker': ticker.replace('.BK', ''),
                        'Revenue CAGR (%)': round(rev_cagr, 2),
                        'Net Profit Growth (%)': round(profit_growth, 2),
                        'Net Margin (%)': round(net_margin, 2)
                    })
        except Exception:
            continue
            
    progress_bar.empty()
    status_text.empty()
    return pd.DataFrame(data)

# --- Main Logic ---
if run_button:
    if not tickers_to_process:
        st.warning("กรุณาระบุรายชื่อหุ้นก่อนครับ")
    else:
        st.info(f"⏳ กำลังดึงข้อมูล {len(tickers_to_process)} บริษัท... (อาจใช้เวลา 2-3 วินาทีต่อ 1 บริษัท)")
        
        df = fetch_data(tickers_to_process, lookback_years)
        
        if not df.empty:
            filtered_df = df[df['Revenue CAGR (%)'] >= min_rev_cagr]
            if show_only_profit_growth:
                filtered_df = filtered_df[filtered_df['Net Profit Growth (%)'] > 0]
            
            st.success(f"✅ เสร็จสิ้น! พบ {len(filtered_df)} หุ้นที่ผ่านเกณฑ์")
            
            col1, col2 = st.columns([3, 1])
            
            with col1:
                st.subheader(f"📊 แผนภาพการเติบโต ({lookback_years} ปี)")
                if len(filtered_df) > 0:
                    fig = px.scatter(
                        filtered_df, 
                        x="Revenue CAGR (%)", 
                        y="Net Profit Growth (%)",
                        size="Net Margin (%)",
                        color="Net Profit Growth (%)",
                        hover_name="Ticker", 
                        text="Ticker", 
                        color_continuous_scale="RdYlGn",
                        height=650
                    )
                    fig.add_vline(x=min_rev_cagr, line_dash="dash", line_color="gray")
                    fig.add_hline(y=0, line_color="black")
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.warning("ไม่มีหุ้นที่ผ่านเกณฑ์การกรอง")

            with col2:
                st.subheader("📋 รายชื่อหุ้น")
                st.dataframe(
                    filtered_df[['Ticker', 'Revenue CAGR (%)', 'Net Profit Growth (%)']].sort_values(by='Net Profit Growth (%)', ascending=False),
                    height=600
                )

        else:
            st.error("ไม่สามารถดึงข้อมูลได้ หรือ ไม่มีข้อมูลเพียงพอในช่วงปีที่เลือก")
else:
    st.info("👈 เลือกกลุ่มหุ้น แล้วกดปุ่ม **'🚀 เริ่มวิเคราะห์'**")
