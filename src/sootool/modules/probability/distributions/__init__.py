"""Probability distributions (normal, binomial, poisson, gamma, beta, exponential, lognormal, chi-square, F).

Importing this package registers every distribution tool in REGISTRY.
"""
from __future__ import annotations

from sootool.modules.probability.distributions import (  # noqa: F401
    beta_family,
    discrete,
    gamma_family,
    lognormal,
    normal,
)
from sootool.modules.probability.distributions._common import (  # noqa: F401
    _SIG_DIGITS,
    _dist_result,
    _parse_float,
    _parse_prob,
    _parse_quantile,
    _validate_non_negative_int,
    _validate_nonneg_float,
    _validate_positive_float,
    stats,
)
from sootool.modules.probability.distributions.beta_family import (  # noqa: F401
    beta_cdf,
    beta_pdf,
    beta_ppf,
    f_cdf,
    f_pdf,
    f_ppf,
)
from sootool.modules.probability.distributions.discrete import (  # noqa: F401
    binomial_cdf,
    binomial_pmf,
    poisson_cdf,
    poisson_pmf,
)
from sootool.modules.probability.distributions.gamma_family import (  # noqa: F401
    chi_square_cdf,
    chi_square_pdf,
    chi_square_ppf,
    exponential_cdf,
    exponential_pdf,
    exponential_ppf,
    gamma_cdf,
    gamma_pdf,
    gamma_ppf,
)
from sootool.modules.probability.distributions.lognormal import (  # noqa: F401
    lognormal_cdf,
    lognormal_pdf,
    lognormal_ppf,
)
from sootool.modules.probability.distributions.normal import (  # noqa: F401
    normal_cdf,
    normal_pdf,
    normal_ppf,
)
