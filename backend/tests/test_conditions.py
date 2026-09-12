"""conditions_at is Gate 2. These tests run against stub adapters, so they pin
the assembly rules rather than the weather: which source wins, what happens when
one dies, and that a non-finite reading can never reach a person."""

import datetime as dt

import pytest
from pydantic import ValidationError

from dhruva.sources.base import FetchError, FetchOutcome, Observation
from dhruva.sources.conditions import conditions_at
from dhruva.sources.registry import (
    AuthKind,
    DatasetEntry,
    Registry,
    SourceKind,
    SpatialExtent,
    TemporalExtent,
    Variable,
    VariableSpec,
)

NOW = dt.datetime(2026, 9, 12, 12, 0, tzinfo=dt.UTC)
LAT, LON = 11.05, 79.85
BOX = SpatialExtent(lat_min=6, lat_max=24, lon_min=66, lon_max=94, grid_resolution_deg=0.083)


def _entry(ident: str, variables: list[Variable], latency: float) -> DatasetEntry:
    return DatasetEntry(
        id=ident,
        title=ident,
        source=SourceKind.OPEN_METEO,
        dataset_id=f"up-{ident}",
        endpoint="https://example.invalid",
        auth=AuthKind.NONE,
        latency_hours=latency,
        variables={
            v: VariableSpec(native_name=v.value, native_unit="x", unit="x") for v in variables
        },
        spatial=BOX,
        temporal=TemporalExtent(
            coverage_start=dt.datetime(2020, 1, 1, tzinfo=dt.UTC), cadence="PT1H"
        ),
    )


def _obs(ident: str, var: Variable, value: float) -> Observation:
    return Observation(
        variable=var,
        value=value,
        unit="x",
        dataset_id=ident,
        upstream_dataset_id=f"up-{ident}",
        valid_time=NOW,
        cell_lat=LAT,
        cell_lon=LON,
        requested_lat=LAT,
        requested_lon=LON,
        grid_resolution_deg=0.083,
        fetched_at=NOW,
    )


class StubAdapter:
    """Returns whatever it was told to, per dataset id."""

    def __init__(
        self,
        values: dict[str, dict[Variable, float]],
        dead: set[str] | None = None,
        explodes: set[str] | None = None,
    ) -> None:
        self.values = values
        self.dead = dead or set()
        self.explodes = explodes or set()
        self.calls: list[tuple[str, tuple[Variable, ...]]] = []

    async def fetch(self, entry, variables, lat, lon, when):
        self.calls.append((entry.id, tuple(variables)))
        if entry.id in self.explodes:
            raise RuntimeError("adapter bug")
        if entry.id in self.dead:
            return FetchOutcome(errors=[FetchError(dataset_id=entry.id, error="provider down")])
        got = self.values.get(entry.id, {})
        return FetchOutcome(observations=[_obs(entry.id, v, got[v]) for v in variables if v in got])


async def _run(registry, adapter, variables):
    return await conditions_at(
        LAT,
        LON,
        NOW,
        registry=registry,
        adapters={SourceKind.OPEN_METEO: adapter},
        variables=variables,
    )


class TestSourceSelection:
    async def test_lower_latency_becomes_primary_and_the_other_a_cross_check(self):
        reg = Registry(
            datasets=[_entry("slow", [Variable.SST], 10), _entry("fast", [Variable.SST], 1)]
        )
        stub = StubAdapter({"fast": {Variable.SST: 30.6}, "slow": {Variable.SST: 30.5}})
        c = await _run(reg, stub, (Variable.SST,))
        assert c.primary[Variable.SST].dataset_id == "fast"
        assert [o.dataset_id for o in c.cross_checks] == ["slow"]

    async def test_each_dataset_is_fetched_once_with_all_its_variables(self):
        """Asking for three variables one source serves must cost one call."""
        reg = Registry(
            datasets=[_entry("multi", [Variable.SST, Variable.WAVE_HEIGHT, Variable.WIND_SPEED], 1)]
        )
        stub = StubAdapter(
            {"multi": {Variable.SST: 30.0, Variable.WAVE_HEIGHT: 1.0, Variable.WIND_SPEED: 10.0}}
        )
        await _run(reg, stub, (Variable.SST, Variable.WAVE_HEIGHT, Variable.WIND_SPEED))
        assert len(stub.calls) == 1
        assert set(stub.calls[0][1]) == {Variable.SST, Variable.WAVE_HEIGHT, Variable.WIND_SPEED}

    async def test_a_variable_no_source_covers_is_reported_not_invented(self):
        reg = Registry(datasets=[_entry("a", [Variable.SST], 1)])
        c = await _run(
            reg, StubAdapter({"a": {Variable.SST: 30.0}}), (Variable.SST, Variable.CHLOROPHYLL)
        )
        assert c.value(Variable.CHLOROPHYLL) is None
        assert Variable.CHLOROPHYLL in c.missing
        assert any(e.variable is Variable.CHLOROPHYLL for e in c.errors)


class TestDegradation:
    async def test_a_dead_provider_falls_through_to_the_next(self):
        reg = Registry(
            datasets=[_entry("fast", [Variable.SST], 1), _entry("slow", [Variable.SST], 9)]
        )
        stub = StubAdapter({"slow": {Variable.SST: 30.5}}, dead={"fast"})
        c = await _run(reg, stub, (Variable.SST,))
        assert c.primary[Variable.SST].dataset_id == "slow"
        assert any(e.dataset_id == "fast" for e in c.errors)

    async def test_one_dead_provider_does_not_lose_other_variables(self):
        reg = Registry(
            datasets=[_entry("a", [Variable.SST], 1), _entry("b", [Variable.WAVE_HEIGHT], 1)]
        )
        stub = StubAdapter({"b": {Variable.WAVE_HEIGHT: 2.5}}, dead={"a"})
        c = await _run(reg, stub, (Variable.SST, Variable.WAVE_HEIGHT))
        assert c.value(Variable.WAVE_HEIGHT) == 2.5
        assert c.value(Variable.SST) is None

    async def test_an_adapter_that_raises_is_contained(self):
        """A bug in one adapter must not take the whole answer with it."""
        reg = Registry(
            datasets=[_entry("boom", [Variable.SST], 1), _entry("ok", [Variable.WAVE_HEIGHT], 1)]
        )
        stub = StubAdapter({"ok": {Variable.WAVE_HEIGHT: 1.2}}, explodes={"boom"})
        c = await _run(reg, stub, (Variable.SST, Variable.WAVE_HEIGHT))
        assert c.value(Variable.WAVE_HEIGHT) == 1.2
        assert any("RuntimeError" in e.error for e in c.errors)

    async def test_a_source_kind_with_no_adapter_is_an_error_not_a_crash(self):
        entry = _entry("erd", [Variable.SST], 1).model_copy(update={"source": SourceKind.ERDDAP})
        c = await conditions_at(
            LAT,
            LON,
            NOW,
            registry=Registry(datasets=[entry]),
            adapters={},
            variables=(Variable.SST,),
        )
        assert c.value(Variable.SST) is None
        assert any("no adapter" in e.error for e in c.errors)


class TestDisagreement:
    async def test_agreement_within_tolerance_is_not_flagged(self):
        reg = Registry(datasets=[_entry("a", [Variable.SST], 1), _entry("b", [Variable.SST], 5)])
        stub = StubAdapter({"a": {Variable.SST: 30.60}, "b": {Variable.SST: 30.56}})
        c = await _run(reg, stub, (Variable.SST,))
        assert c.disagreements() == []

    async def test_a_real_split_is_flagged(self):
        reg = Registry(datasets=[_entry("a", [Variable.SST], 1), _entry("b", [Variable.SST], 5)])
        stub = StubAdapter({"a": {Variable.SST: 30.6}, "b": {Variable.SST: 26.0}})
        c = await _run(reg, stub, (Variable.SST,))
        found = c.disagreements()
        assert len(found) == 1
        assert found[0].delta == pytest.approx(4.6)

    async def test_directions_compare_the_short_way_round_the_compass(self):
        """350 and 010 are 20 degrees apart, not 340. Getting this wrong would
        flag every northerly wind as a disagreement."""
        reg = Registry(
            datasets=[
                _entry("a", [Variable.WIND_DIRECTION], 1),
                _entry("b", [Variable.WIND_DIRECTION], 5),
            ]
        )
        stub = StubAdapter(
            {"a": {Variable.WIND_DIRECTION: 350.0}, "b": {Variable.WIND_DIRECTION: 10.0}}
        )
        c = await _run(reg, stub, (Variable.WIND_DIRECTION,))
        assert c.disagreements() == []


class TestNonFiniteValues:
    def test_an_observation_cannot_hold_nan(self):
        """Ocean models fill land cells with NaN. A wave height reading "nan" is
        the exact failure the numeric firewall exists to prevent."""
        with pytest.raises(ValidationError):
            _obs("d", Variable.WAVE_HEIGHT, float("nan"))

    def test_an_observation_cannot_hold_infinity(self):
        with pytest.raises(ValidationError):
            _obs("d", Variable.WAVE_HEIGHT, float("inf"))


class TestResultShape:
    async def test_every_value_carries_units_a_timestamp_and_a_cell(self):
        reg = Registry(datasets=[_entry("a", [Variable.SST], 1)])
        c = await _run(reg, StubAdapter({"a": {Variable.SST: 30.0}}), (Variable.SST,))
        o = c.primary[Variable.SST]
        assert o.unit and o.valid_time and o.dataset_id
        assert (o.cell_lat, o.cell_lon) == (LAT, LON)

    async def test_the_advisory_notice_is_always_present(self):
        reg = Registry(datasets=[_entry("a", [Variable.SST], 1)])
        c = await _run(reg, StubAdapter({"a": {Variable.SST: 30.0}}), (Variable.SST,))
        assert "INCOIS" in c.notice and "IMD" in c.notice
