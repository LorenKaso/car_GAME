"""Starter car, level curve, and planned city catalog; no playable track seeds."""

from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("INSERT INTO game.level_curves VALUES (1, 'Prototype curve v1')")
    op.execute(
        "INSERT INTO game.level_thresholds VALUES (1,1,0),(1,2,1000),(1,3,3000),(1,4,6000),(1,5,10000)"
    )
    op.execute("""INSERT INTO game.cars VALUES (
      '10000000-0000-0000-0000-000000000001','starter','Origin One','Original Prototype','One',
      180,50,55,60,40,'placeholder/car/origin-one',true,true)""")
    # Approximate public city centers for catalog orientation, not road/survey coordinates.
    op.execute("""INSERT INTO game.locations VALUES
      ('20000000-0000-0000-0000-000000000001','miami','Miami','US','planned',public.ST_GeogFromText('SRID=4326;POINT(-80.19 25.76)')),
      ('20000000-0000-0000-0000-000000000002','las-vegas','Las Vegas','US','planned',public.ST_GeogFromText('SRID=4326;POINT(-115.14 36.17)')),
      ('20000000-0000-0000-0000-000000000003','washington-dc','Washington D.C.','US','planned',public.ST_GeogFromText('SRID=4326;POINT(-77.04 38.91)')),
      ('20000000-0000-0000-0000-000000000004','new-york','New York','US','planned',public.ST_GeogFromText('SRID=4326;POINT(-74.01 40.71)'))""")


def downgrade():
    # Referenced catalogs cannot be removed while account/track data exists.
    op.execute("DELETE FROM game.locations WHERE id::text LIKE '20000000-%'")
    op.execute("DELETE FROM game.cars WHERE code='starter'")
    op.execute("DELETE FROM game.level_thresholds WHERE curve_version=1")
    op.execute("DELETE FROM game.level_curves WHERE version=1")
