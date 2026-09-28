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

# --- KẾT NỐI MYSQL AIVEN ---
DB_CONFIG = {
    "host": "mysql-1b346c1b-kimchi8019-4ea9.e.aivencloud.com",
    "port": 21314,
    "user": "avnadmin",
    "password": "AVNS_ZuLUVTHk6cKBskjg0Kp",
    "database": "smarttour_db",
    "ssl_disabled": False,  # Aiven bắt buộc sử dụng SSL
    "connection_timeout": 15,
    "charset": "utf8mb4",
}

VAT_RATE = 0.08
DEPOSIT_RATE = 0.30
MAX_DISCOUNT_PCT = 0.20

# ----------------------------------------------------------------------------
# DỮ LIỆU THAM CHIẾU: TOUR, KHÁCH SẠN, PHÒNG, DỊCH VỤ
# ----------------------------------------------------------------------------
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
SEASON_LABEL = {
    "peak": "Cao điểm lễ/Tết",
    "high": "Mùa cao điểm hè",
    "normal": "Mùa thường",
    "low": "Mùa thấp điểm",
}
WEEKEND_HOTEL_SURCHARGE = 0.15  # Đêm thứ 6 và thứ 7

EXTRAS = {
    "Bảo hiểm du lịch": {"price": 60_000, "unit": "người"},
    "Đưa đón sân bay/ga 2 chiều": {"price": 400_000, "unit": "xe (4 khách)"},
    "Hướng dẫn viên riêng": {"price": 1_200_000, "unit": "ngày"},
    "Gói ăn uống nâng cấp": {"price": 250_000, "unit": "người/ngày"},
    "Vé tham quan VIP (fast-track)": {"price": 300_000, "unit": "người"},
}

PROMOS = {
    "SMART10": {"type": "pct", "value": 0.10, "desc": "Giảm 10% giá tour"},
    "WELCOME": {"type": "flat", "value": 200_000, "desc": "Giảm 200.000đ"},
    "FAMILY5": {"type": "pct", "value": 0.05, "desc": "Giảm 5% giá tour"},
}

HOLIDAYS = [
    (date(2026, 12, 24), date(2027, 1, 3)),
    (date(2027, 2, 3), date(2027, 2, 12)),
    (date(2027, 4, 28), date(2027, 5, 3)),
    (date(2027, 8, 30), date(2027, 9, 3)),
    (date(2027, 12, 24), date(2028, 1, 2)),
    (date(2028, 1, 23), date(2028, 2, 1)),
]

# ----------------------------------------------------------------------------
# HÀM TIỆN ÍCH
# ----------------------------------------------------------------------------
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

def hotel_night_multiplier(d: date):
    s = season_of(d)
    m = HOTEL_SEASON[s]
    weekend = d.weekday() in (4, 5)
    if weekend:
        m *= 1 + WEEKEND_HOTEL_SURCHARGE
    return m, s, weekend

# --- DATABASE DDL CHUẨN - BỎ RÀNG BUỘC KHÓA NGOẠI TRÁNH LỖI AIVEN ---
DDL = [
    # 1. Tạo bảng bookings
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
        status VARCHAR(40) NOT NULL DEFAULT 'Chờ thanh toán cọc',
        cancelled_at DATETIME NULL,
        cancel_fee DECIMAL(14,2) NULL,
        refund_amount DECIMAL(14,2) NULL,
        INDEX idx_phone (phone), INDEX idx_email (email), INDEX idx_depart (depart_at)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
    
    # 2. Tạo bảng booking_guests
    """CREATE TABLE IF NOT EXISTS booking_guests (
        id INT AUTO_INCREMENT PRIMARY KEY,
        booking_code VARCHAR(20) NOT NULL,
        guest_no INT NOT NULL,
        age INT NOT NULL,
        age_group VARCHAR(60),
        INDEX idx_booking_code (booking_code)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
    
    # 3. Tạo bảng booking_lines
    """CREATE TABLE IF NOT EXISTS booking_lines (
        id INT AUTO_INCREMENT PRIMARY KEY,
        booking_code VARCHAR(20) NOT NULL,
        category VARCHAR(40),
        detail VARCHAR(300),
        amount DECIMAL(14,2) NOT NULL,
        INDEX idx_booking_code (booking_code)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
]

def get_conn():
    return mysql.connector.connect(**DB_CONFIG)

@st.cache_resource(show_spinner="Đang kết nối MySQL (Aiven)...")
def init_db():
    try:
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
               depart_at, return_at, n_guests, hotel, rooms, subtotal, discount, vat, total, deposit,
               payment, note, status)
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
                "SELECT * FROM bookings WHERE code=%s OR phone=%s OR email=%s "
                "ORDER BY created_at DESC LIMIT %s", (keyword, keyword, keyword, limit)
            )
        else:
            cur.execute("SELECT * FROM bookings ORDER BY created_at DESC LIMIT %s", (limit,))
        return cur.fetchall()
    finally:
        conn.close()

def get_booking(code):
    conn = get_conn()
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT * FROM bookings WHERE code=%s", (code,))
        r = cur.fetchone()
        if not r:
            return None
        cur.execute("SELECT age FROM booking_guests WHERE booking_code=%s ORDER BY guest_no", (code,))
        ages = [x["age"] for x in cur.fetchall()]
        cur.execute("SELECT category, detail, amount FROM booking_lines WHERE booking_code=%s ORDER BY id", (code,))
        lines = [
            {"Hạng mục": x["category"], "Chi tiết": x["detail"], "Thành tiền": float(x["amount"])}
            for x in cur.fetchall()
        ]
        return {
            "code": r["code"],
            "created": r["created_at"].strftime("%d/%m/%Y %H:%M"),
            "customer": r["customer"],
            "phone": r["phone"],
            "email": r["email"],
            "tour": r["tour_name"],
            "depart": r["depart_at"].strftime("%Y-%m-%d %H:%M"),
            "return": r["return_at"].strftime("%Y-%m-%d %H:%M"),
            "n_guests": r["n_guests"],
            "ages": ages,
            "hotel": r["hotel"],
            "rooms": r["rooms"],
            "lines": lines,
            "vat": float(r["vat"]),
            "total": float(r["total"]),
            "deposit": float(r["deposit"]),
            "payment": r["payment"],
            "note": r["note"],
            "status": r["status"],
        }
    finally:
        conn.close()

def update_status(code, status, fee=None, refund=None):
    conn = get_conn()
    try:
        cur = conn.cursor()
        if status == "Đã hủy":
            cur.execute(
                "UPDATE bookings SET status=%s, cancelled_at=NOW(), cancel_fee=%s, refund_amount=%s "
                "WHERE code=%s", (status, fee, refund, code)
            )
        else:
            cur.execute("UPDATE bookings SET status=%s WHERE code=%s", (status, code))
        conn.commit()
    finally:
        conn.close()

def db_stats():
    conn = get_conn()
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute(
            "SELECT COUNT(*) AS n, COALESCE(SUM(CASE WHEN status<>'Đã hủy' THEN total END),0) AS revenue, "
            "SUM(status='Chờ thanh toán cọc') AS pending FROM bookings"
        )
        return cur.fetchone()
    finally:
        conn.close()

# ----------------------------------------------------------------------------
# LOGIC TÍNH GIÁ TOUR
# ----------------------------------------------------------------------------
def calc_quote(tour, depart, ages, hotel, rooms, extras, promo_code):
    lines = []
    n_guests = len(ages)
    season = season_of(depart)
    t_mult = TOUR_SEASON[season]

    # 1) Giá tour theo nhóm tuổi
    tour_fare = 0.0
    for label, cnt in Counter(age_group(a)[0] for a in ages).items():
        factor = next(f for _, _, l, f in AGE_GROUPS if l == label)
        unit = round(tour["base"] * t_mult * factor, -3)
        tour_fare += unit * cnt
        lines.append({
            "Hạng mục": "Tour",
            "Chi tiết": f"{label} × {cnt} ({vnd(unit)}/người)",
            "Thành tiền": unit * cnt
        })

    # 2) Khách sạn theo ngày
    hotel_total, night_rows = 0.0, []
    if hotel and sum(rooms.values()) > 0:
        h_name, stars = hotel
        nights = tour["days"] - 1
        per_type = Counter()
        for i in range(nights):
            d = depart + timedelta(days=i)
            m, s, wk = hotel_night_multiplier(d)
            row = {
                "Đêm": d.strftime("%d/%m/%Y (%a)"),
                "Mùa": SEASON_LABEL[s],
                "Cuối tuần": "+15%" if wk else "-"
            }
            night_sum = 0.0
            for rt, q in rooms.items():
                if q:
                    p = round(room_price(tour, stars, rt) * m, -3)
                    per_type[rt] += p * q
                    night_sum += p * q
                    row[rt] = vnd(p)
            row["Tổng đêm"] = vnd(night_sum)
            night_rows.append(row)
        for rt, amount in per_type.items():
            hotel_total += amount
            lines.append({
                "Hạng mục": "Khách sạn",
                "Chi tiết": f"{h_name} {stars}★ - {rooms[rt]} phòng {rt} × {nights} đêm",
                "Thành tiền": amount
            })

    # 3) Dịch vụ thêm
    extras_total = 0.0
    for name in extras:
        e = EXTRAS[name]
        if name == "Bảo hiểm du lịch":
            qty = n_guests
        elif name.startswith("Đưa đón"):
            qty = math.ceil(n_guests / 4)
        elif name == "Hướng dẫn viên riêng":
            qty = tour["days"]
        elif name == "Gói ăn uống nâng cấp":
            qty = sum(1 for a in ages if a >= 2) * tour["days"]
        else:
            qty = sum(1 for a in ages if a >= 2)
        amount = e["price"] * qty
        extras_total += amount
        lines.append({
            "Hạng mục": "Dịch vụ",
            "Chi tiết": f"{name} × {qty} {e['unit']}",
            "Thành tiền": amount
        })

    # 4) Khuyến mãi & Giảm giá
    pct, flat = 0.0, 0.0
    days_ahead = (depart - date.today()).days
    if days_ahead >= 30:
        pct += 0.05
        lines.append({
            "Hạng mục": "Giảm giá",
            "Chi tiết": "Đặt sớm ≥ 30 ngày (5%)",
            "Thành tiền": -0.05 * tour_fare
        })
    if n_guests >= 10:
        pct += 0.05
        lines.append({
            "Hạng mục": "Giảm giá",
            "Chi tiết": "Đoàn ≥ 10 khách (5%)",
            "Thành tiền": -0.05 * tour_fare
        })
    
    promo = PROMOS.get(promo_code)
    if promo:
        if promo["type"] == "pct":
            pct += promo["value"]
            lines.append({
                "Hạng mục": "Giảm giá",
                "Chi tiết": f"Mã {promo_code}: {promo['desc']}",
                "Thành tiền": -promo["value"] * tour_fare
            })
        else:
            flat += promo["value"]
            lines.append({
                "Hạng mục": "Giảm giá",
                "Chi tiết": f"Mã {promo_code}: {promo['desc']}",
                "Thành tiền": -promo["value"]
            })

    capped = min(pct, MAX_DISCOUNT_PCT)
    discount = capped * tour_fare + flat
    if pct > MAX_DISCOUNT_PCT:
        lines.append({
            "Hạng mục": "Giảm giá",
            "Chi tiết": "Điều chỉnh về mức giảm tối đa 20%",
            "Thành tiền": (pct - capped) * tour_fare
        })

    subtotal = tour_fare + hotel_total + extras_total
    taxable = max(subtotal - discount, 0)
    vat = taxable * VAT_RATE
    total = taxable + vat

    return {
        "lines": lines,
        "night_rows": night_rows,
        "season": season,
        "tour_fare": tour_fare,
        "hotel_total": hotel_total,
        "extras_total": extras_total,
        "subtotal": subtotal,
        "discount": discount,
        "vat": vat,
        "total": total,
        "deposit": total * DEPOSIT_RATE,
        "days_ahead": days_ahead,
    }

def cancellation_fee_pct(days_left: int) -> float:
    if days_left >= 30:
        return 0.0
    if days_left >= 15:
        return 0.30
    if days_left >= 7:
        return 0.50
    return 1.0

def invoice_text(b: dict) -> str:
    out = [
        "=" * 60, "SMART TOUR - XÁC NHẬN ĐẶT TOUR", "=" * 60,
        f"Mã đặt tour : {b['code']}",
        f"Ngày đặt    : {b['created']}",
        f"Khách hàng  : {b['customer']} - {b['phone']} - {b['email']}",
        f"Tour        : {b['tour']}",
        f"Khởi hành   : {b['depart']}",
        f"Kết thúc    : {b['return']}",
        f"Số khách    : {b['n_guests']} (tuổi: {', '.join(map(str, b['ages']))})",
        f"Khách sạn   : {b['hotel']}",
        f"Phòng       : {b['rooms']}",
        "-" * 60,
    ]
    for ln in b["lines"]:
        out.append(f"{ln['Hạng mục']:<10} {ln['Chi tiết'][:38]:<38} {vnd(ln['Thành tiền']):>14}")
    out += [
        "-" * 60,
        f"Thuế VAT {VAT_RATE:.0%}: {vnd(b['vat'])}",
        f"TỔNG CỘNG: {vnd(b['total'])}",
        f"Đặt cọc {DEPOSIT_RATE:.0%}: {vnd(b['deposit'])} | Thanh toán: {b['payment']}",
        f"Còn lại {vnd(b['total'] - b['deposit'])} - thanh toán trước ngày khởi hành 7 ngày.",
        f"Trạng thái: {b['status']}",
    ]
    return "\n".join(out)

# ----------------------------------------------------------------------------
# GIAO DIỆN STREAMLIT
# ----------------------------------------------------------------------------
db_error = init_db()

with st.sidebar:
    st.header("🗄️ Cơ sở dữ liệu")
    if db_error:
        st.error("Chưa kết nối được MySQL")
        st.caption(db_error)
    else:
        st.success("Đã kết nối MySQL Aiven")
        st.caption(f"{DB_CONFIG['host']}:{DB_CONFIG['port']} / {DB_CONFIG['database']}")
    if st.button("🔄 Kết nối lại"):
        init_db.clear()
        st.rerun()

st.title("🌴 Smart Tour - Đặt tour thông minh")
st.caption("Chọn tour • ngày giờ đi • độ tuổi khách • khách sạn & phòng • giá tự động cập nhật theo mùa")

tab_book, tab_manage, tab_policy = st.tabs(["🧭 Đặt tour", "📋 Đơn đặt của tôi", "ℹ️ Chính sách & bảng giá"])

# ============================== TAB ĐẶT TOUR ================================
with tab_book:
    col_form, col_sum = st.columns([3, 2], gap="large")

    with col_form:
        # 1. Tour
        st.subheader("1. Chọn tour")
        tour_id = st.selectbox(
            "Tour",
            list(TOURS),
            format_func=lambda k: f"{TOURS[k]['name']} ({TOURS[k]['days']}N{TOURS[k]['days']-1}Đ) - từ {vnd(TOURS[k]['base'])}"
        )
        tour = TOURS[tour_id]
        st.info(f"**Điểm nhấn:** {tour['highlights']}  \n**Di chuyển:** {tour['transport']}")

        # 2. Ngày giờ
        st.subheader("2. Ngày & giờ khởi hành")
        c1, c2 = st.columns(2)
        depart = c1.date_input(
            "Ngày khởi hành",
            value=date.today() + timedelta(days=35),
            min_value=date.today() + timedelta(days=1),
            format="DD/MM/YYYY"
        )
        dep_time = c2.selectbox("Giờ khởi hành", tour["times"])
        end_date = depart + timedelta(days=tour["days"] - 1)
        s_key = season_of(depart)
        st.write(
            f"🗓️ **{depart:%A %d/%m/%Y} {dep_time}** → về **{end_date:%d/%m/%Y} 18:00** "
            f"| Mùa: **{SEASON_LABEL[s_key]}** (hệ số giá tour ×{TOUR_SEASON[s_key]})"
        )

        # 3. Khách & độ tuổi
        st.subheader("3. Khách tham gia & độ tuổi")
        n_guests = st.number_input("Tổng số khách", 1, 30, 2)
        ages = []
        cols = st.columns(4)
        for i in range(int(n_guests)):
            ages.append(cols[i % 4].number_input(f"Tuổi khách {i+1}", 0, 100, 30, key=f"age_{i}"))
        occupants = sum(1 for a in ages if a >= 2)
        adults = sum(1 for a in ages if a >= 18)

        # 4. Khách sạn
        st.subheader("4. Khách sạn & phòng")
        hotel_opts = ["Không đặt khách sạn"] + [f"{n} ({s}★)" for n, s in tour["hotels"]]
        hotel_choice = st.selectbox("Khách sạn", hotel_opts, index=2)
        hotel, rooms = None, {rt: 0 for rt in ROOM_TYPES}
        
        if hotel_choice != hotel_opts[0]:
            h_idx = hotel_opts.index(hotel_choice) - 1
            hotel = tour["hotels"][h_idx]
            st.caption(
                f"Số đêm: {tour['days']-1} | Giá đã bao gồm hệ số mùa & phụ thu cuối tuần (T6, T7) "
                f"— xem chi tiết từng đêm ở bảng bên dưới."
            )
            rc = st.columns(3)
            for i, (rt, info) in enumerate(ROOM_TYPES.items()):
                p = room_price(tour, hotel[1], rt)
                rooms[rt] = rc[i].number_input(
                    f"{rt} (tối đa {info['cap']} người)\n{vnd(p)}/đêm",
                    0, 15, 1 if rt == "Standard" else 0, key=f"room_{rt}"
                )
            st.caption(f"💡 Gợi ý: {occupants} khách cần tối thiểu {math.ceil(occupants/2)} phòng Standard.")

        # 5. Dịch vụ + Mã giảm giá
        st.subheader("5. Dịch vụ thêm & ưu đãi")
        extras = st.multiselect(
            "Dịch vụ thêm",
            list(EXTRAS),
            format_func=lambda k: f"{k} - {vnd(EXTRAS[k]['price'])}/{EXTRAS[k]['unit']}"
        )
        promo_code = st.text_input("Mã giảm giá (thử: SMART10, WELCOME, FAMILY5)").strip().upper()
        if promo_code:
            if promo_code in PROMOS:
                st.success(PROMOS[promo_code]["desc"])
            else:
                st.warning("Mã không hợp lệ.")

        # 6. Liên hệ
        st.subheader("6. Thông tin liên hệ")
        cc = st.columns(2)
        name = cc[0].text_input("Họ tên người đặt")
        phone = cc[1].text_input("Số điện thoại")
        email = st.text_input("Email")
        note = st.text_area("Yêu cầu đặc biệt (ăn chay, dị ứng, xe lăn, ...)")
        payment = st.selectbox(
            "Hình thức thanh toán đặt cọc",
            ["Chuyển khoản ngân hàng", "Thẻ tín dụng", "Ví MoMo/ZaloPay", "Tiền mặt tại văn phòng"]
        )

    # ---- Kiểm tra hợp lệ dữ liệu
    errors = []
    if adults < 1:
        errors.append("Cần ít nhất 1 người từ 18 tuổi trở lên trong đoàn.")
    if hotel:
        cap = sum(q * ROOM_TYPES[rt]["cap"] for rt, q in rooms.items())
        if sum(rooms.values()) == 0:
            errors.append("Hãy chọn ít nhất 1 phòng hoặc chọn 'Không đặt khách sạn'.")
        elif cap < occupants:
            errors.append(f"Sức chứa phòng ({cap}) nhỏ hơn số khách cần giường ({occupants}).")
        elif sum(rooms.values()) > occupants:
            errors.append("Số phòng nhiều hơn số khách - vui lòng kiểm tra lại.")

    quote = calc_quote(tour, depart, ages, hotel, rooms, extras, promo_code)

    # ---- Cột tổng quan & thanh toán
    with col_sum:
        st.subheader("💰 Báo giá tạm tính")
        m1, m2 = st.columns(2)
        m1.metric("Tổng thanh toán", vnd(quote["total"]))
        m2.metric(f"Đặt cọc {DEPOSIT_RATE:.0%}", vnd(quote["deposit"]))
        
        st.dataframe(
            pd.DataFrame(quote["lines"]).assign(**{"Thành tiền": lambda d: d["Thành tiền"].map(vnd)}),
            hide_index=True,
            use_container_width=True
        )
        
        st.write(
            f"Tạm tính: **{vnd(quote['subtotal'])}**  \n"
            f"Giảm giá: **-{vnd(quote['discount'])}**  \n"
            f"VAT {VAT_RATE:.0%}: **{vnd(quote['vat'])}**  \n"
            f"### Tổng: {vnd(quote['total'])}"
        )
        
        if quote["night_rows"]:
            with st.expander("Giá phòng chi tiết từng đêm"):
                st.dataframe(pd.DataFrame(quote["night_rows"]), hide_index=True, use_container_width=True)
                
        for e in errors:
            st.error(e)

        if st.button("✅ Xác nhận đặt tour", type="primary", use_container_width=True):
            if db_error:
                st.error("Chưa kết nối được cơ sở dữ liệu - xem thanh bên trái.")
            elif errors:
                st.error("Vui lòng sửa các lỗi ở trên.")
            elif not name.strip() or len(phone.strip()) < 9 or "@" not in email:
                st.error("Vui lòng nhập họ tên, số điện thoại và email hợp lệ.")
            else:
                booking = {
                    "code": f"ST{datetime.now():%y%m%d}-{uuid.uuid4().hex[:4].upper()}",
                    "created": f"{datetime.now():%d/%m/%Y %H:%M}",
                    "customer": name.strip(),
                    "phone": phone.strip(),
                    "email": email.strip(),
                    "tour": tour["name"],
                    "depart": f"{depart:%Y-%m-%d} {dep_time}",
                    "return": f"{end_date:%Y-%m-%d} 18:00",
                    "n_guests": int(n_guests),
                    "ages": [int(a) for a in ages],
                    "hotel": hotel_choice,
                    "rooms": ", ".join(f"{q} {rt}" for rt, q in rooms.items() if q) or "-",
                    "lines": quote["lines"],
                    "vat": quote["vat"],
                    "total": quote["total"],
                    "deposit": quote["deposit"],
                    "payment": payment,
                    "note": note,
                    "status": "Chờ thanh toán cọc",
                }
                try:
                    insert_booking(booking, tour_id, quote, ages)
                    st.session_state.last_booking = booking
                    st.balloons()
                except Exception as ex:
                    st.error(f"Không lưu được vào MySQL: {ex}")

        if "last_booking" in st.session_state:
            lb = st.session_state.last_booking
            st.success(f"Đặt tour thành công! Mã: **{lb['code']}**")
            st.download_button(
                "⬇️ Tải phiếu xác nhận",
                invoice_text(lb),
                file_name=f"{lb['code']}.txt"
            )

# ============================== TAB QUẢN LÝ =================================
with tab_manage:
    if db_error:
        st.error("Chưa kết nối được cơ sở dữ liệu.")
    else:
        try:
            stt = db_stats()
            k1, k2, k3 = st.columns(3)
            k1.metric("Tổng số đơn", int(stt["n"]))
            k2.metric("Doanh thu (không tính đơn hủy)", vnd(float(stt["revenue"])))
            k3.metric("Đơn chờ cọc", int(stt["pending"] or 0))

            kw = st.text_input("Tra cứu theo mã đơn / số điện thoại / email (để trống = 50 đơn mới nhất)").strip()
            rows = fetch_bookings(kw)
            if not rows:
                st.info("Không tìm thấy đơn đặt tour nào.")
            else:
                st.dataframe(
                    pd.DataFrame([{
                        "Mã": r["code"],
                        "Khách": r["customer"],
                        "Tour": r["tour_name"],
                        "Khởi hành": r["depart_at"].strftime("%d/%m/%Y %H:%M"),
                        "Số khách": r["n_guests"],
                        "Tổng tiền": vnd(float(r["total"])),
                        "Trạng thái": r["status"]
                    } for r in rows]),
                    hide_index=True,
                    use_container_width=True
                )
                
                code = st.selectbox("Xem chi tiết đơn", [r["code"] for r in rows])
                b = get_booking(code)
                if b:
                    st.code(invoice_text(b), language="text")
                    cA, cB = st.columns(2)
                    
                    if b["status"] == "Chờ thanh toán cọc" and cA.button("💳 Xác nhận đã nhận cọc"):
                        update_status(code, "Đã đặt cọc")
                        st.rerun()
                        
                    if b["status"] != "Đã hủy":
                        d_left = (datetime.strptime(b["depart"][:10], "%Y-%m-%d").date() - date.today()).days
                        fee_pct = cancellation_fee_pct(d_left)
                        fee = b["total"] * fee_pct
                        paid = b["deposit"] if b["status"] == "Đã đặt cọc" else 0
                        refund = max(paid - fee, 0)
                        
                        cB.caption(f"Còn {d_left} ngày → phí hủy {fee_pct:.0%} ({vnd(fee)}). Hoàn lại: {vnd(refund)}")
                        if cB.button("❌ Hủy tour"):
                            update_status(code, "Đã hủy", fee, refund)
                            st.rerun()
        except Exception as ex:
            st.error(f"Lỗi truy vấn MySQL: {ex}")

# ============================== TAB CHÍNH SÁCH ==============================
with tab_policy:
    st.subheader("Hệ số giá theo độ tuổi")
    st.table(pd.DataFrame([{"Nhóm tuổi": l, "% giá tour": f"{f:.0%}"} for _, _, l, f in AGE_GROUPS]))
    
    st.subheader("Giá phòng khách sạn theo mùa")
    st.write(
        "Giá gốc × hệ số mùa: " + ", ".join(f"{SEASON_LABEL[k]} ×{v}" for k, v in HOTEL_SEASON.items())
        + f". Đêm thứ 6 và thứ 7 phụ thu {WEEKEND_HOTEL_SURCHARGE:.0%}."
    )
    
    st.subheader("Giá tour theo mùa")
    st.write(", ".join(f"{SEASON_LABEL[k]} ×{v}" for k, v in TOUR_SEASON.items()))
    
    st.subheader("Ưu đãi")
    st.write(
        "- Đặt sớm ≥ 30 ngày: giảm 5% giá tour\n"
        "- Đoàn ≥ 10 khách: giảm 5% giá tour\n"
        "- Mã giảm giá: SMART10, WELCOME, FAMILY5\n"
        "- Tổng giảm theo % tối đa 20% giá tour"
    )
    
    st.subheader("Chính sách hủy tour")
    st.write(
        "- ≥ 30 ngày trước ngày đi: không mất phí\n"
        "- 15–29 ngày: phí 30% tổng giá trị\n"
        "- 7–14 ngày: phí 50%\n"
        "- Dưới 7 ngày: phí 100%"
    )
    
    st.subheader("Thanh toán")
    st.write(
        f"Đặt cọc {DEPOSIT_RATE:.0%} khi đặt; thanh toán phần còn lại trước 7 ngày khởi hành. "
        f"Giá đã gồm VAT {VAT_RATE:.0%}."
    )
