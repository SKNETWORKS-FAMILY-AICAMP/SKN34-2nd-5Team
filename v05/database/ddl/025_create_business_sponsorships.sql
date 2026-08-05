CREATE TABLE IF NOT EXISTS business_sponsorships (
    sponsorship_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    business_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
    region_state VARCHAR(8) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    priority_tier TINYINT UNSIGNED NOT NULL DEFAULT 1,
    status VARCHAR(16) CHARACTER SET ascii COLLATE ascii_bin NOT NULL DEFAULT 'pending',
    created_by VARCHAR(64) NOT NULL,
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    KEY idx_sponsorship_region (region_state, status, start_date, end_date),
    KEY idx_sponsorship_business (business_id),
    CONSTRAINT chk_sponsorship_dates CHECK (end_date >= start_date),
    CONSTRAINT chk_sponsorship_status CHECK (status IN ('pending', 'approved', 'expired'))
) ENGINE=InnoDB;
