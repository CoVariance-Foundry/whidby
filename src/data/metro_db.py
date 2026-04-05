"""Metro database — static CBSA data mapped to DataForSEO location codes. (M1)

Provides the geographic backbone for all queries.
Spec reference: Algo Spec V1.1, §3.2-3.3, §15.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Sequence

from .regions import states_for_region

_SEED_PATH = Path(__file__).parent / "seed" / "cbsa_seed.json"


@dataclass
class Metro:
    """A single metropolitan statistical area."""

    cbsa_code: str
    cbsa_name: str
    state: str
    population: int
    principal_cities: list[str] = field(default_factory=list)
    dataforseo_location_codes: list[int] = field(default_factory=list)


class MetroDB:
    """In-memory metro database backed by a seed JSON file.

    Usage::

        db = MetroDB.from_seed()
        metros = db.expand_scope(scope="state", target="AZ", depth="standard")
    """

    def __init__(self, metros: list[Metro]) -> None:
        self._all = metros
        self._by_code: dict[str, Metro] = {m.cbsa_code: m for m in metros}

    # -- Factory -------------------------------------------------------------

    @classmethod
    def from_seed(cls, path: Path | None = None) -> MetroDB:
        """Load from the bundled seed JSON (or a custom path)."""
        src = path or _SEED_PATH
        with open(src) as f:
            raw = json.load(f)
        metros = [
            Metro(
                cbsa_code=r["cbsa_code"],
                cbsa_name=r["cbsa_name"],
                state=r["state"],
                population=r["population"],
                principal_cities=r.get("principal_cities", []),
                dataforseo_location_codes=r.get("dataforseo_location_codes", []),
            )
            for r in raw
        ]
        return cls(metros)

    # -- Public API ----------------------------------------------------------

    def expand_scope(
        self,
        scope: str,
        target: str | list[str],
        depth: str = "standard",
    ) -> list[Metro]:
        """Expand a geographic scope into a sorted list of metros.

        Args:
            scope: "state", "region", or "custom".
            target: State code, region name, or list of CBSA codes.
            depth: "standard" (top 20 by pop) or "deep" (all metros >= 50k pop).

        Returns:
            Metros sorted by population descending.
        """
        if scope == "state":
            assert isinstance(target, str)
            return self._by_state(target, depth)
        elif scope == "region":
            assert isinstance(target, str)
            return self._by_region(target, depth)
        elif scope == "custom":
            assert isinstance(target, (list, tuple))
            return self._by_codes(target)
        else:
            raise ValueError(f"Unknown scope '{scope}'. Use 'state', 'region', or 'custom'.")

    # -- Internal ------------------------------------------------------------

    def _by_state(self, state_code: str, depth: str) -> list[Metro]:
        matches = [m for m in self._all if m.state == state_code.upper()]
        return self._apply_depth(matches, depth)

    def _by_region(self, region_name: str, depth: str) -> list[Metro]:
        states = states_for_region(region_name)
        matches = [m for m in self._all if m.state in states]
        return self._apply_depth(matches, depth)

    def _by_codes(self, codes: Sequence[str]) -> list[Metro]:
        result = [self._by_code[c] for c in codes if c in self._by_code]
        return sorted(result, key=lambda m: m.population, reverse=True)

    @staticmethod
    def _apply_depth(metros: list[Metro], depth: str) -> list[Metro]:
        sorted_metros = sorted(metros, key=lambda m: m.population, reverse=True)
        if depth == "deep":
            return [m for m in sorted_metros if m.population >= 50_000]
        # standard — top 20
        return sorted_metros[:20]
