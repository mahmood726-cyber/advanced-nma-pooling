"""nma_pool package."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("nma-pool")
except PackageNotFoundError:  # pragma: no cover
    __version__ = "0.1.1"

from .data.builder import DatasetBuilder, EvidenceDataset
from .models.bayesian_ml_nmr import BayesianMLNMRFitResult, BayesianMLNMRPooler
from .models.bayesian_bias_adjusted import (
    BayesianBiasAdjustedNMAFitResult,
    BayesianBiasAdjustedNMAPooler,
)
from .models.bias_adjusted import BiasAdjustedNMAFitResult, BiasAdjustedNMAPooler
from .models.ml_nmr import MLNMRFitResult, MLNMRPooler
from .models.core_ad import ADNMAPooler, NMAFitResult
from .models.spec import (
    BayesianMLNMRSpec,
    BayesianBiasAdjustedSpec,
    BiasAdjustedSpec,
    MLNMRSpec,
    ModelSpec,
    SurvivalNPHSpec,
)
from .models.survival_nph import SurvivalNPHFitResult, SurvivalNPHPooler

__all__ = [
    "ADNMAPooler",
    "BayesianMLNMRFitResult",
    "BayesianMLNMRPooler",
    "BayesianMLNMRSpec",
    "BayesianBiasAdjustedNMAFitResult",
    "BayesianBiasAdjustedNMAPooler",
    "BayesianBiasAdjustedSpec",
    "BiasAdjustedNMAFitResult",
    "BiasAdjustedNMAPooler",
    "BiasAdjustedSpec",
    "DatasetBuilder",
    "EvidenceDataset",
    "MLNMRFitResult",
    "MLNMRPooler",
    "MLNMRSpec",
    "ModelSpec",
    "NMAFitResult",
    "SurvivalNPHFitResult",
    "SurvivalNPHPooler",
    "SurvivalNPHSpec",
    "__version__",
]

