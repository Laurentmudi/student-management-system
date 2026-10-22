-- Run once as a MySQL admin (e.g.  mysql -u root -p < database/setup.sql)
CREATE DATABASE IF NOT EXISTS tucode_sms CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER IF NOT EXISTS 'sms_user'@'localhost' IDENTIFIED BY 'sms_password';
GRANT ALL PRIVILEGES ON tucode_sms.* TO 'sms_user'@'localhost';
FLUSH PRIVILEGES;
