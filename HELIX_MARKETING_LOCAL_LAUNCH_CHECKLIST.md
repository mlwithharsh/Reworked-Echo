# HELIX Marketing Local Launch Checklist

## 1. Backend Boot

Open a terminal in `D:\ECHO V1` and set the minimum environment:

```powershell
Set-Location -LiteralPath 'D:\ECHO V1'
$env:HELIX_API_TOKEN='dev-token'
$env:HELIX_CREDENTIAL_SECRET='replace-with-a-long-random-secret'
```

If you are using Supabase-backed chat/profile features, also set:

```powershell
$env:SUPABASE_URL='https://<project>.supabase.co'
$env:SUPABASE_SERVICE_ROLE_KEY='<service-role-key>'
```

Start the backend:

```powershell
.venv\Scripts\activate
uvicorn helix_backend.fullstack.main:app --reload --port 8000
```

Expected result:

- FastAPI starts on `http://localhost:8000`
- `GET /api/status` responds
- `GET /api/marketing/platform-health` responds

## 2. Frontend Boot

Open a second terminal:

```powershell
Set-Location -LiteralPath 'D:\ECHO V1\helix-frontend'
$env:VITE_BACKEND_URL='http://localhost:8001'
$env:VITE_API_TOKEN='dev-token'
npm run dev
```

Expected result:

- frontend starts locally
- navbar shows `Agent`
- `Agent` page loads without auth errors

## 3. Save Local Platform Credentials

In the Agent page:

1. Open `Operator Settings`
2. Select a platform
3. Enter credentials for `default`
4. Click `Save Local Credentials`

Recommended first platforms:

- `webhook`
- `telegram`
- then `x` or `linkedin`

Expected result:

- credentials save successfully
- `Platform Readiness` changes to `Live Ready`
- saved configured fields appear in the settings panel

## 4. Dry-Run Smoke Test

From `D:\ECHO V1`:

```powershell
$env:HELIX_API_TOKEN='dev-token'
.venv\Scripts\python smoke_marketing_local.py --base-url http://localhost:8000
```

Expected result:

- brand profile created
- campaign created
- strategy generated
- variants generated
- jobs scheduled
- dry-run dispatch succeeds
- optimization returns a result

Stop here if any step fails. Fix before live posting.

## 5. First Live Validation

Use one platform at a time.

Recommended order:

1. `webhook`
2. `telegram`
3. `x`
4. `linkedin`
5. `discord`
6. `reddit`

For each platform:

1. Create or select a campaign
2. Generate variants for one platform only
3. Approve exactly one variant
4. Schedule one job
5. Use the `Live` button from `Scheduled Jobs`
6. Confirm the platform received the post
7. Check `Delivery Logs`

Success criteria:

- job moves through expected state
- delivery log records platform and status
- real post/message appears on the target platform
- no duplicate or malformed output is sent

## 6. Failure Checks

If live dispatch fails:

- inspect `Platform Readiness`
- inspect `Delivery Logs`
- confirm the saved credentials match the platform
- confirm the target account/channel/subreddit identifiers are correct
- retry with one job only

Do not test multiple live platforms at once until one platform is stable.

## 7. Safe Production Baseline

Before enabling real usage:

- keep `HELIX_CREDENTIAL_SECRET` set
- use one default account per platform first
- prefer dry-run before every new platform/account
- keep rate of live posts low during initial rollout
- verify platform policy compliance manually

## 8. Recommended First Production Scope

Start with:

- `webhook`
- `telegram`
- one of `x` or `linkedin`

Delay until later:

- `reddit`
- multi-account operation
- high-frequency posting
- parallel live dispatch across many channels

## 9. Operational Definition Of Done

Helix is locally launch-ready when all of the following are true:

- backend runs locally without startup errors
- frontend Agent workspace loads
- platform credentials can be saved locally
- platform readiness reflects saved credentials
- smoke test completes successfully
- one live post succeeds on at least one real platform
- delivery logs and analytics update after execution
