from __future__ import annotations

import pytest

from dhruva.geo.local_boundaries import BoundaryDistance, nearest_boundaries


def test_bundled_data_file_loads_real_features():
    results = nearest_boundaries(9.9658, 76.2367)  # Kochi
    assert len(results) > 0


def test_dhanushkodi_is_close_to_the_india_sri_lanka_line():
    # Dhanushkodi, Tamil Nadu — a few nm from the IMBL by construction.
    # Straight baselines are excluded by default: they hug every coastline
    # and would trivially "win" as nearest without being navigationally
    # meaningful (see local_boundaries.py's _NAVIGATIONALLY_RELEVANT_EXCLUDES).
    results = nearest_boundaries(9.15, 79.45, limit=1)
    assert len(results) == 1
    nearest = results[0]
    assert nearest.distance_nm < 60  # generously loose; the real point is only a few nm off
    assert "Sri Lanka" in (nearest.territory1 or "") or "Sri Lanka" in (nearest.territory2 or "")


def test_kochi_is_farther_from_the_india_sri_lanka_line_than_dhanushkodi():
    kochi = nearest_boundaries(9.9658, 76.2367, limit=1)[0]
    dhanushkodi = nearest_boundaries(9.15, 79.45, limit=1)[0]
    assert kochi.distance_m > dhanushkodi.distance_m


def test_straight_baselines_excluded_by_default_but_available_on_request():
    without = nearest_boundaries(9.9658, 76.2367, limit=1)
    with_baselines = nearest_boundaries(9.9658, 76.2367, limit=1, include_baselines=True)
    assert without[0].line_type != "straight_baseline"
    assert with_baselines[0].line_type == "straight_baseline"  # nearest to any coastal point
    assert with_baselines[0].distance_m < without[0].distance_m


def test_results_are_sorted_nearest_first():
    results = nearest_boundaries(9.15, 79.45, limit=5)
    distances = [r.distance_m for r in results]
    assert distances == sorted(distances)


def test_boundary_distance_cannot_be_constructed_as_non_indicative():
    with pytest.raises(ValueError, match="indicative"):
        BoundaryDistance(
            name="x", line_type="imbl", territory1="India", territory2="Sri Lanka",
            distance_m=1000.0, indicative=False, source_url=None,
        )
