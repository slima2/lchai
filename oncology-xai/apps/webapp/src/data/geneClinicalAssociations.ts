/**
 * Condensed “Gene–pattern–treatment” rows aligned with the thesis integrated
 * reference table (Chapter 3, Table `tab:gene_unified` in `ch03_usecase_data.tex`).
 *
 * The thesis gives full prose, mechanisms, prevalence, and bibliography
 * (e.g. Leighl et al.; Shim et al.; Yoshizawa et al.; Skoulidis et al.; TCGA).
 * This copy is for UI orientation only—not a substitute for NCCN / product labels.
 */
export const GENE_CLINICAL_ASSOC_THESIS_REF =
  'Thesis Ch. 3, Table “Integrated gene reference” (\\label{tab:gene_unified}); see thesis bibliography for primary sources.';

export type GeneClinicalRow = {
  gene: string;
  patternAssociation: string;
  treatmentImplications: string;
  /** Short pointer to thesis text / typical citations (for tooltips / docs). */
  citationNote: string;
};

export const GENE_CLINICAL_ASSOC_ROWS: readonly GeneClinicalRow[] = [
  {
    gene: 'TP53',
    patternAssociation: 'Solid, micropapillary',
    treatmentImplications:
      'No targeted therapy; immunotherapy (e.g. pembrolizumab, nivolumab) may benefit in selected cases; chemotherapy standard',
    citationNote: 'Thesis Table tab:gene_unified; Leighl et al. (TP53 morphology)',
  },
  {
    gene: 'EGFR',
    patternAssociation: 'Lepidic, papillary',
    treatmentImplications:
      'Osimertinib (3rd-gen TKI), erlotinib, gefitinib, afatinib (per guideline)',
    citationNote: 'Thesis Table tab:gene_unified; Yoshizawa et al. (EGFR morphology)',
  },
  {
    gene: 'KRAS',
    patternAssociation: 'Mucinous invasive (IMA), solid',
    treatmentImplications: 'Sotorasib, adagrasib (G12C-specific); no approved targeted therapy for all KRAS variants',
    citationNote: 'Thesis Table tab:gene_unified; Shim et al. (KRAS / IMA morphology)',
  },
  {
    gene: 'STK11',
    patternAssociation: 'Variable (immune-cold microenvironment)',
    treatmentImplications: 'May predict resistance to PD-1/PD-L1 immunotherapy; no approved targeted monotherapy',
    citationNote: 'Thesis Table tab:gene_unified; Skoulidis et al. (STK11 / immune)',
  },
  {
    gene: 'KEAP1',
    patternAssociation: 'Diffuse (no single dominant pattern)',
    treatmentImplications: 'NRF2 pathway context; concurrent mutations affect IO response (trials)',
    citationNote: 'Thesis Table tab:gene_unified; TCGA LUAD; thesis text',
  },
  {
    gene: 'RBM10',
    patternAssociation: 'Variable (no established dominant pattern)',
    treatmentImplications: 'No approved targeted therapy; research-stage / splicing biology',
    citationNote: 'Thesis Table tab:gene_unified; TCGA LUAD',
  },
] as const;

export function clinicalAssocForGene(gene: string): GeneClinicalRow | undefined {
  return GENE_CLINICAL_ASSOC_ROWS.find((r) => r.gene === gene);
}
