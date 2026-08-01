-- Per-reviewer selection-year radius joined to its region, restricted to
-- rows where a radius could actually be computed (radius_available=1 —
-- excludes reviewers with 0 or 1 spatially-located business in that
-- period). Quartile/median math happens in the API service layer (Python),
-- not here — MySQL 8 has no built-in PERCENTILE_CONT, and this keeps the
-- view a plain row-level join instead of an approximation.
CREATE OR REPLACE VIEW vw_reviewer_regional_radius AS
SELECT
    summary.model_version,
    summary.sample_id,
    region.state,
    summary.p90_radius_km
-- "spatial" is a MySQL 8 reserved word (spatial indexes/types), so the
-- table alias avoids it even though the table name itself is fine.
FROM reviewer_spatial_summary AS summary
JOIN reviewer_region AS region
  ON region.model_version = summary.model_version
 AND region.sample_id = summary.sample_id
WHERE summary.period_type = 'selection'
  AND summary.radius_available = 1;
