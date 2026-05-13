"""NAICS -> SOC code mapping and average job-hours data.

Maps service NAICS codes to primary BLS occupation codes (SOC)
and stores average job duration estimates for ACV calculation.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ServiceOccupation:
    naics: str
    soc: str
    label: str
    avg_job_hours: float
    overhead_multiplier: float = 2.0


NAICS_SOC_MAP: dict[str, ServiceOccupation] = {
    "238220": ServiceOccupation(
        naics="238220", soc="472152",
        label="Plumbing contractors -> Plumbers",
        avg_job_hours=3.0,
    ),
    "238210": ServiceOccupation(
        naics="238210", soc="472111",
        label="Electrical contractors -> Electricians",
        avg_job_hours=2.5,
    ),
    "238160": ServiceOccupation(
        naics="238160", soc="472181",
        label="Roofing contractors -> Roofers",
        avg_job_hours=8.0,
    ),
    "561730": ServiceOccupation(
        naics="561730", soc="372012",
        label="Landscaping -> Landscaping workers",
        avg_job_hours=2.0,
    ),
    "561720": ServiceOccupation(
        naics="561720", soc="372012",
        label="Janitorial -> Janitors",
        avg_job_hours=2.0,
        overhead_multiplier=1.5,
    ),
    "238140": ServiceOccupation(
        naics="238140", soc="472031",
        label="Masonry contractors -> Masons",
        avg_job_hours=6.0,
    ),
    "238330": ServiceOccupation(
        naics="238330", soc="472044",
        label="Flooring contractors -> Tile setters",
        avg_job_hours=5.0,
    ),
    "238910": ServiceOccupation(
        naics="238910", soc="499071",
        label="Site preparation -> Maintenance workers",
        avg_job_hours=4.0,
    ),
}


def get_soc_for_naics(naics: str) -> ServiceOccupation | None:
    return NAICS_SOC_MAP.get(naics)


def compute_acv(
    mean_hourly_wage: float,
    avg_job_hours: float,
    overhead_multiplier: float = 2.0,
) -> float:
    """ACV = mean_hourly_wage x avg_job_hours x overhead_multiplier."""
    return mean_hourly_wage * avg_job_hours * overhead_multiplier
