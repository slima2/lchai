-- Fix predominant_pattern with a single CASE statement to avoid cascading
UPDATE result_bundles SET predominant_pattern = CASE predominant_pattern
    WHEN 'micropapillary' THEN 'acinar_REAL'
    WHEN 'papillary' THEN 'micropapillary_REAL'
    ELSE predominant_pattern
END;

-- Now the ones that were already correctly remapped need fixing too
-- Current state after the botched sequential update:
-- "acinar" originals became "papillary" (wrong cascade)
-- Need to recalculate from pattern_composition

UPDATE result_bundles 
SET predominant_pattern = (
    SELECT key FROM (
        SELECT key, value::float as val 
        FROM jsonb_each_text(pattern_composition)
    ) sub 
    ORDER BY val DESC 
    LIMIT 1
)
WHERE pattern_composition IS NOT NULL;
