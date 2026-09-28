import os
import uuid
from datetime import date, datetime, timedelta

import pandas as pd
import streamlit as st
import mysql.connector

st.set_page_config(page_title="SMART TOUR", page_icon="🌴", layout="wide", initial_sidebar_state="expanded")
APP_VERSION = "SMART TOUR v2.1 – MySQL no-FK schema"

# ============================================================
# SMART TOUR - CUSTOMER + ADMIN + AI CHATBOT + MYSQL AIVEN
# ============================================================

DB_CONFIG = {
    "host": "mysql-1b346c1b-kimchi8019-4ea9.e.aivencloud.com",
    "port": 21314,
    "user": "avnadmin",
    "password": "AVNS_ZuLUVTHk6cKBskjg0Kp",
    "database": "defaultdb",
    "ssl_disabled": False,
    "connection_timeout": 20,
    "charset": "utf8mb4",
}

VAT_RATE = 0.08
DEPOSIT_RATE = 0.30


def load_db_config():
    cfg = DB_CONFIG.copy()
    try:
        if "mysql" in st.secrets:
            for key in cfg:
                if key in st.secrets["mysql"]:
                    cfg[key] = st.secrets["mysql"][key]
    except Exception:
        pass
    return cfg


def get_ai_key():
    try:
        if "GEMINI_API_KEY" in st.secrets:
            return str(st.secrets["GEMINI_API_KEY"])
    except Exception:
        pass
    return os.getenv("GEMINI_API_KEY", "")


def ask_gemini(question, tour_context):
    api_key = get_ai_key()
    if not api_key:
        return ("🤖 Trợ lý AI chưa được cấu hình GEMINI_API_KEY. "
                "Bạn vẫn có thể xem và đặt tour bình thường. "
                "Trên Streamlit Cloud, thêm GEMINI_API_KEY trong Settings → Secrets.")
    try:
        from google import genai
        client = genai.Client(api_key=api_key)
        prompt = f"""
Bạn là Trợ lý AI của SMART TOUR, tư vấn du lịch bằng tiếng Việt.
Hãy trả lời ngắn gọn, lịch sự, rõ ràng. Chỉ sử dụng giá tour trong dữ liệu được cung cấp,
không tự bịa giá. Nếu khách muốn đặt tour, hãy hướng dẫn họ sang trang Đặt tour.
Nếu thiếu thông tin, hỏi điểm đến, ngày đi, số người lớn, số trẻ em và nhu cầu phòng/ăn/xe.

DỮ LIỆU TOUR:
{tour_context}

CÂU HỎI KHÁCH:
{question}
"""
        response = client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
        return (getattr(response, "text", None) or "AI chưa tạo được câu trả lời.").strip()
    except Exception as e:
        return f"Không thể gọi AI lúc này: {e}"


def new_connection():
    return mysql.connector.connect(**load_db_config())


def execute(sql, params=None, fetch=False, many=False):
    conn = new_connection()
    cur = conn.cursor(dictionary=True)
    try:
        if many:
            cur.executemany(sql, params or [])
        else:
            cur.execute(sql, params or ())
        result = cur.fetchall() if fetch else None
        conn.commit()
        return result
    finally:
        cur.close()
        conn.close()


def query_df(sql, params=None):
    return pd.DataFrame(execute(sql, params, fetch=True) or [])


def init_database():
    try:
        conn = new_connection()
        cur = conn.cursor()
        tables = [
            """CREATE TABLE IF NOT EXISTS smarttour_users (
                id INT AUTO_INCREMENT PRIMARY KEY,
                username VARCHAR(100) NOT NULL UNIQUE,
                password VARCHAR(255) NOT NULL,
                full_name VARCHAR(150) NOT NULL,
                phone VARCHAR(30),
                role ENUM('admin','customer') NOT NULL DEFAULT 'customer',
                created_at DATETIME NOT NULL
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
            """CREATE TABLE IF NOT EXISTS smarttour_tours (
                id INT AUTO_INCREMENT PRIMARY KEY,
                code VARCHAR(30) NOT NULL UNIQUE,
                name VARCHAR(200) NOT NULL,
                destination VARCHAR(200) NOT NULL,
                duration VARCHAR(100) NOT NULL,
                description VARCHAR(1000),
                image_url VARCHAR(500),
                base_price DECIMAL(15,2) NOT NULL DEFAULT 0,
                child_percent DECIMAL(5,2) NOT NULL DEFAULT 70,
                active TINYINT(1) NOT NULL DEFAULT 1,
                created_at DATETIME NOT NULL
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
            """CREATE TABLE IF NOT EXISTS smarttour_rooms (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(150) NOT NULL,
                room_type VARCHAR(100) NOT NULL,
                price_normal DECIMAL(15,2) NOT NULL DEFAULT 0,
                price_peak DECIMAL(15,2) NOT NULL DEFAULT 0,
                capacity INT NOT NULL DEFAULT 2,
                image_url VARCHAR(500),
                active TINYINT(1) NOT NULL DEFAULT 1
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
            """CREATE TABLE IF NOT EXISTS smarttour_meals (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(150) NOT NULL,
                meal_type VARCHAR(80) NOT NULL,
                price_adult DECIMAL(15,2) NOT NULL DEFAULT 0,
                price_child DECIMAL(15,2) NOT NULL DEFAULT 0,
                restaurant VARCHAR(200),
                image_url VARCHAR(500),
                active TINYINT(1) NOT NULL DEFAULT 1
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
            """CREATE TABLE IF NOT EXISTS smarttour_transports (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(150) NOT NULL,
                transport_type VARCHAR(80) NOT NULL,
                price_per_person DECIMAL(15,2) NOT NULL DEFAULT 0,
                description VARCHAR(500),
                image_url VARCHAR(500),
                active TINYINT(1) NOT NULL DEFAULT 1
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
            """CREATE TABLE IF NOT EXISTS smarttour_bookings (
                id VARCHAR(30) PRIMARY KEY,
                user_id INT NULL,
                customer_name VARCHAR(150) NOT NULL,
                phone VARCHAR(30) NOT NULL,
                tour_id INT NOT NULL,
                tour_name VARCHAR(200) NOT NULL,
                departure_date DATE NOT NULL,
                departure_time TIME NOT NULL,
                adults INT NOT NULL DEFAULT 1,
                children INT NOT NULL DEFAULT 0,
                room_id INT NULL,
                room_name VARCHAR(150),
                nights INT NOT NULL DEFAULT 1,
                meal_id INT NULL,
                meal_name VARCHAR(150),
                meal_days INT NOT NULL DEFAULT 1,
                transport_id INT NULL,
                transport_name VARCHAR(150),
                room_amount DECIMAL(15,2) NOT NULL DEFAULT 0,
                meal_amount DECIMAL(15,2) NOT NULL DEFAULT 0,
                transport_amount DECIMAL(15,2) NOT NULL DEFAULT 0,
                tour_amount DECIMAL(15,2) NOT NULL DEFAULT 0,
                discount_amount DECIMAL(15,2) NOT NULL DEFAULT 0,
                vat_amount DECIMAL(15,2) NOT NULL DEFAULT 0,
                total_amount DECIMAL(15,2) NOT NULL DEFAULT 0,
                deposit_amount DECIMAL(15,2) NOT NULL DEFAULT 0,
                status VARCHAR(50) NOT NULL DEFAULT 'Chờ xác nhận',
                payment_status VARCHAR(50) NOT NULL DEFAULT 'Chưa thanh toán',
                note VARCHAR(500),
                created_at DATETIME NOT NULL,
                INDEX idx_bookings_user (user_id),
                INDEX idx_bookings_tour (tour_id),
                INDEX idx_bookings_room (room_id),
                INDEX idx_bookings_meal (meal_id),
                INDEX idx_bookings_transport (transport_id)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
        ]
        table_names = [
            "smarttour_users", "smarttour_tours", "smarttour_rooms",
            "smarttour_meals", "smarttour_transports", "smarttour_bookings"
        ]
        for table_name, sql in zip(table_names, tables):
            try:
                cur.execute(sql)
            except Exception as e:
                raise RuntimeError(f"Lỗi tạo bảng {table_name}: {e}") from e

        cur.execute("SELECT COUNT(*) AS n FROM smarttour_users WHERE username='admin'")
        if cur.fetchone()["n"] == 0:
            cur.execute("INSERT INTO smarttour_users(username,password,full_name,phone,role,created_at) VALUES(%s,%s,%s,%s,'admin',%s)",
                        ("admin", "admin123", "Quản trị viên SMART TOUR", "", datetime.now()))

        cur.execute("SELECT COUNT(*) AS n FROM smarttour_tours")
        if cur.fetchone()["n"] == 0:
            cur.executemany("""INSERT INTO smarttour_tours(code,name,destination,duration,description,image_url,base_price,child_percent,active,created_at)
                VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""", [
                ("T01", "Khám phá Hạ Long Rồng Việt", "Hạ Long", "3 ngày 2 đêm", "Du thuyền 5 sao, hang Sửng Sốt, đảo Ti Tốp, chèo Kayak.", "https://images.unsplash.com/photo-1528127269322-539801943592?auto=format&fit=crop&w=1200&q=85", 3500000, 70, 1, datetime.now()),
                ("T02", "Đà Nẵng - Hội An - Bà Nà Hills", "Đà Nẵng - Hội An", "4 ngày 3 đêm", "Cầu Vàng, phố cổ Hội An, biển Mỹ Khê.", "https://images.unsplash.com/photo-1559592413-7cec4d0cae2b?auto=format&fit=crop&w=1200&q=85", 4800000, 70, 1, datetime.now()),
                ("T03", "Phú Quốc Thiên Đường Biển Ngọc", "Phú Quốc", "3 ngày 2 đêm", "Hòn Thơm, biển đảo, hoàng hôn và lặn ngắm san hô.", "https://images.unsplash.com/photo-1540202404-a2f29016b523?auto=format&fit=crop&w=1200&q=85", 5200000, 70, 1, datetime.now()),
                ("T04", "Sapa Sương Mù - Đỉnh Fansipan", "Sapa", "2 ngày 1 đêm", "Fansipan, bản Cát Cát và ẩm thực vùng cao.", "https://images.unsplash.com/photo-1508873696983-2df515122519?auto=format&fit=crop&w=1200&q=85", 2900000, 70, 1, datetime.now()),
            ])

        cur.execute("SELECT COUNT(*) AS n FROM smarttour_rooms")
        if cur.fetchone()["n"] == 0:
            cur.executemany("""INSERT INTO smarttour_rooms(name,room_type,price_normal,price_peak,capacity,image_url,active)
                VALUES(%s,%s,%s,%s,%s,%s,%s)""", [
                ("Phòng Standard 2 người", "Standard", 500000, 650000, 2, "https://images.unsplash.com/photo-1611892440504-42a792e24d32?auto=format&fit=crop&w=900&q=80", 1),
                ("Phòng Deluxe 2 người", "Deluxe", 750000, 950000, 2, "https://images.unsplash.com/photo-1590490360182-c33d57733427?auto=format&fit=crop&w=900&q=80", 1),
                ("Phòng Family 4 người", "Family", 1100000, 1400000, 4, "https://images.unsplash.com/photo-1582719478250-c89cae4dc85b?auto=format&fit=crop&w=900&q=80", 1),
                ("Phòng VIP", "VIP", 1500000, 1900000, 2, "https://images.unsplash.com/photo-1566665797739-1674de7a421a?auto=format&fit=crop&w=900&q=80", 1),
            ])

        cur.execute("SELECT COUNT(*) AS n FROM smarttour_meals")
        if cur.fetchone()["n"] == 0:
            cur.executemany("""INSERT INTO smarttour_meals(name,meal_type,price_adult,price_child,restaurant,image_url,active)
                VALUES(%s,%s,%s,%s,%s,%s,%s)""", [
                ("Gói ăn tiêu chuẩn", "3 bữa/ngày", 250000, 175000, "Nhà hàng địa phương", "https://images.unsplash.com/photo-1547592180-85f173990554?auto=format&fit=crop&w=900&q=80", 1),
                ("Gói ăn nâng cao", "3 bữa/ngày", 400000, 280000, "Nhà hàng cao cấp", "https://images.unsplash.com/photo-1517248135467-4c7edcad34c4?auto=format&fit=crop&w=900&q=80", 1),
                ("Gói ăn sáng", "Bữa sáng", 90000, 60000, "Nhà hàng khách sạn", "https://images.unsplash.com/photo-1533089860892-a7c6f0a88666?auto=format&fit=crop&w=900&q=80", 1),
            ])

        cur.execute("SELECT COUNT(*) AS n FROM smarttour_transports")
        if cur.fetchone()["n"] == 0:
            cur.executemany("""INSERT INTO smarttour_transports(name,transport_type,price_per_person,description,image_url,active)
                VALUES(%s,%s,%s,%s,%s,%s)""", [
                ("Xe du lịch 16 chỗ", "Ô tô", 350000, "Đón/trả theo chương trình", "https://images.unsplash.com/photo-1544620347-c4fd4a3d5957?auto=format&fit=crop&w=900&q=80", 1),
                ("Xe du lịch 29 chỗ", "Ô tô", 450000, "Phù hợp đoàn đông", "https://images.unsplash.com/photo-1570125909232-eb263c188f7e?auto=format&fit=crop&w=900&q=80", 1),
                ("Xe Limousine", "Limousine", 650000, "Dịch vụ đưa đón cao cấp", "https://images.unsplash.com/photo-1511919884226-fd3cad34687c?auto=format&fit=crop&w=900&q=80", 1),
            ])

        conn.commit()
        return True, "OK"
    except Exception as e:
        try:
            conn.rollback()
        except Exception:
            pass
        return False, str(e)
    finally:
        try:
            cur.close()
            conn.close()
        except Exception:
            pass


def money(v):
    return f"{float(v or 0):,.0f} VNĐ"


def is_peak_period(d):
    return (date(d.year, 6, 1) <= d <= date(d.year, 8, 31)) or d >= date(d.year, 12, 20) or d <= date(d.year, 1, 5)


def calculate_booking(tour, room, meal, transport, adults, children, nights, meal_days, departure_date):
    child_rate = float(tour["child_percent"]) / 100
    tour_amount = adults * float(tour["base_price"]) + children * float(tour["base_price"]) * child_rate
    peak = is_peak_period(departure_date)
    room_price = float(room["price_peak"] if peak else room["price_normal"])
    total_people = adults + children
    room_count = max(1, (total_people + int(room["capacity"]) - 1) // int(room["capacity"]))
    room_amount = room_count * room_price * nights
    meal_amount = (adults * float(meal["price_adult"]) + children * float(meal["price_child"])) * meal_days
    transport_amount = total_people * float(transport["price_per_person"])
    subtotal = tour_amount + room_amount + meal_amount + transport_amount
    vat = subtotal * VAT_RATE
    total = subtotal + vat
    return {
        "tour_amount": tour_amount,
        "room_amount": room_amount,
        "meal_amount": meal_amount,
        "transport_amount": transport_amount,
        "vat_amount": vat,
        "total_amount": total,
        "deposit_amount": total * DEPOSIT_RATE,
        "room_count": room_count,
        "room_price": room_price,
        "peak": peak,
    }


# ============================================================
# CSS
# ============================================================
st.markdown("""
<style>
.stApp { background:#f5f7fb; }
.hero { padding:32px; border-radius:22px; color:white; min-height:230px; display:flex; flex-direction:column; justify-content:center; background:linear-gradient(90deg,rgba(0,43,92,.92),rgba(0,118,130,.62)),url('https://images.unsplash.com/photo-1507525428034-b723cf961d3e?auto=format&fit=crop&w=1800&q=85'); background-size:cover; background-position:center; margin-bottom:24px; }
.hero h1 { font-size:42px; margin:0 0 8px; }
.hero p { font-size:18px; max-width:850px; }
.card { background:white; border:1px solid #e7ebf1; border-radius:16px; padding:18px; box-shadow:0 5px 18px rgba(0,0,0,.06); margin-bottom:16px; }
.price { color:#e44d26; font-size:23px; font-weight:800; }
.section-title { color:#073b66; font-size:29px; font-weight:800; margin:10px 0 18px; }
div[data-testid='stMetric'] { background:white; border:1px solid #e7ebf1; padding:14px; border-radius:14px; box-shadow:0 4px 12px rgba(0,0,0,.04); }
</style>
""", unsafe_allow_html=True)

# ============================================================
# INIT DATABASE
# ============================================================
try:
    ok, msg = init_database()
except Exception as e:
    ok, msg = False, str(e)

if not ok:
    st.error("❌ SMART TOUR chưa khởi tạo được cơ sở dữ liệu MySQL Aiven.")
    st.code(msg)
    st.warning("Bản này dùng 6 bảng riêng có tiền tố smarttour_ và KHÔNG dùng FOREIGN KEY, để tránh lỗi MySQL 1215 từ schema cũ.")
    st.info("Nếu vẫn thấy lỗi 1215 sau khi deploy bản này, hãy kiểm tra GitHub đã thay đúng file app.py và bấm Reboot app trên Streamlit Cloud.")
    st.stop()

# ============================================================
# SESSION
# ============================================================
for k, default in {"logged_in":False, "role":None, "user_id":None, "full_name":"", "chat_history":[]}.items():
    if k not in st.session_state:
        st.session_state[k] = default


def login_page():
    st.markdown("""
    <div class='hero'><h1>🌴 SMART TOUR</h1><p>Nền tảng đặt tour thông minh: Tour • Phòng • Nhà hàng • Phương tiện • AI tư vấn</p></div>
    """, unsafe_allow_html=True)
    left, right = st.columns([1.1, 1])
    with left:
        st.image("https://images.unsplash.com/photo-1469474968028-56623f02e42e?auto=format&fit=crop&w=1400&q=85", use_container_width=True)
        st.markdown("<div class='card'><h3>✨ Trải nghiệm SMART TOUR</h3><p>Khách tự chọn tour, ngày giờ, người lớn/trẻ em, phòng, bữa ăn và phương tiện. Hệ thống tự tính giá và lưu booking vào MySQL Aiven.</p></div>", unsafe_allow_html=True)
    with right:
        st.markdown("<div class='section-title'>Đăng nhập hệ thống</div>", unsafe_allow_html=True)
        role_choice = st.radio("Bạn là", ["👤 Khách hàng", "🛠️ Quản trị viên"], horizontal=True)
        username = st.text_input("Tên đăng nhập")
        password = st.text_input("Mật khẩu", type="password")
        if st.button("Đăng nhập", type="primary", use_container_width=True):
            role = "customer" if role_choice.startswith("👤") else "admin"
            rows = execute("SELECT id,username,password,full_name,role FROM smarttour_users WHERE username=%s AND role=%s LIMIT 1", (username.strip(), role), fetch=True)
            if rows and rows[0]["password"] == password:
                st.session_state.logged_in = True
                st.session_state.role = rows[0]["role"]
                st.session_state.user_id = rows[0]["id"]
                st.session_state.full_name = rows[0]["full_name"]
                st.rerun()
            else:
                st.error("Sai tài khoản, mật khẩu hoặc vai trò.")
        st.caption("Admin mặc định: admin / admin123")
        with st.expander("📝 Tạo tài khoản khách hàng"):
            rn = st.text_input("Họ tên", key="rn")
            rp = st.text_input("Số điện thoại", key="rp")
            ru = st.text_input("Tên đăng nhập", key="ru")
            rpw = st.text_input("Mật khẩu", type="password", key="rpw")
            if st.button("Đăng ký", use_container_width=True):
                if not rn or not rp or not ru or not rpw:
                    st.warning("Vui lòng nhập đủ thông tin.")
                else:
                    try:
                        execute("INSERT INTO smarttour_users(username,password,full_name,phone,role,created_at) VALUES(%s,%s,%s,%s,'customer',%s)", (ru.strip(), rpw, rn.strip(), rp.strip(), datetime.now()))
                        st.success("Đăng ký thành công.")
                    except Exception as e:
                        st.error(f"Không thể đăng ký: {e}")


def chatbot():
    smarttour_tours = query_df("SELECT code,name,destination,duration,base_price,child_percent FROM smarttour_tours WHERE active=1 ORDER BY id")
    context = smarttour_tours.to_string(index=False) if not smarttour_tours.empty else "Chưa có tour."
    st.markdown("<div class='section-title'>🤖 Trợ lý AI Smart Tour</div>", unsafe_allow_html=True)
    st.caption("Hỏi về tour, giá, ngày đi, người lớn/trẻ em, phòng, bữa ăn và phương tiện.")
    for m in st.session_state.chat_history:
        with st.chat_message(m["role"]):
            st.write(m["content"])
    q = st.chat_input("Ví dụ: Gia đình 4 người nên đi Đà Nẵng tour nào?")
    if q:
        st.session_state.chat_history.append({"role":"user","content":q})
        ans = ask_gemini(q, context)
        st.session_state.chat_history.append({"role":"assistant","content":ans})
        st.rerun()


def booking_page():
    st.markdown("<div class='section-title'>📝 Đặt tour & tính giá tự động</div>", unsafe_allow_html=True)
    smarttour_tours = query_df("SELECT * FROM smarttour_tours WHERE active=1 ORDER BY id")
    smarttour_rooms = query_df("SELECT * FROM smarttour_rooms WHERE active=1 ORDER BY price_normal")
    smarttour_meals = query_df("SELECT * FROM smarttour_meals WHERE active=1 ORDER BY price_adult")
    smarttour_transports = query_df("SELECT * FROM smarttour_transports WHERE active=1 ORDER BY price_per_person")
    if smarttour_tours.empty or smarttour_rooms.empty or smarttour_meals.empty or smarttour_transports.empty:
        st.error("Dữ liệu tour/phòng/bữa ăn/phương tiện chưa đầy đủ.")
        return
    tm = {int(r.id): r for r in smarttour_tours.itertuples(index=False)}
    rm = {int(r.id): r for r in smarttour_rooms.itertuples(index=False)}
    mm = {int(r.id): r for r in smarttour_meals.itertuples(index=False)}
    vm = {int(r.id): r for r in smarttour_transports.itertuples(index=False)}

    with st.form("booking_form"):
        c1, c2 = st.columns(2)
        with c1:
            name = st.text_input("Họ và tên *", value=st.session_state.full_name)
            phone = st.text_input("Số điện thoại *")
            tour_id = st.selectbox("Tour *", list(tm), format_func=lambda x: f"{tm[x].code} - {tm[x].name}")
            dep_date = st.date_input("Ngày khởi hành *", min_value=date.today(), value=date.today()+timedelta(days=7))
            dep_time = st.time_input("Giờ khởi hành *", value=datetime.strptime("07:30","%H:%M").time())
        with c2:
            adults = st.number_input("Người lớn", 1, 100, 2)
            children = st.number_input("Trẻ em", 0, 100, 0)
            room_id = st.selectbox("Phòng ở *", list(rm), format_func=lambda x: f"{rm[x].name} · tối đa {rm[x].capacity} người")
            nights = st.number_input("Số đêm", 1, 30, 2)
            meal_id = st.selectbox("Gói bữa ăn *", list(mm), format_func=lambda x: f"{mm[x].name} · {money(mm[x].price_adult)}/người lớn")
            meal_days = st.number_input("Số ngày dùng bữa", 1, 30, 2)
            transport_id = st.selectbox("Phương tiện *", list(vm), format_func=lambda x: f"{vm[x].name} · {money(vm[x].price_per_person)}/người")
            note = st.text_area("Ghi chú")
        submitted = st.form_submit_button("🚀 XÁC NHẬN ĐẶT TOUR", type="primary", use_container_width=True)

    if submitted:
        if not name.strip() or not phone.strip():
            st.error("Vui lòng nhập họ tên và số điện thoại.")
            return
        t, r, m, v = tm[tour_id], rm[room_id], mm[meal_id], vm[transport_id]
        calc = calculate_booking(t, r, m, v, int(adults), int(children), int(nights), int(meal_days), dep_date)
        bid = "ST-" + uuid.uuid4().hex[:8].upper()
        try:
            execute("""INSERT INTO smarttour_bookings(id,user_id,customer_name,phone,tour_id,tour_name,departure_date,departure_time,adults,children,room_id,room_name,nights,meal_id,meal_name,meal_days,transport_id,transport_name,room_amount,meal_amount,transport_amount,tour_amount,discount_amount,vat_amount,total_amount,deposit_amount,status,payment_status,note,created_at)
            VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
            (bid, st.session_state.user_id, name.strip(), phone.strip(), int(tour_id), t.name, dep_date, dep_time, int(adults), int(children), int(room_id), r.name, int(nights), int(meal_id), m.name, int(meal_days), int(transport_id), v.name, calc["room_amount"], calc["meal_amount"], calc["transport_amount"], calc["tour_amount"], 0, calc["vat_amount"], calc["total_amount"], calc["deposit_amount"], "Chờ xác nhận", "Chưa thanh toán", note.strip(), datetime.now()))
            st.success(f"🎉 Đặt tour thành công! Mã booking: **{bid}**")
            a,b,c,d = st.columns(4)
            a.metric("Tiền tour", money(calc["tour_amount"]))
            b.metric("Phòng", money(calc["room_amount"]))
            c.metric("Ăn + xe", money(calc["meal_amount"]+calc["transport_amount"]))
            d.metric("Tổng", money(calc["total_amount"]))
            st.info(f"{'🔥 CAO ĐIỂM' if calc['peak'] else '🌿 MÙA THƯỜNG'} · {calc['room_count']} phòng · Giá phòng áp dụng {money(calc['room_price'])}/đêm · Cọc 30%: **{money(calc['deposit_amount'])}**")
        except Exception as e:
            st.error(f"Lỗi lưu booking: {e}")


def customer_portal():
    st.sidebar.markdown(f"### 👋 {st.session_state.full_name}")
    menu = st.sidebar.radio("Trang khách hàng", ["🏠 Trang chủ","🌴 Khám phá tour","📝 Đặt tour","📋 Đơn của tôi","🤖 Trợ lý AI"])
    if st.sidebar.button("Đăng xuất"):
        st.session_state.logged_in=False; st.session_state.role=None; st.rerun()
    if menu == "🏠 Trang chủ":
        st.markdown("<div class='hero'><h1>🌴 SMART TOUR</h1><p>Chọn hành trình. Chọn dịch vụ. Để hệ thống tự tính chi phí.</p></div>", unsafe_allow_html=True)
        a,b,c,d=st.columns(4)
        a.metric("Tour", int(query_df("SELECT COUNT(*) c FROM smarttour_tours WHERE active=1").iloc[0]["c"]))
        b.metric("Phòng", int(query_df("SELECT COUNT(*) c FROM smarttour_rooms WHERE active=1").iloc[0]["c"]))
        c.metric("Gói ăn", int(query_df("SELECT COUNT(*) c FROM smarttour_meals WHERE active=1").iloc[0]["c"]))
        d.metric("Phương tiện", int(query_df("SELECT COUNT(*) c FROM smarttour_transports WHERE active=1").iloc[0]["c"]))
        st.markdown("### 🌟 Tour nổi bật")
        smarttour_tours=query_df("SELECT * FROM smarttour_tours WHERE active=1 ORDER BY id DESC LIMIT 4")
        cols=st.columns(2)
        for i,(_,r) in enumerate(smarttour_tours.iterrows()):
            with cols[i%2]:
                st.image(r.image_url, use_container_width=True)
                st.markdown(f"**{r.name}**")
                st.write(r.description)
                st.markdown(f"<span class='price'>{money(r.base_price)}</span> / người lớn", unsafe_allow_html=True)
    elif menu == "🌴 Khám phá tour":
        st.markdown("<div class='section-title'>🌴 Khám phá các hành trình</div>", unsafe_allow_html=True)
        smarttour_tours=query_df("SELECT * FROM smarttour_tours WHERE active=1 ORDER BY id")
        cols=st.columns(2)
        for i,(_,r) in enumerate(smarttour_tours.iterrows()):
            with cols[i%2]:
                st.image(r.image_url,use_container_width=True)
                st.markdown(f"<div class='card'><div style='font-size:22px;font-weight:700;color:#073b66'>{r.code} · {r.name}</div>",unsafe_allow_html=True)
                st.write(f"📍 {r.destination} | ⏱️ {r.duration}")
                st.write(r.description)
                st.markdown(f"💰 Người lớn: <span class='price'>{money(r.base_price)}</span>",unsafe_allow_html=True)
                st.write(f"👶 Trẻ em: {float(r.child_percent):g}% giá người lớn")
                st.markdown("</div>",unsafe_allow_html=True)
    elif menu == "📝 Đặt tour": booking_page()
    elif menu == "📋 Đơn của tôi":
        st.markdown("<div class='section-title'>📋 Đơn đặt tour của tôi</div>",unsafe_allow_html=True)
        df=query_df("SELECT id AS 'Mã',tour_name AS 'Tour',departure_date AS 'Ngày đi',departure_time AS 'Giờ đi',adults AS 'NL',children AS 'TE',room_name AS 'Phòng',meal_name AS 'Bữa ăn',transport_name AS 'Xe',total_amount AS 'Tổng',deposit_amount AS 'Cọc',status AS 'Trạng thái',payment_status AS 'Thanh toán' FROM smarttour_bookings WHERE user_id=%s ORDER BY created_at DESC",(st.session_state.user_id,))
        if df.empty: st.info("Bạn chưa có đơn.")
        else: st.dataframe(df,use_container_width=True)
    else: chatbot()


def admin_portal():
    st.sidebar.markdown("### 🛠️ SMART TOUR ADMIN")
    menu=st.sidebar.radio("Khu vực quản trị",["📊 Dashboard","🌴 Quản lý tour","🏨 Quản lý phòng","🍽️ Quản lý nhà hàng","🚌 Quản lý phương tiện","📋 Quản lý booking","👥 Quản lý khách hàng","🤖 Trợ lý AI"])
    if st.sidebar.button("Đăng xuất"):
        st.session_state.logged_in=False; st.session_state.role=None; st.rerun()
    if menu=="📊 Dashboard": admin_dashboard()
    elif menu=="🌴 Quản lý tour": manage_tours()
    elif menu=="🏨 Quản lý phòng": manage_rooms()
    elif menu=="🍽️ Quản lý nhà hàng": manage_meals()
    elif menu=="🚌 Quản lý phương tiện": manage_transports()
    elif menu=="📋 Quản lý booking": manage_bookings()
    elif menu=="👥 Quản lý khách hàng": manage_customers()
    else: chatbot()


def admin_dashboard():
    st.markdown("<div class='hero'><h1>📊 SMART TOUR ADMIN</h1><p>Điều hành tour, dịch vụ và booking tập trung trên MySQL Aiven.</p></div>",unsafe_allow_html=True)
    b=query_df("SELECT * FROM smarttour_bookings")
    revenue=float(b.total_amount.sum()) if not b.empty else 0
    deposit=float(b.deposit_amount.sum()) if not b.empty else 0
    a,b1,c,d,e=st.columns(5)
    a.metric("Booking",len(b)); b1.metric("Doanh thu",money(revenue)); c.metric("Tiền cọc",money(deposit)); d.metric("Tour",int(query_df("SELECT COUNT(*) c FROM smarttour_tours WHERE active=1").iloc[0]['c'])); e.metric("Khách",int(query_df("SELECT COUNT(*) c FROM smarttour_users WHERE role='customer'").iloc[0]['c']))
    if not b.empty:
        s=b.groupby('tour_name',as_index=False)['total_amount'].sum(); st.bar_chart(s,x='tour_name',y='total_amount')
    r=query_df("SELECT id AS 'Mã',customer_name AS 'Khách',phone AS 'SĐT',tour_name AS 'Tour',departure_date AS 'Ngày đi',departure_time AS 'Giờ',adults AS 'NL',children AS 'TE',total_amount AS 'Tổng',status AS 'Trạng thái' FROM smarttour_bookings ORDER BY created_at DESC LIMIT 10")
    st.dataframe(r,use_container_width=True)


def manage_tours():
    st.markdown("<div class='section-title'>🌴 Quản lý tour</div>",unsafe_allow_html=True)
    with st.expander("➕ Thêm tour"):
        with st.form("addtour"):
            code=st.text_input("Mã tour"); name=st.text_input("Tên tour"); dest=st.text_input("Điểm đến"); duration=st.text_input("Thời lượng","3 ngày 2 đêm"); price=st.number_input("Giá người lớn",0,100000000,3000000,100000); child=st.number_input("Trẻ em (%)",0.0,100.0,70.0); image=st.text_input("URL ảnh"); desc=st.text_area("Mô tả")
            if st.form_submit_button("Lưu"):
                try:
                    execute("INSERT INTO smarttour_tours(code,name,destination,duration,description,image_url,base_price,child_percent,active,created_at) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,1,%s)",(code,name,dest,duration,desc,image,price,child,datetime.now())); st.success("Đã thêm tour."); st.rerun()
                except Exception as e: st.error(e)
    st.dataframe(query_df("SELECT id,code,name,destination,duration,base_price,child_percent,active FROM smarttour_tours ORDER BY id"),use_container_width=True)


def manage_rooms():
    st.markdown("<div class='section-title'>🏨 Quản lý phòng & giá cao điểm</div>",unsafe_allow_html=True)
    st.info("Admin chỉnh Giá mùa thường và Giá mùa cao điểm. Ngày thuộc mùa cao điểm sẽ tự lấy giá peak.")
    df=query_df("SELECT * FROM smarttour_rooms ORDER BY id")
    for _,r in df.iterrows():
        with st.expander(f"🏨 {r['name']} · {r['room_type']}"):
            with st.form(f"room{r['id']}"):
                n=st.text_input("Tên",r['name'],key=f'n{r.id}'); rt=st.text_input("Loại",r['room_type'],key=f'rt{r.id}'); cap=st.number_input("Sức chứa",1,20,int(r['capacity']),key=f'c{r.id}'); normal=st.number_input("Giá thường",0,100000000,int(r['price_normal']),50000,key=f'norm{r.id}'); peak=st.number_input("Giá cao điểm",0,100000000,int(r['price_peak']),50000,key=f'peak{r.id}'); img=st.text_input("URL ảnh",r['image_url'] or '',key=f'i{r.id}'); active=st.checkbox("Đang bán",bool(r['active']),key=f'a{r.id}')
                if st.form_submit_button("💾 Cập nhật"):
                    execute("UPDATE smarttour_rooms SET name=%s,room_type=%s,price_normal=%s,price_peak=%s,capacity=%s,image_url=%s,active=%s WHERE id=%s",(n,rt,normal,peak,cap,img,int(active),int(r['id']))); st.success("Đã cập nhật."); st.rerun()


def manage_meals():
    st.markdown("<div class='section-title'>🍽️ Quản lý nhà hàng / bữa ăn</div>",unsafe_allow_html=True)
    with st.expander("➕ Thêm gói ăn"):
        with st.form("addmeal"):
            n=st.text_input("Tên gói"); mt=st.text_input("Loại bữa","3 bữa/ngày"); pa=st.number_input("Giá NL",0,10000000,250000,10000); pc=st.number_input("Giá TE",0,10000000,175000,10000); rest=st.text_input("Nhà hàng"); img=st.text_input("URL ảnh")
            if st.form_submit_button("Thêm"):
                execute("INSERT INTO smarttour_meals(name,meal_type,price_adult,price_child,restaurant,image_url,active) VALUES(%s,%s,%s,%s,%s,%s,1)",(n,mt,pa,pc,rest,img)); st.success("Đã thêm."); st.rerun()
    st.dataframe(query_df("SELECT * FROM smarttour_meals ORDER BY id"),use_container_width=True)


def manage_transports():
    st.markdown("<div class='section-title'>🚌 Quản lý phương tiện</div>",unsafe_allow_html=True)
    with st.expander("➕ Thêm phương tiện"):
        with st.form("addvehicle"):
            n=st.text_input("Tên"); typ=st.text_input("Loại","Ô tô"); p=st.number_input("Giá/người",0,100000000,350000,10000); desc=st.text_input("Mô tả"); img=st.text_input("URL ảnh")
            if st.form_submit_button("Thêm"):
                execute("INSERT INTO smarttour_transports(name,transport_type,price_per_person,description,image_url,active) VALUES(%s,%s,%s,%s,%s,1)",(n,typ,p,desc,img)); st.success("Đã thêm."); st.rerun()
    st.dataframe(query_df("SELECT * FROM smarttour_transports ORDER BY id"),use_container_width=True)


def manage_bookings():
    st.markdown("<div class='section-title'>📋 Quản lý booking</div>",unsafe_allow_html=True)
    df=query_df("SELECT id AS 'Mã',customer_name AS 'Khách',phone AS 'SĐT',tour_name AS 'Tour',departure_date AS 'Ngày',departure_time AS 'Giờ',adults AS 'NL',children AS 'TE',room_name AS 'Phòng',meal_name AS 'Bữa',transport_name AS 'Xe',tour_amount AS 'Tour tiền',room_amount AS 'Phòng tiền',meal_amount AS 'Ăn tiền',transport_amount AS 'Xe tiền',vat_amount AS 'VAT',total_amount AS 'Tổng',deposit_amount AS 'Cọc',status AS 'Trạng thái',payment_status AS 'Thanh toán' FROM smarttour_bookings ORDER BY created_at DESC")
    st.dataframe(df,use_container_width=True)
    if not df.empty:
        bid=st.selectbox("Chọn booking",df['Mã'].tolist()); status=st.selectbox("Trạng thái",["Chờ xác nhận","Đã xác nhận","Đang thực hiện","Hoàn tất","Đã hủy"]); pay=st.selectbox("Thanh toán",["Chưa thanh toán","Đã cọc","Đã thanh toán đủ"])
        if st.button("Cập nhật booking",type='primary'):
            execute("UPDATE smarttour_bookings SET status=%s,payment_status=%s WHERE id=%s",(status,pay,bid)); st.success("Đã cập nhật."); st.rerun()


def manage_customers():
    st.markdown("<div class='section-title'>👥 Quản lý khách hàng</div>",unsafe_allow_html=True)
    st.dataframe(query_df("SELECT id,username,full_name,phone,created_at FROM smarttour_users WHERE role='customer' ORDER BY created_at DESC"),use_container_width=True)


if not st.session_state.logged_in:
    login_page()
elif st.session_state.role == 'admin':
    admin_portal()
else:
    customer_portal()

