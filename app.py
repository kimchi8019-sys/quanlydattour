import streamlit as st
import mysql.connector
from mysql.connector import Error
import pandas as pd
from datetime import datetime, date, time
import hashlib
import os

# ============================================================
# SMART TOUR - STREAMLIT + MYSQL AIVEN
# Quản lý tour: tour + phòng + nhà hàng/bữa ăn + phương tiện
# Khách đặt: Họ tên + SĐT; tách người lớn/trẻ em
# ============================================================

st.set_page_config(
    page_title="SMART TOUR",
    page_icon="✈️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ============================================================
# AIVEN MYSQL CONFIG
# Có thể giữ trực tiếp như dưới đây để chạy ngay.
# Nếu triển khai công khai, nên chuyển sang st.secrets.
# ============================================================

DB_CONFIG = {
    "host": "mysql-1b346c1b-kimchi8019-4ea9.e.aivencloud.com",
    "port": 21314,
    "user": "avnadmin",
    "password": "AVNS_ZuLUVTHk6cKBskjg0Kp",
    "database": "defaultdb",
    "ssl_disabled": False,
}

# ============================================================
# DATABASE
# ============================================================

@st.cache_resource
def get_connection():
    return mysql.connector.connect(**DB_CONFIG)


def db_ok():
    try:
        conn = get_connection()
        if conn.is_connected():
            return True, ""
        return False, "Không thể kết nối MySQL."
    except Error as e:
        return False, str(e)


def init_db():
    conn = get_connection()
    cur = conn.cursor()

    # MySQL: dùng VARCHAR thay cho TEXT DEFAULT để tránh lỗi
    # DEFAULT của TEXT trên một số cấu hình MySQL.
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INT AUTO_INCREMENT PRIMARY KEY,
            full_name VARCHAR(150) NOT NULL,
            phone VARCHAR(30) NOT NULL,
            username VARCHAR(80) UNIQUE NOT NULL,
            password VARCHAR(255) NOT NULL,
            role VARCHAR(20) NOT NULL DEFAULT 'customer',
            created_at DATETIME NOT NULL

        ) ENGINE=InnoDB
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS tours (
            id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(200) NOT NULL,
            destination VARCHAR(150) NOT NULL,
            duration VARCHAR(80) NOT NULL,
            days INT NOT NULL DEFAULT 1,
            nights INT NOT NULL DEFAULT 0,
            adult_price DECIMAL(15,2) NOT NULL DEFAULT 0,
            child_price DECIMAL(15,2) NOT NULL DEFAULT 0,
            max_people INT NOT NULL DEFAULT 30,
            available_seats INT NOT NULL DEFAULT 30,
            interests VARCHAR(500) DEFAULT '',
            description VARCHAR(1000) DEFAULT '',
            status VARCHAR(30) NOT NULL DEFAULT 'Đang mở'
        ) ENGINE=InnoDB
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS hotels (
            id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(200) NOT NULL,
            destination VARCHAR(150) NOT NULL,
            stars INT NOT NULL DEFAULT 3,
            room_type VARCHAR(80) NOT NULL,
            normal_price DECIMAL(15,2) NOT NULL DEFAULT 0,
            peak_price DECIMAL(15,2) NOT NULL DEFAULT 0,
            total_rooms INT NOT NULL DEFAULT 10,
            available_rooms INT NOT NULL DEFAULT 10,
            peak_season TINYINT(1) NOT NULL DEFAULT 0,
            description VARCHAR(1000) DEFAULT '',
            status VARCHAR(30) NOT NULL DEFAULT 'Đang hoạt động'
        ) ENGINE=InnoDB
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS meals (
            id INT AUTO_INCREMENT PRIMARY KEY,
            restaurant_name VARCHAR(200) NOT NULL,
            destination VARCHAR(150) NOT NULL,
            meal_type VARCHAR(50) NOT NULL,
            adult_price DECIMAL(15,2) NOT NULL DEFAULT 0,
            child_price DECIMAL(15,2) NOT NULL DEFAULT 0,
            description VARCHAR(500) DEFAULT '',
            status VARCHAR(30) NOT NULL DEFAULT 'Đang hoạt động'
        ) ENGINE=InnoDB
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS transports (
            id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(150) NOT NULL,
            destination VARCHAR(150) NOT NULL,
            vehicle_type VARCHAR(80) NOT NULL,
            price_per_trip DECIMAL(15,2) NOT NULL DEFAULT 0,
            price_per_person DECIMAL(15,2) NOT NULL DEFAULT 0,
            description VARCHAR(500) DEFAULT '',
            status VARCHAR(30) NOT NULL DEFAULT 'Đang hoạt động'
        ) ENGINE=InnoDB
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS bookings (
            id INT AUTO_INCREMENT PRIMARY KEY,
            full_name VARCHAR(150) NOT NULL,
            phone VARCHAR(30) NOT NULL,
            tour_id INT NOT NULL,
            hotel_id INT NULL,
            meal_id INT NULL,
            transport_id INT NULL,
            booking_date DATETIME NOT NULL,
            departure_date DATE NOT NULL,
            departure_time TIME NOT NULL,
            adults INT NOT NULL DEFAULT 1,
            children INT NOT NULL DEFAULT 0,
            rooms INT NOT NULL DEFAULT 1,
            nights INT NOT NULL DEFAULT 0,
            tour_amount DECIMAL(15,2) NOT NULL DEFAULT 0,
            hotel_amount DECIMAL(15,2) NOT NULL DEFAULT 0,
            meal_amount DECIMAL(15,2) NOT NULL DEFAULT 0,
            transport_amount DECIMAL(15,2) NOT NULL DEFAULT 0,
            total_amount DECIMAL(15,2) NOT NULL DEFAULT 0,
            payment_method VARCHAR(80) NOT NULL,
            payment_status VARCHAR(50) NOT NULL DEFAULT 'Chưa thanh toán',
            booking_status VARCHAR(50) NOT NULL DEFAULT 'Chờ xác nhận',
            note VARCHAR(1000) DEFAULT '',
            FOREIGN KEY (tour_id) REFERENCES tours(id),
            FOREIGN KEY (hotel_id) REFERENCES hotels(id),
            FOREIGN KEY (meal_id) REFERENCES meals(id),
            FOREIGN KEY (transport_id) REFERENCES transports(id)
        ) ENGINE=InnoDB
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS payments (
            id INT AUTO_INCREMENT PRIMARY KEY,
            booking_id INT NOT NULL,
            amount DECIMAL(15,2) NOT NULL,
            method VARCHAR(80) NOT NULL,
            paid_at DATETIME NOT NULL,
            status VARCHAR(50) NOT NULL DEFAULT 'Thành công',
            FOREIGN KEY (booking_id) REFERENCES bookings(id)
        ) ENGINE=InnoDB
    """)

    conn.commit()

    # Admin mặc định
    cur.execute("SELECT COUNT(*) FROM users WHERE username = 'admin'")
    if cur.fetchone()[0] == 0:
        cur.execute("""
            INSERT INTO users
            (full_name, phone, username, password, role, created_at)
            VALUES (%s, %s, %s, %s, 'admin', %s)
        """, (
            "Quản trị viên",
            "0900000000",
            "admin",
            hash_password("admin123"),
            datetime.now(),
        ))

    # Seed dữ liệu nếu bảng rỗng
    cur.execute("SELECT COUNT(*) FROM tours")
    if cur.fetchone()[0] == 0:
        tours = [
            (
                "Vũng Tàu 3N2Đ - Biển & Ẩm thực", "Vũng Tàu",
                "3 ngày 2 đêm", 3, 2, 1890000, 1323000, 30, 30,
                "biển,ăn uống,nghỉ dưỡng,check-in",
                "Khám phá Bãi Sau, Bạch Dinh, Núi Nhỏ, Hải Đăng và ẩm thực địa phương."
            ),
            (
                "Đà Lạt 3N2Đ - Hoa & Sống ảo", "Đà Lạt",
                "3 ngày 2 đêm", 3, 2, 2590000, 1813000, 30, 30,
                "thiên nhiên,chụp ảnh,cafe,ăn uống",
                "Khám phá các điểm check-in, cà phê và cảnh quan Đà Lạt."
            ),
            (
                "Phú Quốc 4N3Đ - Biển đảo", "Phú Quốc",
                "4 ngày 3 đêm", 4, 3, 4490000, 3143000, 25, 25,
                "biển,nghỉ dưỡng,hải sản,gia đình",
                "Nghỉ dưỡng biển và khám phá các trải nghiệm đảo."
            ),
            (
                "Nha Trang 3N2Đ - Biển & Giải trí", "Nha Trang",
                "3 ngày 2 đêm", 3, 2, 3290000, 2303000, 30, 30,
                "biển,gia đình,giải trí,ăn uống",
                "Biển Nha Trang, vui chơi và trải nghiệm ẩm thực địa phương."
            ),
            (
                "Đà Nẵng - Hội An 4N3Đ", "Đà Nẵng - Hội An",
                "4 ngày 3 đêm", 4, 3, 3990000, 2793000, 30, 30,
                "biển,văn hóa,chụp ảnh,ăn uống",
                "Kết hợp biển Đà Nẵng và phố cổ Hội An."
            ),
            (
                "Tây Nguyên 3N2Đ - Thiên nhiên & Văn hóa", "Buôn Ma Thuột",
                "3 ngày 2 đêm", 3, 2, 2790000, 1953000, 25, 25,
                "thiên nhiên,văn hóa,khám phá,ẩm thực",
                "Trải nghiệm văn hóa Tây Nguyên, thác nước và cà phê."
            ),
        ]
        cur.executemany("""
            INSERT INTO tours
            (name,destination,duration,days,nights,adult_price,child_price,
             max_people,available_seats,interests,description)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """, tours)

    cur.execute("SELECT COUNT(*) FROM hotels")
    if cur.fetchone()[0] == 0:
        hotels = [
            ("Ocean Vũng Tàu Hotel", "Vũng Tàu", 3, "Phòng đôi", 750000, 1050000, 20, 20, 0, "Gần biển."),
            ("Sea Star Vũng Tàu", "Vũng Tàu", 4, "Phòng đôi", 1150000, 1550000, 15, 15, 0, "Khách sạn 4 sao."),
            ("Dalat Garden Hotel", "Đà Lạt", 3, "Phòng đôi", 850000, 1200000, 20, 20, 0, "Gần trung tâm."),
            ("Pine Hill Đà Lạt", "Đà Lạt", 4, "Phòng đôi", 1350000, 1800000, 15, 15, 0, "View đẹp."),
            ("Island Pearl Phú Quốc", "Phú Quốc", 4, "Phòng đôi", 1650000, 2300000, 20, 20, 0, "Gần biển."),
            ("Sun Bay Nha Trang", "Nha Trang", 3, "Phòng đôi", 950000, 1350000, 20, 20, 0, "Gần biển."),
            ("Hoi An Riverside", "Đà Nẵng - Hội An", 4, "Phòng đôi", 1450000, 1950000, 15, 15, 0, "Không gian đẹp."),
            ("Highland Coffee Resort", "Buôn Ma Thuột", 3, "Phòng đôi", 800000, 1100000, 15, 15, 0, "Gần thiên nhiên."),
        ]
        cur.executemany("""
            INSERT INTO hotels
            (name,destination,stars,room_type,normal_price,peak_price,
             total_rooms,available_rooms,peak_season,description)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """, hotels)

    cur.execute("SELECT COUNT(*) FROM meals")
    if cur.fetchone()[0] == 0:
        meals = [
            ("Nhà hàng Biển Xanh", "Vũng Tàu", "Trưa", 150000, 105000, "Hải sản địa phương."),
            ("Nhà hàng Biển Xanh", "Vũng Tàu", "Tối", 180000, 126000, "Set menu hải sản."),
            ("Dalat Garden Restaurant", "Đà Lạt", "Trưa", 140000, 98000, "Ẩm thực địa phương."),
            ("Dalat Garden Restaurant", "Đà Lạt", "Tối", 170000, 119000, "Set menu."),
            ("Phú Quốc Seafood", "Phú Quốc", "Tối", 220000, 154000, "Hải sản."),
            ("Nha Trang Ocean Restaurant", "Nha Trang", "Trưa", 160000, 112000, "Set menu."),
            ("Hoi An Riverside Restaurant", "Đà Nẵng - Hội An", "Tối", 190000, 133000, "Ẩm thực miền Trung."),
            ("Highland Restaurant", "Buôn Ma Thuột", "Tối", 150000, 105000, "Ẩm thực Tây Nguyên."),
        ]
        cur.executemany("""
            INSERT INTO meals
            (restaurant_name,destination,meal_type,adult_price,child_price,description)
            VALUES (%s,%s,%s,%s,%s,%s)
        """, meals)

    cur.execute("SELECT COUNT(*) FROM transports")
    if cur.fetchone()[0] == 0:
        transports = [
            ("Xe Vũng Tàu 29 chỗ", "Vũng Tàu", "Xe du lịch", 0, 120000, "Xe du lịch theo khách."),
            ("Xe Đà Lạt 29 chỗ", "Đà Lạt", "Xe du lịch", 0, 180000, "Xe du lịch."),
            ("Xe Nha Trang 29 chỗ", "Nha Trang", "Xe du lịch", 0, 180000, "Xe du lịch."),
            ("Xe Buôn Ma Thuột 29 chỗ", "Buôn Ma Thuột", "Xe du lịch", 0, 170000, "Xe du lịch."),
            ("Vé máy bay Phú Quốc", "Phú Quốc", "Máy bay", 0, 1200000, "Giá mô phỏng cho bài tập."),
            ("Vé máy bay Đà Nẵng", "Đà Nẵng - Hội An", "Máy bay", 0, 950000, "Giá mô phỏng cho bài tập."),
        ]
        cur.executemany("""
            INSERT INTO transports
            (name,destination,vehicle_type,price_per_trip,price_per_person,description)
            VALUES (%s,%s,%s,%s,%s,%s)
        """, transports)

    conn.commit()
    cur.close()


# ============================================================
# HELPERS
# ============================================================

def hash_password(password):
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def money(value):
    try:
        return f"{float(value):,.0f} VNĐ"
    except Exception:
        return "0 VNĐ"


def query_df(sql, params=()):
    conn = get_connection()
    return pd.read_sql(sql, conn, params=params)


def execute(sql, params=()):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(sql, params)
    conn.commit()
    last_id = cur.lastrowid
    cur.close()
    return last_id


def fetch_one(sql, params=()):
    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute(sql, params)
    row = cur.fetchone()
    cur.close()
    return row


def get_tour(tour_id):
    return fetch_one("SELECT * FROM tours WHERE id=%s", (tour_id,))


def get_user(username, password):
    return fetch_one(
        "SELECT * FROM users WHERE username=%s AND password=%s",
        (username, hash_password(password))
    )


def login_required():
    if not st.session_state.get("user"):
        st.warning("Vui lòng đăng nhập.")
        st.stop()


def admin_required():
    login_required()
    if st.session_state.user["role"] != "admin":
        st.error("Bạn không có quyền truy cập.")
        st.stop()


def logout():
    st.session_state.clear()


def hotel_price(hotel):
    return float(hotel["peak_price"] if int(hotel["peak_season"]) == 1 else hotel["normal_price"])


def calculate_total(tour, hotel, meal, transport, adults, children, rooms):
    tour_amount = adults * float(tour["adult_price"]) + children * float(tour["child_price"])

    hotel_amount = 0
    if hotel is not None:
        hotel_amount = (
            hotel_price(hotel)
            * int(tour["nights"])
            * rooms
        )

    meal_amount = 0
    if meal is not None:
        meal_amount = (
            adults * float(meal["adult_price"])
            + children * float(meal["child_price"])
        )

    transport_amount = 0
    if transport is not None:
        total_people = adults + children
        transport_amount = (
            float(transport["price_per_person"]) * total_people
            + float(transport["price_per_trip"])
        )

    total = tour_amount + hotel_amount + meal_amount + transport_amount

    return {
        "tour": tour_amount,
        "hotel": hotel_amount,
        "meal": meal_amount,
        "transport": transport_amount,
        "total": total,
    }


# ============================================================
# INIT DATABASE
# ============================================================

ok, error_message = db_ok()
if not ok:
    st.error("❌ Không thể kết nối MySQL Aiven.")
    st.code(error_message)
    st.info(
        "Kiểm tra Host, Port, Username, Password và trạng thái RUNNING "
        "của MySQL trên Aiven."
    )
    st.stop()

try:
    init_db()
except Exception as e:
    st.error("❌ Kết nối được MySQL nhưng không thể khởi tạo bảng.")
    st.exception(e)
    st.stop()


# ============================================================
# CSS
# ============================================================

st.markdown("""
<style>
.stApp {
    background: #f5f7fb;
}
.hero {
    padding: 28px;
    border-radius: 18px;
    background: linear-gradient(135deg,#0b5ed7,#39a0ff);
    color: white;
    margin-bottom: 20px;
}
.hero h1,.hero h2,.hero p {
    color: white !important;
}
.card {
    background: white;
    padding: 18px;
    border-radius: 15px;
    box-shadow: 0 2px 12px rgba(0,0,0,.07);
    margin-bottom: 15px;
}
.price {
    color: #0b5ed7;
    font-size: 20px;
    font-weight: 700;
}
.total {
    font-size: 25px;
    font-weight: 800;
}
[data-testid="stMetric"] {
    background: white;
    padding: 14px;
    border-radius: 12px;
    box-shadow: 0 2px 8px rgba(0,0,0,.05);
}
</style>
""", unsafe_allow_html=True)


# ============================================================
# SESSION
# ============================================================

if "user" not in st.session_state:
    st.session_state.user = None

if "selected_tour_id" not in st.session_state:
    st.session_state.selected_tour_id = None


# ============================================================
# LOGIN / REGISTER
# ============================================================

if st.session_state.user is None:
    st.markdown("""
    <div class="hero">
        <h1>✈️ SMART TOUR</h1>
        <p>Hệ thống đặt tour du lịch thông minh</p>
        <p>Tour • Phòng • Nhà hàng • Phương tiện • Tính giá tự động</p>
    </div>
    """, unsafe_allow_html=True)

    tab1, tab2 = st.tabs(["🔐 Đăng nhập", "📝 Đăng ký"])

    with tab1:
        st.subheader("Đăng nhập")

        with st.form("login_form"):
            username = st.text_input("Tên đăng nhập")
            password = st.text_input("Mật khẩu", type="password")
            submit = st.form_submit_button(
                "🔐 Đăng nhập",
                use_container_width=True
            )

        if submit:
            user = get_user(username.strip(), password)
            if user:
                st.session_state.user = user
                st.success("Đăng nhập thành công!")
                st.rerun()
            else:
                st.error("Sai tên đăng nhập hoặc mật khẩu.")

        st.info("Admin mặc định: admin / admin123")

    with tab2:
        st.subheader("Tạo tài khoản")

        with st.form("register_form"):
            full_name = st.text_input("Họ và tên *")
            phone = st.text_input("Số điện thoại *")
            username = st.text_input("Tên đăng nhập *")
            password = st.text_input("Mật khẩu *", type="password")
            password2 = st.text_input("Nhập lại mật khẩu *", type="password")

            submit = st.form_submit_button(
                "📝 Đăng ký",
                use_container_width=True
            )

        if submit:
            if not full_name.strip() or not phone.strip() or not username.strip() or not password:
                st.error("Vui lòng nhập đủ thông tin.")
            elif password != password2:
                st.error("Mật khẩu nhập lại không khớp.")
            elif len(password) < 6:
                st.error("Mật khẩu tối thiểu 6 ký tự.")
            else:
                try:
                    execute("""
                        INSERT INTO users
                        (full_name,phone,username,password,role,created_at)
                        VALUES (%s,%s,%s,%s,'customer',%s)
                    """, (
                        full_name.strip(),
                        phone.strip(),
                        username.strip(),
                        hash_password(password),
                        datetime.now()
                    ))
                    st.success("Đăng ký thành công. Hãy đăng nhập.")
                except Error as e:
                    if "Duplicate" in str(e):
                        st.error("Tên đăng nhập đã tồn tại.")
                    else:
                        st.error(str(e))

    st.stop()


# ============================================================
# SIDEBAR
# ============================================================

user = st.session_state.user

st.sidebar.title("✈️ SMART TOUR")
st.sidebar.caption("Tour • Hotel • Meal • Transport")
st.sidebar.markdown("---")

if user["role"] == "admin":
    menu = [
        "🏠 Trang chủ",
        "🔎 Tìm & đặt tour",
        "📋 Đơn của tôi",
        "💳 Thanh toán",
        "🔧 Quản lý tour",
        "🏨 Quản lý phòng",
        "🍽️ Quản lý nhà hàng",
        "🚐 Quản lý phương tiện",
        "👥 Quản lý khách",
        "🧾 Quản lý đơn",
        "📊 Dashboard Admin",
    ]
else:
    menu = [
        "🏠 Trang chủ",
        "🔎 Tìm & đặt tour",
        "📋 Đơn của tôi",
        "💳 Thanh toán",
    ]

page = st.sidebar.radio("MENU", menu)

st.sidebar.markdown("---")
st.sidebar.write(f"👤 **{user['full_name']}**")
st.sidebar.write(f"📞 {user['phone']}")
st.sidebar.caption(f"Vai trò: {user['role']}")

if st.sidebar.button("🚪 Đăng xuất", use_container_width=True):
    logout()
    st.rerun()


# ============================================================
# TRANG CHỦ
# ============================================================

if page == "🏠 Trang chủ":
    tours = query_df("SELECT * FROM tours WHERE status='Đang mở'")
    hotels = query_df("SELECT * FROM hotels WHERE status='Đang hoạt động'")
    bookings = query_df(
        "SELECT * FROM bookings WHERE phone=%s ORDER BY id DESC",
        (user["phone"],)
    )

    st.markdown(f"""
    <div class="hero">
        <h1>Xin chào {user['full_name']} 👋</h1>
        <p>Chào mừng bạn đến với SMART TOUR.</p>
        <p>Đặt trọn gói tour, phòng, bữa ăn và phương tiện trong một đơn.</p>
    </div>
    """, unsafe_allow_html=True)

    c1,c2,c3,c4 = st.columns(4)
    c1.metric("🌍 Tour", len(tours))
    c2.metric("🏨 Khách sạn", len(hotels))
    c3.metric("🧾 Đơn của tôi", len(bookings))
    c4.metric(
        "💰 Tổng tiền",
        money(bookings["total_amount"].sum()) if not bookings.empty else "0 VNĐ"
    )

    st.subheader("⭐ Điểm nhấn của SMART TOUR")

    a,b,c,d = st.columns(4)
    a.markdown("### 🤖 Gợi ý thông minh\nTheo điểm đến, ngân sách và số khách.")
    b.markdown("### 👨‍👩‍👧 Người lớn & trẻ em\nTính giá riêng cho từng nhóm.")
    c.markdown("### 🏨 Giá mùa cao điểm\nAdmin có thể cập nhật giá phòng.")
    d.markdown("### 🧮 Báo giá minh bạch\nTách tour, phòng, ăn, xe.")

    st.markdown("---")
    st.subheader("🔥 Tour nổi bật")

    featured = tours.head(4)
    cols = st.columns(2)

    for i, (_, t) in enumerate(featured.iterrows()):
        with cols[i % 2]:
            st.markdown(f"""
            <div class="card">
                <h3>🌴 {t['name']}</h3>
                <p>📍 {t['destination']} | ⏱️ {t['duration']}</p>
                <p class="price">Người lớn: {money(t['adult_price'])}</p>
                <p>👶 Trẻ em: {money(t['child_price'])}</p>
                <p>{t['description']}</p>
            </div>
            """, unsafe_allow_html=True)


# ============================================================
# TÌM & ĐẶT TOUR
# ============================================================

elif page == "🔎 Tìm & đặt tour":
    st.title("🔎 TÌM & ĐẶT TOUR")

    tours = query_df("""
        SELECT * FROM tours
        WHERE status='Đang mở'
        ORDER BY id DESC
    """)

    if tours.empty:
        st.warning("Chưa có tour.")
        st.stop()

    destinations = ["Tất cả"] + sorted(tours["destination"].unique().tolist())

    c1,c2,c3 = st.columns(3)

    with c1:
        destination = st.selectbox("📍 Điểm đến", destinations)

    with c2:
        adults = st.number_input("👨 Người lớn", 1, 100, 2)

    with c3:
        children = st.number_input("👶 Trẻ em", 0, 100, 0)

    budget = st.number_input(
        "💰 Ngân sách dự kiến",
        min_value=0,
        value=10000000,
        step=500000
    )

    interests = st.multiselect(
        "❤️ Sở thích",
        ["biển","ăn uống","nghỉ dưỡng","chụp ảnh","cafe",
         "thiên nhiên","gia đình","giải trí","văn hóa",
         "khám phá","hải sản"],
        default=["biển","ăn uống"]
    )

    filtered = tours.copy()

    if destination != "Tất cả":
        filtered = filtered[
            filtered["destination"].str.contains(
                destination, case=False, na=False
            )
        ]

    if filtered.empty:
        st.warning("Không có tour phù hợp.")
    else:
        filtered["estimated_base"] = (
            adults * filtered["adult_price"]
            + children * filtered["child_price"]
        )

        def score(row):
            s = 0
            text = str(row["interests"]).lower()

            for interest in interests:
                if interest.lower() in text:
                    s += 10

            if row["estimated_base"] <= budget:
                s += 30
            elif row["estimated_base"] <= budget * 1.15:
                s += 10

            if int(row["available_seats"]) >= adults + children:
                s += 20

            return s

        filtered["score"] = filtered.apply(score, axis=1)
        filtered = filtered.sort_values(
            ["score","estimated_base"],
            ascending=[False,True]
        )

        st.subheader("🤖 Phương án đề xuất")

        for _, t in filtered.head(6).iterrows():
            with st.container(border=True):
                st.markdown(f"### 🌴 {t['name']}")
                st.write(
                    f"📍 {t['destination']} | ⏱️ {t['duration']} | "
                    f"🪑 Còn {int(t['available_seats'])} chỗ"
                )
                st.write(
                    f"👨 {adults} người lớn × {money(t['adult_price'])} = "
                    f"{money(adults * float(t['adult_price']))}"
                )
                st.write(
                    f"👶 {children} trẻ em × {money(t['child_price'])} = "
                    f"{money(children * float(t['child_price']))}"
                )
                st.write(
                    f"💰 Giá tour cơ bản: "
                    f"**{money(t['estimated_base'])}**"
                )

                if st.button(
                    f"📅 Chọn tour này",
                    key=f"select_tour_{int(t['id'])}"
                ):
                    st.session_state.selected_tour_id = int(t["id"])
                    st.session_state.selected_adults = int(adults)
                    st.session_state.selected_children = int(children)
                    st.rerun()

    # ---------------- BOOKING ----------------
    if st.session_state.selected_tour_id:
        tour = get_tour(st.session_state.selected_tour_id)

        if tour:
            st.markdown("---")
            st.title("📅 ĐẶT TOUR TRỌN GÓI")

            st.info(
                "Bạn đang đặt: "
                f"**{tour['name']}** — {tour['destination']}"
            )

            c1,c2,c3 = st.columns(3)

            with c1:
                booking_adults = st.number_input(
                    "👨 Người lớn",
                    1,
                    int(tour["available_seats"]),
                    int(st.session_state.get("selected_adults",2))
                )

            with c2:
                max_children = max(
                    0,
                    int(tour["available_seats"]) - int(booking_adults)
                )
                booking_children = st.number_input(
                    "👶 Trẻ em",
                    0,
                    max_children,
                    min(
                        int(st.session_state.get("selected_children",0)),
                        max_children
                    )
                )

            with c3:
                room_count = st.number_input(
                    "🏨 Số phòng",
                    1,
                    20,
                    max(
                        1,
                        (int(booking_adults)+int(booking_children)+1)//2
                    )
                )

            c1,c2 = st.columns(2)

            with c1:
                departure_date = st.date_input(
                    "📅 Ngày khởi hành",
                    min_value=date.today(),
                    value=date.today()
                )

            with c2:
                departure_time = st.time_input(
                    "⏰ Giờ khởi hành",
                    value=time(6,30)
                )

            hotels = query_df("""
                SELECT * FROM hotels
                WHERE destination=%s
                AND status='Đang hoạt động'
                AND available_rooms >= %s
                ORDER BY stars DESC
            """, (tour["destination"], int(room_count)))

            if hotels.empty:
                st.warning("Không còn phòng phù hợp tại điểm đến này.")
                hotel = None
                hotel_label = "Không có phòng"
            else:
                hotel_options = {}
                for _, h in hotels.iterrows():
                    season = "CAO ĐIỂM" if int(h["peak_season"]) else "THƯỜNG"
                    hotel_options[
                        f"{h['name']} | {h['room_type']} | "
                        f"{season} | {money(hotel_price(h))}/đêm"
                    ] = int(h["id"])

                hotel_label = st.selectbox(
                    "🏨 Chọn khách sạn/phòng",
                    list(hotel_options.keys())
                )

                hotel_id = hotel_options[hotel_label]
                hotel = fetch_one(
                    "SELECT * FROM hotels WHERE id=%s",
                    (hotel_id,)
                )

            meals = query_df("""
                SELECT * FROM meals
                WHERE destination=%s
                AND status='Đang hoạt động'
                ORDER BY restaurant_name, meal_type
            """, (tour["destination"],))

            if meals.empty:
                meal = None
                st.info("Chưa có dữ liệu bữa ăn.")
            else:
                meal_options = {
                    f"{m['restaurant_name']} - {m['meal_type']} | "
                    f"NL {money(m['adult_price'])} | "
                    f"TE {money(m['child_price'])}": int(m["id"])
                    for _,m in meals.iterrows()
                }

                meal_label = st.selectbox(
                    "🍽️ Nhà hàng & bữa ăn",
                    list(meal_options.keys())
                )
                meal = fetch_one(
                    "SELECT * FROM meals WHERE id=%s",
                    (meal_options[meal_label],)
                )

            transports = query_df("""
                SELECT * FROM transports
                WHERE destination=%s
                AND status='Đang hoạt động'
            """, (tour["destination"],))

            if transports.empty:
                transport = None
                st.info("Chưa có dữ liệu phương tiện.")
            else:
                transport_options = {
                    f"{x['name']} | {x['vehicle_type']} | "
                    f"{money(x['price_per_person'])}/người": int(x["id"])
                    for _,x in transports.iterrows()
                }

                transport_label = st.selectbox(
                    "🚐 Phương tiện đi lại",
                    list(transport_options.keys())
                )
                transport = fetch_one(
                    "SELECT * FROM transports WHERE id=%s",
                    (transport_options[transport_label],)
                )

            note = st.text_area(
                "📝 Ghi chú",
                placeholder="Ví dụ: cần phòng tầng thấp, ăn chay..."
            )

            payment_method = st.selectbox(
                "💳 Phương thức thanh toán",
                [
                    "Chuyển khoản ngân hàng",
                    "Ví điện tử",
                    "Thanh toán tại văn phòng"
                ]
            )

            # Tính giá trực tiếp
            amounts = calculate_total(
                tour,
                hotel,
                meal,
                transport,
                int(booking_adults),
                int(booking_children),
                int(room_count)
            )

            st.markdown("---")
            st.subheader("🧮 CHI TIẾT GIÁ")

            c1,c2,c3,c4 = st.columns(4)
            c1.metric("🌴 Tiền tour", money(amounts["tour"]))
            c2.metric("🏨 Tiền phòng", money(amounts["hotel"]))
            c3.metric("🍽️ Tiền ăn", money(amounts["meal"]))
            c4.metric("🚐 Tiền xe", money(amounts["transport"]))

            st.markdown(
                f'<div class="card total">💰 TỔNG CỘNG: '
                f'{money(amounts["total"])}</div>',
                unsafe_allow_html=True
            )

            if budget > 0:
                if amounts["total"] <= budget:
                    st.success(
                        f"✅ Trong ngân sách. Còn {money(budget-amounts['total'])}."
                    )
                else:
                    st.warning(
                        f"⚠️ Vượt ngân sách {money(amounts['total']-budget)}."
                    )

            if st.button(
                "🚀 XÁC NHẬN ĐẶT TOUR",
                type="primary",
                use_container_width=True
            ):
                total_people = int(booking_adults) + int(booking_children)

                if total_people > int(tour["available_seats"]):
                    st.error("Tour không đủ chỗ.")
                elif hotel and int(hotel["available_rooms"]) < int(room_count):
                    st.error("Khách sạn không đủ phòng.")
                else:
                    booking_id = execute("""
                        INSERT INTO bookings (
                            full_name,phone,tour_id,hotel_id,meal_id,transport_id,
                            booking_date,departure_date,departure_time,
                            adults,children,rooms,nights,
                            tour_amount,hotel_amount,meal_amount,
                            transport_amount,total_amount,
                            payment_method,payment_status,booking_status,note
                        )
                        VALUES (
                            %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,
                            %s,%s,%s,%s,%s,%s,'Chưa thanh toán','Chờ xác nhận',%s
                        )
                    """, (
                        user["full_name"],
                        user["phone"],
                        int(tour["id"]),
                        int(hotel["id"]) if hotel else None,
                        int(meal["id"]) if meal else None,
                        int(transport["id"]) if transport else None,
                        datetime.now(),
                        departure_date,
                        departure_time,
                        int(booking_adults),
                        int(booking_children),
                        int(room_count),
                        int(tour["nights"]),
                        amounts["tour"],
                        amounts["hotel"],
                        amounts["meal"],
                        amounts["transport"],
                        amounts["total"],
                        payment_method,
                        note
                    ))

                    execute("""
                        UPDATE tours
                        SET available_seats = available_seats - %s
                        WHERE id=%s
                    """, (total_people, int(tour["id"])))

                    if hotel:
                        execute("""
                            UPDATE hotels
                            SET available_rooms = available_rooms - %s
                            WHERE id=%s
                        """, (int(room_count), int(hotel["id"])))

                    st.success(
                        f"🎉 Đặt tour thành công! Mã đơn: **#{booking_id}**"
                    )

                    st.info(
                        f"Khởi hành: {departure_date.strftime('%d/%m/%Y')} "
                        f"lúc {departure_time.strftime('%H:%M')}"
                    )

                    st.session_state.selected_tour_id = None
                    st.rerun()


# ============================================================
# ĐƠN CỦA TÔI
# ============================================================

elif page == "📋 Đơn của tôi":
    st.title("📋 ĐƠN ĐẶT CỦA TÔI")

    bookings = query_df("""
        SELECT
            b.*,
            t.name AS tour_name,
            t.destination,
            h.name AS hotel_name,
            m.restaurant_name,
            m.meal_type,
            tr.name AS transport_name
        FROM bookings b
        JOIN tours t ON b.tour_id=t.id
        LEFT JOIN hotels h ON b.hotel_id=h.id
        LEFT JOIN meals m ON b.meal_id=m.id
        LEFT JOIN transports tr ON b.transport_id=tr.id
        WHERE b.phone=%s
        ORDER BY b.id DESC
    """, (user["phone"],))

    if bookings.empty:
        st.info("Bạn chưa có đơn.")
    else:
        for _,b in bookings.iterrows():
            with st.expander(
                f"#{int(b['id'])} — {b['tour_name']} — {b['booking_status']}"
            ):
                st.write(f"👤 **Khách:** {b['full_name']}")
                st.write(f"📞 **SĐT:** {b['phone']}")
                st.write(f"📍 **Điểm đến:** {b['destination']}")
                st.write(
                    f"📅 **Khởi hành:** "
                    f"{pd.to_datetime(b['departure_date']).strftime('%d/%m/%Y')} "
                    f"{str(b['departure_time'])[:5]}"
                )
                st.write(
                    f"👨 Người lớn: **{int(b['adults'])}** | "
                    f"👶 Trẻ em: **{int(b['children'])}**"
                )
                st.write(f"🏨 Phòng: {b['hotel_name'] or 'Không chọn'}")
                st.write(
                    f"🍽️ Bữa ăn: "
                    f"{b['restaurant_name'] or 'Không chọn'} "
                    f"{b['meal_type'] or ''}"
                )
                st.write(
                    f"🚐 Phương tiện: "
                    f"{b['transport_name'] or 'Không chọn'}"
                )

                st.markdown("### 🧮 Chi phí")
                st.write(f"🌴 Tour: **{money(b['tour_amount'])}**")
                st.write(f"🏨 Phòng: **{money(b['hotel_amount'])}**")
                st.write(f"🍽️ Ăn: **{money(b['meal_amount'])}**")
                st.write(f"🚐 Xe: **{money(b['transport_amount'])}**")
                st.markdown(
                    f"### 💰 Tổng: **{money(b['total_amount'])}**"
                )
                st.write(f"💳 Thanh toán: {b['payment_status']}")
                st.write(f"📌 Trạng thái: {b['booking_status']}")


# ============================================================
# THANH TOÁN
# ============================================================

elif page == "💳 Thanh toán":
    st.title("💳 THANH TOÁN")

    bookings = query_df("""
        SELECT b.*,t.name AS tour_name
        FROM bookings b
        JOIN tours t ON b.tour_id=t.id
        WHERE b.phone=%s
        AND b.payment_status='Chưa thanh toán'
        AND b.booking_status!='Đã hủy'
        ORDER BY b.id DESC
    """, (user["phone"],))

    if bookings.empty:
        st.success("Không có đơn đang chờ thanh toán.")
    else:
        options = {
            f"#{int(r['id'])} - {r['tour_name']} - {money(r['total_amount'])}":
            int(r["id"])
            for _,r in bookings.iterrows()
        }

        selected = st.selectbox("Chọn đơn", list(options.keys()))
        booking_id = options[selected]

        method = st.radio(
            "Phương thức",
            [
                "Chuyển khoản ngân hàng",
                "Ví điện tử",
                "Thanh toán tại văn phòng"
            ]
        )

        if st.button(
            "💳 XÁC NHẬN THANH TOÁN",
            type="primary",
            use_container_width=True
        ):
            booking = fetch_one(
                "SELECT * FROM bookings WHERE id=%s",
                (booking_id,)
            )

            execute("""
                UPDATE bookings
                SET payment_status='Đã thanh toán',
                    booking_status='Đã xác nhận',
                    payment_method=%s
                WHERE id=%s
            """, (method, booking_id))

            execute("""
                INSERT INTO payments
                (booking_id,amount,method,paid_at,status)
                VALUES (%s,%s,%s,%s,'Thành công')
            """, (
                booking_id,
                float(booking["total_amount"]),
                method,
                datetime.now()
            ))

            st.success("✅ Thanh toán thành công!")
            st.rerun()


# ============================================================
# ADMIN - TOUR
# ============================================================

elif page == "🔧 Quản lý tour":
    admin_required()
    st.title("🔧 QUẢN LÝ TOUR")

    tours = query_df("SELECT * FROM tours ORDER BY id DESC")

    st.dataframe(
        tours[
            [
                "id","name","destination","adult_price","child_price",
                "available_seats","status"
            ]
        ].rename(columns={
            "id":"ID",
            "name":"Tên tour",
            "destination":"Điểm đến",
            "adult_price":"Giá NL",
            "child_price":"Giá TE",
            "available_seats":"Chỗ còn",
            "status":"Trạng thái"
        }),
        use_container_width=True,
        hide_index=True
    )

    st.subheader("✏️ Cập nhật giá/trạng thái")

    if not tours.empty:
        tour_id = st.selectbox("Chọn tour", tours["id"].tolist())
        tour = tours[tours["id"] == tour_id].iloc[0]

        with st.form("edit_tour"):
            c1,c2,c3 = st.columns(3)

            with c1:
                adult_price = st.number_input(
                    "Giá người lớn",
                    0,
                    100000000,
                    int(tour["adult_price"]),
                    100000
                )

            with c2:
                child_price = st.number_input(
                    "Giá trẻ em",
                    0,
                    100000000,
                    int(tour["child_price"]),
                    100000
                )

            with c3:
                seats = st.number_input(
                    "Chỗ còn",
                    0,
                    1000,
                    int(tour["available_seats"])
                )

            status = st.selectbox(
                "Trạng thái",
                ["Đang mở","Tạm dừng","Đã đóng"],
                index=["Đang mở","Tạm dừng","Đã đóng"].index(tour["status"])
            )

            save = st.form_submit_button(
                "💾 Lưu",
                use_container_width=True
            )

        if save:
            execute("""
                UPDATE tours
                SET adult_price=%s,
                    child_price=%s,
                    available_seats=%s,
                    status=%s
                WHERE id=%s
            """, (
                adult_price,
                child_price,
                seats,
                status,
                int(tour_id)
            ))
            st.success("Đã cập nhật tour.")
            st.rerun()

    st.subheader("➕ Thêm tour")

    with st.form("add_tour"):
        name = st.text_input("Tên tour *")
        destination = st.text_input("Điểm đến *")
        duration = st.text_input("Thời gian", "3 ngày 2 đêm")

        c1,c2,c3,c4 = st.columns(4)
        days = c1.number_input("Số ngày",1,30,3)
        nights = c2.number_input("Số đêm",0,30,2)
        adult_price = c3.number_input("Giá NL",0,100000000,2000000,100000)
        child_price = c4.number_input("Giá TE",0,100000000,1400000,100000)

        seats = st.number_input("Số chỗ",1,1000,30)
        interests = st.text_input("Sở thích", "biển,ăn uống")
        description = st.text_area("Mô tả")

        save = st.form_submit_button(
            "➕ Thêm tour",
            use_container_width=True
        )

    if save:
        if not name.strip() or not destination.strip():
            st.error("Vui lòng nhập tên và điểm đến.")
        else:
            execute("""
                INSERT INTO tours
                (name,destination,duration,days,nights,adult_price,
                 child_price,max_people,available_seats,interests,description)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """, (
                name.strip(),destination.strip(),duration,days,nights,
                adult_price,child_price,seats,seats,interests,description
            ))
            st.success("Đã thêm tour.")
            st.rerun()


# ============================================================
# ADMIN - KHÁCH SẠN / PHÒNG
# ============================================================

elif page == "🏨 Quản lý phòng":
    admin_required()
    st.title("🏨 QUẢN LÝ PHÒNG & GIÁ MÙA CAO ĐIỂM")

    hotels = query_df("SELECT * FROM hotels ORDER BY id DESC")

    st.dataframe(
        hotels[
            [
                "id","name","destination","stars","room_type",
                "normal_price","peak_price","peak_season",
                "available_rooms","status"
            ]
        ].rename(columns={
            "id":"ID",
            "name":"Khách sạn",
            "destination":"Điểm đến",
            "stars":"Sao",
            "room_type":"Loại phòng",
            "normal_price":"Giá thường",
            "peak_price":"Giá cao điểm",
            "peak_season":"Đang cao điểm",
            "available_rooms":"Phòng còn",
            "status":"Trạng thái"
        }),
        use_container_width=True,
        hide_index=True
    )

    if not hotels.empty:
        hotel_id = st.selectbox(
            "Chọn khách sạn/phòng để cập nhật",
            hotels["id"].tolist()
        )

        h = hotels[hotels["id"] == hotel_id].iloc[0]

        with st.form("edit_hotel"):
            normal_price = st.number_input(
                "💵 Giá mùa thường",
                0,
                100000000,
                int(h["normal_price"]),
                50000
            )

            peak_price = st.number_input(
                "🔥 Giá mùa cao điểm",
                0,
                100000000,
                int(h["peak_price"]),
                50000
            )

            peak = st.checkbox(
                "🔥 Đang áp dụng giá cao điểm",
                value=bool(h["peak_season"])
            )

            available = st.number_input(
                "Phòng còn",
                0,
                10000,
                int(h["available_rooms"])
            )

            status = st.selectbox(
                "Trạng thái",
                ["Đang hoạt động","Tạm dừng"],
                index=0 if h["status"] == "Đang hoạt động" else 1
            )

            save = st.form_submit_button(
                "💾 Cập nhật giá phòng",
                use_container_width=True
            )

        if save:
            execute("""
                UPDATE hotels
                SET normal_price=%s,
                    peak_price=%s,
                    peak_season=%s,
                    available_rooms=%s,
                    status=%s
                WHERE id=%s
            """, (
                normal_price,
                peak_price,
                int(peak),
                available,
                status,
                int(hotel_id)
            ))
            st.success(
                "Đã cập nhật. Khách đặt mới sẽ lấy giá hiện tại từ database."
            )
            st.rerun()

    st.subheader("➕ Thêm loại phòng")

    with st.form("add_hotel"):
        name = st.text_input("Tên khách sạn *")
        destination = st.text_input("Điểm đến *")

        c1,c2,c3 = st.columns(3)
        stars = c1.selectbox("Số sao",[1,2,3,4,5],index=2)
        room_type = c2.selectbox(
            "Loại phòng",
            ["Phòng đơn","Phòng đôi","Phòng gia đình","Suite"]
        )
        rooms = c3.number_input("Tổng phòng",1,10000,20)

        c1,c2 = st.columns(2)
        normal_price = c1.number_input(
            "Giá thường",0,100000000,800000,50000
        )
        peak_price = c2.number_input(
            "Giá cao điểm",0,100000000,1100000,50000
        )

        description = st.text_area("Mô tả")

        save = st.form_submit_button(
            "➕ Thêm phòng",
            use_container_width=True
        )

    if save:
        if not name.strip() or not destination.strip():
            st.error("Vui lòng nhập tên và điểm đến.")
        else:
            execute("""
                INSERT INTO hotels
                (name,destination,stars,room_type,normal_price,peak_price,
                 total_rooms,available_rooms,description)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """, (
                name,destination,stars,room_type,
                normal_price,peak_price,rooms,rooms,description
            ))
            st.success("Đã thêm phòng.")
            st.rerun()


# ============================================================
# ADMIN - NHÀ HÀNG / BỮA ĂN
# ============================================================

elif page == "🍽️ Quản lý nhà hàng":
    admin_required()
    st.title("🍽️ QUẢN LÝ NHÀ HÀNG & BỮA ĂN")

    meals = query_df("SELECT * FROM meals ORDER BY id DESC")

    st.dataframe(
        meals.rename(columns={
            "id":"ID",
            "restaurant_name":"Nhà hàng",
            "destination":"Điểm đến",
            "meal_type":"Bữa",
            "adult_price":"Giá NL",
            "child_price":"Giá TE",
            "status":"Trạng thái"
        }),
        use_container_width=True,
        hide_index=True
    )

    with st.form("add_meal"):
        restaurant = st.text_input("Tên nhà hàng *")
        destination = st.text_input("Điểm đến *")
        meal_type = st.selectbox(
            "Bữa ăn",
            ["Sáng","Trưa","Tối","Combo"]
        )

        c1,c2 = st.columns(2)
        adult_price = c1.number_input(
            "Giá người lớn",
            0,10000000,150000,10000
        )
        child_price = c2.number_input(
            "Giá trẻ em",
            0,10000000,105000,10000
        )

        description = st.text_area("Mô tả")
        save = st.form_submit_button(
            "➕ Thêm bữa ăn",
            use_container_width=True
        )

    if save:
        if not restaurant.strip() or not destination.strip():
            st.error("Vui lòng nhập đủ thông tin.")
        else:
            execute("""
                INSERT INTO meals
                (restaurant_name,destination,meal_type,
                 adult_price,child_price,description)
                VALUES (%s,%s,%s,%s,%s,%s)
            """, (
                restaurant,destination,meal_type,
                adult_price,child_price,description
            ))
            st.success("Đã thêm bữa ăn.")
            st.rerun()


# ============================================================
# ADMIN - PHƯƠNG TIỆN
# ============================================================

elif page == "🚐 Quản lý phương tiện":
    admin_required()
    st.title("🚐 QUẢN LÝ PHƯƠNG TIỆN")

    transports = query_df("SELECT * FROM transports ORDER BY id DESC")

    st.dataframe(
        transports.rename(columns={
            "id":"ID",
            "name":"Tên",
            "destination":"Điểm đến",
            "vehicle_type":"Loại xe",
            "price_per_trip":"Giá/chuyến",
            "price_per_person":"Giá/người",
            "status":"Trạng thái"
        }),
        use_container_width=True,
        hide_index=True
    )

    with st.form("add_transport"):
        name = st.text_input("Tên phương tiện *")
        destination = st.text_input("Điểm đến *")
        vehicle_type = st.selectbox(
            "Loại phương tiện",
            ["Xe du lịch","Xe riêng","Máy bay","Tàu","Xe + máy bay"]
        )

        c1,c2 = st.columns(2)
        price_per_trip = c1.number_input(
            "Giá/chuyến",
            0,100000000,0,50000
        )
        price_per_person = c2.number_input(
            "Giá/người",
            0,100000000,150000,50000
        )

        description = st.text_area("Mô tả")

        save = st.form_submit_button(
            "➕ Thêm phương tiện",
            use_container_width=True
        )

    if save:
        if not name.strip() or not destination.strip():
            st.error("Vui lòng nhập đủ thông tin.")
        else:
            execute("""
                INSERT INTO transports
                (name,destination,vehicle_type,price_per_trip,
                 price_per_person,description)
                VALUES (%s,%s,%s,%s,%s,%s)
            """, (
                name,destination,vehicle_type,
                price_per_trip,price_per_person,description
            ))
            st.success("Đã thêm phương tiện.")
            st.rerun()


# ============================================================
# ADMIN - KHÁCH
# ============================================================

elif page == "👥 Quản lý khách":
    admin_required()
    st.title("👥 QUẢN LÝ KHÁCH HÀNG")

    users = query_df("""
        SELECT id,full_name,phone,username,created_at
        FROM users
        WHERE role='customer'
        ORDER BY id DESC
    """)

    if users.empty:
        st.info("Chưa có khách hàng.")
    else:
        st.dataframe(
            users.rename(columns={
                "id":"ID",
                "full_name":"Họ tên",
                "phone":"SĐT",
                "username":"Tài khoản",
                "created_at":"Ngày đăng ký"
            }),
            use_container_width=True,
            hide_index=True
        )


# ============================================================
# ADMIN - ĐƠN
# ============================================================

elif page == "🧾 Quản lý đơn":
    admin_required()
    st.title("🧾 QUẢN LÝ ĐƠN ĐẶT")

    bookings = query_df("""
        SELECT
            b.id,
            b.full_name,
            b.phone,
            t.name AS tour_name,
            t.destination,
            b.departure_date,
            b.departure_time,
            b.adults,
            b.children,
            b.rooms,
            b.total_amount,
            b.payment_status,
            b.booking_status
        FROM bookings b
        JOIN tours t ON b.tour_id=t.id
        ORDER BY b.id DESC
    """)

    if bookings.empty:
        st.info("Chưa có đơn.")
    else:
        st.dataframe(
            bookings.rename(columns={
                "id":"ID",
                "full_name":"Khách",
                "phone":"SĐT",
                "tour_name":"Tour",
                "destination":"Điểm đến",
                "departure_date":"Ngày đi",
                "departure_time":"Giờ đi",
                "adults":"NL",
                "children":"TE",
                "rooms":"Phòng",
                "total_amount":"Tổng tiền",
                "payment_status":"Thanh toán",
                "booking_status":"Trạng thái"
            }),
            use_container_width=True,
            hide_index=True
        )

        st.subheader("⚙️ Xử lý đơn")

        booking_id = st.selectbox(
            "Chọn ID đơn",
            bookings["id"].tolist()
        )

        selected = bookings[
            bookings["id"] == booking_id
        ].iloc[0]

        new_status = st.selectbox(
            "Trạng thái đơn",
            [
                "Chờ xác nhận",
                "Đã xác nhận",
                "Đã hoàn thành",
                "Đã hủy"
            ],
            index=[
                "Chờ xác nhận",
                "Đã xác nhận",
                "Đã hoàn thành",
                "Đã hủy"
            ].index(selected["booking_status"])
        )

        if st.button(
            "💾 Cập nhật trạng thái",
            use_container_width=True
        ):
            execute("""
                UPDATE bookings
                SET booking_status=%s
                WHERE id=%s
            """, (new_status,int(booking_id)))

            st.success("Đã cập nhật.")
            st.rerun()


# ============================================================
# ADMIN DASHBOARD
# ============================================================

elif page == "📊 Dashboard Admin":
    admin_required()
    st.title("📊 DASHBOARD SMART TOUR")

    customers = query_df(
        "SELECT * FROM users WHERE role='customer'"
    )
    tours = query_df("SELECT * FROM tours")
    hotels = query_df("SELECT * FROM hotels")
    bookings = query_df("SELECT * FROM bookings")
    payments = query_df("SELECT * FROM payments")

    revenue = (
        payments[payments["status"]=="Thành công"]["amount"].sum()
        if not payments.empty else 0
    )

    c1,c2,c3,c4,c5 = st.columns(5)

    c1.metric("👥 Khách",len(customers))
    c2.metric("🌍 Tour",len(tours))
    c3.metric("🏨 Phòng",len(hotels))
    c4.metric("🧾 Đơn",len(bookings))
    c5.metric("💰 Doanh thu",money(revenue))

    st.markdown("---")

    if not bookings.empty:
        st.subheader("📈 Đơn theo trạng thái")
        st.bar_chart(
            bookings["booking_status"].value_counts()
        )

    if not payments.empty:
        st.subheader("💳 Doanh thu theo phương thức")
        st.bar_chart(
            payments.groupby("method")["amount"].sum()
        )

    st.subheader("🔥 Tour được đặt nhiều")

    if not bookings.empty:
        popular = (
            bookings.groupby("tour_id")
            .size()
            .reset_index(name="so_don")
            .merge(
                tours[["id","name","destination"]],
                left_on="tour_id",
                right_on="id"
            )
            .sort_values("so_don",ascending=False)
        )

        st.dataframe(
            popular[
                ["name","destination","so_don"]
            ].rename(columns={
                "name":"Tour",
                "destination":"Điểm đến",
                "so_don":"Số đơn"
            }),
            use_container_width=True,
            hide_index=True
        )

    st.subheader("🗄️ Trạng thái database")

    try:
        db_info = query_df(
            "SELECT DATABASE() AS db_name, VERSION() AS version"
        )
        st.dataframe(
            db_info,
            use_container_width=True,
            hide_index=True
        )
    except Exception as e:
        st.error(str(e))

