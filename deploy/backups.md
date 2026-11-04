# Pilot backup and recovery

`backup_localfrom.py` is installed root-owned as
`/usr/local/sbin/localfrom-backup` and uses the application virtualenv.
It requires the initialized local restic repository and a root-private
`/etc/localfrom/restic-password`. Keep that password separately off-server;
never paste it into chat, publish it, or include it in the repository's sources.

The backup captures a completed MySQL single-transaction dump, the app commit
and source, public/private uploads, production environment, Nginx, Redis/MySQL
configuration, application/backup units, and Let's Encrypt configuration/keys.
The snapshot is encrypted by restic. Credential files and the unencrypted SQL
staging payload are root-private; secrets are not passed as process arguments.
The encryption password and repository itself are never included as sources.
Regenerable static files, application caches and Git metadata are excluded.

Create `/var/lib/localfrom-backup` and `/var/cache/localfrom-backup` root-owned
0700 before starting the hardened systemd backup unit. The daily timer runs
03:10 Asia/Kolkata plus up to ten minutes of randomized delay. Failures are
reported in the journal. Configure external failure/disk alerts separately;
a timer is not proof of a successful backup.

This is an online database backup; it does not stop the application or guarantee
one transaction spanning MySQL and filesystem uploads. Before schema changes,
or when an exact database/media cut is required, arrange an approved write
maintenance window. Monitor capacity: the SQL staging payload and the local
encrypted repository consume the same 40 GB disk as the application.
No retention deletion or prune operation is automated without approval.

## Acceptance and off-server protection

1. Run the backup service and require its success marker and exit status 0.
2. Run `restic check --read-data` with the repository/password-file options.
3. Restore the snapshot to a new root-private directory, never `/` or `/srv`.
   Compare the restored SQL/config/media against the snapshot and staging data.
4. With explicit approval, import the SQL into a newly named isolated MySQL
   database using a privileged operator. Do not import it into `localfrom`.
   Check table counts, migration state and representative data. Do not grant
   the normal app account global privileges for this test.
5. Copy the complete encrypted repository off-server while the backup job is
   idle, or configure an approved remote restic destination. Preserve the
   decryption password separately in protected storage. Verify the copied repo
   can be opened. Local backups alone do not protect against VPS/disk loss.

No backup/restore rehearsal has passed merely because these files exist.
Disaster recovery must restore source/config/media, import SQL into the intended
empty database, regenerate static files, reapply ownership, and validate access
before opening traffic. Do not restore old Redis OTP/session proof caches.
