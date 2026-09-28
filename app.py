import streamlit as st
import mysql.connector
from mysql.connector import Error
from decimal import Decimal, ROUND_HALF_UP
from datetime import date, datetime, timedelta
import pandas as pd

# ============================================================
# SMART TOUR - APP ĐẶT TOUR + ĐIỀU HÀNH TOUR
# Streamlit + MySQL Aiven
#
# Chạy:
#   pip install -r requirements.txt
#   streamlit run app.py
# ============================================================

st.set_page_config(
    page_title="SMART TOUR",
    page_icon="✈️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ============================================================
# MYSQL AIVEN - THÔNG TIN TỪ ẢNH NGƯỜI DÙNG CUNG CẤP
# ============================================================
DB_CONFIG = {
    "host": "mysql-1b346c1b-kimchi8019-4ea9.e.aivencloud.com",
    "port": 21314,
    "user": "avnadmin",
    "password": "AVNS_ZuLUVTHk6cKBskjg0Kp",
    "database": "defaultdb",
    "connection_timeout": 15,
    "autocommit": False,
    "ssl_disabled": False,  # Aiven đang để SSL REQUIRED
}

# Nếu muốn xác thực CA certificate chặt hơn:
# SSL_CA_PATH = r"C:\duong-dan\ca.pem"
SSL_CA_PATH = ""

# ============================================================
# GIAO DIỆN
# ============================================================
st.markdown("""
<style>
.stApp { background:#f5f7fb; }
.hero {
    padding:32px;
    border-radius:20px;
    background:linear-gradient(135deg,#0757b8,#2d9cff);
    color:#fff;
    margin-bottom:22px;
}
.hero h1,.hero h2,.hero p { color:#fff !important; }
.card {
    background:#fff;
    padding:20px;
    border-radius:16px;
    box-shadow:0 2px 12px rgba(0,0,0,.07);
    margin-bottom:16px;
}
.total {
    font-size:30px;
    font-weight:900;
    color:#0757b8;
}
.price {
    font-size:22px;
    font-weight:800;
    color:#0757b8;
}
.note {
    background:#eef6ff;
    border-left:4px solid #0b5ed7;
    padding:12px 16px;
    border-radius:8px;
}
.warning {
    background:#fff8e6;
    border-left:4px solid #f0a000;
    padding:12px 16px;
    border-radius:8px;
}
.danger {
    background:#fff0f0;
    border-left:4px solid #d33;
    padding:12px 16px;
    border-radius:8px;
}
</style>
""", unsafe_allow_html=True)

# ============================================================
# HÀM CHUNG
# ============================================================
def money(v):
    try:
        d = Decimal(str(v)).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
        return f"{d:,.0f} VNĐ"
    except Exception:
        return "0 VNĐ"

def D(v):
    return Decimal(str(v or 0))

def age_group(age):
    age = int(age)
    if age <= 1:
        return "infant"
    if age <= 5:
        return "young_child"
    if age <= 10:
        return "child"
    return "adult"

def group_name(group):
    return {
        "adult": "Người lớn (11+)",
        "child": "Trẻ em (6–10)",
        "young_child": "Trẻ nhỏ (2–5)",
        "infant": "Em bé (0–1)",
    }[group]

def normalize_phone(phone):
    return "".join(x for x in str(phone) if x.isdigit())

# ============================================================
# DATABASE
# ============================================================
def db_connect():
    cfg = DB_CONFIG.copy()
    if SSL_CA_PATH:
        cfg["ssl_ca"] = SSL_CA_PATH
        cfg["ssl_verify_cert"] = True
        cfg["ssl_verify_identity"] = True
    return mysql.connector.connect(**cfg)

def execute(sql, params=(), fetch=None):
    conn = None
    cur = None
    try:
        conn = db_connect()
        cur = conn.cursor(dictionary=True)
        cur.execute(sql, params)

        if fetch == "one":
            return cur.fetchone()
        if fetch == "all":
            return cur.fetchall()

        conn.commit()
        return cur.lastrowid
    except Exception:
        if conn:
            conn.rollback()
        raise
    finally:
        if cur:
            cur.close()
        if conn and conn.is_connected():
            conn.close()

def df_query(sql, params=()):
    conn = db_connect()
    try:
        return pd.read_sql(sql, conn, params=params)
    finally:
        if conn and conn.is_connected():
            conn.close()

# ============================================================
# KHỞI TẠO CSDL
# ============================================================
def init_database():
    conn = db_connect()
    cur = conn.cursor()

    tables = [
        """
        CREATE TABLE IF NOT EXISTS tours (
            id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(200) NOT NULL,
            destination VARCHAR(150) NOT NULL,
            duration VARCHAR(100) NOT NULL,
            days INT NOT NULL DEFAULT 1,
            nights INT NOT NULL DEFAULT 0,
            adult_price DECIMAL(15,2) NOT NULL DEFAULT 0,
            child_price DECIMAL(15,2) NOT NULL DEFAULT 0,
            infant_price DECIMAL(15,2) NOT NULL DEFAULT 0,
            max_people INT NOT NULL DEFAULT 30,
            available_seats INT NOT NULL DEFAULT 30,
            description VARCHAR(2000) DEFAULT '',
            interests VARCHAR(500) DEFAULT '',
            status VARCHAR(30) NOT NULL DEFAULT 'Đang mở',
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """,
        """
        CREATE TABLE IF NOT EXISTS peak_seasons (
            id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(150) NOT NULL,
            start_date DATE NOT NULL,
            end_date DATE NOT NULL,
            surcharge_percent DECIMAL(5,2) NOT NULL DEFAULT 0,
            status VARCHAR(30) NOT NULL DEFAULT 'Đang áp dụng'
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """,
        """
        CREATE TABLE IF NOT EXISTS hotels (
            id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(200) NOT NULL,
            destination VARCHAR(150) NOT NULL,
            stars INT NOT NULL DEFAULT 3,
            description VARCHAR(1000) DEFAULT '',
            status VARCHAR(30) NOT NULL DEFAULT 'Đang hoạt động'
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """,
        """
        CREATE TABLE IF NOT EXISTS hotel_rooms (
            id INT AUTO_INCREMENT PRIMARY KEY,
            hotel_id INT NOT NULL,
            room_type VARCHAR(120) NOT NULL,
            max_guests INT NOT NULL DEFAULT 2,
            normal_price DECIMAL(15,2) NOT NULL DEFAULT 0,
            peak_price DECIMAL(15,2) NOT NULL DEFAULT 0,
            extra_adult DECIMAL(15,2) NOT NULL DEFAULT 0,
            extra_child DECIMAL(15,2) NOT NULL DEFAULT 0,
            inventory INT NOT NULL DEFAULT 10,
            breakfast TINYINT(1) NOT NULL DEFAULT 1,
            status VARCHAR(30) NOT NULL DEFAULT 'Đang bán',
            UNIQUE KEY uq_hotel_room (hotel_id, room_type),
            FOREIGN KEY (hotel_id) REFERENCES hotels(id) ON DELETE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """,
        """
        CREATE TABLE IF NOT EXISTS meals (
            id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(200) NOT NULL,
            destination VARCHAR(150) NOT NULL,
            meal_type VARCHAR(50) NOT NULL,
            adult_price DECIMAL(15,2) NOT NULL DEFAULT 0,
            child_price DECIMAL(15,2) NOT NULL DEFAULT 0,
            infant_price DECIMAL(15,2) NOT NULL DEFAULT 0,
            status VARCHAR(30) NOT NULL DEFAULT 'Đang bán'
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """,
        """
        CREATE TABLE IF NOT EXISTS transports (
            id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(200) NOT NULL,
            vehicle_type VARCHAR(100) NOT NULL,
            capacity INT NOT NULL DEFAULT 16,
            price_per_person DECIMAL(15,2) NOT NULL DEFAULT 0,
            trip_fee DECIMAL(15,2) NOT NULL DEFAULT 0,
            status VARCHAR(30) NOT NULL DEFAULT 'Đang bán'
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """,
        """
        CREATE TABLE IF NOT EXISTS bookings (
            id INT AUTO_INCREMENT PRIMARY KEY,
            booking_code VARCHAR(40) UNIQUE NOT NULL,
            customer_name VARCHAR(150) NOT NULL,
            customer_phone VARCHAR(30) NOT NULL,
            tour_id INT NOT NULL,
            departure_date DATE NOT NULL,
            adults INT NOT NULL DEFAULT 0,
            children INT NOT NULL DEFAULT 0,
            young_children INT NOT NULL DEFAULT 0,
            infants INT NOT NULL DEFAULT 0,
            total_people INT NOT NULL DEFAULT 0,
            hotel_id INT NULL,
            room_id INT NULL,
            rooms INT NOT NULL DEFAULT 0,
            meal_id INT NULL,
            transport_id INT NULL,
            tour_amount DECIMAL(15,2) NOT NULL DEFAULT 0,
            hotel_amount DECIMAL(15,2) NOT NULL DEFAULT 0,
            meal_amount DECIMAL(15,2) NOT NULL DEFAULT 0,
            transport_amount DECIMAL(15,2) NOT NULL DEFAULT 0,
            subtotal DECIMAL(15,2) NOT NULL DEFAULT 0,
            markup_percent DECIMAL(6,2) NOT NULL DEFAULT 0,
            selling_price DECIMAL(15,2) NOT NULL DEFAULT 0,
            status VARCHAR(40) NOT NULL DEFAULT 'Chờ xác nhận',
            note VARCHAR(2000) DEFAULT '',
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (tour_id) REFERENCES tours(id),
            FOREIGN KEY (hotel_id) REFERENCES hotels(id) ON DELETE SET NULL,
            FOREIGN KEY (room_id) REFERENCES hotel_rooms(id) ON DELETE SET NULL,
            FOREIGN KEY (meal_id) REFERENCES meals(id) ON DELETE SET NULL,
            FOREIGN KEY (transport_id) REFERENCES transports(id) ON DELETE SET NULL
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """,
        """
        CREATE TABLE IF NOT EXISTS booking_guests (
            id INT AUTO_INCREMENT PRIMARY KEY,
            booking_id INT NOT NULL,
            guest_no INT NOT NULL,
            age INT NOT NULL,
            category VARCHAR(30) NOT NULL,
            FOREIGN KEY (booking_id) REFERENCES bookings(id) ON DELETE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """,
    ]

    try:
        for sql in tables:
            cur.execute(sql)

        # Dữ liệu mẫu chỉ được thêm khi bảng rỗng.
        cur.execute("SELECT COUNT(*) AS n FROM tours")
        if cur.fetchone()["n"] == 0:
            cur.executemany("""
                INSERT INTO tours
                (name,destination,duration,days,nights,adult_price,child_price,
                 infant_price,max_people,available_seats,description,interests)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """, [
                ("Vũng Tàu 2N1Đ - Biển & Di sản","Vũng Tàu","2 ngày 1 đêm",
                 2,1,1250000,875000,0,30,30,
                 "Bạch Dinh, biển Vũng Tàu và các điểm văn hóa địa phương.",
                 "biển, văn hóa, lịch sử, nghỉ dưỡng"),
                ("Đà Lạt 3N2Đ - Thành phố ngàn hoa","Đà Lạt","3 ngày 2 đêm",
                 3,2,2950000,2065000,0,30,30,
                 "Nghỉ dưỡng, thiên nhiên và trải nghiệm ẩm thực.",
                 "núi, thiên nhiên, nghỉ dưỡng, check-in"),
                ("Nha Trang 3N2Đ - Biển đảo","Nha Trang","3 ngày 2 đêm",
                 3,2,3150000,2205000,0,40,40,
                 "Biển, đảo và thời gian nghỉ ngơi hợp lý.",
                 "biển, đảo, gia đình, nghỉ dưỡng"),
                ("Phú Quốc 4N3Đ - Nghỉ dưỡng","Phú Quốc","4 ngày 3 đêm",
                 4,3,4950000,3465000,0,30,30,
                 "Nghỉ dưỡng biển đảo và trải nghiệm địa phương.",
                 "biển, đảo, nghỉ dưỡng"),
            ])

        cur.execute("SELECT COUNT(*) AS n FROM peak_seasons")
        if cur.fetchone()["n"] == 0:
            y = date.today().year
            cur.executemany("""
                INSERT INTO peak_seasons(name,start_date,end_date,surcharge_percent)
                VALUES (%s,%s,%s,%s)
            """, [
                ("Tết / đầu năm", date(y,1,20), date(y,2,20), 15),
                ("30/4 - 1/5", date(y,4,28), date(y,5,3), 20),
                ("Mùa hè", date(y,6,1), date(y,8,31), 10),
                ("Quốc khánh", date(y,8,30), date(y,9,3), 20),
            ])

        cur.execute("SELECT COUNT(*) AS n FROM hotels")
        if cur.fetchone()["n"] == 0:
            cur.executemany("""
                INSERT INTO hotels(name,destination,stars,description)
                VALUES (%s,%s,%s,%s)
            """, [
                ("Khách sạn Biển Xanh","Vũng Tàu",3,"Gần biển, phù hợp gia đình."),
                ("Khách sạn Bạch Dinh","Vũng Tàu",4,"Khách sạn cao cấp."),
                ("Đà Lạt Garden Hotel","Đà Lạt",3,"Gần trung tâm."),
                ("Nha Trang Xanh Hotel","Nha Trang",4,"Gần biển."),
                ("Phú Quốc Ocean Resort","Phú Quốc",4,"Khu nghỉ dưỡng biển."),
            ])

        cur.execute("SELECT COUNT(*) AS n FROM hotel_rooms")
        if cur.fetchone()["n"] == 0:
            cur.execute("SELECT id,name FROM hotels")
            h = {x["name"]: x["id"] for x in cur.fetchall()}
            cur.executemany("""
                INSERT INTO hotel_rooms
                (hotel_id,room_type,max_guests,normal_price,peak_price,
                 extra_adult,extra_child,inventory,breakfast)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """, [
                (h["Khách sạn Biển Xanh"],"Standard",2,650000,800000,200000,100000,30,1),
                (h["Khách sạn Biển Xanh"],"Deluxe",3,850000,1050000,250000,120000,20,1),
                (h["Khách sạn Bạch Dinh"],"Deluxe",2,1200000,1500000,350000,150000,20,1),
                (h["Khách sạn Bạch Dinh"],"Family",4,1650000,2050000,350000,150000,10,1),
                (h["Đà Lạt Garden Hotel"],"Standard",2,700000,900000,200000,100000,30,1),
                (h["Đà Lạt Garden Hotel"],"Family",4,1350000,1700000,250000,120000,15,1),
                (h["Nha Trang Xanh Hotel"],"Deluxe",2,950000,1200000,250000,120000,20,1),
                (h["Nha Trang Xanh Hotel"],"Family",4,1750000,2200000,300000,150000,10,1),
                (h["Phú Quốc Ocean Resort"],"Deluxe",2,1450000,1900000,400000,180000,20,1),
                (h["Phú Quốc Ocean Resort"],"Family",4,2450000,3100000,450000,200000,10,1),
            ])

        cur.execute("SELECT COUNT(*) AS n FROM meals")
        if cur.fetchone()["n"] == 0:
            cur.executemany("""
                INSERT INTO meals
                (name,destination,meal_type,adult_price,child_price,infant_price)
                VALUES (%s,%s,%s,%s,%s,%s)
            """, [
                ("Set Vũng Tàu","Vũng Tàu","Trưa",140000,98000,0),
                ("Set hải sản Vũng Tàu","Vũng Tàu","Tối",220000,154000,0),
                ("Set Đà Lạt","Đà Lạt","Trưa",150000,105000,0),
                ("Set tối Đà Lạt","Đà Lạt","Tối",180000,126000,0),
                ("Set Nha Trang","Nha Trang","Trưa",160000,112000,0),
                ("Set tối Nha Trang","Nha Trang","Tối",200000,140000,0),
                ("Set Phú Quốc","Phú Quốc","Trưa",200000,140000,0),
                ("Set tối Phú Quốc","Phú Quốc","Tối",250000,175000,0),
            ])

        cur.execute("SELECT COUNT(*) AS n FROM transports")
        if cur.fetchone()["n"] == 0:
            cur.executemany("""
                INSERT INTO transports
                (name,vehicle_type,capacity,price_per_person,trip_fee)
                VALUES (%s,%s,%s,%s,%s)
            """, [
                ("Xe 7 chỗ","7 chỗ",7,350000,0),
                ("Xe 16 chỗ","16 chỗ",16,180000,0),
                ("Xe 29 chỗ","29 chỗ",29,220000,0),
                ("Xe 45 chỗ","45 chỗ",45,260000,0),
            ])

        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()

# ============================================================
# DATA FUNCTIONS
# ============================================================
def get_tours():
    return execute("SELECT * FROM tours WHERE status='Đang mở' ORDER BY id", fetch="all")

def get_tour(tour_id):
    return execute("SELECT * FROM tours WHERE id=%s", (tour_id,), fetch="one")

def get_peak(d):
    return execute("""
        SELECT * FROM peak_seasons
        WHERE status='Đang áp dụng'
        AND %s BETWEEN start_date AND end_date
        LIMIT 1
    """, (d,), fetch="one")

def get_hotels(destination):
    return execute("""
        SELECT * FROM hotels
        WHERE destination=%s AND status='Đang hoạt động'
        ORDER BY stars DESC,name
    """, (destination,), fetch="all")

def get_rooms(hotel_id):
    return execute("""
        SELECT * FROM hotel_rooms
        WHERE hotel_id=%s AND status='Đang bán'
        ORDER BY normal_price
    """, (hotel_id,), fetch="all")

def get_meals(destination):
    return execute("""
        SELECT * FROM meals
        WHERE destination=%s AND status='Đang bán'
        ORDER BY meal_type,name
    """, (destination,), fetch="all")

def get_transports():
    return execute("SELECT * FROM transports WHERE status='Đang bán' ORDER BY capacity", fetch="all")

def booked_people(tour_id, departure_date):
    r = execute("""
        SELECT COALESCE(SUM(total_people),0) AS n
        FROM bookings
        WHERE tour_id=%s AND departure_date=%s
        AND status<>'Đã hủy'
    """, (tour_id,departure_date), fetch="one")
    return int(r["n"] or 0)

def room_count(guest_ages, capacity):
    sleeping = sum(age_group(a) != "infant" for a in guest_ages)
    return max(1, (sleeping + capacity - 1)//capacity)

# ============================================================
# TÍNH GIÁ
# ============================================================
def calculate_price(tour, departure, ages, room, rooms, meal, transport, markup_percent):
    counts = {k:0 for k in ["adult","child","young_child","infant"]}
    for age in ages:
        counts[age_group(age)] += 1

    # Giá tour:
    # 11+ = adult_price
    # 6-10 = child_price (mẫu 70%)
    # 2-5 = 50% adult
    # 0-1 = infant_price
    tour_amount = (
        D(counts["adult"]) * D(tour["adult_price"])
        + D(counts["child"]) * D(tour["child_price"])
        + D(counts["young_child"]) * D(tour["adult_price"]) * D("0.50")
        + D(counts["infant"]) * D(tour["infant_price"])
    )

    peak = get_peak(departure)
    hotel_amount = D(0)
    room_unit = D(0)
    extra_amount = D(0)

    if room and rooms:
        room_unit = D(room["peak_price"] if peak else room["normal_price"])
        hotel_amount = room_unit * D(rooms) * D(tour["nights"])

        capacity = int(room["max_guests"])
        sleeping = counts["adult"] + counts["child"] + counts["young_child"]
        included = capacity * int(rooms)
        extra = max(0, sleeping-included)

        extra_adults = min(extra, counts["adult"])
        extra_children = max(0, extra-extra_adults)
        extra_amount = (
            D(extra_adults) * D(room["extra_adult"])
            + D(extra_children) * D(room["extra_child"])
        )
        hotel_amount += extra_amount

    meal_amount = D(0)
    if meal:
        meal_amount = (
            D(counts["adult"])*D(meal["adult_price"])
            + D(counts["child"])*D(meal["child_price"])
            + D(counts["young_child"])*D(meal["child_price"])
            + D(counts["infant"])*D(meal["infant_price"])
        )

    transport_amount = D(0)
    if transport:
        transport_amount = D(len(ages))*D(transport["price_per_person"]) + D(transport["trip_fee"])

    subtotal = tour_amount + hotel_amount + meal_amount + transport_amount
    markup = subtotal * D(markup_percent) / D(100)
    selling = subtotal + markup

    return {
        "counts":counts,
        "tour":tour_amount,
        "hotel":hotel_amount,
        "meal":meal_amount,
        "transport":transport_amount,
        "extra_room":extra_amount,
        "subtotal":subtotal,
        "markup":markup,
        "selling":selling,
        "room_unit":room_unit,
        "peak":peak,
    }

def save_booking(customer_name, phone, tour, departure, ages, hotel, room,
                 rooms, meal, transport, amounts, note, markup_percent):
    code = "ST-" + datetime.now().strftime("%Y%m%d-%H%M%S")
    conn = db_connect()
    cur = conn.cursor()
    try:
        cur.execute("""
            INSERT INTO bookings
            (booking_code,customer_name,customer_phone,tour_id,departure_date,
             adults,children,young_children,infants,total_people,
             hotel_id,room_id,rooms,meal_id,transport_id,
             tour_amount,hotel_amount,meal_amount,transport_amount,
             subtotal,markup_percent,selling_price,status,note)
            VALUES
            (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,
             %s,%s,%s,%s,%s,%s,%s,'Chờ xác nhận',%s)
        """, (
            code,customer_name,phone,tour["id"],departure,
            amounts["counts"]["adult"],amounts["counts"]["child"],
            amounts["counts"]["young_child"],amounts["counts"]["infant"],
            len(ages),
            hotel["id"] if hotel else None,
            room["id"] if room else None,
            rooms,
            meal["id"] if meal else None,
            transport["id"] if transport else None,
            amounts["tour"],amounts["hotel"],amounts["meal"],
            amounts["transport"],amounts["subtotal"],
            markup_percent,amounts["selling"],note
        ))
        booking_id = cur.lastrowid

        for i, age in enumerate(ages, 1):
            cur.execute("""
                INSERT INTO booking_guests(booking_id,guest_no,age,category)
                VALUES (%s,%s,%s,%s)
            """, (booking_id,i,age,age_group(age)))

        conn.commit()
        return code
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()

# ============================================================
# KIỂM TRA KẾT NỐI
# ============================================================
try:
    init_database()
except Exception as e:
    st.error("❌ Không kết nối/khởi tạo được MySQL Aiven.")
    st.code(f"{type(e).__name__}: {e}")
    st.info("Kiểm tra Aiven đang RUNNING, Host/Port/User/Password đúng và SSL đang REQUIRED.")
    st.stop()

# ============================================================
# SIDEBAR
# ============================================================
st.sidebar.title("✈️ SMART TOUR")
page = st.sidebar.radio("Chức năng", [
    "🏠 Đặt tour",
    "🔎 Tra cứu booking",
    "⚙️ Điều hành & quản lý",
])

# ============================================================
# TRANG ĐẶT TOUR
# ============================================================
if page == "🏠 Đặt tour":
    st.markdown("""
    <div class="hero">
        <h1>✈️ SMART TOUR</h1>
        <p>Đặt tour - tính giá - phòng khách sạn - độ tuổi - dịch vụ</p>
    </div>
    """, unsafe_allow_html=True)

    tours = get_tours()
    if not tours:
        st.warning("Chưa có tour.")
        st.stop()

    st.subheader("1. Chọn tour")
    destination_list = ["Tất cả"] + sorted({t["destination"] for t in tours})
    destination = st.selectbox("Điểm đến", destination_list)

    available_tours = [t for t in tours if destination=="Tất cả" or t["destination"]==destination]
    tour_id = st.selectbox(
        "Tour",
        [t["id"] for t in available_tours],
        format_func=lambda x: next(t["name"] for t in available_tours if t["id"]==x)
    )
    tour = get_tour(tour_id)

    st.markdown(f"""
    <div class="card">
        <h3>{tour["name"]}</h3>
        <p><b>Điểm đến:</b> {tour["destination"]}</p>
        <p><b>Thời lượng:</b> {tour["duration"]}</p>
        <p><b>Mô tả:</b> {tour["description"]}</p>
        <div class="price">{money(tour["adult_price"])} / người lớn</div>
    </div>
    """, unsafe_allow_html=True)

    st.subheader("2. Ngày khởi hành")
    departure = st.date_input(
        "Ngày đi",
        value=date.today()+timedelta(days=1),
        min_value=date.today()+timedelta(days=1)
    )

    peak = get_peak(departure)
    if peak:
        st.markdown(
            f'<div class="warning">🔥 {peak["name"]}: giá phòng cao điểm được áp dụng. '
            f'Phụ thu mùa cao điểm: {peak["surcharge_percent"]}%.</div>',
            unsafe_allow_html=True
        )
    else:
        st.markdown('<div class="note">Ngày thường - áp dụng giá phòng thường.</div>',
                    unsafe_allow_html=True)

    left = int(tour["available_seats"]) - booked_people(tour["id"], departure)
    st.metric("Số chỗ còn lại", max(0,left))

    st.subheader("3. Thông tin người đặt")
    c1,c2 = st.columns(2)
    with c1:
        customer_name = st.text_input("Họ tên *")
    with c2:
        phone = st.text_input("Số điện thoại *")

    st.subheader("4. Độ tuổi từng khách")
    guest_count = st.number_input(
        "Tổng số khách", min_value=1, max_value=int(tour["max_people"]), value=2
    )

    ages = []
    for start in range(0,int(guest_count),4):
        cols = st.columns(4)
        for j,col in enumerate(cols):
            i = start+j
            if i >= int(guest_count):
                break
            with col:
                default_age = 25 if i < 2 else 10
                ages.append(int(st.number_input(
                    f"Khách {i+1}", min_value=0, max_value=120,
                    value=default_age, key=f"age_{i}"
                )))

    counts = {k:sum(age_group(a)==k for a in ages)
              for k in ["adult","child","young_child","infant"]}

    a,b,c,d = st.columns(4)
    a.metric("Người lớn",counts["adult"])
    b.metric("Trẻ 6–10",counts["child"])
    c.metric("Trẻ 2–5",counts["young_child"])
    d.metric("Em bé 0–1",counts["infant"])

    st.caption("Quy tắc mẫu: 11+ = người lớn; 6–10 = child_price; 2–5 = 50% giá người lớn; 0–1 = infant_price.")

    st.subheader("5. Khách sạn & phòng")
    hotels = get_hotels(tour["destination"])
    hotel = None
    room = None
    rooms = 0

    if hotels:
        hotel_id = st.selectbox(
            "Khách sạn",
            [h["id"] for h in hotels],
            format_func=lambda x: next(
                f'{h["name"]} - {h["stars"]}⭐' for h in hotels if h["id"]==x
            )
        )
        hotel = next(h for h in hotels if h["id"]==hotel_id)
        room_list = get_rooms(hotel_id)

        if room_list:
            room_id = st.selectbox(
                "Loại phòng",
                [r["id"] for r in room_list],
                format_func=lambda x: next(
                    f'{r["room_type"]} - {r["max_guests"]} khách - thường {money(r["normal_price"])} - cao điểm {money(r["peak_price"])}'
                    for r in room_list if r["id"]==x
                )
            )
            room = next(r for r in room_list if r["id"]==room_id)
            auto_rooms = room_count(ages,int(room["max_guests"]))
            rooms = int(st.number_input(
                "Số phòng",
                min_value=1,
                max_value=int(room["inventory"]),
                value=min(auto_rooms,int(room["inventory"])),
            ))
            current_room_price = room["peak_price"] if peak else room["normal_price"]
            st.info(
                f"Giá phòng hiện tại: {money(current_room_price)}/phòng/đêm × "
                f"{rooms} phòng × {tour['nights']} đêm."
            )

    st.subheader("6. Ăn uống")
    meals = get_meals(tour["destination"])
    meal = None
    if meals:
        meal_id = st.selectbox(
            "Suất ăn",
            [0]+[m["id"] for m in meals],
            format_func=lambda x: "Không chọn" if x==0 else next(
                f'{m["meal_type"]} - {m["name"]} - {money(m["adult_price"])} người lớn'
                for m in meals if m["id"]==x
            )
        )
        if meal_id:
            meal = next(m for m in meals if m["id"]==meal_id)

    st.subheader("7. Phương tiện")
    transports = get_transports()
    transport = None
    if transports:
        transport_id = st.selectbox(
            "Xe",
            [0]+[t["id"] for t in transports],
            format_func=lambda x: "Không chọn" if x==0 else next(
                f'{t["name"]} - {t["capacity"]} chỗ - {money(t["price_per_person"])}/khách'
                for t in transports if t["id"]==x
            )
        )
        if transport_id:
            transport = next(t for t in transports if t["id"]==transport_id)
            if int(transport["capacity"]) < len(ages):
                st.warning(f"Xe {transport['capacity']} chỗ không đủ {len(ages)} khách.")

    st.subheader("8. Tính giá")
    markup = st.number_input("Markup/lợi nhuận điều hành (%)", min_value=0.0, max_value=100.0, value=10.0, step=1.0)

    amounts = calculate_price(
        tour,departure,ages,room,rooms,meal,transport,markup
    )

    p1,p2,p3,p4 = st.columns(4)
    p1.metric("Tour",money(amounts["tour"]))
    p2.metric("Khách sạn",money(amounts["hotel"]))
    p3.metric("Ăn uống",money(amounts["meal"]))
    p4.metric("Phương tiện",money(amounts["transport"]))

    st.markdown(f"""
    <div class="card">
        <p><b>Giá vốn / subtotal:</b> {money(amounts["subtotal"])}</p>
        <p><b>Markup {markup:.1f}%:</b> {money(amounts["markup"])}</p>
        <div class="total">GIÁ BÁN: {money(amounts["selling"])}</div>
    </div>
    """, unsafe_allow_html=True)

    note = st.text_area("Ghi chú / yêu cầu đặc biệt")

    if st.button("✅ XÁC NHẬN ĐẶT TOUR", type="primary", use_container_width=True):
        errors = []
        if not customer_name.strip():
            errors.append("Chưa nhập họ tên.")
        if len(normalize_phone(phone)) < 9:
            errors.append("Số điện thoại không hợp lệ.")
        if len(ages) > left:
            errors.append(f"Ngày này chỉ còn {left} chỗ.")
        if transport and int(transport["capacity"]) < len(ages):
            errors.append("Phương tiện không đủ chỗ.")
        if rooms > int(room["inventory"]) if room else False:
            errors.append("Số phòng vượt tồn kho.")

        if errors:
            for e in errors:
                st.error(e)
        else:
            try:
                code = save_booking(
                    customer_name.strip(),phone.strip(),tour,departure,ages,
                    hotel,room,rooms,meal,transport,amounts,note,markup
                )
                st.success(f"🎉 Đặt tour thành công. Mã booking: {code}")
                st.info("Booking đã lưu trực tiếp vào MySQL Aiven với trạng thái 'Chờ xác nhận'.")
            except Error as e:
                st.error("Không thể lưu booking.")
                st.code(str(e))

# ============================================================
# TRA CỨU
# ============================================================
elif page == "🔎 Tra cứu booking":
    st.title("🔎 Tra cứu booking")
    code = st.text_input("Mã booking").strip()

    if st.button("Tra cứu", type="primary"):
        if not code:
            st.warning("Nhập mã booking.")
        else:
            b = execute("""
                SELECT b.*, t.name AS tour_name, t.destination,
                       h.name AS hotel_name, r.room_type
                FROM bookings b
                JOIN tours t ON t.id=b.tour_id
                LEFT JOIN hotels h ON h.id=b.hotel_id
                LEFT JOIN hotel_rooms r ON r.id=b.room_id
                WHERE b.booking_code=%s
            """,(code,),fetch="one")

            if not b:
                st.error("Không tìm thấy booking.")
            else:
                st.success("Đã tìm thấy booking.")
                c1,c2,c3 = st.columns(3)
                c1.metric("Mã",b["booking_code"])
                c2.metric("Trạng thái",b["status"])
                c3.metric("Giá bán",money(b["selling_price"]))

                st.markdown(f"""
                <div class="card">
                    <h3>{b["tour_name"]}</h3>
                    <p><b>Khách:</b> {b["customer_name"]} - {b["customer_phone"]}</p>
                    <p><b>Ngày đi:</b> {b["departure_date"]}</p>
                    <p><b>Người:</b> {b["total_people"]} 
                    (NL {b["adults"]}, TE {b["children"]}, trẻ nhỏ {b["young_children"]}, em bé {b["infants"]})</p>
                    <p><b>Khách sạn:</b> {b["hotel_name"] or "Không chọn"} - {b["room_type"] or ""}</p>
                    <p><b>Tour:</b> {money(b["tour_amount"])}</p>
                    <p><b>Phòng:</b> {money(b["hotel_amount"])}</p>
                    <p><b>Ăn:</b> {money(b["meal_amount"])}</p>
                    <p><b>Xe:</b> {money(b["transport_amount"])}</p>
                    <p><b>Giá vốn:</b> {money(b["subtotal"])}</p>
                    <p><b>Markup:</b> {b["markup_percent"]}%</p>
                    <div class="total">GIÁ BÁN: {money(b["selling_price"])}</div>
                    <p><b>Ghi chú:</b> {b["note"] or "Không có"}</p>
                </div>
                """,unsafe_allow_html=True)

# ============================================================
# ĐIỀU HÀNH / QUẢN LÝ
# ============================================================
else:
    st.title("⚙️ Điều hành & quản lý SMART TOUR")

    tab1,tab2,tab3,tab4 = st.tabs([
        "📋 Booking","🏨 Giá phòng","🚌 Dịch vụ","📈 Doanh thu"
    ])

    with tab1:
        st.subheader("Danh sách booking")
        data = df_query("""
            SELECT b.booking_code,b.customer_name,b.customer_phone,
                   t.name AS tour,b.departure_date,b.total_people,
                   b.adults,b.children,b.young_children,b.infants,
                   b.subtotal,b.markup_percent,b.selling_price,b.status,b.created_at
            FROM bookings b JOIN tours t ON t.id=b.tour_id
            ORDER BY b.created_at DESC
        """)
        st.dataframe(data,use_container_width=True,hide_index=True)

        if not data.empty:
            st.download_button(
                "⬇️ Xuất CSV",
                data=data.to_csv(index=False).encode("utf-8-sig"),
                file_name="smart_tour_bookings.csv",
                mime="text/csv"
            )

        st.subheader("Cập nhật trạng thái booking")
        booking_code = st.text_input("Mã booking cần cập nhật")
        new_status = st.selectbox(
            "Trạng thái",
            ["Chờ xác nhận","Đã xác nhận","Đã thanh toán","Đang đi tour","Hoàn thành","Đã hủy"]
        )
        if st.button("Cập nhật trạng thái"):
            if booking_code.strip():
                execute(
                    "UPDATE bookings SET status=%s WHERE booking_code=%s",
                    (new_status,booking_code.strip())
                )
                st.success("Đã cập nhật.")
                st.rerun()

    with tab2:
        st.subheader("Bảng giá phòng hiện tại")
        rooms_df = df_query("""
            SELECT h.name AS hotel,h.destination,h.stars,
                   r.room_type,r.max_guests,r.normal_price,
                   r.peak_price,r.extra_adult,r.extra_child,
                   r.inventory,r.breakfast
            FROM hotel_rooms r JOIN hotels h ON h.id=r.hotel_id
            ORDER BY h.destination,h.name,r.normal_price
        """)
        st.dataframe(rooms_df,use_container_width=True,hide_index=True)
        st.info("Muốn thay đổi giá phòng, có thể cập nhật trực tiếp dữ liệu MySQL; app sẽ dùng normal_price/peak_price theo ngày khởi hành.")

    with tab3:
        st.subheader("Dịch vụ vận chuyển")
        st.dataframe(
            df_query("SELECT * FROM transports ORDER BY capacity"),
            use_container_width=True,hide_index=True
        )
        st.subheader("Suất ăn")
        st.dataframe(
            df_query("SELECT * FROM meals ORDER BY destination,meal_type"),
            use_container_width=True,hide_index=True
        )

    with tab4:
        st.subheader("Tổng quan kinh doanh")
        summary = execute("""
            SELECT
                COUNT(*) AS bookings,
                COALESCE(SUM(subtotal),0) AS cost_total,
                COALESCE(SUM(selling_price),0) AS sales_total,
                COALESCE(SUM(selling_price-subtotal),0) AS profit_total
            FROM bookings
            WHERE status<>'Đã hủy'
        """,fetch="one")

        c1,c2,c3,c4 = st.columns(4)
        c1.metric("Số booking",summary["bookings"])
        c2.metric("Giá vốn",money(summary["cost_total"]))
        c3.metric("Doanh thu",money(summary["sales_total"]))
        c4.metric("Markup/lợi nhuận",money(summary["profit_total"]))

        by_tour = df_query("""
            SELECT t.destination,
                   COUNT(*) AS bookings,
                   SUM(b.selling_price) AS revenue,
                   SUM(b.selling_price-b.subtotal) AS profit
            FROM bookings b JOIN tours t ON t.id=b.tour_id
            WHERE b.status<>'Đã hủy'
            GROUP BY t.destination
            ORDER BY revenue DESC
        """)
        st.dataframe(by_tour,use_container_width=True,hide_index=True)
