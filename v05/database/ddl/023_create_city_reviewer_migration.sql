CREATE TABLE IF NOT EXISTS city_reviewer_migration (
    model_version VARCHAR(16) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
    selection_year SMALLINT UNSIGNED NOT NULL,
    state VARCHAR(8) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
    city_key VARCHAR(128) NOT NULL,
    city VARCHAR(128) NOT NULL,
    outflow_count INT UNSIGNED NOT NULL,
    inflow_count INT UNSIGNED NOT NULL,
    net_migration INT NOT NULL,
    loaded_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    PRIMARY KEY (model_version, selection_year, state, city_key),
    KEY idx_city_migration_location (model_version, state, city_key, selection_year),
    CONSTRAINT fk_city_migration_model
        FOREIGN KEY (model_version)
        REFERENCES model_versions (model_version),
    CONSTRAINT chk_city_migration_outflow CHECK (outflow_count >= 0),
    CONSTRAINT chk_city_migration_inflow CHECK (inflow_count >= 0)
) ENGINE=InnoDB;
