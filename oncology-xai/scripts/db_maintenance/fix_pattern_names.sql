-- Fix choquet_shapley_values JSONB
UPDATE genetic_results 
SET choquet_shapley_values = 
  replace(replace(replace(replace(replace(replace(
    replace(replace(replace(replace(replace(replace(
      choquet_shapley_values::text,
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
WHERE choquet_shapley_values IS NOT NULL;

-- Fix choquet_interaction_indices JSONB
UPDATE genetic_results 
SET choquet_interaction_indices = 
  replace(replace(replace(replace(replace(replace(
    replace(replace(replace(replace(replace(replace(
      choquet_interaction_indices::text,
      'acinar', '_MP'),
      'lepidic', '_CR'),
      'micropapillary', '_PA'),
      'mucinous', '_LE'),
      'papillary', '_SO'),
      'solid', '_AC'),
    '_MP', 'micropapillary'),
    '_CR', 'cribriform'),
    '_PA', 'papillary'),
    '_LE', 'lepidic'),
    '_SO', 'solid'),
    '_AC', 'acinar')::jsonb
WHERE choquet_interaction_indices IS NOT NULL;

-- Fix shap_top_patterns JSONB  
UPDATE genetic_results 
SET shap_top_patterns = 
  replace(replace(replace(replace(replace(replace(
    replace(replace(replace(replace(replace(replace(
      shap_top_patterns::text,
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
WHERE shap_top_patterns IS NOT NULL;
