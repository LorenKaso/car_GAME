CREATE TABLE game.users (
 id uuid PRIMARY KEY, email varchar(254) NOT NULL UNIQUE,
 password_hash text NOT NULL, email_verified_at timestamptz,
 is_active boolean NOT NULL DEFAULT true, created_at timestamptz NOT NULL DEFAULT now(),
 CHECK (email = lower(email))
);
CREATE TABLE game.profiles (
 id uuid PRIMARY KEY, user_id uuid NOT NULL UNIQUE REFERENCES game.users(id),
 username varchar(30) NOT NULL UNIQUE CHECK (username ~ '^[a-z][a-z0-9_]{2,29}$'),
 display_name varchar(60) NOT NULL CHECK (length(trim(display_name)) > 0),
 avatar_reference varchar(100), country varchar(2) CHECK (country ~ '^[A-Z]{2}$'),
 created_at timestamptz NOT NULL DEFAULT now(), updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE game.sessions (
 id uuid PRIMARY KEY, user_id uuid NOT NULL REFERENCES game.users(id),
 access_hash varchar(64) NOT NULL UNIQUE, refresh_hash varchar(64) NOT NULL UNIQUE,
 access_expires_at timestamptz NOT NULL, refresh_expires_at timestamptz NOT NULL,
 absolute_expires_at timestamptz NOT NULL, revoked_at timestamptz,
 created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX ix_sessions_user ON game.sessions(user_id);
CREATE TABLE game.used_refresh_tokens (
 token_hash varchar(64) PRIMARY KEY, session_id uuid NOT NULL REFERENCES game.sessions(id),
 used_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE game.account_tokens (
 id uuid PRIMARY KEY, user_id uuid NOT NULL REFERENCES game.users(id),
 purpose varchar(20) NOT NULL CHECK (purpose IN ('verify','reset')),
 token_hash varchar(64) NOT NULL UNIQUE, expires_at timestamptz NOT NULL, used_at timestamptz
);
CREATE INDEX ix_account_tokens_user ON game.account_tokens(user_id, purpose);
CREATE TABLE game.cars (
 id uuid PRIMARY KEY, code varchar(40) NOT NULL UNIQUE, name varchar(80) NOT NULL,
 manufacturer varchar(80) NOT NULL, model varchar(80) NOT NULL,
 base_top_speed_kph integer NOT NULL CHECK (base_top_speed_kph > 0),
 acceleration integer NOT NULL CHECK (acceleration BETWEEN 0 AND 100),
 handling integer NOT NULL CHECK (handling BETWEEN 0 AND 100),
 braking integer NOT NULL CHECK (braking BETWEEN 0 AND 100),
 boost integer NOT NULL CHECK (boost BETWEEN 0 AND 100),
 asset_identifier varchar(120) NOT NULL, is_starter boolean NOT NULL DEFAULT false,
 enabled boolean NOT NULL DEFAULT true
);
CREATE UNIQUE INDEX ix_one_starter_definition ON game.cars(is_starter) WHERE is_starter;
CREATE TABLE game.user_cars (
 id uuid PRIMARY KEY, user_id uuid NOT NULL REFERENCES game.users(id),
 car_id uuid NOT NULL REFERENCES game.cars(id), grant_type varchar(30) NOT NULL,
 is_selected boolean NOT NULL DEFAULT false, created_at timestamptz NOT NULL DEFAULT now()
);
CREATE UNIQUE INDEX ix_one_starter_per_user ON game.user_cars(user_id) WHERE grant_type='starter';
CREATE UNIQUE INDEX ix_one_selected_per_user ON game.user_cars(user_id) WHERE is_selected;
CREATE INDEX ix_user_cars_user ON game.user_cars(user_id);
CREATE TABLE game.level_curves (version integer PRIMARY KEY, name varchar(80) NOT NULL);
CREATE TABLE game.level_thresholds (
 curve_version integer NOT NULL REFERENCES game.level_curves(version),
 level integer NOT NULL CHECK (level >= 1), minimum_xp bigint NOT NULL CHECK (minimum_xp >= 0),
 PRIMARY KEY (curve_version, level), UNIQUE(curve_version, minimum_xp)
);
CREATE TABLE game.player_state (
 user_id uuid PRIMARY KEY REFERENCES game.users(id), coins bigint NOT NULL DEFAULT 0 CHECK(coins >= 0),
 xp bigint NOT NULL DEFAULT 0 CHECK(xp >= 0), curve_version integer NOT NULL REFERENCES game.level_curves(version),
 updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE game.economy_transactions (
 id uuid PRIMARY KEY, user_id uuid NOT NULL REFERENCES game.users(id), kind varchar(40) NOT NULL,
 coins_delta bigint NOT NULL, xp_delta bigint NOT NULL,
 reference_type varchar(40) NOT NULL, reference_id uuid NOT NULL,
 created_at timestamptz NOT NULL DEFAULT now(), UNIQUE(user_id, reference_type, reference_id)
);
CREATE INDEX ix_economy_history ON game.economy_transactions(user_id, created_at, id);
CREATE FUNCTION game.zero_opening_state() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF NEW.coins <> 0 OR NEW.xp <> 0 THEN RAISE EXCEPTION 'Opening balances must be zero'; END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER zero_opening BEFORE INSERT ON game.player_state FOR EACH ROW EXECUTE FUNCTION game.zero_opening_state();
CREATE FUNCTION game.apply_ledger_entry() RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER
 SET search_path = pg_catalog, game AS $$
BEGIN
 UPDATE game.player_state SET coins=coins+NEW.coins_delta, xp=xp+NEW.xp_delta,
 updated_at=now() WHERE user_id=NEW.user_id;
 IF NOT FOUND THEN RAISE EXCEPTION 'Player state missing'; END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER apply_economy AFTER INSERT ON game.economy_transactions FOR EACH ROW EXECUTE FUNCTION game.apply_ledger_entry();
CREATE FUNCTION game.immutable_ledger() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN RAISE EXCEPTION 'Economy history is append-only'; END $$;
CREATE TRIGGER immutable_economy BEFORE UPDATE OR DELETE ON game.economy_transactions
 FOR EACH ROW EXECUTE FUNCTION game.immutable_ledger();
REVOKE ALL ON FUNCTION game.apply_ledger_entry() FROM PUBLIC;
CREATE TABLE game.outbox_messages (
 id uuid PRIMARY KEY, payload_encrypted text, attempts integer NOT NULL DEFAULT 0,
 available_at timestamptz NOT NULL DEFAULT now(), expires_at timestamptz NOT NULL, sent_at timestamptz
);
CREATE INDEX ix_outbox_due ON game.outbox_messages(available_at) WHERE sent_at IS NULL;
CREATE TABLE game.rate_limits (
 key_hash varchar(64) NOT NULL, window_start bigint NOT NULL, hits integer NOT NULL,
 PRIMARY KEY(key_hash, window_start)
);
CREATE TABLE game.locations (
 id uuid PRIMARY KEY, slug varchar(60) NOT NULL UNIQUE, name varchar(80) NOT NULL,
 country varchar(2) NOT NULL, status varchar(20) NOT NULL CHECK(status IN ('planned','available')),
 center public.geography(POINT,4326)
);
CREATE INDEX ix_location_center ON game.locations USING gist(center);
CREATE TABLE game.race_zones (
 id uuid PRIMARY KEY, location_id uuid NOT NULL REFERENCES game.locations(id), name varchar(80) NOT NULL,
 status varchar(20) NOT NULL CHECK(status IN ('draft','review','published','retired')),
 boundary public.geometry(MULTIPOLYGON,4326) NOT NULL,
 CHECK(public.ST_IsValid(boundary) AND NOT public.ST_IsEmpty(boundary))
);
CREATE INDEX ix_zone_boundary ON game.race_zones USING gist(boundary);
CREATE INDEX ix_zone_geography ON game.race_zones USING gist((boundary::public.geography));
CREATE TABLE game.track_versions (
 id uuid PRIMARY KEY, race_zone_id uuid NOT NULL REFERENCES game.race_zones(id),
 version integer NOT NULL CHECK(version > 0), status varchar(20) NOT NULL CHECK(status IN ('draft','published','retired')),
 manifest_key varchar(240), gameplay_hash varchar(64), UNIQUE(race_zone_id, version),
 CHECK(status <> 'published' OR (manifest_key IS NOT NULL AND gameplay_hash ~ '^[a-f0-9]{64}$'))
);
GRANT SELECT ON ALL TABLES IN SCHEMA game TO racing_app;
GRANT INSERT, UPDATE ON game.users, game.profiles, game.sessions, game.account_tokens,
 game.user_cars, game.outbox_messages TO racing_app;
GRANT INSERT ON game.used_refresh_tokens, game.player_state, game.economy_transactions TO racing_app;
GRANT INSERT, UPDATE, DELETE ON game.rate_limits TO racing_app;
