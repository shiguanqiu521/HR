CREATE TABLE IF NOT EXISTS employee
(
    id         BIGINT       NOT NULL AUTO_INCREMENT PRIMARY KEY,
    name       VARCHAR(50)  NOT NULL,
    phone      VARCHAR(20)  NOT NULL,
    department VARCHAR(50)  NOT NULL,
    position   VARCHAR(50)  NOT NULL,
    hire_date  DATE         NOT NULL,
    status     VARCHAR(10)  NOT NULL,
    deleted    TINYINT      NOT NULL DEFAULT 0,
    created_at DATETIME     NOT NULL,
    updated_at DATETIME     NOT NULL,
    INDEX idx_employee_deleted (deleted),
    INDEX idx_employee_name (name),
    INDEX idx_employee_department (department),
    INDEX idx_employee_phone (phone)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS sys_user
(
    id            BIGINT       NOT NULL AUTO_INCREMENT PRIMARY KEY,
    username      VARCHAR(50)  NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    salt          VARCHAR(64)  NOT NULL,
    display_name  VARCHAR(50)  NOT NULL,
    enabled       TINYINT      NOT NULL DEFAULT 1,
    created_at    DATETIME     NOT NULL,
    updated_at    DATETIME     NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
