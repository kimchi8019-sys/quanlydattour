CREATE DATABASE IF NOT EXISTS smart_tour CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE smart_tour;

CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    full_name VARCHAR(150) NOT NULL,
    username VARCHAR(100) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL,
    role VARCHAR(20) NOT NULL DEFAULT 'customer',
    phone VARCHAR(30) DEFAULT '',
    email VARCHAR(150) DEFAULT '',
    created_at DATETIME NOT NULL
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS tours (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    destination VARCHAR(150) NOT NULL,
    duration VARCHAR(100) NOT NULL,
    days INT NOT NULL,
    nights INT NOT NULL,
    price_per_person DECIMAL(15,2) NOT NULL,
    max_people INT NOT NULL DEFAULT 30,
    available_seats INT NOT NULL DEFAULT 30,
    interests TEXT,
    description TEXT,
    transport VARCHAR(100) DEFAULT 'Xe du lịch',
    status VARCHAR(50) NOT NULL DEFAULT 'Đang mở'
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS hotels (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    destination VARCHAR(150) NOT NULL,
    stars INT NOT NULL DEFAULT 3,
    room_type VARCHAR(100) NOT NULL,
    price_per_room DECIMAL(15,2) NOT NULL,
    total_rooms INT NOT NULL DEFAULT 10,
    available_rooms INT NOT NULL DEFAULT 10,
    description TEXT,
    status VARCHAR(50) NOT NULL DEFAULT 'Đang hoạt động'
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS bookings (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    tour_id INT NOT NULL,
    hotel_id INT NULL,
    booking_date DATETIME NOT NULL,
    start_date DATE NOT NULL,
    people INT NOT NULL,
    rooms INT NOT NULL DEFAULT 1,
    total_amount DECIMAL(15,2) NOT NULL,
    payment_method VARCHAR(50) NOT NULL,
    payment_status VARCHAR(50) NOT NULL DEFAULT 'Chưa thanh toán',
    booking_status VARCHAR(50) NOT NULL DEFAULT 'Chờ xác nhận',
    note TEXT,
    CONSTRAINT fk_booking_user FOREIGN KEY (user_id) REFERENCES users(id),
    CONSTRAINT fk_booking_tour FOREIGN KEY (tour_id) REFERENCES tours(id),
    CONSTRAINT fk_booking_hotel FOREIGN KEY (hotel_id) REFERENCES hotels(id)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS payments (
    id INT AUTO_INCREMENT PRIMARY KEY,
    booking_id INT NOT NULL,
    amount DECIMAL(15,2) NOT NULL,
    method VARCHAR(50) NOT NULL,
    paid_at DATETIME NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'Thành công',
    CONSTRAINT fk_payment_booking FOREIGN KEY (booking_id) REFERENCES bookings(id)
) ENGINE=InnoDB;
