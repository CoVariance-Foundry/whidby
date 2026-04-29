-- 009_metros_and_census.sql
--
-- Promotes metros from a JSON seed (src/data/seed/cbsa_seed.json) to a real
-- Supabase table, extends with ACS demographic columns, and adds a CBP
-- establishment-counts table keyed by (cbsa_code, naics_code, year).
--
-- Source datasets:
--   - CBSA delineation file (Census, Sept 2023)
--   - ACS 5-year by CBSA (B01003 pop, B25003 tenure, B19013 income, B25035 yr built)
--   - CBP MSA-level (most recent vintage, NAICS-6 establishment counts)
--
-- Rationale: V2 scoring needs absolute, census-grounded benchmarks (per-capita
-- demand, real establishment counts) instead of cohort-relative percentiles.

-- ============================================================
-- 1. metros — promoted from JSON seed, extended with ACS data
-- ============================================================

CREATE TABLE IF NOT EXISTS public.metros (
    cbsa_code              TEXT PRIMARY KEY,
    cbsa_name              TEXT NOT NULL,
    state                  TEXT NOT NULL,                 -- primary state for the CBSA
    cbsa_type              TEXT,                          -- 'metro' or 'micro'
    population             INTEGER,                       -- ACS B01003_001E (most recent vintage)
    principal_cities       TEXT[] NOT NULL DEFAULT '{}',
    dataforseo_location_codes INTEGER[] NOT NULL DEFAULT '{}',

    -- ACS demographic extensions (5-year estimates, vintage tracked separately)
    households                     INTEGER,                -- ACS B25003_001E
    owner_occupied_housing_units   INTEGER,                -- ACS B25003_002E
    renter_occupied_housing_units  INTEGER,                -- ACS B25003_003E
    owner_occupancy_rate           NUMERIC(5,4),           -- derived: owner / total
    median_household_income_usd    INTEGER,                -- ACS B19013_001E
    median_year_structure_built    INTEGER,                -- ACS B25035_001E
    median_age_years               NUMERIC(4,1),           -- ACS B01002_001E
    acs_vintage                    INTEGER,                -- e.g., 2022 = ACS 2018-2022 5-yr
    acs_loaded_at                  TIMESTAMPTZ,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_metros_state ON public.metros(state);
CREATE INDEX IF NOT EXISTS idx_metros_population ON public.metros(population DESC);

-- ============================================================
-- 2. census_cbp_establishments — CBP NAICS-6 by metro
-- ============================================================
-- One row per (cbsa_code, naics_code, year). CBP suppresses small cells (D, S
-- flags); we keep est total + size-class buckets where available.

CREATE TABLE IF NOT EXISTS public.census_cbp_establishments (
    cbsa_code   TEXT NOT NULL REFERENCES public.metros(cbsa_code) ON DELETE CASCADE,
    naics_code  TEXT NOT NULL,                      -- 6-digit (or 2/4-digit roll-ups)
    naics_label TEXT,                               -- e.g., "Concrete contractors"
    year        INTEGER NOT NULL,                   -- CBP vintage (e.g., 2022)

    -- Establishment counts by size class (CBP standard buckets)
    est         INTEGER,                            -- total establishments
    n1_4        INTEGER,                            -- 1-4 employees
    n5_9        INTEGER,
    n10_19      INTEGER,
    n20_49      INTEGER,
    n50_99      INTEGER,
    n100_249    INTEGER,
    n250_499    INTEGER,
    n500_999    INTEGER,
    n1000       INTEGER,                            -- 1000+

    -- Optional: total employment + payroll if we pull them
    emp         INTEGER,
    ap          BIGINT,                             -- annual payroll (thousands of USD)

    -- Disclosure / quality flags from CBP
    empflag     TEXT,                               -- A, B, C, ... or NULL
    suppressed  BOOLEAN NOT NULL DEFAULT FALSE,

    loaded_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    PRIMARY KEY (cbsa_code, naics_code, year)
);

CREATE INDEX IF NOT EXISTS idx_cbp_naics ON public.census_cbp_establishments(naics_code);
CREATE INDEX IF NOT EXISTS idx_cbp_year ON public.census_cbp_establishments(year);

-- ============================================================
-- 3. census_target_naics — the rank-and-rent target NAICS list
-- ============================================================
-- Filter list used during CBP load + during niche → NAICS mapping at scoring time.

CREATE TABLE IF NOT EXISTS public.census_target_naics (
    naics_code  TEXT PRIMARY KEY,                   -- 6-digit
    label       TEXT NOT NULL,
    sector      TEXT,                               -- e.g., 'Construction', 'Other Services'
    niche_tags  TEXT[] NOT NULL DEFAULT '{}',       -- e.g., ['concrete','contractor','foundation']
    notes       TEXT
);

-- Seed the target NAICS (rank-and-rent niches Coral & co. actually target)
INSERT INTO public.census_target_naics (naics_code, label, sector, niche_tags) VALUES
    ('236115', 'New single-family housing construction (except for-sale builders)', 'Construction', ARRAY['home builder','custom home']),
    ('236118', 'Residential remodelers',                              'Construction', ARRAY['remodeling','renovation']),
    ('238110', 'Poured concrete foundation and structure contractors', 'Construction', ARRAY['concrete','foundation']),
    ('238130', 'Framing contractors',                                  'Construction', ARRAY['framing']),
    ('238140', 'Masonry contractors',                                  'Construction', ARRAY['masonry','brick','stone']),
    ('238150', 'Glass and glazing contractors',                        'Construction', ARRAY['glass','window install']),
    ('238160', 'Roofing contractors',                                  'Construction', ARRAY['roofing','roofer']),
    ('238170', 'Siding contractors',                                   'Construction', ARRAY['siding']),
    ('238210', 'Electrical contractors and other wiring installation', 'Construction', ARRAY['electrician','electrical']),
    ('238220', 'Plumbing, heating, and air-conditioning contractors',  'Construction', ARRAY['plumber','plumbing','hvac','heating','air conditioning']),
    ('238290', 'Other building equipment contractors',                 'Construction', ARRAY['elevator','garage door']),
    ('238310', 'Drywall and insulation contractors',                   'Construction', ARRAY['drywall','insulation']),
    ('238320', 'Painting and wall covering contractors',               'Construction', ARRAY['painter','painting']),
    ('238330', 'Flooring contractors',                                 'Construction', ARRAY['flooring','tile','hardwood']),
    ('238340', 'Tile and terrazzo contractors',                        'Construction', ARRAY['tile','tile contractor']),
    ('238350', 'Finish carpentry contractors',                         'Construction', ARRAY['carpenter','finish carpentry']),
    ('238910', 'Site preparation contractors',                         'Construction', ARRAY['excavation','grading']),
    ('238990', 'All other specialty trade contractors',                'Construction', ARRAY['fence','deck','pool builder']),
    ('541350', 'Building inspection services',                         'Professional', ARRAY['home inspector','inspection']),
    ('561210', 'Facilities support services',                          'Admin Support', ARRAY['property management']),
    ('561320', 'Temporary help services',                              'Admin Support', ARRAY['staffing']),
    ('561621', 'Security systems services (except locksmiths)',        'Admin Support', ARRAY['security','alarm','locksmith']),
    ('561622', 'Locksmiths',                                           'Admin Support', ARRAY['locksmith']),
    ('561720', 'Janitorial services',                                  'Admin Support', ARRAY['cleaning','janitorial','commercial cleaning']),
    ('561730', 'Landscaping services',                                 'Admin Support', ARRAY['landscaping','lawn care','tree service']),
    ('561740', 'Carpet and upholstery cleaning services',              'Admin Support', ARRAY['carpet cleaning','upholstery cleaning']),
    ('561790', 'Other services to buildings and dwellings',            'Admin Support', ARRAY['pressure washing','window cleaning','gutter cleaning']),
    ('562111', 'Solid waste collection',                               'Admin Support', ARRAY['junk removal','dumpster']),
    ('562910', 'Remediation services',                                 'Admin Support', ARRAY['water damage','mold remediation','restoration']),
    ('811111', 'General automotive repair',                            'Other Services', ARRAY['auto repair','mechanic']),
    ('811121', 'Automotive body, paint, and interior repair',          'Other Services', ARRAY['auto body','collision repair']),
    ('811122', 'Automotive glass replacement shops',                   'Other Services', ARRAY['auto glass']),
    ('811191', 'Automotive oil change and lubrication shops',          'Other Services', ARRAY['oil change']),
    ('811198', 'All other automotive repair and maintenance',          'Other Services', ARRAY['detailing','car wash']),
    ('811310', 'Commercial and industrial machinery and equipment repair', 'Other Services', ARRAY['equipment repair']),
    ('811411', 'Home and garden equipment repair',                     'Other Services', ARRAY['mower repair','small engine']),
    ('811412', 'Appliance repair',                                     'Other Services', ARRAY['appliance repair','refrigerator repair']),
    ('812320', 'Drycleaning and laundry services (except coin-operated)', 'Other Services', ARRAY['drycleaning','laundry']),
    ('812910', 'Pet care (except veterinary) services',                'Other Services', ARRAY['pet groomer','dog grooming','pet sitting']),
    ('812921', 'Photofinishing laboratories (except one-hour)',        'Other Services', ARRAY['photography services']),
    ('541921', 'Photography studios, portrait',                        'Professional', ARRAY['photographer','portrait']),
    ('541922', 'Commercial photography',                               'Professional', ARRAY['commercial photography']),
    ('611620', 'Sports and recreation instruction',                    'Education', ARRAY['music lessons','tennis','swim lessons']),
    ('611691', 'Exam preparation and tutoring',                        'Education', ARRAY['tutoring','test prep']),
    ('611699', 'All other miscellaneous schools and instruction',      'Education', ARRAY['driving school'])
ON CONFLICT (naics_code) DO UPDATE SET
    label      = EXCLUDED.label,
    sector     = EXCLUDED.sector,
    niche_tags = EXCLUDED.niche_tags;

-- ============================================================
-- 4. updated_at trigger for metros
-- ============================================================

CREATE OR REPLACE FUNCTION public.set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS metros_set_updated_at ON public.metros;
CREATE TRIGGER metros_set_updated_at
    BEFORE UPDATE ON public.metros
    FOR EACH ROW
    EXECUTE FUNCTION public.set_updated_at();

-- ============================================================
-- 5. RLS: read-only for authenticated, no public writes
-- ============================================================

ALTER TABLE public.metros ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.census_cbp_establishments ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.census_target_naics ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS metros_read_all ON public.metros;
CREATE POLICY metros_read_all ON public.metros FOR SELECT USING (true);

DROP POLICY IF EXISTS cbp_read_all ON public.census_cbp_establishments;
CREATE POLICY cbp_read_all ON public.census_cbp_establishments FOR SELECT USING (true);

DROP POLICY IF EXISTS naics_read_all ON public.census_target_naics;
CREATE POLICY naics_read_all ON public.census_target_naics FOR SELECT USING (true);

COMMENT ON TABLE public.metros IS
    'Reference table of CBSAs (Core-Based Statistical Areas). Promoted from cbsa_seed.json. Extended with ACS demographic data. Source of truth for geographic targeting in the scoring engine.';

COMMENT ON TABLE public.census_cbp_establishments IS
    'County Business Patterns establishment counts by NAICS-6 by CBSA by year. Source for V2 monetization scoring (real business density) and rank-and-rent suitability checks.';

COMMENT ON TABLE public.census_target_naics IS
    'Curated NAICS codes for rank-and-rent niches with niche_tags for keyword → NAICS mapping at scoring time.';
