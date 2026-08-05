-- Preserve cancelled scheduled registrations without exposing them in active admin tabs.
ALTER TABLE business_sponsorships
    DROP CHECK chk_sponsorship_status;

ALTER TABLE business_sponsorships
    ADD CONSTRAINT chk_sponsorship_status
    CHECK (status IN ('scheduled', 'active', 'expired', 'cancelled'));
