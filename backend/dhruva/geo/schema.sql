-- Maritime boundaries and zones.
--
-- Every row carries `indicative` and it is CHECKed true, not merely defaulted.
-- Marine Regions publishes these as a best-available compilation, not as legal
-- delimitations, and DHRUVA renders a boundary next to a warning that can send a
-- boat one way or the other. Making the column unfalsifiable means no later
-- migration, import or well-meaning UPDATE can quietly promote one of these
-- lines to authoritative.

CREATE EXTENSION IF NOT EXISTS postgis;

-- ---------------------------------------------------------------- lines ----
-- EEZ boundaries, including the India-Sri Lanka IMBL the drift warning is
-- measured against.
CREATE TABLE IF NOT EXISTS boundary_line (
    id           bigserial PRIMARY KEY,
    line_id      integer,
    name         text,
    line_type    text,
    territory1   text,
    territory2   text,
    sovereign1   text,
    sovereign2   text,
    length_km    double precision,
    indicative   boolean NOT NULL DEFAULT true,
    source_name  text,
    source_url   text,
    doc_date     text,
    fetched_at   timestamptz NOT NULL DEFAULT now(),
    geom         geometry(MultiLineString, 4326) NOT NULL,
    CONSTRAINT boundary_line_is_indicative CHECK (indicative),
    CONSTRAINT boundary_line_unique UNIQUE (line_id)
);

CREATE INDEX IF NOT EXISTS boundary_line_geom_gist ON boundary_line USING GIST (geom);
CREATE INDEX IF NOT EXISTS boundary_line_geog_gist
    ON boundary_line USING GIST (CAST(geom AS geography));
CREATE INDEX IF NOT EXISTS boundary_line_type_idx ON boundary_line (line_type);

-- ---------------------------------------------------------------- zones ----
-- EEZ / territorial-sea polygons, and marine protected or closed areas.
CREATE TABLE IF NOT EXISTS maritime_zone (
    id           bigserial PRIMARY KEY,
    mrgid        integer,
    name         text,
    zone_type    text NOT NULL,
    territory    text,
    sovereign    text,
    iso_ter      text,
    indicative   boolean NOT NULL DEFAULT true,
    source_name  text,
    source_url   text,
    fetched_at   timestamptz NOT NULL DEFAULT now(),
    geom         geometry(MultiPolygon, 4326) NOT NULL,
    CONSTRAINT maritime_zone_is_indicative CHECK (indicative),
    CONSTRAINT maritime_zone_kind CHECK (
        zone_type IN ('internal_waters', 'territorial_sea_12nm', 'contiguous_24nm',
                      'eez', 'mpa', 'closed')
    ),
    CONSTRAINT maritime_zone_unique UNIQUE (mrgid, zone_type)
);

CREATE INDEX IF NOT EXISTS maritime_zone_geom_gist ON maritime_zone USING GIST (geom);
CREATE INDEX IF NOT EXISTS maritime_zone_geog_gist
    ON maritime_zone USING GIST (CAST(geom AS geography));
CREATE INDEX IF NOT EXISTS maritime_zone_type_idx ON maritime_zone (zone_type);

-- ------------------------------------------------------------------ pfz ----
-- INCOIS potential fishing zone advisories. There is no API; these are scraped,
-- so source_url and fetched_at are NOT NULL — a PFZ line with no attribution
-- must be impossible to store.
CREATE TABLE IF NOT EXISTS pfz_advisory (
    id            bigserial PRIMARY KEY,
    issued_for    date NOT NULL,
    region        text,
    landing_centre text,
    bearing_deg   double precision,
    distance_nm   double precision,
    depth_m       double precision,
    valid_until   timestamptz,
    source_url    text NOT NULL,
    source_name   text NOT NULL DEFAULT 'INCOIS PFZ advisory (scraped)',
    fetched_at    timestamptz NOT NULL DEFAULT now(),
    raw           jsonb,
    geom          geometry(Point, 4326),
    CONSTRAINT pfz_attribution_present CHECK (length(source_url) > 0)
);

CREATE INDEX IF NOT EXISTS pfz_geom_gist ON pfz_advisory USING GIST (geom);
CREATE INDEX IF NOT EXISTS pfz_issued_idx ON pfz_advisory (issued_for DESC);
