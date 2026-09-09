# Future lobby contract — design only

No lobby tables, endpoints or simulation are implemented in this milestone. Do not enable
an Enter Race button until real admission and lifecycle behavior exist.

Proposed tables: lobbies(id, host_user_id, visibility, max_players CHECK 2..8,
location_id, optional track_version_id while draft, status, created_at, expires_at,
version); lobby_members(lobby_id, user_id, selected_user_car_id, invited/joined/ready state,
joined_at); lobby_invitations(id, lobby_id, invited_user_id or invitation_hash, expires_at,
used_at, revoked_at). Composite keys/unique membership, ownership checks, and a locked
lobby row enforce capacity under concurrent joins. A published selected track must belong
to the selected location through its race zone. No launch while a required track is absent.

Future protected APIs: create/get lobby, invite/join/leave, select owned car, set ready,
cancel lobby. Host permissions cover lobby management only. Public visibility is not
permission to mutate; private invite codes are hashed, expiring and rate-limited. Invite
and membership changes require verified accounts. No player email/GPS appears in roster.

The status machine is draft → open → locked → closed/cancelled; transition into future
gameplay will be defined after the unique game rules are agreed. User's later unique game
system determines win conditions. Do not encode conventional laps/checkpoints/race scoring
here. Player-to-player car collisions remain excluded. Session ownership, content versions
and roster are reusable across future gameplay modes.
