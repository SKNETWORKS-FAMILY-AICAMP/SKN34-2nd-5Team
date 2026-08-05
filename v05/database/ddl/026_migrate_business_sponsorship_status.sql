-- Apply after 025_create_business_sponsorships.sql.
-- Existing rows are classified from their current exposure dates.
ALTER TABLE business_sponsorships
    DROP CHECK chk_sponsorship_status;

UPDATE business_sponsorships
SET status = CASE
    WHEN end_date < CURDATE() THEN 'expired'
    WHEN start_date > CURDATE() THEN 'scheduled'
    ELSE 'active'
END;

ALTER TABLE business_sponsorships
    ADD CONSTRAINT chk_sponsorship_status
    CHECK (status IN ('scheduled', 'active', 'expired'));
