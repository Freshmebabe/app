import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta, timezone
from collections import defaultdict
from database import get_db_connection

# Streamlit Cloud 服务器使用 UTC，用户在中国（UTC+8）
CHINA_TZ = timezone(timedelta(hours=8))


def calendar_page():
    st.write("### 📅 饮食日历与统计")
    
    cal_tabs = st.tabs(["🗓️ 日历视图", "📊 统计图表"])
    user_id = st.session_state.current_user['username']

    with cal_tabs[0]:
        st.caption("查看过去30天的饮食记录")
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        thirty_days_ago = (datetime.now(CHINA_TZ) - timedelta(days=30)).date()
        cursor.execute("""
            SELECT date, food_name, meal_time, rating
            FROM eat_history
            WHERE user_id = %s AND date >= %s
            ORDER BY date DESC, created_at DESC
        """, (user_id, thirty_days_ago.isoformat()))
        
        records = cursor.fetchall()
        
        if records:
            by_date = defaultdict(list)
            for rec in records:
                by_date[rec['date']].append(rec)
            
            for date in sorted(by_date.keys(), reverse=True):
                st.markdown(f"##### 📆 {date}")
                for rec in by_date[date]:
                    meal_emoji = {"早餐": "🌅", "午餐": "☀️", "下午茶": "🍰", "晚餐": "🌙", "夜宵": "🌃"}.get(rec['meal_time'], "🍽️")
                    rating_stars = "⭐" * (rec['rating'] or 0)
                    st.markdown(f"<span style='font-size:0.95rem;'>{meal_emoji} **{rec['meal_time']}**: {rec['food_name']} {rating_stars}</span>", unsafe_allow_html=True)
                st.markdown("<hr style='border:0.5px solid #eee'>", unsafe_allow_html=True)
        else:
            st.info("还没有饮食记录哦")

    with cal_tabs[1]:
        st.caption("通过图表回顾你的饮食习惯")
        
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT e.date, e.meal_time, e.food_name, e.rating, f.health_tag
            FROM eat_history e
            LEFT JOIN foods f ON e.food_name = f.name
            WHERE e.user_id = %s
        """, (user_id,))
        history_data = cursor.fetchall()
        column_names = [description[0] for description in cursor.description]

        if not history_data:
            st.info("还没有足够的饮食记录来生成统计图表哦。")
        else:
            df = pd.DataFrame(history_data, columns=column_names)
            df['date'] = pd.to_datetime(df['date'])

            st.write("#### 📅 最近30天饮食热力图")
            thirty_days_ago = pd.to_datetime(datetime.now(CHINA_TZ) - timedelta(days=30))
            recent_df = df[df['date'] >= thirty_days_ago]
            
            if not recent_df.empty:
                daily_counts = recent_df.groupby(df['date'].dt.date).size().reset_index(name='counts')
                daily_counts['date'] = pd.to_datetime(daily_counts['date'])
                date_range = pd.date_range(start=daily_counts['date'].min(), end=daily_counts['date'].max())
                full_range_df = pd.DataFrame(date_range, columns=['date'])
                daily_counts = pd.merge(full_range_df, daily_counts, on='date', how='left').fillna(0)

                fig_heatmap = px.density_heatmap(daily_counts, x=daily_counts['date'].dt.dayofweek, y=daily_counts['date'].dt.isocalendar().week, z='counts', labels={'x': '星期', 'y': '周数', 'z': '记录数'}, title="每日记录数 (颜色越深记录越多)", text_auto=True, color_continuous_scale="Greens")
                fig_heatmap.update_layout(yaxis_title="周数", xaxis_title="星期", xaxis={'ticktext': ['一', '二', '三', '四', '五', '六', '日'], 'tickvals': list(range(7))})
                st.plotly_chart(fig_heatmap, use_container_width=True)
            else:
                st.info("最近30天没有饮食记录。")

            st.divider()
            col1, col2 = st.columns(2)
            with col1:
                st.write("#### 🍽️ 餐次分布")
                meal_counts = df['meal_time'].value_counts().reset_index()
                fig_pie = px.pie(meal_counts, values='count', names='meal_time', title="各项餐次占比")
                st.plotly_chart(fig_pie, use_container_width=True)
            with col2:
                st.write("#### 🍔 健康标签分布")
                health_tag_counts = df['health_tag'].value_counts().reset_index()
                fig_bar = px.bar(health_tag_counts, x='health_tag', y='count', title="各类饮食标签占比", labels={'health_tag': '健康标签', 'count': '次数'})
                st.plotly_chart(fig_bar, use_container_width=True)
