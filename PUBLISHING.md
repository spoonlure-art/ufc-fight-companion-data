# Publishing workflow

1. Prepare and verify event JSON privately.
2. The owner explicitly approves the exact version.
3. Upload approved JSON to `events/<event-id>.json`.
4. Update `manifest.json` with a higher revision, UTC publication timestamp, event path and SHA-256.
5. Future Android app versions will fetch this manifest via HTTPS and cache the latest validated event.

Only repository collaborators with write permission can publish. A local admin toggle does not grant server-side rights. This public repository is readable by anyone. The current Android app does not yet sync automatically.
