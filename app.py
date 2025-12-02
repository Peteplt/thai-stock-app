import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.express as px

# --- 1. รายชื่อหุ้น (เหมือนเดิม) ---
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

# --- ตั้งค่าหน้าเว็บ (Responsive Mode) ---
st.set_page_config(page_title="Thai Stock Growth", layout="wide", initial_sidebar_state="collapsed")
# initial_sidebar_state="collapsed" ช่วยให้เปิดมาในมือถือแล้วเห็นเนื้อหาเลย ไม่โดนเมนูบัง

st.title("📈 Thai Stock Analyzer")
st.caption("วิเคราะห์การเติบโตหุ้นไทย (Mobile Friendly)")

# --- Sidebar ---
st.sidebar.header("⚙️ ตั้งค่า (Filter)")
lookback_years = st.sidebar.selectbox("📅 ย้อนหลังกี่ปี?", options=[1, 3, 5, 7, 10], index=1)

st.sidebar.subheader("🗂️ เลือกกลุ่มหุ้น")
stock_source = st.sidebar.radio(
    "Source:",
    ("SET50", "SET100", "Custom List")
)

tickers_to_process = []
if stock_source == "SET50":
    tickers_to_process = [s + ".BK" for s in SET50]
elif stock_source == "SET100":
    tickers_to_process = [s + ".BK" for s in SET100]
else:
    default_custom = "AOT, PTT, CPALL, DELTA, SCB"
    user_input = st.sidebar.text_area("ระบุชื่อหุ้น (comma separated)", default_custom)
    if user_input:
        raw_list = [x.strip() for x in user_input.split(',')]
        tickers_to_process = [x + ".BK" if not x.upper().endswith(".BK") else x for x in raw_list if x.strip()]

min_rev_cagr = st.sidebar.slider("รายได้โตขั้นต่ำ (%)", -20, 50, 5) # ปรับให้เลือกติดลบได้เผื่อดูตัวแย่
show_only_profit_growth = st.sidebar.checkbox("เฉพาะกำไรโต (Profit > 0)", value=True)

st.sidebar.markdown("---")
run_button = st.sidebar.button("🚀 เริ่มวิเคราะห์", type="primary", use_container_width=True) # ปุ่มเต็มความกว้าง

# --- Function ---
@st.cache_data(ttl=3600)
def fetch_data(tickers, years):
    data = []
    progress_bar = st.progress(0)
    status_text = st.empty()
    total = len(tickers)
    
    for i, ticker in enumerate(tickers):
        status_text.caption(f"Loading {i+1}/{total}: {ticker}")
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
        except: continue
            
    progress_bar.empty()
    status_text.empty()
    return pd.DataFrame(data)

# --- Main Display ---
if run_button:
    if not tickers_to_process:
        st.warning("กรุณาระบุหุ้น")
    else:
        with st.spinner('กำลังดึงข้อมูล...'):
            df = fetch_data(tickers_to_process, lookback_years)
        
        if not df.empty:
            filtered_df = df[df['Revenue CAGR (%)'] >= min_rev_cagr]
            if show_only_profit_growth:
                filtered_df = filtered_df[filtered_df['Net Profit Growth (%)'] > 0]
            
            st.success(f"✅ พบ {len(filtered_df)} หุ้น")

            # --- ใช้ Tabs แทน Columns เพื่อความ Responsive ---
            tab1, tab2 = st.tabs(["📊 แผนภาพ (Graph)", "📋 รายชื่อ (List)"])

            with tab1:
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
                        height=550 # ปรับความสูงให้พอดีมือถือ
                    )
                    # ปรับแต่ง Layout สำหรับมือถือ
                    fig.update_layout(
                        legend=dict(
                            orientation="h", # เอา Legend แนวนอน
                            yanchor="bottom", y=1.02, # ย้ายไปไว้ด้านบนกราฟ
                            xanchor="right", x=1
                        ),
                        margin=dict(l=20, r=20, t=50, b=20) # ลดขอบขาว
                    )
                    fig.add_vline(x=min_rev_cagr, line_dash="dash", line_color="gray")
                    fig.add_hline(y=0, line_color="black")
                    
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.warning("ไม่มีข้อมูลตามเงื่อนไข")

            with tab2:
                # โชว์ตารางแบบเรียบง่าย
                st.dataframe(
                    filtered_df.sort_values(by='Net Profit Growth (%)', ascending=False),
                    use_container_width=True,
                    hide_index=True
                )
        else:
            st.error("ไม่พบข้อมูล")
