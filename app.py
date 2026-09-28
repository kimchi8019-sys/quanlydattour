import math
import os
import uuid
from collections import Counter
from datetime import date, datetime, timedelta

import mysql.connector
import pandas as pd
from google import genai
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
response = client.models.generate_content(
    model="gemini-2.5-flash",
    contents=user_prompt,  # biến chứa câu hỏi của người dùng
)
bot_reply = response.text

VAT_RATE = 0.08
DEPOSIT_RATE = 0.30
MAX_DISCOUNT_PCT = 0.20

TOURS = {
    "T01": {
        "name": "Đà Nẵng - Hội An - Bà Nà Hills", "days": 4, "base": 4_990_000,
        "transport": "Máy bay khứ hồi", "room_base": 600_000,
        "highlights": "Bà Nà Hills, Cầu Vàng, phố cổ Hội An, biển Mỹ Khê",
        "hotels": [("Han Riverside", 3), ("Novotel Danang", 4), ("Furama Resort", 5)],
        "times": ["05:30", "08:00", "13:30"],
    },
    "T02": {
        "name": "Phú Quốc - Đảo Ngọc", "days": 3, "base": 5_490_000,
        "transport": "Máy bay khứ hồi", "room_base": 750_000,
        "highlights": "Vinpearl Safari, cáp treo Hòn Thơm, lặn ngắm san hô",
        "hotels": [("Sea Star", 3), ("Sol by Melia", 4), ("JW Marriott", 5)],
        "times": ["06:00", "09:30", "14:00"],
    },
    "T03": {
        "name": "Sa Pa - Fansipan - Bản Cát Cát", "days": 3, "base": 3_890_000,
        "transport": "Xe limousine giường nằm", "room_base": 500_000,
        "highlights": "Fansipan, bản Cát Cát, thác Bạc, chợ tình",
        "hotels": [("Sapa Central", 3), ("Pao's Sapa Leisure", 4), ("Hotel de la Coupole", 5)],
        "times": ["20:00", "22:00"],
    },
    "T04": {
        "name": "Hạ Long - Yên Tử", "days": 3, "base": 3_590_000,
        "transport": "Xe du lịch đời mới", "room_base": 550_000,
        "highlights": "Du thuyền vịnh Hạ Long, hang Sửng Sốt, chùa Yên Tử",
        "hotels": [("Hạ Long Bay Hotel", 3), ("Wyndham Legend", 4), ("Vinpearl Resort", 5)],
        "times": ["06:30", "08:00"],
    },
    "T05": {
        "name": "Đà Lạt - Thành phố ngàn hoa", "days": 3, "base": 3_290_000,
        "transport": "Xe limousine", "room_base": 450_000,
        "highlights": "Hồ Xuân Hương, đồi chè Cầu Đất, Langbiang, chợ đêm",
        "hotels": [("Dalat Palace Lite", 3), ("Ana Mandara Villas", 4), ("Dalat Palace Heritage", 5)],
        "times": ["05:30", "07:30", "13:00"],
    },
}

STAR_MULT = {3: 1.0, 4: 1.7, 5: 3.0}
ROOM_TYPES = {
    "Standard": {"mult": 1.0, "cap": 2},
    "Deluxe": {"mult": 1.4, "cap": 3},
    "Suite": {"mult": 2.3, "cap": 4},
}

AGE_GROUPS = [
    (0, 1, "Em bé (dưới 2 tuổi)", 0.10),
    (2, 4, "Trẻ nhỏ (2-4 tuổi)", 0.50),
    (5, 11, "Trẻ em (5-11 tuổi)", 0.75),
    (12, 59, "Người lớn (12-59 tuổi)", 1.00),
    (60, 120, "Cao tuổi (60+)", 0.90),
]

TOUR_SEASON = {"peak": 1.25, "high": 1.10, "normal": 1.00, "low": 0.92}
HOTEL_SEASON = {"peak": 1.60, "high": 1.20, "normal": 1.00, "low": 0.85}

EXTRAS = {
    "Bảo hiểm du lịch": {"price": 60_000, "unit": "người"},
    "Đưa đón sân bay/ga 2 chiều": {"price": 400_000, "unit": "xe (4 khách)"},
    "Hướng dẫn viên riêng": {"price": 1_200_000, "unit": "ngày"},
    "Gói ăn uống nâng cấp": {"price": 250_000, "unit": "người/ngày"},
    "Vé tham quan VIP (fast-track)": {"price": 300_000, "unit": "người"},
}

HOLIDAYS = [
    (date(2026, 12, 24), date(2027, 1, 3)),
    (date(2027, 2, 3), date(2027, 2, 12)),
    (date(2027, 4, 28), date(2027, 5, 3)),
]

def vnd(x: float) -> str:
    return f"{x:,.0f}".replace(",", ".") + " ₫"

def season_of(d: date) -> str:
    if any(a <= d <= b for a, b in HOLIDAYS):
        return "peak"
    if d.month in (6, 7, 8):
        return "high"
    if (d.month == 9 and d.day >= 5) or d.month == 10 or (d.month == 11 and d.day <= 15):
        return "low"
    return "normal"

def age_group(age: int):
    for lo, hi, label, factor in AGE_GROUPS:
        if lo <= age <= hi:
            return label, factor
    return AGE_GROUPS[-1][2], AGE_GROUPS[-1][3]

def room_price(tour: dict, stars: int, room_type: str) -> float:
    return round(tour["room_base"] * STAR_MULT[stars] * ROOM_TYPES[room_type]["mult"], -3)

DDL = [
    """CREATE TABLE IF NOT EXISTS bookings (
        code VARCHAR(20) PRIMARY KEY,
        created_at DATETIME NOT NULL,
        customer VARCHAR(120) NOT NULL,
        phone VARCHAR(20) NOT NULL,
        email VARCHAR(120) NOT NULL,
        tour_id VARCHAR(10) NOT NULL,
        tour_name VARCHAR(200) NOT NULL,
        depart_at DATETIME NOT NULL,
        return_at DATETIME NOT NULL,
        n_guests INT NOT NULL,
        hotel VARCHAR(200),
        rooms VARCHAR(200),
        subtotal DECIMAL(14,2) DEFAULT 0,
        discount DECIMAL(14,2) DEFAULT 0,
        vat DECIMAL(14,2) DEFAULT 0,
        total DECIMAL(14,2) NOT NULL,
        deposit DECIMAL(14,2) NOT NULL,
        payment VARCHAR(60),
        note TEXT,
        status VARCHAR(40) NOT NULL DEFAULT 'Chờ thanh toán cọc'
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
    """CREATE TABLE IF NOT EXISTS booking_guests (
        id INT AUTO_INCREMENT PRIMARY KEY,
        booking_code VARCHAR(20) NOT NULL,
        guest_no INT NOT NULL,
        age INT NOT NULL,
        age_group VARCHAR(60)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
    """CREATE TABLE IF NOT EXISTS booking_lines (
        id INT AUTO_INCREMENT PRIMARY KEY,
        booking_code VARCHAR(20) NOT NULL,
        category VARCHAR(40),
        detail VARCHAR(300),
        amount DECIMAL(14,2) NOT NULL
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
]

def get_conn():
    return mysql.connector.connect(**DB_CONFIG)

def init_db():
    try:
        base_cfg = DB_CONFIG.copy()
        db_name = base_cfg.pop("database")
        conn = mysql.connector.connect(**base_cfg)
        cur = conn.cursor()
        cur.execute(f"CREATE DATABASE IF NOT EXISTS {db_name} CHARACTER SET utf8mb4")
        cur.close()
        conn.close()

        conn = get_conn()
        cur = conn.cursor()
        for q in DDL:
            cur.execute(q)
        conn.commit()
        cur.close()
        conn.close()
        return None
    except Exception as e:
        return str(e)

def insert_booking(b, tour_id, quote, ages):
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO bookings (code, created_at, customer, phone, email, tour_id, tour_name,
               depart_at, return_at, n_guests, hotel, rooms, subtotal, discount, vat, total, deposit, payment, note, status)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
            (
                b["code"], datetime.now(), b["customer"], b["phone"], b["email"], tour_id, b["tour"],
                b["depart"], b["return"], b["n_guests"], b["hotel"], b["rooms"], quote["subtotal"],
                quote["discount"], quote["vat"], quote["total"], quote["deposit"], b["payment"],
                b["note"], b["status"]
            )
        )
        cur.executemany(
            "INSERT INTO booking_guests (booking_code, guest_no, age, age_group) VALUES (%s,%s,%s,%s)",
            [(b["code"], i + 1, int(a), age_group(int(a))[0]) for i, a in enumerate(ages)]
        )
        cur.executemany(
            "INSERT INTO booking_lines (booking_code, category, detail, amount) VALUES (%s,%s,%s,%s)",
            [(b["code"], ln["Hạng mục"], ln["Chi tiết"], float(ln["Thành tiền"])) for ln in quote["lines"]]
        )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

def fetch_bookings(keyword="", limit=50):
    conn = get_conn()
    try:
        cur = conn.cursor(dictionary=True)
        if keyword:
            cur.execute(
                "SELECT * FROM bookings WHERE code=%s OR phone=%s OR email=%s ORDER BY created_at DESC LIMIT %s",
                (keyword, keyword, keyword, limit)
            )
        else:
            cur.execute("SELECT * FROM bookings ORDER BY created_at DESC LIMIT %s", (limit,))
        return cur.fetchall()
    finally:
        conn.close()

def calc_quote(tour, depart, ages, hotel, rooms, extras, promo_code):
    lines = []
    n_guests = len(ages)
    season = season_of(depart)
    t_mult = TOUR_SEASON[season]

    tour_fare = 0.0
    for label, cnt in Counter(age_group(a)[0] for a in ages).items():
        factor = next(f for _, _, l, f in AGE_GROUPS if l == label)
        unit = round(tour["base"] * t_mult * factor, -3)
        tour_fare += unit * cnt
        lines.append({"Hạng mục": "Tour", "Chi tiết": f"{label} × {cnt} ({vnd(unit)}/người)", "Thành tiền": unit * cnt})

    hotel_total = 0.0
    if hotel and sum(rooms.values()) > 0:
        h_name, stars = hotel
        nights = tour["days"] - 1
        for rt, q in rooms.items():
            if q:
                p = round(room_price(tour, stars, rt) * nights, -3)
                hotel_total += p * q
                lines.append({"Hạng mục": "Khách sạn", "Chi tiết": f"{h_name} {stars}★ - {q} phòng {rt} × {nights} đêm", "Thành tiền": p * q})

    extras_total = 0.0
    for name in extras:
        e = EXTRAS[name]
        qty = n_guests if name == "Bảo hiểm du lịch" else 1
        amount = e["price"] * qty
        extras_total += amount
        lines.append({"Hạng mục": "Dịch vụ", "Chi tiết": f"{name} × {qty} {e['unit']}", "Thành tiền": amount})

    discount = 0.0
    subtotal = tour_fare + hotel_total + extras_total
    vat = subtotal * VAT_RATE
    total = subtotal + vat

    return {
        "lines": lines, "subtotal": subtotal, "discount": discount,
        "vat": vat, "total": total, "deposit": total * DEPOSIT_RATE
    }

# ----------------------------------------------------------------------------
# THIẾT LẬP CƠ SỞ DỮ LIỆU & THANH BÊN (SIDEBAR)
# ----------------------------------------------------------------------------
db_error = init_db()

# --- CSS TÙY CHỈNH CHATBOT CHUYÊN NGHIỆP ---
st.markdown("""
<style>
    .ai-card {
        background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
        color: white;
        padding: 12px 15px;
        border-radius: 12px;
        margin-bottom: 12px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    .ai-title {
        font-size: 15px;
        font-weight: 700;
        margin: 0;
        display: flex;
        align-items: center;
        gap: 8px;
    }
    .ai-subtitle {
        font-size: 11px;
        opacity: 0.85;
        margin-top: 2px;
    }
    .chat-bubble-bot {
        background-color: #f0f2f5;
        color: #1c1e21;
        padding: 10px 12px;
        border-radius: 15px 15px 15px 2px;
        margin-bottom: 8px;
        font-size: 13px;
        line-height: 1.4;
        border: 1px solid #e4e6eb;
    }
    .chat-bubble-user {
        background-color: #0084ff;
        color: white;
        padding: 10px 12px;
        border-radius: 15px 15px 2px 15px;
        margin-bottom: 8px;
        font-size: 13px;
        line-height: 1.4;
        text-align: right;
        margin-left: auto;
        max-width: 85%;
    }
</style>
""", unsafe_allow_html=True)

with st.sidebar:
    st.header("🗄️ Cơ sở dữ liệu")
    if db_error:
        st.error("Chưa kết nối được MySQL")
    else:
        st.success("Đã kết nối MySQL Aiven!")
        
    st.divider()

    # ================= KHU VỰC CHATBOT AI SANG TRỌNG =================
    st.markdown("""
        <div class="ai-card">
            <div class="ai-title">🤖 Trợ lý AI Smart Tour</div>
            <div class="ai-subtitle">Tư vấn lịch trình & báo giá tự động 24/7</div>
        </div>
    """, unsafe_allow_html=True)

    # Nút bấm làm mới hội thoại
    col_ai1, col_ai2 = st.columns([3, 1])
    with col_ai2:
        if st.button("🗑️ Xóa", help="Làm mới cuộc trò chuyện"):
            st.session_state.ai_chat_history = []
            st.rerun()

    # Kiểm tra thư viện AI
    has_genai = False
    sdk_type = None

    try:
        import google.generativeai as genai
        has_genai = True
        sdk_type = "legacy"
    except ImportError:
        try:
            import google.genai as genai
            has_genai = True
            sdk_type = "new"
        except ImportError:
            has_genai = False

    if not has_genai:
        st.info("💡 Bạn cần thêm `google-generativeai` vào `requirements.txt` trên GitHub để bật AI.")
    else:
        try:
            if sdk_type == "legacy":
                genai.configure(api_key=API_KEY)
                model = genai.GenerativeModel("gemini-1.5-flash")
            else:
                client = genai.Client(api_key=API_KEY)

            if "ai_chat_history" not in st.session_state or not st.session_state.ai_chat_history:
                st.session_state.ai_chat_history = [
                    {"role": "model", "content": "Xin chào! Tôi là Trợ lý AI Smart Tour 🌴. Bạn cần tư vấn tour gì hôm nay?"}
                ]

            # Khung chat hiển thị dạng bong bóng tin nhắn tinh tế
            chat_box = st.container(height=320)
            with chat_box:
                for msg in st.session_state.ai_chat_history:
                    if msg["role"] == "model":
                        st.markdown(f'<div class="chat-bubble-bot">🤖 {msg["content"]}</div>', unsafe_allow_html=True)
                    else:
                        st.markdown(f'<div class="chat-bubble-user">{msg["content"]}</div>', unsafe_allow_html=True)

            # Ô nhập liệu nhắn tin
            if user_prompt := st.chat_input("Nhập câu hỏi..."):
                st.session_state.ai_chat_history.append({"role": "user", "content": user_prompt})
                
                tour_info = "\n".join([f"- {v['name']}: {v['days']} ngày, giá từ {v['base']:,}đ, gồm {v['highlights']}" for v in TOURS.values()])
                system_context = f"Bạn là nhân viên tư vấn du lịch Smart Tour chuyên nghiệp, thân thiện. Danh sách tour đang có:\n{tour_info}\nTrả lời ngắn gọn, rõ ràng, tối đa 3-4 câu."

                if sdk_type == "legacy":
                    history_legacy = []
                    for m in st.session_state.ai_chat_history[:-1]:
                        history_legacy.append({"role": m["role"], "parts": [m["content"]]})
                    chat = model.start_chat(history=history_legacy)
                    resp = chat.send_message(f"{system_context}\n\nKhách hỏi: {user_prompt}")
                    reply = resp.text
                else:
                    resp = client.models.generate_content(
                        model="gemini-2.5-flash",
                        contents=f"{system_context}\n\nKhách hỏi: {user_prompt}"
                    )
                    reply = resp.text

                st.session_state.ai_chat_history.append({"role": "model", "content": reply})
                st.rerun()

        except Exception as e:
            st.error(f"Lỗi AI: {e}")

# ----------------------------------------------------------------------------
# GIAO DIỆN CHÍNH
# ----------------------------------------------------------------------------
st.title("🌴 Smart Tour - Quản lý & Đặt tour")

tab_book, tab_manage, tab_stats, tab_policy = st.tabs([
    "🧭 Đặt tour", 
    "📋 Đơn đặt của tôi", 
    "📊 Thống kê Nội bộ", 
    "ℹ️ Chính sách & bảng giá"
])

# TAB 1: ĐẶT TOUR
with tab_book:
    col_form, col_sum = st.columns([3, 2], gap="large")
    with col_form:
        st.subheader("1. Chọn tour")
        tour_id = st.selectbox("Tour", list(TOURS), format_func=lambda k: f"{TOURS[k]['name']} - {vnd(TOURS[k]['base'])}")
        tour = TOURS[tour_id]

        st.subheader("2. Ngày khởi hành")
        depart = st.date_input("Ngày khởi hành", value=date.today() + timedelta(days=30))

        st.subheader("3. Khách tham gia")
        n_guests = st.number_input("Tổng số khách", 1, 30, 2)
        ages = [st.number_input(f"Tuổi khách {i+1}", 0, 100, 30, key=f"a_{i}") for i in range(int(n_guests))]

        st.subheader("4. Khách sạn")
        hotel_choice = st.selectbox("Khách sạn", ["Không đặt khách sạn"] + [f"{n} ({s}★)" for n, s in tour["hotels"]])
        hotel, rooms = None, {rt: 0 for rt in ROOM_TYPES}
        if hotel_choice != "Không đặt khách sạn":
            h_idx = [f"{n} ({s}★)" for n, s in tour["hotels"]].index(hotel_choice)
            hotel = tour["hotels"][h_idx]
            rooms["Standard"] = st.number_input("Số phòng Standard", 0, 10, 1)

        extras = st.multiselect("Dịch vụ thêm", list(EXTRAS))
        
        st.subheader("5. Thông tin khách hàng")
        name = st.text_input("Họ tên")
        phone = st.text_input("Số điện thoại")
        email = st.text_input("Email")
        payment = st.selectbox("Thanh toán", ["Chuyển khoản", "Tiền mặt"])

    quote = calc_quote(tour, depart, ages, hotel, rooms, extras, "")

    with col_sum:
        st.subheader("💰 Báo giá")
        st.metric("Tổng tiền", vnd(quote["total"]))
        st.metric("Cọc (30%)", vnd(quote["deposit"]))
        
        if st.button("✅ Xác nhận đặt tour", type="primary", use_container_width=True):
            if not name or not phone or "@" not in email:
                st.error("Vui lòng điền đầy đủ thông tin liên hệ!")
            else:
                b = {
                    "code": f"ST{datetime.now():%y%m%d}-{uuid.uuid4().hex[:4].upper()}",
                    "customer": name, "phone": phone, "email": email, "tour": tour["name"],
                    "depart": f"{depart:%Y-%m-%d} 08:00", "return": f"{depart+timedelta(days=tour['days']):%Y-%m-%d} 18:00",
                    "n_guests": int(n_guests), "hotel": hotel_choice,
                    "rooms": ", ".join(f"{q} {rt}" for rt, q in rooms.items() if q),
                    "payment": payment, "note": "", "status": "Chờ thanh toán cọc"
                }
                insert_booking(b, tour_id, quote, ages)
                st.balloons()
                st.success(f"Đặt tour thành công! Mã đơn: {b['code']}")

# TAB 2: ĐƠN ĐẶT CỦA TÔI
with tab_manage:
    st.subheader("📋 Trạng thái đơn đặt tour")
    kw = st.text_input("Tìm kiếm theo mã / SĐT / Email")
    rows = fetch_bookings(kw)
    if rows:
        st.dataframe(pd.DataFrame(rows)[['code', 'customer', 'phone', 'tour_name', 'total', 'status']], use_container_width=True)

# TAB 3: THỐNG KÊ NỘI BỘ
with tab_stats:
    st.subheader("📊 Báo cáo & Thống kê Kinh doanh (Nội bộ)")
    if not db_error:
        try:
            conn = get_conn()
            df = pd.read_sql("SELECT * FROM bookings", conn)
            conn.close()

            if not df.empty:
                df['total'] = df['total'].astype(float)
                df['deposit'] = df['deposit'].astype(float)

                c1, c2, c3 = st.columns(3)
                c1.metric("💰 Tổng Doanh Thu", vnd(df['total'].sum()))
                c2.metric("💵 Tiền Cọc Đã Thu", vnd(df['deposit'].sum()))
                c3.metric("📈 Tổng Đơn Đặt", len(df))

                st.divider()
                st.write("📈 **Doanh thu theo Tour**")
                st.bar_chart(df.groupby('tour_name')['total'].sum())

                st.write("📑 **Xuất dữ liệu cho Kế toán**")
                csv_data = df.to_csv(index=False, encoding='utf-8-sig').encode('utf-8-sig')
                st.download_button("📥 Tải File Excel Báo Cáo", csv_data, f"bao_cao_{date.today()}.csv", "text/csv")
            else:
                st.info("Chưa có đơn đặt nào.")
        except Exception as ex:
            st.error(f"Lỗi tải dữ liệu: {ex}")

# TAB 4: CHÍNH SÁCH
with tab_policy:
    st.subheader("Thông tin chính sách giá")
    st.table(pd.DataFrame([{"Mức tuổi": l, "% Giá": f"{f:.0%}"} for _, _, l, f in AGE_GROUPS]))
