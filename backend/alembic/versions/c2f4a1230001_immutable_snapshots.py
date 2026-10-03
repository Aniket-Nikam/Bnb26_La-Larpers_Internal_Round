"""Seal snapshots and prohibit mutation of published proof material."""

import sqlalchemy as sa

from alembic import op

revision = "c2f4a1230001"
down_revision = "b3194d72d2b4"
branch_labels = depends_on = None


def upgrade():
    op.add_column(
        "draw_runs",
        sa.Column("snapshot_sealed", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.execute("UPDATE draw_runs SET snapshot_sealed = true")
    op.execute("""
    CREATE FUNCTION protect_frozen_entry() RETURNS trigger LANGUAGE plpgsql AS $$
    BEGIN
      IF TG_OP <> 'INSERT' THEN RAISE EXCEPTION 'frozen membership is immutable'; END IF;
      IF (SELECT snapshot_sealed FROM draw_runs WHERE id = NEW.draw_id) THEN
        RAISE EXCEPTION 'frozen manifest is sealed';
      END IF;
      RETURN NEW;
    END $$;
    CREATE TRIGGER frozen_immutable BEFORE INSERT OR UPDATE OR DELETE ON frozen_entries
      FOR EACH ROW EXECUTE FUNCTION protect_frozen_entry();
    CREATE FUNCTION protect_draw_rank() RETURNS trigger LANGUAGE plpgsql AS $$
    DECLARE target uuid;
    BEGIN
      IF TG_OP = 'INSERT' THEN target := NEW.draw_id; ELSE target := OLD.draw_id; END IF;
      IF (SELECT status FROM draw_runs WHERE id = target) <> 'COMPUTING' THEN
        RAISE EXCEPTION 'ranking mutation requires computing state';
      END IF;
      IF TG_OP = 'DELETE' THEN RETURN OLD; ELSE RETURN NEW; END IF;
    END $$;
    CREATE TRIGGER ranks_immutable BEFORE INSERT OR UPDATE OR DELETE ON draw_ranks
      FOR EACH ROW EXECUTE FUNCTION protect_draw_rank();
    CREATE FUNCTION protect_draw_run() RETURNS trigger LANGUAGE plpgsql AS $$
    BEGIN
      IF OLD.snapshot_sealed AND (NOT NEW.snapshot_sealed OR
        ROW(NEW.drop_id,NEW.total_entries,NEW.manifest_commitment,NEW.algorithm_version) IS DISTINCT FROM
        ROW(OLD.drop_id,OLD.total_entries,OLD.manifest_commitment,OLD.algorithm_version)) THEN
        RAISE EXCEPTION 'sealed draw facts are immutable';
      END IF;
      IF OLD.status = 'PUBLISHED' AND NEW.status <> 'PUBLISHED' THEN
        RAISE EXCEPTION 'published draw cannot be reset';
      END IF;
      IF NEW.next_rank < OLD.next_rank THEN RAISE EXCEPTION 'promotion cursor cannot rewind'; END IF;
      RETURN NEW;
    END $$;
    CREATE TRIGGER draw_immutable BEFORE UPDATE ON draw_runs FOR EACH ROW EXECUTE FUNCTION protect_draw_run();
    """)


def downgrade():
    op.execute(
        "DROP TRIGGER draw_immutable ON draw_runs; DROP FUNCTION protect_draw_run(); "
        "DROP TRIGGER ranks_immutable ON draw_ranks; DROP FUNCTION protect_draw_rank(); "
        "DROP TRIGGER frozen_immutable ON frozen_entries; DROP FUNCTION protect_frozen_entry();"
    )
    op.drop_column("draw_runs", "snapshot_sealed")
