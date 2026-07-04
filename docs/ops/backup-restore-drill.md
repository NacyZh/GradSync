# Backup Restore Drill

Backups are not release-ready until a restore has been rehearsed from the same
backup path operators will use during an incident.

## Drill Cadence

- Run before the first production launch.
- Run after database version upgrades or backup storage changes.
- Run at least quarterly for an active deployment.

## Drill Procedure

1. Create a fresh production backup:

   ```bash
   POSTGRES_USER=gradsync POSTGRES_DB=gradsync ./scripts/postgres-backup.sh
   ```

2. Copy the dump to encrypted off-host storage configured by
   `POSTGRES_BACKUP_OFFSITE_URI`.
3. Start an isolated restore target with no production writers attached.
4. Restore the backup:

   ```bash
   POSTGRES_USER=gradsync POSTGRES_DB=gradsync ./scripts/postgres-restore.sh backups/postgres/gradsync-TIMESTAMP.dump
   ```

5. Run migration, readiness, and smoke checks against the restored database.
6. Record evidence in `docs/ops/restore-drills/latest.md`.

## Acceptance Criteria

- RPO: latest usable backup is no older than 24 hours.
- RTO: restore plus smoke validation completes within 2 hours.
- Restored data includes users, projects, tasks, submissions, bookings,
  notifications, and audit records.
- Evidence includes backup name, restore target, start/end times, operator,
  validation commands, and result.
# Research Collaboration Upload Restore Expectations

For `specs/003-research-collab-platform`, database backups and media backups
must be treated as a matched restore unit. `common.UploadedFile` rows store the
category, original filename, stored object key, checksum, content type, owner,
and byte size for papers, code archives, documents, writing drafts, and
feedback files.

Before applying collaboration migrations, take a PostgreSQL backup and preserve
the current media volume. Rollback may deploy earlier application images, but
must not delete uploaded media or metadata until an administrator has confirmed
that no business records reference those files. Restore validation must include
at least one metadata query, one checksum comparison, and one authorized
download path that writes an audit event.

## Research Collaboration 003 Release Validation Addendum

Before releasing `specs/003-research-collab-platform`, operators must validate
that collaboration migrations apply cleanly and that rollback notes preserve
both database rows and uploaded media. The validation evidence should include a
successful migration dry run, a restored `common.UploadedFile` metadata query,
a checksum comparison against restored media, and an authorized download that
creates an audit event.

Notification failure records, writing feedback files, resource-use decisions,
role activation records, and audit events are part of the restore acceptance
set. If email delivery is unavailable during restore validation, the business
records still pass only when notification status records show retry-needed or
failed states with masked failure details.
