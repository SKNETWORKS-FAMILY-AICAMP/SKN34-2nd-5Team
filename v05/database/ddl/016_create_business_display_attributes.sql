-- Display-only Yelp Open Dataset attributes for v05 restaurant candidates.
-- These values are a historical snapshot and must not be presented as live data.

CREATE TABLE IF NOT EXISTS business_display_attribute (
    business_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
    address VARCHAR(255) NULL,
    postal_code VARCHAR(32) NULL,
    is_open_snapshot TINYINT(1) NOT NULL,
    hours_json JSON NULL,
    price_range TINYINT UNSIGNED NULL,
    takeout TINYINT(1) NULL,
    delivery TINYINT(1) NULL,
    reservations TINYINT(1) NULL,
    outdoor_seating TINYINT(1) NULL,
    wifi VARCHAR(32) CHARACTER SET ascii COLLATE ascii_bin NULL,
    parking_json JSON NULL,
    wheelchair_accessible TINYINT(1) NULL,
    alcohol VARCHAR(32) CHARACTER SET ascii COLLATE ascii_bin NULL,
    source_type VARCHAR(32) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
    loaded_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    PRIMARY KEY (business_id),
    CONSTRAINT chk_business_display_open_snapshot
        CHECK (is_open_snapshot IN (0, 1)),
    CONSTRAINT chk_business_display_price
        CHECK (price_range IS NULL OR price_range BETWEEN 1 AND 4),
    CONSTRAINT chk_business_display_takeout
        CHECK (takeout IS NULL OR takeout IN (0, 1)),
    CONSTRAINT chk_business_display_delivery
        CHECK (delivery IS NULL OR delivery IN (0, 1)),
    CONSTRAINT chk_business_display_reservations
        CHECK (reservations IS NULL OR reservations IN (0, 1)),
    CONSTRAINT chk_business_display_outdoor
        CHECK (outdoor_seating IS NULL OR outdoor_seating IN (0, 1)),
    CONSTRAINT chk_business_display_wheelchair
        CHECK (wheelchair_accessible IS NULL OR wheelchair_accessible IN (0, 1)),
    CONSTRAINT chk_business_display_source
        CHECK (source_type = 'yelp_open_dataset')
) ENGINE=InnoDB;
