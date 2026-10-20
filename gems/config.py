"""Constants. Every value states its source.

Sources (verified in this session unless marked otherwise):
- CRS EPSG:32611 = "WGS 84 / UTM zone 11N": checked with pyproj 3.7.2 (PROJ 9.5.1) database.
- Shape (3730, 3292) and 100 m resolution: printed by the GEMS reference notebook
  (drivendataorg/gems-prize-reference-solution, unet-mc-cv-reference-solution.ipynb, cells 5-6).
- alpha=0.2, beta=0.8, 300 m triangular tolerance: stated in the project brief (user-supplied).
  The official scoring text (GEMS_96647.pdf) was NOT reachable from the sandbox; see docs/SOURCES.md.
"""

EXPECTED_CRS = "EPSG:32611"
EXPECTED_RES_M = 100.0
EXPECTED_SHAPE = (3730, 3292)  # (height, width) from the reference notebook output
N_FEATURE_BANDS = 19           # reference notebook prints Band 1..19 for the feature file

TVERSKY_ALPHA = 0.2            # weight on false positives
TVERSKY_BETA = 0.8             # weight on false negatives
TOLERANCE_M = 300.0            # triangular kernel radius used in the pooled DTI

NODATA_FLOOR = -1e38           # feature nodata in reference is -3.4028e38
DEFAULT_BUFFER_M = 1000.0      # ASSUMPTION: exclusion buffer around withheld segments
DEFAULT_FOLDS = 5              # spatial stripes used for hide-and-recover
DEFAULT_SEED = 0
LEAKAGE_AUC_LIMIT = 0.90       # brief: AUC above 0.90 = leakage until proven otherwise
EVALUATOR_VERSION = "holdout-dti-0.1.0"
