import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import date, datetime, timedelta
import json
import io


# ── CONFIG ──────────────────────────────────────────────────────────────────
DAILY_BENCHMARK = 200_000          # VNĐ
CATEGORIES = ["Ăn uống", "Di chuyển / Xăng xe", "Mua sắm", "Khác"]
SHEET_NAME  = "ChiTieuCaNhan"      # Tên Google Sheet của bạn
WORKSHEET   = "Data"               # Tên tab trong sheet

# Màu sắc cho biểu đồ
CAT_COLORS = {
    "Ăn uống":              "#E07B5D",
    "Di chuyển / Xăng xe": "#5D8FE0",
    "Mua sắm":              "#E0C05D",
    "Khác":                 "#7BE0A8",
}

# ── PAGE CONFIG ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Chi Tiêu Cá Nhân",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
    /* Font & global */
    @import url('https://fonts.googleapis.com/css2?family=Be+Vietnam+Pro:wght@400;500;600;700&display=swap');
    html, body, [class*="css"] { font-family: 'Be Vietnam Pro', sans-serif; }

    /* Metric cards */
    [data-testid="metric-container"] {
        background: #FAFAF9;
        border: 1px solid #E8E6E0;
        border-radius: 12px;
        padding: 16px 20px;
    }
    [data-testid="metric-container"] label { font-size: 13px !important; color: #888; }
    [data-testid="metric-container"] [data-testid="stMetricValue"] { font-size: 26px !important; font-weight: 600; }

    /* Button */
    .stButton > button {
        border-radius: 10px;
        font-weight: 600;
        font-size: 15px;
        padding: 10px 24px;
        width: 100%;
    }

    /* Status box */
    .status-ok   { background:#E8F7EE; border-left:4px solid #2ECC71; padding:16px 20px; border-radius:8px; }
    .status-warn { background:#FEF2E7; border-left:4px solid #E07B5D; padding:16px 20px; border-radius:8px; }

    /* Header */
    .main-title { font-size: 28px; font-weight: 700; letter-spacing: -0.5px; margin-bottom: 4px; }
    .sub-title  { font-size: 14px; color: #888; margin-bottom: 24px; }

    /* Sidebar */
    section[data-testid="stSidebar"] { background: #F7F5F0; }
</style>
""", unsafe_allow_html=True)


# ── GOOGLE SHEETS CONNECTION ─────────────────────────────────────────────────
@st.cache_resource
def get_gsheet():
    """Kết nối Google Sheets qua service account credentials trong st.secrets."""
    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive",
    ]
    creds_dict = dict(st.secrets["gcp_service_account"])
    creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
    client = gspread.authorize(creds)
    sheet = client.open(SHEET_NAME).worksheet(WORKSHEET)
    return sheet


def load_data(sheet) -> pd.DataFrame:
    records = sheet.get_all_records()
    if not records:
        return pd.DataFrame(columns=["date", "category", "amount", "note", "created_at"])
    df = pd.DataFrame(records)
    df["date"]   = pd.to_datetime(df["date"]).dt.date
    df["amount"] = pd.to_numeric(df["amount"], errors="coerce").fillna(0)
    return df


def append_row(sheet, date_val, category, amount, note):
    sheet.append_row([
        str(date_val),
        category,
        int(amount),
        note,
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    ])


def delete_last_row(sheet, df):
    """Xoá dòng cuối cùng trong sheet (dùng để undo)."""
    n = len(df) + 1  # +1 vì row 1 là header
    sheet.delete_rows(n + 1)


# ── HELPERS ──────────────────────────────────────────────────────────────────
def fmt_vnd(amount: int) -> str:
    return f"{amount:,.0f}đ".replace(",", ".")


def pct_of_benchmark(total: int) -> float:
    return round(total / DAILY_BENCHMARK * 100, 1)


# ── SIDEBAR: NHẬP LIỆU ──────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### ➕ Thêm khoản chi")
    st.markdown("---")

    entry_date = st.date_input("Ngày", value=date.today(), max_value=date.today())
    category   = st.selectbox("Danh mục", CATEGORIES)
    amount     = st.number_input(
        "Số tiền (VNĐ)", min_value=1_000, max_value=10_000_000,
        step=1_000, value=50_000, format="%d"
    )
    note = st.text_input("Ghi chú (tuỳ chọn)", placeholder="Phở bò, grab, ...")

    if st.button("💾 Lưu khoản chi", type="primary"):
        try:
            sheet = get_gsheet()
            append_row(sheet, entry_date, category, amount, note)
            st.cache_data.clear()
            st.success("Đã lưu! ✅")
            st.rerun()
        except Exception as e:
            st.error(f"Lỗi kết nối Google Sheets:\n{e}")

    st.markdown("---")
    st.markdown("### ⚙️ Benchmark")
    benchmark_input = st.number_input(
        "Chi tiêu tối đa/ngày (đ)",
        min_value=50_000, max_value=5_000_000,
        step=10_000, value=DAILY_BENCHMARK, format="%d"
    )
    DAILY_BENCHMARK = benchmark_input

    st.markdown("---")
    st.caption("💡 Dữ liệu lưu trên Google Sheets của bạn.")


# ── MAIN CONTENT ─────────────────────────────────────────────────────────────
st.markdown('<div class="main-title">💰 Chi Tiêu Cá Nhân</div>', unsafe_allow_html=True)
st.markdown(f'<div class="sub-title">Benchmark: {fmt_vnd(DAILY_BENCHMARK)}/ngày</div>', unsafe_allow_html=True)

# Load data
try:
    sheet = get_gsheet()
    df = load_data(sheet)
    connected = True
except Exception:
    st.warning("⚠️ Chưa kết nối Google Sheets. Đang dùng dữ liệu demo.")
    demo = {
        "date":       [date.today(), date.today(), date.today() - timedelta(days=1)],
        "category":   ["Ăn uống", "Di chuyển / Xăng xe", "Ăn uống"],
        "amount":     [85_000, 40_000, 120_000],
        "note":       ["Cơm trưa", "Grab", "Bún bò"],
        "created_at": [datetime.now().isoformat()] * 3,
    }
    df = pd.DataFrame(demo)
    df["date"] = pd.to_datetime(df["date"]).dt.date
    connected = False

# ── TABS ────────────────────────────────────────────────────────────────────
tab_today, tab_history, tab_export = st.tabs(["📅 Hôm nay", "📊 Lịch sử", "📥 Xuất dữ liệu"])

# ──────────────── TAB 1: HÔM NAY ────────────────────────────────────────────
with tab_today:
    today = date.today()
    df_today = df[df["date"] == today].copy()
    total_today = int(df_today["amount"].sum())
    over_budget = total_today > DAILY_BENCHMARK
    remaining   = DAILY_BENCHMARK - total_today

    # KPI row
    col1, col2, col3 = st.columns(3)
    col1.metric("Chi hôm nay",   fmt_vnd(total_today))
    col2.metric("Benchmark",     fmt_vnd(DAILY_BENCHMARK))
    col3.metric(
        "Còn lại" if not over_budget else "Vượt quá",
        fmt_vnd(abs(remaining)),
        delta=f"{pct_of_benchmark(total_today)}% benchmark",
        delta_color="inverse" if not over_budget else "normal",
    )

    st.markdown("")

    # Status
    if total_today == 0:
        st.info("📭 Hôm nay chưa có khoản chi nào. Thêm khoản đầu tiên nhé!")
    elif not over_budget:
        st.markdown(f"""
        <div class="status-ok">
            <b>🎉 Congratulations!</b> Bạn đang chi tiêu trong mức cho phép.<br>
            Còn lại <b>{fmt_vnd(remaining)}</b> ({100 - pct_of_benchmark(total_today):.1f}% benchmark).
        </div>""", unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <div class="status-warn">
            <b>⚠️ Xem xét lại!</b> Bạn đã vượt benchmark <b>{fmt_vnd(abs(remaining))}</b>
            ({pct_of_benchmark(total_today):.1f}% so với benchmark).
        </div>""", unsafe_allow_html=True)

    st.markdown("")

    # Biểu đồ hôm nay
    if not df_today.empty:
        import plotly.express as px
        import plotly.graph_objects as go

        col_chart, col_table = st.columns([1, 1])

        with col_chart:
            cat_sum = df_today.groupby("category")["amount"].sum().reset_index()
            fig = px.pie(
                cat_sum, values="amount", names="category",
                color="category", color_discrete_map=CAT_COLORS,
                hole=0.45,
            )
            fig.update_traces(textinfo="percent+label", textfont_size=13)
            fig.update_layout(
                margin=dict(t=10, b=10, l=10, r=10),
                showlegend=False, height=260,
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
            )
            st.plotly_chart(fig, use_container_width=True)

        with col_table:
            st.markdown("**Danh sách hôm nay**")
            display = df_today[["category", "amount", "note"]].copy()
            display["amount"] = display["amount"].apply(fmt_vnd)
            display.columns = ["Danh mục", "Số tiền", "Ghi chú"]
            st.dataframe(display, use_container_width=True, hide_index=True)

        # Thanh % benchmark
        pct = min(pct_of_benchmark(total_today), 150)
        bar_color = "#2ECC71" if pct <= 100 else "#E07B5D"
        st.markdown(f"""
        <div style="margin:16px 0 4px;font-size:13px;color:#888;">
            Tiến độ benchmark ({pct_of_benchmark(total_today):.1f}%)
        </div>
        <div style="background:#F0EDE8;border-radius:6px;height:10px;overflow:hidden;">
            <div style="width:{min(pct,100)}%;background:{bar_color};height:100%;border-radius:6px;
                        transition:width .4s ease;"></div>
        </div>
        """, unsafe_allow_html=True)


# ──────────────── TAB 2: LỊCH SỬ ────────────────────────────────────────────
with tab_history:
    if df.empty:
        st.info("Chưa có dữ liệu.")
    else:
        import plotly.express as px

        # Chọn khoảng thời gian
        col_f1, col_f2 = st.columns(2)
        with col_f1:
            date_from = st.date_input("Từ ngày", value=date.today() - timedelta(days=29))
        with col_f2:
            date_to = st.date_input("Đến ngày", value=date.today())

        mask = (df["date"] >= date_from) & (df["date"] <= date_to)
        df_range = df[mask].copy()

        if df_range.empty:
            st.warning("Không có dữ liệu trong khoảng thời gian này.")
        else:
            # Daily total bar chart
            daily = df_range.groupby("date")["amount"].sum().reset_index()
            daily["over"] = daily["amount"] > DAILY_BENCHMARK

            fig_bar = px.bar(
                daily, x="date", y="amount",
                color="over",
                color_discrete_map={True: "#E07B5D", False: "#5D8FE0"},
                labels={"amount": "Chi tiêu (đ)", "date": "Ngày", "over": "Vượt benchmark"},
            )
            fig_bar.add_hline(
                y=DAILY_BENCHMARK, line_dash="dash",
                line_color="#888", annotation_text="Benchmark",
            )
            fig_bar.update_layout(
                height=300, showlegend=False,
                margin=dict(t=10, b=10),
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                yaxis=dict(gridcolor="#F0EDE8"),
            )
            st.plotly_chart(fig_bar, use_container_width=True)

            # Summary stats
            c1, c2, c3, c4 = st.columns(4)
            days_over = int(daily["over"].sum())
            c1.metric("Tổng chi", fmt_vnd(int(df_range["amount"].sum())))
            c2.metric("TB/ngày",  fmt_vnd(int(daily["amount"].mean())))
            c3.metric("Ngày vượt benchmark", f"{days_over} ngày")
            c4.metric("Ngày tiết kiệm",
                      f"{len(daily) - days_over} ngày")

            # Category breakdown
            st.markdown("---")
            st.markdown("**Phân bổ theo danh mục**")
            cat_total = df_range.groupby("category")["amount"].sum().reset_index()
            fig_cat = px.bar(
                cat_total.sort_values("amount"),
                x="amount", y="category", orientation="h",
                color="category", color_discrete_map=CAT_COLORS,
                labels={"amount": "Tổng (đ)", "category": ""},
            )
            fig_cat.update_layout(
                height=220, showlegend=False,
                margin=dict(t=0, b=0),
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                xaxis=dict(gridcolor="#F0EDE8"),
            )
            st.plotly_chart(fig_cat, use_container_width=True)

            # Raw table
            with st.expander("📋 Xem toàn bộ giao dịch"):
                show = df_range.sort_values("date", ascending=False).copy()
                show["amount"] = show["amount"].apply(fmt_vnd)
                show.columns = [c.title() for c in show.columns]
                st.dataframe(show, use_container_width=True, hide_index=True)


# ──────────────── TAB 3: XUẤT DỮ LIỆU ──────────────────────────────────────
with tab_export:
    st.markdown("### 📥 Tải dữ liệu về máy")

    if df.empty:
        st.info("Chưa có dữ liệu để xuất.")
    else:
        col_e1, col_e2 = st.columns(2)

        # CSV
        csv_buf = df.to_csv(index=False).encode("utf-8-sig")
        col_e1.download_button(
            label="⬇️ Tải CSV (cho Power BI)",
            data=csv_buf,
            file_name=f"chi_tieu_{date.today()}.csv",
            mime="text/csv",
            use_container_width=True,
        )

        # Excel
        excel_buf = io.BytesIO()
        with pd.ExcelWriter(excel_buf, engine="xlsxwriter") as writer:
            df.to_excel(writer, index=False, sheet_name="ChiTieu")
            # Worksheet tổng hợp
            summary = df.groupby(["date", "category"])["amount"].sum().reset_index()
            summary.to_excel(writer, index=False, sheet_name="TongHop")
        excel_buf.seek(0)

        col_e2.download_button(
            label="⬇️ Tải Excel",
            data=excel_buf,
            file_name=f"chi_tieu_{date.today()}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )

        st.markdown("---")
        st.markdown("**💡 Kết nối thẳng Power BI vào Google Sheets:**")
        st.markdown("""
        1. Mở Power BI Desktop → **Get Data** → **Web**
        2. Dán URL Google Sheet của bạn (dạng `https://docs.google.com/spreadsheets/d/...`)
        3. Đổi `/edit` → `/export?format=csv`
        4. Nhấn **OK** → dữ liệu tự cập nhật mỗi khi refresh
        """)

        # Preview
        st.markdown("---")
        st.markdown("**Preview dữ liệu**")
        st.dataframe(df.tail(20), use_container_width=True, hide_index=True)
