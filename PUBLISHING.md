# Owner-controlled publication

The Android fan app has no publication credentials or write API. The isolated
review app can preview DRAFT files but cannot promote them to PUBLISHED.

1. Research privately; keep field-level evidence and unresolved conflicts.
2. Prepare a non-sample DRAFT. Normally verification is VERIFIED with zero
   unresolved fields. Alternatively, the owner may explicitly accept documented
   limitations in a separate approvals/*.json record binding this exact SHA,
   event ID, source verification status/count, owner actor and approval evidence.
   Partial verification is never relabeled VERIFIED by that acceptance.
3. Show the owner the exact changes and SHA-256 of the candidate file.
4. Only after the owner's explicit approval, manually run **Owner-approved
   publication** on main with that exact draft path and SHA-256. A changed file,
   wrong actor, sample data, missing headliners or unaccepted source limitations
   block it. Pass owner_approval only for an explicit exact-version acceptance.
5. The workflow writes an immutable `events/<id>_r<revision>.json` and manifest
   together in one commit. SHA-256 is calculated over exact UTF-8 file bytes.

No push, PR, build, scheduled task or validator automatically publishes. The
original UFC333 review draft remains sample/unverified and cannot pass publishing.
The owner must never approve a file merely because structural tests pass.

## UFC333 owner decision, 2026-10-23

The owner explicitly approved UFC333 and authorized central publication in the
project conversation after the known limitations had been disclosed. The separate
UFC333_OWNER_APPROVED_CANDIDATE.json is non-sample; the source verification remains
PARTIALLY_VERIFIED. Exact acceptance is in approvals/UFC333_OWNER_APPROVAL_20261023.json.

For this authorized publication the connected GitHub tools have no workflow
dispatch operation. The same tested prepare() function was invoked locally with
the approval record and the authenticated owner's verified GitHub login. The
event, manifest and approval are uploaded in one atomic Git commit with a
compare-and-swap branch update. This is an explicitly authorized publication via
the connected write API, not a claim that the manual Actions workflow ran.

## Rollback

Do not reduce revision or mutate an old event file. Prepare the previous good
content as a new reviewed DRAFT; obtain explicit owner approval; publish it with
a higher revision and a new immutable path. Consumer apps accept it as an update.

## Repository permissions and limitations

Restrict write access to trusted maintainers; enable 2FA on the owner's account.
Use branch protection/required validation checks on this public repository.
Tooling cannot prevent an administrator from changing the policy or directly
editing main. The current connection cannot configure repository protection;
that setup remains outstanding. Do not describe these scripts as enforced branch
protection. A checksum detects inconsistency; it is not independent authentication.

Drafts already present in this public repository are public, including history.
No confidentiality is claimed. Future private research belongs in a private
workspace/repository. Never commit account tokens or production signing keys.
