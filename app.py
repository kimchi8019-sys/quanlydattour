
import streamlit as st
import sqlite3
import hashlib
from datetime import date, datetime
import pandas as pd

# ============================================================
# SMART TOUR - APP ĐẶT TOUR DU LỊCH THÔNG MINH
# Streamlit + SQLite
# ============================================================

st.set_page_config(
    page_title="SMART TOUR",
    page_icon="✈️",
    layout="wide",
    initial_sidebar_state="expanded",
)

DB_NAME = "smart_tour.db"


# -------------------- DATABASE --------------------

@st.cache_resource
def get_connection():
    conn = sqlite3.connect(DB_NAME, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


conn = get_connection()


def hash_password(password):
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def init_db():
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name TEXT NOT NULL,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'customer',
            phone TEXT DEFAULT '',
            email TEXT DEFAULT '',
            created_at TEXT NOT NULL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS tours (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            destination TEXT NOT NULL,
            duration TEXT NOT NULL,
            days INTEGER NOT NULL,
            nights INTEGER NOT NULL,
            price_per_person REAL NOT NULL,
            max_people INTEGER NOT NULL DEFAULT 30,
            available_seats INTEGER NOT NULL DEFAULT 30,
            interests TEXT DEFAULT '',
            description TEXT DEFAULT '',
            transport TEXT DEFAULT 'Xe du lịch',
            status TEXT NOT NULL DEFAULT 'Đang mở'
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS hotels (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            destination TEXT NOT NULL,
            stars INTEGER NOT NULL DEFAULT 3,
            room_type TEXT NOT NULL,
            price_per_room REAL NOT NULL,
            total_rooms INTEGER NOT NULL DEFAULT 10,
            available_rooms INTEGER NOT NULL DEFAULT 10,
            description TEXT DEFAULT '',
            status TEXT NOT NULL DEFAULT 'Đang hoạt động'
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS bookings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            tour_id INTEGER NOT NULL,
            hotel_id INTEGER,
            booking_date TEXT NOT NULL,
            start_date TEXT NOT NULL,
            people INTEGER NOT NULL,
            rooms INTEGER NOT NULL DEFAULT 1,
            total_amount REAL NOT NULL,
            payment_method TEXT NOT NULL,
            payment_status TEXT NOT NULL DEFAULT 'Chưa thanh toán',
            booking_status TEXT NOT NULL DEFAULT 'Chờ xác nhận',
            note TEXT DEFAULT '',
            FOREIGN KEY(user_id) REFERENCES users(id),
            FOREIGN KEY(tour_id) REFERENCES tours(id),
            FOREIGN KEY(hotel_id) REFERENCES hotels(id)
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            booking_id INTEGER NOT NULL,
            amount REAL NOT NULL,
            method TEXT NOT NULL,
            paid_at TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'Thành công',
            FOREIGN KEY(booking_id) REFERENCES bookings(id)
        )
    """)

    # Tài khoản admin mặc định
    cur.execute("SELECT COUNT(*) FROM users WHERE username = ?", ("admin",))
    if cur.fetchone()[0] == 0:
        cur.execute("""
            INSERT INTO users
            (full_name, username, password, role, phone, email, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            "Quản trị viên",
            "admin",
            hash_password("admin123"),
            "admin",
            "",
            "admin@smarttour.local",
            datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ))

    # Tour mẫu
    cur.execute("SELECT COUNT(*) FROM tours")
    if cur.fetchone()[0] == 0:
        tours = [
            (
                "Vũng Tàu 3N2Đ - Biển & Ẩm thực",
                "Vũng Tàu",
                "3 ngày 2 đêm",
                3, 2, 1890000, 30, 30,
                "biển,ăn uống,nghỉ dưỡng,check-in",
                "Khám phá Bãi Sau, Bạch Dinh, Núi Nhỏ, ngọn Hải Đăng và thưởng thức hải sản.",
                "Xe du lịch",
                "Đang mở"
            ),
            (
                "Đà Lạt 3N2Đ - Hoa & Sống ảo",
                "Đà Lạt",
                "3 ngày 2 đêm",
                3, 2, 2590000, 30, 30,
                "thiên nhiên,chụp ảnh,ăn uống,cafe",
                "Hành trình khám phá Đà Lạt với các điểm check-in, cà phê và cảnh quan thiên nhiên.",
                "Xe du lịch",
                "Đang mở"
            ),
            (
                "Phú Quốc 4N3Đ - Biển đảo",
                "Phú Quốc",
                "4 ngày 3 đêm",
                4, 3, 4490000, 25, 25,
                "biển,nghỉ dưỡng,hải sản,gia đình",
                "Nghỉ dưỡng biển, khám phá đảo và thưởng thức đặc sản Phú Quốc.",
                "Máy bay",
                "Đang mở"
            ),
            (
                "Nha Trang 3N2Đ - Biển & Giải trí",
                "Nha Trang",
                "3 ngày 2 đêm",
                3, 2, 3290000, 30, 30,
                "biển,gia đình,giải trí,ăn uống",
                "Tham quan biển Nha Trang, vui chơi và trải nghiệm ẩm thực địa phương.",
                "Máy bay",
                "Đang mở"
            ),
            (
                "Đà Nẵng - Hội An 4N3Đ",
                "Đà Nẵng - Hội An",
                "4 ngày 3 đêm",
                4, 3, 3990000, 30, 30,
                "biển,văn hóa,chụp ảnh,ăn uống",
                "Kết hợp biển Đà Nẵng và phố cổ Hội An, phù hợp gia đình và nhóm bạn.",
                "Máy bay",
                "Đang mở"
            ),
            (
                "Tây Nguyên 3N2Đ - Thiên nhiên & Văn hóa",
                "Buôn Ma Thuột",
                "3 ngày 2 đêm",
                3, 2, 2790000, 25, 25,
                "thiên nhiên,văn hóa,khám phá,ẩm thực",
                "Trải nghiệm văn hóa Tây Nguyên, thác nước và cà phê địa phương.",
                "Xe du lịch",
                "Đang mở"
            ),
        ]
        cur.executemany("""
            INSERT INTO tours
            (name, destination, duration, days, nights, price_per_person,
             max_people, available_seats, interests, description, transport, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, tours)

    # Khách sạn mẫu
    cur.execute("SELECT COUNT(*) FROM hotels")
    if cur.fetchone()[0] == 0:
        hotels = [
            ("Ocean Vũng Tàu Hotel", "Vũng Tàu", 3, "Phòng đôi", 750000, 20, 20,
             "Khách sạn gần biển, phù hợp nghỉ dưỡng.", "Đang hoạt động"),
            ("Sea Star Vũng Tàu", "Vũng Tàu", 4, "Phòng đôi", 1150000, 15, 15,
             "Khách sạn 4 sao, tiện nghi đầy đủ.", "Đang hoạt động"),
            ("Dalat Garden Hotel", "Đà Lạt", 3, "Phòng đôi", 850000, 20, 20,
             "Không gian yên tĩnh, gần trung tâm.", "Đang hoạt động"),
            ("Pine Hill Đà Lạt", "Đà Lạt", 4, "Phòng đôi", 1350000, 15, 15,
             "Khách sạn cao cấp, view đẹp.", "Đang hoạt động"),
            ("Island Pearl Phú Quốc", "Phú Quốc", 4, "Phòng đôi", 1650000, 20, 20,
             "Gần biển, thích hợp nghỉ dưỡng.", "Đang hoạt động"),
            ("Sun Bay Nha Trang", "Nha Trang", 3, "Phòng đôi", 950000, 20, 20,
             "Vị trí thuận tiện, gần biển.", "Đang hoạt động"),
            ("Hoi An Riverside", "Đà Nẵng - Hội An", 4, "Phòng đôi", 1450000, 15, 15,
             "Không gian đẹp, phù hợp trải nghiệm văn hóa.", "Đang hoạt động"),
            ("Highland Coffee Resort", "Buôn Ma Thuột", 3, "Phòng đôi", 800000, 15, 15,
             "Gần các điểm tham quan thiên nhiên.", "Đang hoạt động"),
        ]
        cur.executemany("""
            INSERT INTO hotels
            (name, destination, stars, room_type, price_per_room,
             total_rooms, available_rooms, description, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, hotels)

    conn.commit()


init_db()


# -------------------- HELPERS --------------------

def money(value):
    return f"{float(value):,.0f} VNĐ"


def query_df(sql, params=()):
    return pd.read_sql_query(sql, conn, params=params)


def execute(sql, params=()):
    cur = conn.cursor()
    cur.execute(sql, params)
    conn.commit()
    return cur.lastrowid


def get_user(username, password):
    row = conn.execute("""
        SELECT * FROM users
        WHERE username = ? AND password = ?
    """, (username, hash_password(password))).fetchone()
    return row


def get_user_by_id(user_id):
    return conn.execute(
        "SELECT * FROM users WHERE id = ?", (user_id,)
    ).fetchone()


def tour_score(tour, destination, budget, people, interests):
    score = 0
    interests_text = str(tour["interests"]).lower()
    destination_text = str(tour["destination"]).lower()
    name_text = str(tour["name"]).lower()

    if destination == "Tất cả" or destination.lower() in destination_text:
        score += 30

    for interest in interests:
        if interest.lower() in interests_text:
            score += 15

    total_base = float(tour["price_per_person"]) * people
    if total_base <= budget:
        score += 30
    elif total_base <= budget * 1.15:
        score += 10

    if int(tour["available_seats"]) >= people:
        score += 10

    if "biển" in interests and ("biển" in interests_text or "nghỉ dưỡng" in interests_text):
        score += 5

    return score


def recommend_tours(destination, budget, people, interests):
    tours = query_df("""
        SELECT * FROM tours
        WHERE status = 'Đang mở' AND available_seats >= ?
        ORDER BY id
    """, (people,))

    if tours.empty:
        return tours

    tours["score"] = tours.apply(
        lambda row: tour_score(row, destination, budget, people, interests),
        axis=1
    )
    tours["estimated_total"] = tours["price_per_person"] * people
    return tours.sort_values(
        ["score", "estimated_total"],
        ascending=[False, True]
    )


def recommend_hotels(destination, budget, nights, rooms):
    hotels = query_df("""
        SELECT * FROM hotels
        WHERE destination = ?
        AND status = 'Đang hoạt động'
        AND available_rooms >= ?
    """, (destination, rooms))

    if hotels.empty:
        return hotels

    hotels["estimated_total"] = hotels["price_per_room"] * nights * rooms
    hotels["budget_gap"] = (hotels["estimated_total"] - budget).clip(lower=0)
    return hotels.sort_values(["budget_gap", "stars"], ascending=[True, False])


def login_required():
    if "user" not in st.session_state:
        st.warning("Vui lòng đăng nhập để sử dụng chức năng này.")
        st.stop()


def admin_required():
    login_required()
    if st.session_state.user["role"] != "admin":
        st.error("Bạn không có quyền truy cập khu vực Admin.")
        st.stop()


def logout():
    for key in ["user", "page"]:
        st.session_state.pop(key, None)


# -------------------- CSS --------------------

st.markdown("""
<style>
    .stApp {
        background: #f6f8fb;
    }

    .hero {
        padding: 30px;
        border-radius: 18px;
        background: linear-gradient(135deg, #0b5ed7, #2b8cff);
        color: white;
        margin-bottom: 20px;
    }

    .hero h1 {
        color: white;
        margin-bottom: 5px;
    }

    .card {
        background: white;
        padding: 20px;
        border-radius: 15px;
        box-shadow: 0 2px 12px rgba(0,0,0,.07);
        margin-bottom: 15px;
    }

    .recommend {
        border-left: 5px solid #0b5ed7;
        background: white;
        padding: 18px;
        border-radius: 12px;
        margin-bottom: 12px;
        box-shadow: 0 2px 10px rgba(0,0,0,.06);
    }

    .price {
        color: #0b5ed7;
        font-size: 20px;
        font-weight: 700;
    }

    .small {
        color: #667085;
        font-size: 14px;
    }

    [data-testid="stMetric"] {
        background: white;
        padding: 15px;
        border-radius: 12px;
        box-shadow: 0 2px 8px rgba(0,0,0,.05);
    }
</style>
""", unsafe_allow_html=True)


# -------------------- SESSION --------------------

if "user" not in st.session_state:
    st.session_state.user = None


# -------------------- LOGIN / REGISTER --------------------

if st.session_state.user is None:

    st.markdown("""
    <div class="hero">
        <h1>✈️ SMART TOUR</h1>
        <p>Ứng dụng đặt tour du lịch thông minh</p>
        <p>Chọn tour • Khách sạn • Ngân sách • Sở thích • Đặt tour • Thanh toán</p>
    </div>
    """, unsafe_allow_html=True)

    tab_login, tab_register = st.tabs(["🔐 Đăng nhập", "📝 Đăng ký"])

    with tab_login:
        st.subheader("Đăng nhập")

        with st.form("login_form"):
            username = st.text_input("Tên đăng nhập")
            password = st.text_input("Mật khẩu", type="password")
            submit = st.form_submit_button("🔐 Đăng nhập", use_container_width=True)

            if submit:
                user = get_user(username.strip(), password)
                if user:
                    st.session_state.user = dict(user)
                    st.success("Đăng nhập thành công!")
                    st.rerun()
                else:
                    st.error("Tên đăng nhập hoặc mật khẩu không đúng.")

        st.info("Tài khoản Admin mặc định: admin / admin123")

    with tab_register:
        st.subheader("Tạo tài khoản khách hàng")

        with st.form("register_form"):
            full_name = st.text_input("Họ và tên *")
            username = st.text_input("Tên đăng nhập *")
            password = st.text_input("Mật khẩu *", type="password")
            password2 = st.text_input("Nhập lại mật khẩu *", type="password")
            phone = st.text_input("Số điện thoại")
            email = st.text_input("Email")

            submit = st.form_submit_button("📝 Đăng ký", use_container_width=True)

            if submit:
                if not full_name.strip() or not username.strip() or not password:
                    st.error("Vui lòng nhập đầy đủ thông tin bắt buộc.")
                elif password != password2:
                    st.error("Mật khẩu nhập lại không khớp.")
                elif len(password) < 6:
                    st.error("Mật khẩu phải có ít nhất 6 ký tự.")
                else:
                    try:
                        execute("""
                            INSERT INTO users
                            (full_name, username, password, role, phone, email, created_at)
                            VALUES (?, ?, ?, 'customer', ?, ?, ?)
                        """, (
                            full_name.strip(),
                            username.strip(),
                            hash_password(password),
                            phone.strip(),
                            email.strip(),
                            datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        ))
                        st.success("Đăng ký thành công. Bạn có thể đăng nhập.")
                    except sqlite3.IntegrityError:
                        st.error("Tên đăng nhập đã tồn tại.")

    st.stop()


# -------------------- SIDEBAR --------------------

user = st.session_state.user

st.sidebar.markdown("# ✈️ SMART TOUR")
st.sidebar.caption("Đặt tour du lịch thông minh")
st.sidebar.markdown("---")

if user["role"] == "admin":
    menu_items = [
        "🏠 Trang chủ",
        "🔎 Tìm & đề xuất tour",
        "📋 Tour của tôi",
        "💳 Thanh toán",
        "🔧 Quản lý tour",
        "🏨 Quản lý khách sạn",
        "👥 Quản lý khách hàng",
        "🧾 Quản lý đơn đặt",
        "📊 Dashboard Admin",
    ]
else:
    menu_items = [
        "🏠 Trang chủ",
        "🔎 Tìm & đề xuất tour",
        "📋 Tour của tôi",
        "💳 Thanh toán",
    ]

page = st.sidebar.radio("MENU", menu_items)

st.sidebar.markdown("---")
st.sidebar.write(f"👤 **{user['full_name']}**")
st.sidebar.caption(f"Vai trò: {user['role']}")

if st.sidebar.button("🚪 Đăng xuất", use_container_width=True):
    logout()
    st.rerun()


# ============================================================
# TRANG CHỦ
# ============================================================

if page == "🏠 Trang chủ":

    st.markdown(f"""
    <div class="hero">
        <h1>Xin chào, {user['full_name']} 👋</h1>
        <p>Chào mừng bạn đến với SMART TOUR.</p>
        <p>Hãy nhập điểm đến, ngân sách và sở thích để hệ thống đề xuất phương án phù hợp.</p>
    </div>
    """, unsafe_allow_html=True)

    tours = query_df("SELECT * FROM tours WHERE status='Đang mở'")
    hotels = query_df("SELECT * FROM hotels WHERE status='Đang hoạt động'")

    bookings = query_df(
        "SELECT * FROM bookings WHERE user_id = ?", (user["id"],)
    )

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("🌍 Tour đang mở", len(tours))
    col2.metric("🏨 Khách sạn", len(hotels))
    col3.metric("📋 Đơn của tôi", len(bookings))
    col4.metric(
        "💰 Tổng đã đặt",
        money(bookings["total_amount"].sum()) if not bookings.empty else "0 VNĐ"
    )

    st.markdown("---")

    st.subheader("⭐ Điểm khác biệt của SMART TOUR")

    c1, c2, c3 = st.columns(3)

    with c1:
        st.markdown("""
        <div class="card">
            <h3>🤖 Gợi ý thông minh</h3>
            <p>Dựa vào ngân sách, số người, điểm đến và sở thích để đề xuất tour phù hợp.</p>
        </div>
        """, unsafe_allow_html=True)

    with c2:
        st.markdown("""
        <div class="card">
            <h3>💰 Kiểm soát ngân sách</h3>
            <p>Tự động tính chi phí tour và cảnh báo khi phương án vượt ngân sách.</p>
        </div>
        """, unsafe_allow_html=True)

    with c3:
        st.markdown("""
        <div class="card">
            <h3>🏨 Kết hợp khách sạn</h3>
            <p>Khách có thể chọn khách sạn, loại phòng và số phòng ngay trong quy trình đặt tour.</p>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")
    st.subheader("🔥 Một số tour nổi bật")

    featured = tours.head(4)

    cols = st.columns(2)
    for index, (_, tour) in enumerate(featured.iterrows()):
        with cols[index % 2]:
            st.markdown(f"""
            <div class="recommend">
                <h3>🌴 {tour['name']}</h3>
                <p>📍 {tour['destination']} &nbsp; | &nbsp; ⏱️ {tour['duration']}</p>
                <p>🚐 {tour['transport']}</p>
                <p class="price">{money(tour['price_per_person'])}/người</p>
                <p>{tour['description']}</p>
            </div>
            """, unsafe_allow_html=True)


# ============================================================
# TÌM & ĐỀ XUẤT TOUR
# ============================================================

elif page == "🔎 Tìm & đề xuất tour":

    st.title("🔎 TÌM & ĐỀ XUẤT TOUR THÔNG MINH")

    st.write(
        "Nhập nhu cầu của bạn. Hệ thống sẽ chấm điểm các tour dựa trên "
        "điểm đến, ngân sách, số người và sở thích."
    )

    with st.form("smart_search"):

        col1, col2, col3 = st.columns(3)

        with col1:
            destination = st.selectbox(
                "📍 Bạn muốn đi đâu?",
                [
                    "Tất cả",
                    "Vũng Tàu",
                    "Đà Lạt",
                    "Phú Quốc",
                    "Nha Trang",
                    "Đà Nẵng - Hội An",
                    "Buôn Ma Thuột"
                ]
            )

        with col2:
            people = st.number_input(
                "👥 Số người",
                min_value=1,
                max_value=50,
                value=2
            )

        with col3:
            budget = st.number_input(
                "💰 Ngân sách tổng",
                min_value=500000,
                value=5000000,
                step=500000
            )

        st.write("❤️ Bạn thích gì?")

        interests = st.multiselect(
            "Chọn một hoặc nhiều sở thích",
            [
                "biển",
                "ăn uống",
                "nghỉ dưỡng",
                "chụp ảnh",
                "cafe",
                "thiên nhiên",
                "gia đình",
                "giải trí",
                "văn hóa",
                "khám phá",
                "hải sản"
            ],
            default=["biển", "ăn uống"]
        )

        submit = st.form_submit_button(
            "🤖 ĐỀ XUẤT PHƯƠNG ÁN",
            use_container_width=True
        )

    if submit:

        recommendations = recommend_tours(
            destination,
            budget,
            people,
            interests
        )

        st.session_state["recommendations"] = recommendations
        st.session_state["search_params"] = {
            "destination": destination,
            "people": people,
            "budget": budget,
            "interests": interests
        }

    if "recommendations" in st.session_state:

        recommendations = st.session_state["recommendations"]
        params = st.session_state["search_params"]

        st.markdown("---")

        if recommendations.empty:
            st.warning("Không tìm thấy tour phù hợp với số người hiện tại.")
        else:

            st.subheader("🤖 KẾT QUẢ ĐỀ XUẤT")

            best = recommendations.iloc[0]
            estimated = float(best["estimated_total"])

            st.markdown(f"""
            <div class="hero">
                <h2>💡 Phương án được hệ thống đề xuất</h2>
                <h1>{best['name']}</h1>
                <p>📍 {best['destination']} | ⏱️ {best['duration']}</p>
                <p>👥 {params['people']} người</p>
                <p>💰 Chi phí tour dự kiến: <b>{money(estimated)}</b></p>
            </div>
            """, unsafe_allow_html=True)

            if estimated > params["budget"]:
                over = estimated - params["budget"]
                st.error(
                    f"⚠️ Phương án này vượt ngân sách khoảng {money(over)}."
                )
                st.info(
                    "💡 Gợi ý tiết kiệm: chọn tour có giá thấp hơn, "
                    "khách sạn 3 sao hoặc giảm số phòng."
                )
            else:
                remain = params["budget"] - estimated
                st.success(
                    f"✅ Phương án nằm trong ngân sách. "
                    f"Ngân sách còn khoảng {money(remain)}."
                )

            st.markdown("---")
            st.subheader("📋 Các phương án khác")

            for _, tour in recommendations.head(6).iterrows():

                total = float(tour["estimated_total"])
                budget_text = (
                    "✅ Trong ngân sách"
                    if total <= params["budget"]
                    else "⚠️ Vượt ngân sách"
                )

                st.markdown(f"""
                <div class="recommend">
                    <h3>🌴 {tour['name']}</h3>
                    <p>📍 {tour['destination']} |
                    ⏱️ {tour['duration']} |
                    🚐 {tour['transport']}</p>
                    <p>💰 {money(tour['price_per_person'])}/người |
                    Tổng {params['people']} người: <b>{money(total)}</b></p>
                    <p>⭐ Điểm phù hợp: <b>{int(tour['score'])}</b> |
                    {budget_text}</p>
                    <p>{tour['description']}</p>
                </div>
                """, unsafe_allow_html=True)

                if st.button(
                    f"📅 Chọn tour: {tour['name']}",
                    key=f"choose_{int(tour['id'])}"
                ):
                    st.session_state["selected_tour_id"] = int(tour["id"])
                    st.success(
                        "Đã chọn tour. Hãy kéo xuống phần đặt tour."
                    )

            st.markdown("---")
            st.subheader("🏨 Tìm khách sạn phù hợp")

            if destination != "Tất cả":
                hotel_destination = destination
                hotel_budget = max(
                    500000,
                    params["budget"] - float(best["estimated_total"])
                )

                hotel_results = recommend_hotels(
                    hotel_destination,
                    hotel_budget,
                    int(best["nights"]),
                    max(1, (params["people"] + 1) // 2)
                )

                if hotel_results.empty:
                    st.info(
                        "Chưa có khách sạn mẫu phù hợp tại điểm đến này."
                    )
                else:
                    for _, hotel in hotel_results.head(5).iterrows():
                        st.write(
                            f"🏨 **{hotel['name']}** — "
                            f"{'⭐' * int(hotel['stars'])} — "
                            f"{money(hotel['price_per_room'])}/phòng/đêm — "
                            f"Dự kiến {money(hotel['estimated_total'])}"
                        )



# ============================================================
# KHU VỰC ĐẶT TOUR - HIỂN THỊ SAU KHI CHỌN TOUR
# ============================================================

if page == "🔎 Tìm & đề xuất tour" and "selected_tour_id" in st.session_state:

    st.markdown("---")
    st.subheader("📅 ĐẶT TOUR")

    selected_tour_id = st.session_state["selected_tour_id"]

    selected_tour_df = query_df(
        "SELECT * FROM tours WHERE id = ?", (selected_tour_id,)
    )

    if not selected_tour_df.empty:

        selected_tour = selected_tour_df.iloc[0]
        search_params = st.session_state.get("search_params", {})

        people_default = int(search_params.get("people", 2))
        destination_default = selected_tour["destination"]

        hotel_df = query_df("""
            SELECT * FROM hotels
            WHERE destination = ?
            AND status = 'Đang hoạt động'
            AND available_rooms > 0
            ORDER BY stars DESC, price_per_room ASC
        """, (destination_default,))

        hotel_choices = {"Không chọn khách sạn": None}

        for _, h in hotel_df.iterrows():
            hotel_choices[
                f"{h['name']} - {'⭐' * int(h['stars'])} - "
                f"{money(h['price_per_room'])}/phòng/đêm"
            ] = int(h["id"])

        with st.form("booking_tour_form"):

            c1, c2, c3 = st.columns(3)

            with c1:
                start_date = st.date_input(
                    "📅 Ngày khởi hành",
                    value=date.today()
                )

            with c2:
                booking_people = st.number_input(
                    "👥 Số người",
                    min_value=1,
                    max_value=int(selected_tour["available_seats"]),
                    value=min(
                        people_default,
                        int(selected_tour["available_seats"])
                    )
                )

            with c3:
                room_count = st.number_input(
                    "🏨 Số phòng",
                    min_value=1,
                    max_value=10,
                    value=max(1, (people_default + 1) // 2)
                )

            hotel_choice = st.selectbox(
                "🏨 Chọn khách sạn",
                list(hotel_choices.keys())
            )

            payment_method = st.selectbox(
                "💳 Phương thức thanh toán",
                [
                    "Chuyển khoản ngân hàng",
                    "Ví điện tử",
                    "Thanh toán tại văn phòng"
                ]
            )

            note = st.text_area(
                "📝 Ghi chú / yêu cầu đặc biệt",
                placeholder="Ví dụ: cần phòng tầng thấp, ăn chay..."
            )

            submit_booking = st.form_submit_button(
                "🚀 XÁC NHẬN ĐẶT TOUR",
                use_container_width=True
            )

            if submit_booking:

                if start_date < date.today():
                    st.error("Ngày khởi hành không được ở trong quá khứ.")
                elif int(selected_tour["available_seats"]) < booking_people:
                    st.error("Tour không còn đủ chỗ.")
                else:

                    hotel_id = hotel_choices[hotel_choice]
                    tour_cost = float(
                        selected_tour["price_per_person"]
                    ) * booking_people

                    hotel_cost = 0
                    selected_hotel = None

                    if hotel_id is not None:
                        selected_hotel_df = query_df(
                            "SELECT * FROM hotels WHERE id = ?",
                            (hotel_id,)
                        )

                        if selected_hotel_df.empty:
                            st.error("Khách sạn không tồn tại.")
                            st.stop()

                        selected_hotel = selected_hotel_df.iloc[0]

                        if int(selected_hotel["available_rooms"]) < room_count:
                            st.error("Khách sạn không đủ số phòng đã chọn.")
                            st.stop()

                        hotel_cost = (
                            float(selected_hotel["price_per_room"])
                            * int(selected_tour["nights"])
                            * room_count
                        )

                    total_amount = tour_cost + hotel_cost

                    booking_id = execute("""
                        INSERT INTO bookings
                        (
                            user_id, tour_id, hotel_id, booking_date,
                            start_date, people, rooms, total_amount,
                            payment_method, payment_status,
                            booking_status, note
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        int(user["id"]),
                        int(selected_tour_id),
                        hotel_id,
                        datetime.now().strftime("%Y-%m-%d"),
                        start_date.strftime("%Y-%m-%d"),
                        int(booking_people),
                        int(room_count),
                        total_amount,
                        payment_method,
                        "Chưa thanh toán",
                        "Chờ xác nhận",
                        note
                    ))

                    execute("""
                        UPDATE tours
                        SET available_seats = available_seats - ?
                        WHERE id = ?
                    """, (
                        int(booking_people),
                        int(selected_tour_id)
                    ))

                    if hotel_id is not None:
                        execute("""
                            UPDATE hotels
                            SET available_rooms = available_rooms - ?
                            WHERE id = ?
                        """, (
                            int(room_count),
                            int(hotel_id)
                        ))

                    st.session_state["last_booking_id"] = booking_id

                    st.success(
                        f"🎉 Đặt tour thành công! Mã đơn của bạn là **#{booking_id}**."
                    )

                    budget = float(
                        search_params.get("budget", total_amount)
                    )

                    st.write(
                        f"🌴 Tiền tour: **{money(tour_cost)}**"
                    )

                    st.write(
                        f"🏨 Tiền khách sạn: **{money(hotel_cost)}**"
                    )

                    st.write(
                        f"💰 Tổng chi phí: **{money(total_amount)}**"
                    )

                    if total_amount > budget:
                        st.warning(
                            f"⚠️ Tổng chi phí vượt ngân sách khoảng "
                            f"**{money(total_amount - budget)}**. "
                            f"Bạn có thể chọn khách sạn rẻ hơn."
                        )
                    else:
                        st.success(
                            f"✅ Tổng chi phí vẫn trong ngân sách. "
                            f"Còn lại khoảng **{money(budget - total_amount)}**."
                        )

                    st.info(
                        "👉 Vào mục **💳 Thanh toán** ở menu bên trái để thanh toán."
                    )

                    st.session_state.pop("selected_tour_id", None)

# ============================================================
# TOUR CỦA TÔI
# ============================================================

elif page == "📋 Tour của tôi":

    st.title("📋 TOUR CỦA TÔI")

    bookings = query_df("""
        SELECT
            b.id,
            t.name AS tour_name,
            t.destination,
            h.name AS hotel_name,
            b.booking_date,
            b.start_date,
            b.people,
            b.rooms,
            b.total_amount,
            b.payment_method,
            b.payment_status,
            b.booking_status,
            b.note
        FROM bookings b
        JOIN tours t ON b.tour_id = t.id
        LEFT JOIN hotels h ON b.hotel_id = h.id
        WHERE b.user_id = ?
        ORDER BY b.id DESC
    """, (user["id"],))

    if bookings.empty:
        st.info("Bạn chưa có đơn đặt tour nào.")
    else:

        for _, booking in bookings.iterrows():

            with st.expander(
                f"#{int(booking['id'])} — "
                f"{booking['tour_name']} — "
                f"{booking['booking_status']}"
            ):

                c1, c2, c3 = st.columns(3)

                c1.write(f"📍 **Điểm đến:** {booking['destination']}")
                c2.write(f"📅 **Ngày đi:** {booking['start_date']}")
                c3.write(f"👥 **Số người:** {int(booking['people'])}")

                st.write(
                    f"🏨 **Khách sạn:** "
                    f"{booking['hotel_name'] or 'Chưa chọn'}"
                )

                st.write(
                    f"💰 **Tổng tiền:** {money(booking['total_amount'])}"
                )

                st.write(
                    f"💳 **Thanh toán:** {booking['payment_status']} "
                    f"({booking['payment_method']})"
                )

                st.write(
                    f"📌 **Trạng thái đơn:** {booking['booking_status']}"
                )


# ============================================================
# THANH TOÁN
# ============================================================

elif page == "💳 Thanh toán":

    st.title("💳 THANH TOÁN")

    bookings = query_df("""
        SELECT b.*, t.name AS tour_name
        FROM bookings b
        JOIN tours t ON b.tour_id = t.id
        WHERE b.user_id = ?
        AND b.payment_status = 'Chưa thanh toán'
        AND b.booking_status != 'Đã hủy'
        ORDER BY b.id DESC
    """, (user["id"],))

    if bookings.empty:
        st.success("🎉 Không có đơn nào đang chờ thanh toán.")
    else:

        options = {
            f"Đơn #{int(row['id'])} - {row['tour_name']} - {money(row['total_amount'])}":
            int(row["id"])
            for _, row in bookings.iterrows()
        }

        selected = st.selectbox(
            "Chọn đơn cần thanh toán",
            list(options.keys())
        )

        booking_id = options[selected]

        booking = bookings[
            bookings["id"] == booking_id
        ].iloc[0]

        st.info(
            f"Tổng tiền cần thanh toán: **{money(booking['total_amount'])}**"
        )

        method = st.radio(
            "Phương thức thanh toán",
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

            execute("""
                UPDATE bookings
                SET payment_status = 'Đã thanh toán',
                    booking_status = 'Đã xác nhận'
                WHERE id = ?
            """, (booking_id,))

            execute("""
                INSERT INTO payments
                (booking_id, amount, method, paid_at, status)
                VALUES (?, ?, ?, ?, 'Thành công')
            """, (
                booking_id,
                float(booking["total_amount"]),
                method,
                datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            ))

            st.success(
                "✅ Thanh toán thành công!"
            )
            st.rerun()


# ============================================================
# ADMIN - QUẢN LÝ TOUR
# ============================================================

elif page == "🔧 Quản lý tour":

    admin_required()

    st.title("🔧 QUẢN LÝ TOUR")

    tab1, tab2 = st.tabs(["📋 Danh sách tour", "➕ Thêm tour"])

    with tab1:

        tours = query_df("SELECT * FROM tours ORDER BY id DESC")

        st.dataframe(
            tours[
                [
                    "id", "name", "destination", "duration",
                    "price_per_person", "available_seats", "status"
                ]
            ].rename(columns={
                "id": "ID",
                "name": "Tên tour",
                "destination": "Điểm đến",
                "duration": "Thời gian",
                "price_per_person": "Giá/người",
                "available_seats": "Chỗ còn",
                "status": "Trạng thái"
            }),
            use_container_width=True,
            hide_index=True
        )

        if not tours.empty:
            tour_id = st.selectbox(
                "Chọn tour để cập nhật",
                tours["id"].tolist()
            )

            tour = tours[tours["id"] == tour_id].iloc[0]

            with st.form("edit_tour"):
                name = st.text_input("Tên tour", value=tour["name"])
                price = st.number_input(
                    "Giá/người",
                    min_value=0,
                    value=int(tour["price_per_person"]),
                    step=100000
                )
                seats = st.number_input(
                    "Số chỗ còn",
                    min_value=0,
                    value=int(tour["available_seats"])
                )
                status = st.selectbox(
                    "Trạng thái",
                    ["Đang mở", "Tạm dừng", "Đã đóng"],
                    index=["Đang mở", "Tạm dừng", "Đã đóng"].index(tour["status"])
                )

                save = st.form_submit_button(
                    "💾 Cập nhật tour",
                    use_container_width=True
                )

                if save:
                    execute("""
                        UPDATE tours
                        SET name = ?, price_per_person = ?,
                            available_seats = ?, status = ?
                        WHERE id = ?
                    """, (name, price, seats, status, int(tour_id)))
                    st.success("Đã cập nhật tour.")
                    st.rerun()

    with tab2:

        with st.form("add_tour"):

            name = st.text_input("Tên tour *")
            destination = st.text_input("Điểm đến *")
            duration = st.text_input("Thời gian", value="3 ngày 2 đêm")

            c1, c2, c3 = st.columns(3)

            with c1:
                days = st.number_input("Số ngày", 1, 30, 3)

            with c2:
                nights = st.number_input("Số đêm", 0, 30, 2)

            with c3:
                price = st.number_input(
                    "Giá/người",
                    min_value=0,
                    value=2000000,
                    step=100000
                )

            seats = st.number_input(
                "Số chỗ",
                min_value=1,
                value=30
            )

            interests = st.text_input(
                "Sở thích, cách nhau bằng dấu phẩy",
                value="biển,ăn uống"
            )

            transport = st.selectbox(
                "Phương tiện",
                ["Xe du lịch", "Máy bay", "Tàu", "Xe + máy bay"]
            )

            description = st.text_area("Mô tả")

            submit = st.form_submit_button(
                "➕ Thêm tour",
                use_container_width=True
            )

            if submit:

                if not name.strip() or not destination.strip():
                    st.error("Vui lòng nhập tên tour và điểm đến.")
                else:
                    execute("""
                        INSERT INTO tours
                        (name, destination, duration, days, nights,
                         price_per_person, max_people, available_seats,
                         interests, description, transport, status)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'Đang mở')
                    """, (
                        name.strip(),
                        destination.strip(),
                        duration,
                        days,
                        nights,
                        price,
                        seats,
                        seats,
                        interests,
                        description,
                        transport
                    ))
                    st.success("Đã thêm tour.")
                    st.rerun()


# ============================================================
# ADMIN - QUẢN LÝ KHÁCH SẠN
# ============================================================

elif page == "🏨 Quản lý khách sạn":

    admin_required()

    st.title("🏨 QUẢN LÝ KHÁCH SẠN")

    hotels = query_df(
        "SELECT * FROM hotels ORDER BY id DESC"
    )

    st.dataframe(
        hotels[
            [
                "id", "name", "destination", "stars",
                "room_type", "price_per_room",
                "available_rooms", "status"
            ]
        ].rename(columns={
            "id": "ID",
            "name": "Khách sạn",
            "destination": "Điểm đến",
            "stars": "Sao",
            "room_type": "Loại phòng",
            "price_per_room": "Giá/phòng",
            "available_rooms": "Phòng còn",
            "status": "Trạng thái"
        }),
        use_container_width=True,
        hide_index=True
    )

    tab1, tab2 = st.tabs(["✏️ Cập nhật", "➕ Thêm khách sạn"])

    with tab1:

        if not hotels.empty:

            hotel_id = st.selectbox(
                "Chọn khách sạn",
                hotels["id"].tolist()
            )

            hotel = hotels[
                hotels["id"] == hotel_id
            ].iloc[0]

            with st.form("edit_hotel"):

                name = st.text_input(
                    "Tên khách sạn",
                    value=hotel["name"]
                )

                price = st.number_input(
                    "Giá phòng/đêm",
                    min_value=0,
                    value=int(hotel["price_per_room"]),
                    step=100000
                )

                available = st.number_input(
                    "Phòng còn",
                    min_value=0,
                    value=int(hotel["available_rooms"])
                )

                status = st.selectbox(
                    "Trạng thái",
                    ["Đang hoạt động", "Tạm dừng"],
                    index=(
                        0 if hotel["status"] == "Đang hoạt động" else 1
                    )
                )

                submit = st.form_submit_button(
                    "💾 Lưu thay đổi",
                    use_container_width=True
                )

                if submit:
                    execute("""
                        UPDATE hotels
                        SET name = ?, price_per_room = ?,
                            available_rooms = ?, status = ?
                        WHERE id = ?
                    """, (
                        name,
                        price,
                        available,
                        status,
                        int(hotel_id)
                    ))
                    st.success("Đã cập nhật khách sạn.")
                    st.rerun()

    with tab2:

        with st.form("add_hotel"):

            name = st.text_input("Tên khách sạn *")
            destination = st.text_input("Điểm đến *")

            c1, c2 = st.columns(2)

            with c1:
                stars = st.selectbox("Hạng sao", [1, 2, 3, 4, 5], index=2)
                room_type = st.selectbox(
                    "Loại phòng",
                    ["Phòng đơn", "Phòng đôi", "Phòng gia đình", "Suite"]
                )

            with c2:
                price = st.number_input(
                    "Giá phòng/đêm",
                    min_value=0,
                    value=800000,
                    step=100000
                )
                rooms = st.number_input(
                    "Tổng số phòng",
                    min_value=1,
                    value=20
                )

            description = st.text_area("Mô tả")

            submit = st.form_submit_button(
                "➕ Thêm khách sạn",
                use_container_width=True
            )

            if submit:

                if not name.strip() or not destination.strip():
                    st.error("Vui lòng nhập tên và điểm đến.")
                else:
                    execute("""
                        INSERT INTO hotels
                        (name, destination, stars, room_type,
                         price_per_room, total_rooms, available_rooms,
                         description, status)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'Đang hoạt động')
                    """, (
                        name,
                        destination,
                        stars,
                        room_type,
                        price,
                        rooms,
                        rooms,
                        description
                    ))
                    st.success("Đã thêm khách sạn.")
                    st.rerun()


# ============================================================
# ADMIN - KHÁCH HÀNG
# ============================================================

elif page == "👥 Quản lý khách hàng":

    admin_required()

    st.title("👥 QUẢN LÝ KHÁCH HÀNG")

    users = query_df("""
        SELECT id, full_name, username, phone, email, created_at
        FROM users
        WHERE role = 'customer'
        ORDER BY id DESC
    """)

    if users.empty:
        st.info("Chưa có khách hàng.")
    else:
        st.dataframe(
            users.rename(columns={
                "id": "ID",
                "full_name": "Họ tên",
                "username": "Tên đăng nhập",
                "phone": "Điện thoại",
                "email": "Email",
                "created_at": "Ngày đăng ký"
            }),
            use_container_width=True,
            hide_index=True
        )


# ============================================================
# ADMIN - ĐƠN ĐẶT
# ============================================================

elif page == "🧾 Quản lý đơn đặt":

    admin_required()

    st.title("🧾 QUẢN LÝ ĐƠN ĐẶT TOUR")

    bookings = query_df("""
        SELECT
            b.id,
            u.full_name AS customer,
            u.phone,
            t.name AS tour,
            t.destination,
            b.booking_date,
            b.start_date,
            b.people,
            b.rooms,
            b.total_amount,
            b.payment_status,
            b.booking_status,
            b.note
        FROM bookings b
        JOIN users u ON b.user_id = u.id
        JOIN tours t ON b.tour_id = t.id
        ORDER BY b.id DESC
    """)

    if bookings.empty:
        st.info("Chưa có đơn đặt tour.")
    else:

        st.dataframe(
            bookings[
                [
                    "id", "customer", "phone", "tour",
                    "destination", "start_date", "people",
                    "total_amount", "payment_status",
                    "booking_status"
                ]
            ].rename(columns={
                "id": "ID",
                "customer": "Khách hàng",
                "phone": "SĐT",
                "tour": "Tour",
                "destination": "Điểm đến",
                "start_date": "Ngày đi",
                "people": "Số người",
                "total_amount": "Tổng tiền",
                "payment_status": "Thanh toán",
                "booking_status": "Đơn hàng"
            }),
            use_container_width=True,
            hide_index=True
        )

        st.markdown("---")
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
                SET booking_status = ?
                WHERE id = ?
            """, (new_status, int(booking_id)))

            st.success("Đã cập nhật đơn.")
            st.rerun()


# ============================================================
# ADMIN DASHBOARD
# ============================================================

elif page == "📊 Dashboard Admin":

    admin_required()

    st.title("📊 DASHBOARD QUẢN TRỊ SMART TOUR")

    users = query_df("SELECT * FROM users WHERE role='customer'")
    tours = query_df("SELECT * FROM tours")
    hotels = query_df("SELECT * FROM hotels")
    bookings = query_df("SELECT * FROM bookings")
    payments = query_df("SELECT * FROM payments")

    revenue = payments[
        payments["status"] == "Thành công"
    ]["amount"].sum() if not payments.empty else 0

    confirmed = len(
        bookings[
            bookings["booking_status"].isin(
                ["Đã xác nhận", "Đã hoàn thành"]
            )
        ]
    ) if not bookings.empty else 0

    c1, c2, c3, c4, c5 = st.columns(5)

    c1.metric("👥 Khách hàng", len(users))
    c2.metric("🌍 Số tour", len(tours))
    c3.metric("🏨 Khách sạn", len(hotels))
    c4.metric("🧾 Đơn đặt", len(bookings))
    c5.metric("💰 Doanh thu", money(revenue))

    st.markdown("---")

    left, right = st.columns(2)

    with left:
        st.subheader("📈 Đơn đặt theo trạng thái")

        if not bookings.empty:
            status_data = bookings["booking_status"].value_counts()
            st.bar_chart(status_data)

    with right:
        st.subheader("💳 Doanh thu theo phương thức")

        if not payments.empty:
            payment_data = payments.groupby(
                "method"
            )["amount"].sum()

            st.bar_chart(payment_data)

    st.markdown("---")

    st.subheader("🔥 Tour được đặt nhiều")

    if not bookings.empty:

        tour_counts = bookings.groupby(
            "tour_id"
        ).size().reset_index(name="bookings")

        popular = tour_counts.merge(
            tours[["id", "name", "destination"]],
            left_on="tour_id",
            right_on="id"
        ).sort_values(
            "bookings",
            ascending=False
        )

        st.dataframe(
            popular[
                ["name", "destination", "bookings"]
            ].rename(columns={
                "name": "Tour",
                "destination": "Điểm đến",
                "bookings": "Số lượt đặt"
            }),
            use_container_width=True,
            hide_index=True
        )

