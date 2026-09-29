import math
import os
import uuid
from collections import Counter
from datetime import date, datetime, timedelta

import mysql.connector
import pandas as pd
import streamlit as st

# --- CẤU HÌNH TRANG ---
st.set_page_config(page_title="Smart Tour", page_icon="🌴", layout="wide")

# --- CẤU HÌNH MYSQL AIVEN ---
DB_CONFIG = {
    "host": "mysql-1b346c1b-kimchi8019-4ea9.e.aivencloud.com",
    "port": 21314,
    "user": "avnadmin",
    "password": "AVNS_ZuLUVTHk6cKBskjg0Kp",
    "database": "smarttour_db",
    "ssl_disabled": False,
    "connection_timeout": 15,
    "charset": "utf8mb4",
}

VAT_RATE = 0.08
DEPOSIT_RATE = 0.30
MAX_DISCOUNT_PCT = 0.20

TOURS = {
    "T01": {
        "name": "Khám Phá Hạ Long Rồng Việt",
        "duration": "3 ngày 2 đêm",
        "price": 3500000,
        "desc": "Du thuyền 5 sao, thăm hang Sửng Sốt, đảo Ti Tốp, chèo thuyền Kayak.",
        "image": "https://images.unsplash.com/photo-1528127269322-539801943592?auto=format&fit=crop&w=600&q=80"
    },
    "T02": {
        "name": "Đà Nẵng - Hội An - Bà Nà Hills",
        "duration": "4 ngày 3 đêm",
        "price": 4800000,
        "desc": "Check-in Cầu Vàng, phố cổ Hội An đêm đèn lồng, tắm biển Mỹ Khê.",
        "image": "https://images.unsplash.com/photo-1559592413-7cec4d0cae2b?auto=format&fit=crop&w=600&q=80"
    },
    "T03": {
        "name": "Phú Quốc Thiên Đường Biển Ngọc",
        "duration": "3 ngày 2 đêm",
        "price": 5200000,
        "desc": "Cáp treo Hòn Thơm, VinWonders, ngắm hoàng hôn Sanato, lặn ngắm san hô.",
        "image": "https://images.unsplash.com/photo-1540202404-a2f29016b523?auto=format&fit=crop&w=600&q=80"
    },
    "T04": {
        "name": "Sapa Sương Mù - Đỉnh Fansipan",
        "duration": "2 ngày 1 đêm",
        "price": 2900000,
        "desc": "Săn mây Fansipan, bản Cát Cát, thưởng thức lẩu thắng cố và đồ nướng Sapa.",
        "image": "https://images.unsplash.com/photo-1508873696983-2df515122519?auto=format&fit=crop&w=600&q=80"
    }
}

# --- KẾT NỐI DATABASE ---
def get_db_connection():
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        return conn
    except Exception as e:
        st.error(f"Lỗi kết nối CSDL: {e}")
        return None

# --- KHỞI TẠO BẢNG CSDL TỰ ĐỘNG ---
def init_db():
    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS bookings (
                id VARCHAR(50) PRIMARY KEY,
                customer_name VARCHAR(100),
                phone VARCHAR(20),
                email VARCHAR(100),
                tour_id VARCHAR(20),
                tour_name VARCHAR(100),
                departure_date DATE,
                num_adults INT,
                num_children INT,
                total_price DOUBLE,
                deposit_amount DOUBLE,
                discount_amount DOUBLE,
                status VARCHAR(20),
                created_at DATETIME
            )
            """)
            conn.commit()
            cursor.close()
            conn.close()
        except Exception as e:
            st.error(f"Lỗi khởi tạo DB: {e}")

init_db()

# --- CSS TÙY CHỈNH GIAO DIỆN MODERN ---
st.markdown("""
<style>
    .main { background-color: #f8f9fa; }
    .stButton>button {
        background-color: #0066cc;
        color: white;
        border-radius: 8px;
        border: none;
        padding: 0.5rem 1rem;
        font-weight: 600;
    }
    .stButton>button:hover { background-color: #004c99; color: white; }
    .card {
        background: white;
        padding: 1.5rem;
        border-radius: 12px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        margin-bottom: 1rem;
    }
    .metric-card {
        background: linear-gradient(135deg, #0066cc 0%, #004c99 100%);
        color: white;
        padding: 1.2rem;
        border-radius: 10px;
        text-align: center;
    }
</style>
""", unsafe_allow_html=True)

# --- SIDEBAR ĐIỀU HƯỚNG ---
with st.sidebar:
    st.title("🌴 Smart Tour Admin")
    st.markdown("---")
    menu = st.radio("Điều hướng hệ thống", ["Danh Sách Tour", "Đặt Tour Mới", "Quản Lý Đơn Đặt Tour", "Thống Kê Doanh Thu"])

# --- HEADER TRANG ---
st.title("☀️ Hệ Thống Quản Lý Đặt Tour Du Lịch")
st.caption("Giải pháp quản lý tour, booking và thống kê doanh thu")
st.markdown("---")

# --- TAB 1: DANH SÁCH TOUR ---
if menu == "Danh Sách Tour":
    st.header("📋 Danh Sách Tour Du Lịch Nổi Bật")
    cols = st.columns(2)
    for idx, (t_id, tour) in enumerate(TOURS.items()):
        with cols[idx % 2]:
            st.markdown(f"""
            <div class="card">
                <img src="{tour['image']}" style="width:100%; height:200px; object-fit:cover; border-radius:8px;">
                <h3 style="margin-top:10px; color:#0066cc;">{tour['name']} ({t_id})</h3>
                <p><b>Thời gian:</b> {tour['duration']}</p>
                <p><b>Giá tour:</b> <span style="color:#e63946; font-size:1.2rem; font-weight:bold;">{tour['price']:,} VNĐ</span>/khách</p>
                <p>{tour['desc']}</p>
            </div>
            """, unsafe_allow_html=True)

# --- TAB 2: ĐẶT TOUR MỚI ---
elif menu == "Đặt Tour Mới":
    st.header("📝 Biểu Mẫu Đặt Tour Trực Tuyến")
    
    with st.form("booking_form"):
        col1, col2 = st.columns(2)
        with col1:
            c_name = st.text_input("Họ và tên khách hàng *")
            c_phone = st.text_input("Số điện thoại *")
            c_email = st.text_input("Địa chỉ Email")
            tour_selected = st.selectbox("Chọn Tour Du Lịch *", list(TOURS.keys()), format_func=lambda x: f"{x} - {TOURS[x]['name']}")
        
        with col2:
            dep_date = st.date_input("Ngày khởi hành *", min_value=date.today())
            n_adults = st.number_input("Số lượng người lớn (100% giá)", min_value=1, value=1)
            n_children = st.number_input("Số lượng trẻ em (70% giá)", min_value=0, value=0)
            discount_code = st.text_input("Mã giảm giá (nếu có)")
            
        submitted = st.form_submit_button("Xác Nhận Đặt Tour")
        
        if submitted:
            if not c_name or not c_phone:
                st.error("Vui lòng điền đầy đủ Họ tên và Số điện thoại!")
            else:
                base_price = TOURS[tour_selected]['price']
                raw_total = (n_adults * base_price) + (n_children * base_price * 0.7)
                
                discount_amt = 0
                if discount_code.upper() == "SMART20":
                    discount_amt = raw_total * MAX_DISCOUNT_PCT
                
                vat_amt = (raw_total - discount_amt) * VAT_RATE
                final_total = (raw_total - discount_amt) + vat_amt
                deposit_required = final_total * DEPOSIT_RATE
                
                booking_id = f"BK-{uuid.uuid4().hex[:6].upper()}"
                
                conn = get_db_connection()
                if conn:
                    try:
                        cursor = conn.cursor()
                        query = """
                        INSERT INTO bookings 
                        (id, customer_name, phone, email, tour_id, tour_name, departure_date, num_adults, num_children, total_price, deposit_amount, discount_amount, status, created_at)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """
                        val = (
                            booking_id, c_name, c_phone, c_email, tour_selected, 
                            TOURS[tour_selected]['name'], dep_date, n_adults, n_children, 
                            final_total, deposit_required, discount_amt, "Chờ xác nhận", datetime.now()
                        )
                        cursor.execute(query, val)
                        conn.commit()
                        cursor.close()
                        conn.close()
                        
                        st.success(f"🎉 Đặt tour thành công! Mã đơn: **{booking_id}**")
                        st.info(f"Tổng tiền: **{final_total:,.0f} VNĐ** (Đã bao gồm VAT) | Tối thiểu cọc: **{deposit_required:,.0f} VNĐ**")
                    except Exception as e:
                        st.error(f"Lỗi lưu booking: {e}")

# --- TAB 3: QUẢN LÝ ĐƠN ĐẶT TOUR ---
elif menu == "Quản Lý Đơn Đặt Tour":
    st.header("📂 Danh Sách Đơn Đặt Tour Trong Hệ Thống")
    
    conn = get_db_connection()
    if conn:
        try:
            df = pd.read_sql("SELECT * FROM bookings ORDER BY created_at DESC", conn)
            conn.close()
            
            if df.empty:
                st.warning("Chưa có đơn đặt tour nào trong hệ thống.")
            else:
                st.dataframe(
                    df,
                    column_config={
                        "id": "Mã Booking",
                        "customer_name": "Khách Hàng",
                        "phone": "Số Điện Thoại",
                        "tour_name": "Tên Tour",
                        "departure_date": "Ngày Đi",
                        "total_price": st.column_config.NumberColumn("Tổng Tiền (VNĐ)", format="%d"),
                        "deposit_amount": st.column_config.NumberColumn("Tiền Cọc (VNĐ)", format="%d"),
                        "status": "Trạng Thái"
                    },
                    use_container_width=True
                )
        except Exception as e:
            st.error(f"Lỗi tải dữ liệu: {e}")

# --- TAB 4: THỐNG KÊ DOANH THU ---
elif menu == "Thống Kê Doanh Thu":
    st.header("📊 Báo Cáo & Thống Kê Kinh Doanh")
    
    conn = get_db_connection()
    if conn:
        try:
            df = pd.read_sql("SELECT * FROM bookings", conn)
            conn.close()
            
            if not df.empty:
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Tổng Đơn Đặt", f"{len(df)} đơn")
                with col2:
                    st.metric("Tổng Doanh Thu", f"{df['total_price'].sum():,.0f} VNĐ")
                with col3:
                    st.metric("Tổng Tiền Cọc Đã Nhận", f"{df['deposit_amount'].sum():,.0f} VNĐ")
                
                st.markdown("---")
                st.subheader("Doanh Thu Theo Tour")
                tour_summary = df.groupby("tour_name")["total_price"].sum().reset_index()
                st.bar_chart(tour_summary, x="tour_name", y="total_price")
            else:
                st.info("Chưa có dữ liệu thống kê.")
        except Exception as e:
            st.error(f"Lỗi tải thống kê: {e}")
