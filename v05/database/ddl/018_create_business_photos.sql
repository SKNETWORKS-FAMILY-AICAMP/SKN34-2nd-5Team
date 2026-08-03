CREATE TABLE IF NOT EXISTS business_photo (
    photo_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
    business_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
    label VARCHAR(16) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
    caption VARCHAR(1024) NULL,
    display_rank INT UNSIGNED NOT NULL,
    source_type VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
    loaded_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    PRIMARY KEY (photo_id),
    UNIQUE KEY uq_business_photo_rank (business_id, display_rank),
    KEY idx_business_photo_lookup (business_id, label, display_rank),
    CONSTRAINT chk_business_photo_rank CHECK (display_rank > 0),
    CONSTRAINT chk_business_photo_label
        CHECK (label IN ('food', 'outside', 'inside', 'drink', 'menu', 'unknown'))
) ENGINE=InnoDB;
