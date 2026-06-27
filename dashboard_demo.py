import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import os

st.set_page_config(page_title="25D03 产出趋势看板", layout="wide")

EXCEL_PATH = os.path.join(os.path.dirname(__file__), "25D0304白夜班数据.xlsx")

@st.cache_data
def load_data():
    df = pd.read_excel(EXCEL_PATH, sheet_name="Sheet2")
    df["日期"] = pd.to_datetime(df["日期"])
    df = df.dropna(subset=["产出数量"]).copy()
    df["产出数量"] = df["产出数量"].astype(int)
    return df

df = load_data()

min_date = df["日期"].min()
max_date = df["日期"].max()
PRODUCT_ORDER = ["车架", "座垫管", "前护杠", "后平叉", "方向把"]
LINE_ORDER = ["一线", "二线", "三线"]
LINE_COLORS = {"一线": "#2E86C1", "二线": "#E67E22", "三线": "#7D3C98"}

st.sidebar.title("筛选条件")
selected_date = st.sidebar.date_input(
    "截止日期（图右端）",
    value=max_date,
    min_value=min_date,
    max_value=max_date,
)
sel_products = st.sidebar.multiselect("产品", PRODUCT_ORDER, default=PRODUCT_ORDER)
sel_lines = st.sidebar.multiselect("产线", [l for l in LINE_ORDER], default=LINE_ORDER)

selected_date = pd.Timestamp(selected_date)
df_f = df[df["日期"] <= selected_date].copy()

st.title("25D03 白夜班产出趋势 — 产品对比")
st.caption(f"数据范围：{min_date.date()} → {selected_date.date()}　|　产品：{', '.join(sel_products)}　|　产线：{', '.join(sel_lines)}")

st.subheader("📈 各产品总产出趋势")
agg = df_f[df_f["产品"].isin(sel_products) & df_f["线别"].isin(sel_lines)].groupby(
    ["日期", "产品"], as_index=False
)["产出数量"].sum()
PRODUCT_COLORS = {"车架": "#E74C3C", "座垫管": "#3498DB", "前护杠": "#2ECC71", "后平叉": "#F39C12", "方向把": "#1ABC9C"}
top_cols = st.columns(len(PRODUCT_ORDER))
for idx, prod in enumerate(PRODUCT_ORDER):
    with top_cols[idx]:
        pdf = agg[agg["产品"] == prod].sort_values("日期")
        if pdf.empty:
            st.info(f"{prod} 无数据")
            continue
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=pdf["日期"], y=pdf["产出数量"],
            mode="lines+markers",
            name=prod,
            line=dict(color=PRODUCT_COLORS[prod], width=3),
            marker=dict(size=6, color=PRODUCT_COLORS[prod]),
            fill="tozeroy",
            fillcolor=f"rgba{tuple(int(PRODUCT_COLORS[prod].lstrip('#')[i:i+2], 16) for i in (0, 2, 4)) + (0.15,)}",
            hovertemplate=f"{prod}<br>%{{x|%m-%d}}<br>总产出: %{{y}}件<extra></extra>",
        ))
        fig.update_layout(
            title=f"<b>{prod}</b>",
            height=220, margin=dict(t=30, b=15, l=10, r=10),
            showlegend=False,
            xaxis=dict(range=[min_date, selected_date], dtick="D1", tickformat="%m-%d", tickangle=45),
            yaxis=dict(title=""),
            hovermode="x unified",
        )
        fig.add_vline(x=selected_date, line_dash="dash", line_color="gray", opacity=0.3)
        st.plotly_chart(fig, use_container_width=True)

st.divider()

SHIFT_LABELS = {"白班": "🌞 白班", "夜班": "🌙 夜班"}

for prod in [p for p in PRODUCT_ORDER if p in sel_products]:
    with st.container():
        st.divider()
        st.subheader(f"📦 {prod}")
        col_left, col_right = st.columns(2)

        for col, shift in [(col_left, "白班"), (col_right, "夜班")]:
            with col:
                st.caption(SHIFT_LABELS[shift])
                sdf = df_f[(df_f["班次"] == shift) & (df_f["产品"] == prod)]
                active_lines = [l for l in sel_lines if l in sdf["线别"].values]
                if not active_lines:
                    st.info("暂无数据")
                    continue

                fig = make_subplots(
                    rows=len(active_lines), cols=1,
                    subplot_titles=[f"{line}" for line in active_lines],
                    shared_xaxes=True,
                    vertical_spacing=0.1,
                )
                for j, line in enumerate(active_lines, 1):
                    ldf = sdf[sdf["线别"] == line].sort_values("日期")
                    fig.add_trace(
                        go.Scatter(
                            x=ldf["日期"], y=ldf["产出数量"],
                            mode="lines+markers",
                            name=line,
                            line=dict(color=LINE_COLORS[line], width=2.5),
                            marker=dict(size=6, color=LINE_COLORS[line]),
                            hovertemplate=f"{prod}-{shift}-{line}<br>%{{x|%m-%d}}<br>产出: %{{y}}件<extra></extra>",
                        ),
                        row=j, col=1,
                    )
                    fig.update_xaxes(
                        range=[min_date, selected_date],
                        dtick="D1", tickformat="%m-%d",
                        row=j, col=1,
                    )
                    fig.add_vline(
                        x=selected_date, line_dash="dash",
                        line_color="gray", opacity=0.3,
                        row=j, col=1,
                    )

                fig.update_layout(
                    height=140 * len(active_lines),
                    showlegend=False,
                    margin=dict(t=25, b=5, l=10, r=10),
                    hovermode="x unified",
                )
                st.plotly_chart(fig, use_container_width=True)

        # Show selected-date output below charts
        today_df = df_f[(df_f["日期"] == selected_date) & (df_f["产品"] == prod) & (df_f["线别"].isin(sel_lines))]
        if not today_df.empty:
            st.markdown(f"<p style='margin:12px 0 2px;font-size:0.85rem;color:#888;'>📋 当日产出（{selected_date.date()}）</p>", unsafe_allow_html=True)
            for line in sel_lines:
                rd = today_df[today_df["线别"] == line]
                if rd.empty:
                    continue
                day_qty = int(rd[rd["班次"] == "白班"]["产出数量"].sum())
                night_qty = int(rd[rd["班次"] == "夜班"]["产出数量"].sum())
                if not (day_qty or night_qty):
                    continue
                c1, c2, c3, c4 = st.columns([1, 1.5, 1.5, 1.5])
                c1.markdown(f"<div style='display:flex;align-items:center;height:70px;font-weight:600;font-size:1rem;'>{line}</div>", unsafe_allow_html=True)
                c2.metric("🌞 白班", f"{day_qty}", delta_color="off")
                c3.metric("🌙 夜班", f"{night_qty}", delta_color="off")
                c4.metric("📊 合计", f"{day_qty + night_qty}", delta_color="off")
