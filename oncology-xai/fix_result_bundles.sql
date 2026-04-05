-- Fix predominant_pattern column
UPDATE result_bundles SET predominant_pattern = 'micropapillary' WHERE predominant_pattern = 'acinar';
UPDATE result_bundles SET predominant_pattern = 'cribriform' WHERE predominant_pattern = 'lepidic';
UPDATE result_bundles SET predominant_pattern = 'papillary_tmp' WHERE predominant_pattern = 'micropapillary';
UPDATE result_bundles SET predominant_pattern = 'lepidic' WHERE predominant_pattern = 'mucinous';
UPDATE result_bundles SET predominant_pattern = 'solid' WHERE predominant_pattern = 'papillary';
UPDATE result_bundles SET predominant_pattern = 'acinar' WHERE predominant_pattern = 'solid';
UPDATE result_bundles SET predominant_pattern = 'papillary' WHERE predominant_pattern = 'papillary_tmp';

-- Fix pattern_composition JSONB
UPDATE result_bundles 
SET pattern_composition = 
  replace(replace(replace(replace(replace(replace(
    replace(replace(replace(replace(replace(replace(
      pattern_composition::text,
      '"acinar"', '"_MP"'),
      '"lepidic"', '"_CR"'),
      '"micropapillary"', '"_PA"'),
      '"mucinous"', '"_LE"'),
      '"papillary"', '"_SO"'),
      '"solid"', '"_AC"'),
    '"_MP"', '"micropapillary"'),
    '"_CR"', '"cribriform"'),
    '"_PA"', '"papillary"'),
    '"_LE"', '"lepidic"'),
    '"_SO"', '"solid"'),
    '"_AC"', '"acinar"')::jsonb
WHERE pattern_composition IS NOT NULL;

-- Fix summary_json (contains text with pattern names)
UPDATE result_bundles 
SET summary_json = 
  replace(replace(replace(replace(replace(replace(
    replace(replace(replace(replace(replace(replace(
      summary_json::text,
      '"acinar"', '"_MP"'),
      '"lepidic"', '"_CR"'),
      '"micropapillary"', '"_PA"'),
      '"mucinous"', '"_LE"'),
      '"papillary"', '"_SO"'),
      '"solid"', '"_AC"'),
    '"_MP"', '"micropapillary"'),
    '"_CR"', '"cribriform"'),
    '"_PA"', '"papillary"'),
    '"_LE"', '"lepidic"'),
    '"_SO"', '"solid"'),
    '"_AC"', '"acinar"')::jsonb
WHERE summary_json IS NOT NULL;
