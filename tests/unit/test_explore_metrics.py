from src.domain.explore.metrics import (
    annualized_growth,
    business_density_per_1k,
    weighted_establishments,
)


def test_weighted_establishments_uses_mapping_weights() -> None:
    cbp_rows = [
        {"naics_code": "238160", "est": 100},
        {"naics_code": "238220", "est": 40},
        {"naics_code": "999999", "est": 999},
    ]
    weights = {"238160": 1.0, "238220": 0.5}

    assert weighted_establishments(cbp_rows, weights) == 120.0


def test_business_density_per_1k_returns_null_without_population() -> None:
    assert business_density_per_1k(100, None) is None
    assert business_density_per_1k(100, 0) is None


def test_business_density_per_1k_scales_for_table_readability() -> None:
    assert business_density_per_1k(250, 100_000) == 2.5


def test_annualized_growth_returns_null_without_prior() -> None:
    assert annualized_growth(latest=120, prior=0, year_span=5) is None
    assert annualized_growth(latest=120, prior=None, year_span=5) is None


def test_annualized_growth_uses_year_span() -> None:
    assert annualized_growth(latest=121, prior=100, year_span=2) == 0.1
