# Free deployment with persistent private lists

Render runs the React/FastAPI app; a separate Turso **libSQL** database stores accounts, sessions, and tasks. Local Windows development keeps using SQLite. Local data is not automatically uploaded.

1. Sign in at https://app.turso.tech/ and select the Free plan.
2. Create a **libSQL** database called little-list near the Render region. This app uses libSQL, not the newer Turso rewrite driver.
3. Obtain the database URL and a database-scoped read/write token. Keep the token private.
4. In https://dashboard.render.com/ choose New > Blueprint and connect the little-list repository. Select the Free plan only.
5. Enter TURSO_DATABASE_URL and TURSO_AUTH_TOKEN in the environment settings. Never put them in GitHub or frontend variables.
6. The blueprint sets REQUIRE_REMOTE_DB=1 and COOKIE_SECURE=1. Missing database configuration blocks startup rather than silently losing data in temporary storage.
7. Wait for Live, open the HTTPS URL, create an app account, add a task, restart the service, and verify it remains. Verify a second account cannot access the first account's tasks.

Render Free may sleep, making the first request slow. Turso retains data independently of app restarts. Free plans have quotas and may change. Backups are advisable; persistent storage is not a substitute for backups.

Passwords use salted PBKDF2-SHA256 with 600,000 iterations. Sessions expire after seven days and use HttpOnly/SameSite cookies, HTTPS-only in deployment. Logout revokes sessions. Every task operation checks ownership. Mutations require a custom request header and reject foreign origins. Sign-in attempts are throttled.

Password recovery, email verification, and account deletion are not implemented. Keep your password safe. Old unowned local tasks are preserved, never assigned automatically; see README.md for an explicit migration command.

Tests cover ownership, sessions, logout, throttling, CSRF checks, tasks and database migration. CI also runs against the native libSQL driver. Cloud persistence must be verified on the actual deployment before calling it complete.

References: https://render.com/docs/free and https://docs.turso.tech/sdk/python/quickstart
