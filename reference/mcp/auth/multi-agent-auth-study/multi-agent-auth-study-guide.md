# Multi-Agent Authentication: A Step-by-Step Learning and Implementation Guide

**Microsoft Entra ID · OAuth/OIDC · On-Behalf-Of (OBO) · Google Cloud · Google ADK · Google Calendar · Agent-to-Agent Security**

**Revision:** 13 November 2026  
**Level:** Developer with Python and HTTP basics; no prior identity experience required  
**Method:** One realistic project, one security decision at a time. Build in stages; verify every trust boundary before adding the next.  
**Format:** Design-first implementation guide. It specifies what to configure, implement, observe, and reject; it does not supply an unreviewed full codebase.

> **Project scenario (synthetic):** An employee signs in with Microsoft Entra ID and asks an assistant either **“Am I free on Friday?”** or **“Show my Microsoft profile.”** An orchestrator routes the first request to a Google Calendar agent and the second to a Microsoft Graph agent. Only the employee's authorized data may be returned. All examples use fictional identities and identifiers.

## Start here: what you will build

**Three agents, three different authentication problems.**

```text
                                 Microsoft Entra ID
                              (login, user API tokens,
                                     OBO)
                                       |
                                       |
Browser -- login --> Web Client -- token for API A --> [A: Orchestrator]
                                                         |           |
                                  Google workload ID token|           |Entra OBO token
                                  (aud = agent B)         |           |(aud = agent C)
                                                         v           v
                                                 [B: Calendar]   [C: Graph]
                                                      |               |
                                        Google OAuth  |               | Entra OBO
                                        user token    |               | (aud = Graph)
                                                      v               v
                                               Google Calendar    Microsoft Graph

Browser <-- signed session cookie --> Web Client / backend session store
OAuth tokens and refresh tokens stay server-side; never in LLM prompts.
```

**Deployment assumption:** Python + Google ADK; a FastAPI web client; separate agent services on Google Cloud Run for the distributed stage; Microsoft Entra ID is the employee identity provider. The first labs run locally. The Entra-protected Graph agent may run on Google Cloud even though its user API tokens come from Microsoft. Google OAuth for Calendar is independent of Entra OBO. **Cloud Run deployment detail:** if agent A is a private Cloud Run service behind a separate web client, that client authenticates to Cloud Run with a Google workload ID token **and** to A's application API with Entra `T_A`; these are independent gate checks (use the documented dual-header pattern).

**Successful finish:** A second employee cannot read the first employee's calendar; a token for agent A is refused by agent C; Google Calendar refuses write operations; a revoked Google grant triggers re-consent; and Graph can be called only after a valid Entra OBO exchange.

### The three rules that prevent most errors

1. **An access token is for one resource audience.** Agent C must reject an access token addressed to agent A. OBO produces a *new* token for a new audience; it does not make an old token universal. [M1][M3]
2. **Entra OBO does not produce a Google Calendar token.** Microsoft Graph/custom Entra APIs use Entra delegation. Google Calendar requires a Google OAuth grant (or a separately justified Google Workspace service-account design). [M1][G1]
3. **Agent identity is not user authorization.** A Cloud Run identity token can prove which service called agent B; it does not prove whose calendar that service may read. You must authorize the employee and the specific grant separately. [G3][A1]

## 1. Learn the vocabulary with one concrete request

| Term | Question it answers | This project's example |
|---|---|---|
| Authentication (AuthN) | Who signed in, or which workload is calling? | Entra login for employee; Cloud Run identity for service A |
| Authorization (AuthZ) | May this actor perform this action on this data? | Employee can read only their own linked calendar |
| OIDC ID token | Who authenticated to the client? | Entra ID token for browser sign-in |
| OAuth access token | Which API may be called, with which grant? | Entra token for `api://agent-a`; Google token for Calendar |
| Refresh token | Can the client obtain a new access token? | Stored in a protected server-side Google OAuth vault |
| Scope (`scp`) | What delegated permission is requested or granted? | `access_as_user`, `User.Read`, `calendar.readonly` |
| Audience (`aud`) | Which resource is allowed to receive this token? | Agent A, agent C, Graph, or Cloud Run service B |
| Issuer (`iss`) | Which authority issued the token? | Microsoft identity platform or Google |
| Subject / tenant | Which identity owns the request? | Entra `(tid, oid)`; Google `(iss, sub)` |
| OBO | Can a middle-tier API request a different user-delegated token? | Agent C exchanges an Entra token for a Graph token |
| Workload identity | Which process/service is calling? | Cloud Run service account; optionally SPIFFE/SPIRE |

**The decision:** Never treat a `user_id` string, email address, or agent name in a request body as proof of identity. Bind identity to a validated token or a trusted server-side session. [M3][A1]

### Token trace: fictional values, not live JWTs

```text
T_A: issuer=Entra, aud=api://agent-a, scope=access_as_user, user=(tenant-01, alice-oid)
T_C: issuer=Entra, aud=api://agent-c, scope=access_as_user, user=(tenant-01, alice-oid)
T_G: issuer=Entra, aud=Microsoft Graph, scope=User.Read, user=(tenant-01, alice-oid)
T_B: issuer=Google, aud=https://calendar-agent-...run.app, principal=agent-a-service
T_CAL: issuer=Google OAuth, scope=calendar.readonly, Google user=google-sub-01
```

The first three are Microsoft user-delegated API access tokens. `T_B` is a **Google-signed workload ID token** for reaching Cloud Run, not the employee's Calendar token. `T_CAL` is the **Google user-delegated access token** used only when calling Calendar. Exact access-token claim encodings can differ; validate with supported middleware rather than comparing raw token strings. [M3][G3]

## 2. Your learning sequence and dependency gates

| Stage | One decision | End state | Go forward only when… |
|---|---|---|---|
| 0 | What breaks without identity? | Simple local assistant and one mock calendar tool | You can describe the missing trust boundary |
| 1 | How does the user sign in? | Entra sign-in and server session | Wrong user / invalid login is rejected |
| 2 | How does agent A protect its API? | Entra bearer token for agent A | Wrong audience and missing scope are denied |
| 3 | How does OBO differ from token forwarding? | Agent A → Graph via Entra OBO | Graph works; original A token is not passed to Graph |
| 4 | How is Google access delegated? | Calendar read-only consent | You can read, but not change, events |
| 5 | Where are tokens owned and stored? | Per-user token broker | Another user or agent cannot fetch them |
| 6 | How do agents call each other? | A → B authenticated service request | Unauthenticated callers are rejected |
| 7 | How is user context propagated safely? | B authorizes employee grant reference | Swapped `user_id` and grant references fail |
| 8 | Can delegation cross two Entra APIs? | A → C → Microsoft Graph | Each audience is correct at every hop |
| 9 | Who handles interrupted agent auth? | ADK auth integration | Consent can resume safely without showing secrets |
| 10 | Which cloud identity do workloads use? | GCP managed identity, optional federation | No long-lived service-account key is required |
| 11 | Is the system ready for failure? | Negative tests and operations | Every deny path has a known recovery |

## 3. Stage 0 — Build the minimum baseline

**Requirement:** The assistant answers a natural language calendar question. **Baseline failure:** If the tool accepts `user_id=alice` from the model or HTTP body, another person can ask it to fetch Alice's data.

**Options:** (a) one local agent plus a mock tool; (b) multiple agents immediately; (c) production identity infrastructure first. **Choose (a)** because agent orchestration is not an authentication mechanism and early complexity hides the failure.

**Implementation path:**

1. Define a local Google ADK orchestrator with two tools: `read_mock_calendar()` and `read_mock_profile()`.
2. Create two fake users, Alice and Bob, with distinct calendar events.
3. Add a local FastAPI endpoint `POST /chat`, but keep all resources fake.
4. Record which incoming value picks the data owner. If it is request JSON or model text, mark this design **intentionally insecure**.
5. Write down the boundary to fix: **HTTP requester → authenticated application session → authorized owner of data**.

**Observe:** A request that changes only `user_id` can currently switch calendars. This is your controlled failing test. **Recovery:** Do not expose this baseline publicly; replace the caller-provided identity in Stages 1–2.

**Design changes if:** You are learning identity alone rather than ADK. Then use two regular HTTP handlers; the authentication decisions remain identical.

## 4. Stage 1 — Sign in the employee with Microsoft Entra ID

**Requirement:** Only a real tenant user may establish a session. **Baseline failure:** A signed `uid` cookie created from browser-supplied data still does not prove a Microsoft login.

**Options:** (a) OIDC authorization code + PKCE; (b) username/password sent to the app; (c) client-only login followed by trusting an arbitrary user ID. **Choose (a)** and use an authentication library, not handcrafted OAuth HTTP. [M2]

**Entra console actions:**

1. Create or select an Entra tenant and a dedicated test user. Follow your supplied `entra_user_guide(1).md` for creating a user and copying the Object ID; do not use a real person's password in test data.
2. In **Entra admin center → App registrations → New registration**, create a **single-tenant web client** named `study-web-client`.
3. Configure a **Web** redirect URI for local testing, for example `http://localhost:8000/auth/entra/callback`. Production redirect URIs must use HTTPS.
4. Record `TENANT_ID` and the client's `CLIENT_ID`. Configure the confidential-client credential on the server; store it outside source control. Prefer a certificate or federated credential where supported in production.
5. Use **OIDC authorization code flow with PKCE**, `state` and `nonce`; validate the callback through an approved library.
6. On successful login, create a random **server-side session ID** and an `HttpOnly`, `Secure` (under HTTPS), `SameSite` cookie. Keep Microsoft tokens on the server, not in the browser or the LLM context.
7. Derive the application user key from the verified **`(tid, oid)`**, not the email address. Define an allowlist or application role/group policy as a separate authorization step.

**Information flow:** Browser → Entra `/authorize` → browser callback containing an authorization code → server exchanges code → validated ID-token claims → app session. The ID token is not the bearer token for agent A or Graph.

**Failure and recovery:** A callback with a different `state` is rejected; restart the login. A missing group claim is not proof of membership (consider Entra group overage or a roles-based design). [M4]

**Verified when:** Two distinct users receive distinct sessions; forged cookie or mismatched callback state fails. **Design changes if:** You are building a SPA/mobile client; public-client credential handling differs, but PKCE remains relevant.

## 5. Stage 2 — Protect the orchestrator as an Entra API

**Requirement:** Agent A must know **who called** and **whether they may use this API**. **Baseline failure:** A valid Entra ID token sent to `/chat` is not automatically a valid API access token.

**Options:** (a) only an application session for a monolith; (b) separate API resource with OAuth scopes; (c) allow any token signed by Microsoft. **Choose (b)** for learning multi-hop OBO. (a) is simpler if you will never split services; **never choose (c)**.

**Entra console actions:**

1. Register a second application, `study-agent-a-api` (resource API A).
2. Under **Expose an API**, define Application ID URI and delegated scope `access_as_user`.
3. Grant the **web client** delegated permission to API A; configure consent as required by your tenant.
4. At login, have the web client obtain a separate API **access token whose audience is agent A**, not Microsoft Graph.
5. In agent A's HTTP middleware, validate token signature, version-appropriate issuer metadata, `iss`, expected `aud`, time constraints, tenant, delegated `scp=access_as_user`, and allowed calling client where required. Use supported Entra-aware middleware. [M3]
6. Reject missing authentication with **401**; reject valid identity lacking permission with **403**. For a separately deployed **private** Cloud Run A, additionally require a Google workload ID token at the Cloud Run gate; the application still verifies Entra `T_A` in its own bearer header. [G3]
7. Resolve owner identity from the verified token; ignore any browser-supplied `oid`, `tenant` or `email` as an authority.

**Information flow (local):** `Web client -- T_A (aud=agent-a, scp=access_as_user) --> Agent A`. The API authorizes the user and sets the internal request principal `tenant/user`. On private Cloud Run, there is an additional front-door **Google ID token for A**, while `T_A` stays the application-level delegated token.

**Failure and recovery:** Present a **Graph token** directly to agent A. It must reject the token for **wrong audience**, even if Graph's token is valid. Get a fresh token targeted at A; never change validation to accept arbitrary audiences.

**Verified when:** A accepts a correct token and rejects missing signature, wrong issuer, wrong audience, expired token and insufficient scope. **Design changes if:** The UI/backend is one monolithic server: the API can use a verified server session internally, but the lesson about audience validation remains essential for a separate resource API.

## 6. Stage 3 — Implement the first Entra OBO exchange

**Requirement:** The backend must call `GET https://graph.microsoft.com/v1.0/me` for the signed-in employee. **Baseline failure:** Sending `T_A` to Graph is incorrect because it was issued for agent A, not Graph.

**Options:** (a) forward `T_A` to Graph; (b) ask the employee to sign in again to Graph; (c) perform Entra **On-Behalf-Of** from the confidential middle tier. **Choose (c)**. [M1]

**Build actions:**

1. In **agent A's** Entra registration, add Microsoft Graph **delegated** `User.Read` permission and complete required consent.
2. Configure agent A as a confidential client with a protected credential (certificate preferred for production; a secret may be used for a short-lived local lab).
3. After agent A validates `T_A`, use an approved MSAL-supported OBO API with **`T_A` as the user assertion** and **Graph's delegated scope** as the target.
4. Let Entra issue **`T_G` whose audience is Microsoft Graph**. Cache tokens according to the library's guidance; never serialize tokens into agent-visible tool output.
5. Call `/v1.0/me` using `T_G`, return only the minimum profile fields needed by the task.

**Exact movement:**

```text
Web client ---- T_A: aud=agent-a ----> Agent A
Agent A -- T_A assertion + its confidential-client proof --> Entra /token
Entra -------- T_G: aud=Graph, scp=User.Read -------> Agent A
Agent A ---- T_G: Authorization Bearer -----------> Microsoft Graph /me
Microsoft Graph ---- profile fields ----------------> Agent A
```

**Failure and recovery:** Missing consent yields a consent/interaction error; do not silently turn it into an app-only Graph call. Initiate the appropriate consent/admin process and retry after the grant is present. An app-only token does **not** represent the user and is not an OBO assertion. [M1]

**Verified when:** `Graph /me` returns the test user; agent A never forwards `T_A` to Graph. **Design changes if:** The task is purely service-owned data with no signed-in user. Use client credentials/application permissions only after separate approval; that is not OBO.

## 7. Stage 4 — Authorize Google Calendar separately

**Requirement:** Read the user's Google Calendar, including if their Google email differs from their Entra email. **Baseline failure:** An Entra token, even one obtained using OBO, is not a Google Calendar token.

**Options:** (a) Google three-legged OAuth for the employee; (b) Google Workspace domain-wide delegation administered for an organization; (c) guess account mapping by matching email. **Choose (a)** for a user-owned learning project. (b) is a separate enterprise administration design, not a shortcut. [G1][G2]

**Google Cloud console actions:**

1. Create a test Google Cloud project and enable **Google Calendar API**.
2. In **Google Auth Platform / OAuth consent configuration**, configure an appropriate audience and add a test user if the app is in testing status. Console labels can change.
3. Create an **OAuth client of type Web application** and register exact callback `http://localhost:8000/auth/google/callback` for local testing.
4. Request **`https://www.googleapis.com/auth/calendar.readonly`**. This reads calendar data without write permissions. If the app needs only busy/free intervals, evaluate the narrower `calendar.freebusy` scope. [G2]
5. Start Google authorization from a **verified Entra session**. Generate unpredictable, one-use **`state`** and PKCE parameters as supported by the chosen OAuth library. Store `state -> authenticated session/user, verifier, expiry` on the server.
6. Validate returned `state`, redeem the authorization code on the server, bind the grant to the confirmed Entra user key `(tid, oid)`, and obtain an independently verified Google account identifier when account identity must be displayed/controlled.
7. Store the granted access/refresh credentials server-side and call the Calendar API using **the Google token**, not the Entra token. For access after the current visit, request offline access and handle the possibility that no new refresh token is returned on later consents. [G1]
8. Attempt a **write** operation with only read-only scope; verify that it is denied.

**Exact movement:**

```text
Entra-authenticated session -- starts consent --> Google /authorize
Google -- auth code + matching random state --> /auth/google/callback
Backend -- auth code + verifier --> Google token endpoint
Google -- T_CAL: delegated calendar.readonly --> protected token vault
Calendar tool -- T_CAL --> Google Calendar API
```

**Failure and recovery:** User denies consent or revokes the grant: return **“Connect Google Calendar”**, delete/mark the stale grant, and restart Google authorization. Never retry indefinitely or use another user's token.

**Verified when:** Alice can read her linked Google Calendar; Alice cannot write events; Bob's account is never silently substituted. **Design changes if:** Your enterprise requires a managed Google Workspace account—add account-linking policy and admin controls rather than inferring identity from equal email strings.

## 8. Stage 5 — Place credentials behind a real boundary

**Requirement:** Multiple agents need API data without being able to inspect each other's refresh tokens. **Baseline failure:** A locally encrypted file plus a `fetch_my_spiffe_svid()` check *inside the same process* is not a separate authorization boundary. A compromised process that already has file/key access can bypass its own check.

**Options:** (a) encrypted local files for a single-user lab; (b) central credential broker/vault with service authentication and per-user authorization; (c) store tokens in ADK session state. **Use (a) only locally**, **choose (b)** for distributed services, and avoid (c) for production. ADK warns about sensitive credential storage in session state. [A1][G5]

**Broker contract (design, not code):**

| Item | Data ownership / access rule |
|---|---|
| Employee key | Entra `(tenant_id, object_id)`; derived from validated identity |
| Google account key | Verified Google `(issuer, sub)` if account identity is obtained |
| OAuth grant | Google client, authorized scopes, encrypted refresh token, status, expiry metadata |
| Agent A | Can request an authorized *read operation* for its authenticated user |
| Agent B | Can perform calendar reads for a short-lived, authenticated and authorized request |
| Broker | Validates caller workload identity **and** user-grant ownership before using a credential |
| LLM/ADK messages | Contain task intent and sanitized results, **never tokens or secrets** |

**Implementation path:** Use a proper credential manager if available for the runtime (Google's Agent Identity auth manager is documented for ADK), or implement a narrow internal broker backed by a managed secret store and protected database. Give each service only its minimal IAM permissions. Prefer an operation-level broker that returns data rather than refresh tokens. [G5]

**Failure and recovery:** Agent B submits a grant reference belonging to Bob while the signed request context says Alice. Broker refuses it and logs a safe audit record. **Verified when:** A stolen grant ID alone cannot read or retrieve credentials. **Design changes if:** All tools run inside one trusted backend with one operator; broker can be deferred until you split trust boundaries.

## 9. Stage 6 — Split the calendar tool into a second agent

**Requirement:** Agent A on Cloud Run invokes independent agent B on Cloud Run. **Baseline failure:** HTTP routing or an A2A agent card is not proof that the caller is trusted.

**Options:** (a) public endpoint with a hardcoded shared API key; (b) private Cloud Run service authenticated by service-account-issued **Google ID token**; (c) SPIFFE mTLS service mesh. **Choose (b)** on Cloud Run; use (c) when a heterogeneous service mesh is a real requirement. [G3][A2]

**GCP implementation path:**

1. Deploy the minimal **calendar agent B** as a separate authenticated Cloud Run service.
2. Give **agent A** its own runtime service account, for example `agent-a-runtime`.
3. Grant that principal **Cloud Run Invoker** only on B. Disable unauthenticated access to B.
4. When A calls B, obtain a **Google-signed ID token** with `aud` set to B's configured service URL or supported custom audience. Use supported Google auth libraries or metadata credentials; do not create a JSON service-account key.
5. B relies on Cloud Run's caller authentication and still performs its **own authorization** for what operation and whose data may be used.
6. Send a narrow request such as `read_availability(start, end, grant_ref, signed_context)` rather than a raw Google token.

**Information movement:**

```text
Agent A -- ID token: aud=Cloud Run B --> Cloud Run IAM gate
Cloud Run gate -- authenticated request --> Agent B
Agent B -- signed user context + grant reference --> credential broker
Broker -- authorized Calendar read --> Google Calendar
Agent B <------------------------- sanitized availability result
```

**Failure and recovery:** A calls B with an ID token for the wrong URL: Cloud Run denies before B runs. Obtain a new audience-bound ID token; never relax audience validation. [G3]

**Verified when:** A can invoke B; an anonymous call and wrong-audience token fail. **Design changes if:** A runs in Azure: use **GCP Workload Identity Federation** to obtain appropriate Google credentials; do not copy a service-account private key. [G4]

## 10. Stage 7 — Pass user context without giving B arbitrary power

**Requirement:** A chooses the employee for a calendar read; B must not trust an arbitrary `user_id` in an agent-generated payload. **Baseline failure:** Valid machine identity from A proves which service called B, but not that the employee authorized reading a given grant.

**Options:** (a) forward the browser's Entra access token to every agent; (b) put a plain `user_id` field in an A2A message; (c) issue a short-lived, audience-specific **signed user context** and enforce grant ownership at B/broker. **Choose (c)** for the Google specialist. This signed context is an application authorization design, **not a Microsoft OBO token**.

**Suggested signed context fields (fictional):**

```text
issuer=your-internal-auth-broker
subject=(tenant-01, alice-oid)
audience=calendar-agent-b
action=calendar.read
expires=short-lived timestamp
request_id=unique ID
grant_ref=alice-calendar-grant-07
```

**Build actions:**

1. Only the trusted entry/backend issues the context **after** verifying the Entra principal and its permissions.
2. B authenticates the caller service through Cloud Run IAM, validates context signature, issuer, audience, expiry and allowed action, and rejects replay as required by your threat model.
3. Broker verifies `grant_ref` actually belongs to the employee in the signed context. The context is not itself a Google refresh token.
4. Return only the minimum time slots needed, with structured access-denied errors. Never include context secrets in model prompts or traces.

**Failure and recovery:** An attacker changes `grant_ref` from Alice's to Bob's: signature mismatch or broker ownership check denies the operation. Correct the mapping; never silently fall back to the first available Google account.

**Verified when:** Every data read is associated with an authenticated service, an approved user, an allowed operation, and the correct grant owner. **Design changes if:** B is an Entra-protected API and itself needs Microsoft delegation: use a properly audience-targeted **Entra token/OBO** rather than this internal context alone.

## 11. Stage 8 — Add Graph agent C and multi-hop OBO

**Requirement:** An independent Graph specialist C must read `/me` for the user. **Baseline failure:** An access token addressed to A cannot be used as the incoming token to C. C cannot redeem a Graph token received from A for OBO as C.

**Options:** (a) keep Graph tool inside A (simplest); (b) A obtains an Entra delegated token for C, then C performs its own OBO to Graph; (c) pass the original token end to end unchanged. **Choose (b)** when C is independently deployed; otherwise (a) is simpler. [M1]

**Entra implementation path:**

1. Create an **Entra API registration C** exposing delegated `access_as_user`.
2. Allow **agent A** to request C's delegated scope, with appropriate consent.
3. Configure C as a confidential client allowed to request Microsoft Graph `User.Read` with consent.
4. A validates `T_A`, then performs an OBO exchange to obtain **`T_C` whose `aud` is C**.
5. A calls C with `T_C`. C validates issuer, signature, audience, expiry, scope, tenant, user and authorized calling client.
6. C performs a **second OBO exchange** using `T_C` as its assertion, obtains **`T_G` for Graph**, calls `/me`, and returns allowed fields only.

**Two-hop trace:**

```text
Web client -- T_A (aud=A) --> A
A -- OBO assertion T_A --> Entra --> T_C (aud=C)
A -- T_C --> C
C -- OBO assertion T_C --> Entra --> T_G (aud=Graph)
C -- T_G --> Microsoft Graph /me
```

**Extra Cloud Run layer (optional):** If C is also a private Cloud Run service, A may need a **Google ID token** for the Cloud Run front door **and** an Entra `Authorization` bearer token for C's API authorization. Cloud Run documents `X-Serverless-Authorization` for its ID token when the application needs the regular `Authorization` header for its own token. Do not confuse these credentials. [G3]

**Failure and recovery:** `T_A` sent directly to C returns 401 for wrong audience. Request `T_C` via OBO. A consent failure needs an authorization remedy; it must not trigger app-only fallback. **Verified when:** C never accepts `T_A`, and Graph sees only `T_G`.

## 12. Stage 9 — Integrate authentication with Google ADK and A2A

**Requirement:** A tool may discover missing user consent during an agent run. **Baseline failure:** A model response containing an OAuth code or raw access token creates a credential exposure path.

**Options:** (a) implement browser authorization redirects in FastAPI and give ADK already-authorized tools; (b) use ADK's tool authentication / credential request and client-side resume flow; (c) let the LLM generate OAuth links from instructions. **Choose (a) first for understanding; evaluate (b) once redirects and session isolation work. Never choose (c).** [A1]

**ADK integration path:**

1. Keep a dedicated **authentication adapter** between HTTP, token manager and agent runtime. The model selects a safe tool; the adapter owns the credential.
2. When the Calendar grant is missing, return a structured authorization-needed result, **not the credential**, and let the trusted web client initiate Google OAuth.
3. If using ADK's native interactive tool flow, follow current ADK documentation for `AuthScheme`, `AuthCredential`, `adk_request_credential` and resume handling. Persist pending auth state per user/session/invocation and validate the callback. ADK APIs and event names change between versions; pin the implementation version. [A1]
4. Keep independent user/session records. Never use a global `user1` identity or shared mutable token dictionary in a multi-user deployment.
5. For remote agents using **A2A**, declare supported security schemes in the agent card, but enforce them at the endpoint. Every task operation, task lookup and result must enforce the caller's authorized visibility. A2A permits an auth-required task state; do not relay tokens in ordinary agent messages. [A2]

**Failure and recovery:** OAuth completes in the wrong browser session. Reject due to state/session mismatch; ask the correct session to restart. **Verified when:** Login/consent resumes the intended pending operation once and the LLM never sees an OAuth authorization code.

**Design changes if:** Your product front end already integrates with ADK's auth manager or a managed A2A authorization handoff. Prefer the official managed integration over reproducing the same broker behavior.

## 13. Stage 10 — Select GCP, Azure and agent workload identity correctly

**Requirement:** Each deployed agent must prove its own workload identity without long-lived shared keys. **Baseline failure:** A service-account JSON key copied into every agent grants broad access and is difficult to rotate.

| Deployment | Preferred starting point | Do not mistake it for |
|---|---|---|
| A and B on Cloud Run | Attached service accounts + Google audience-bound ID tokens + IAM Invoker | Employee's Google Calendar delegation |
| A on Azure, B on GCP | GCP Workload Identity Federation with a mapped trusted external Azure/Entra workload identity | Entra **user OBO** for Google Calendar |
| Mixed Kubernetes / on-prem | SPIFFE/SPIRE workload credentials, enforced by a separate mTLS gateway or broker | A local function that self-checks its SVID |
| Agent needs Graph delegated user data | Microsoft Entra OBO via confidential API credentials | Cloud Run Invoker permission |
| Microsoft Entra Agent ID | Agent identity blueprint and child identities, with their documented agent-specific OBO flows | Generic SPIFFE identity or an interactive sign-in app |

**Optional cross-cloud build:** Configure a GCP workload identity pool/provider for the trusted Azure workload; restrict attribute mappings and IAM membership; obtain short-lived Google credentials via federation; use an audience-targeted Google ID token to invoke B where supported. Verify the precise credential flow for your deployment against the current federation documentation. [G4]

**Optional Microsoft Entra Agent ID track:** Microsoft documents **agent identity blueprints** and agent-specific OBO. Their blueprints/child agent identities do **not** perform a normal interactive `/authorize` sign-in; a regular client app signs in the human and the agent performs downstream token exchange under documented constraints. Keep this as a **separate advanced lab** after ordinary app-registration OBO works. Availability, admin prerequisites and SDK versions must be confirmed for your tenant. [M5]

**Optional Google-managed track:** Google documents **Agent Identity auth manager** as a vault/broker for outbound tool credentials, with ADK integration. Evaluate it as a replacement for a custom token broker, subject to product availability in your project. [G5]

**Failure and recovery:** A Cloud Run 403 after deployment: verify caller principal, `roles/run.invoker`, token audience and runtime service account. Do not expose the service publicly as a debugging shortcut.

## 14. Stage 11 — Prove isolation, failures and recovery

Run these **negative tests** before production deployment. Each is a test of a boundary, not a quiz.

| Inject this failure | Expected result | Recovery path |
|---|---|---|
| No session / expired browser session | 401 or sign-in redirect | Restart Entra login |
| Invalid OAuth `state` or PKCE verifier | Callback rejected; no grant saved | Begin a fresh consent attempt |
| Entra access token `aud=Graph` at agent A | 401, wrong audience | Acquire token for A |
| Entra token `aud=A` at agent C | 401, wrong audience | A performs OBO to C |
| Correct Entra token, missing `access_as_user` scope | 403 | Obtain the proper delegated permission and consent |
| Graph `User.Read` consent missing | OBO fails without privileged fallback | Obtain appropriate consent |
| Call B without Google workload ID token | Cloud Run denies request | Use authorized service account and ID token |
| Call B with ID token for wrong audience | Cloud Run denies request | Request ID token for B |
| B asks broker for Bob's grant while acting for Alice | Deny; no credential returned | Fix identity/grant association |
| Google grant revoked or refresh rejected | Calendar read stops; authorization-needed signal | Delete stale grant and request re-consent |
| Calendar write attempted with read-only scope | Google API rejects | Keep read-only or seek new consent via explicit product decision |
| A2A task ID of another employee | Deny or disclose nothing | Enforce owner/tenant on every task operation |
| Service key / secret exposed | Treat credential as compromised | Revoke/rotate; audit access; prevent recurrence |

### End-to-end request 1: “Am I free Friday?”

```text
1. Browser session identifies Alice as (tenant-01, alice-oid).
2. Web client obtains T_A for API A; A validates and authorizes the caller.
3. A routes to Calendar agent B using Google ID token T_B (aud=B).
4. A also supplies a short-lived signed context for Alice, action=calendar.read.
5. B validates the context. Broker checks Alice owns the linked grant.
6. Broker uses Alice's Google T_CAL to read Google Calendar.
7. B returns only availability intervals. A answers Alice.
8. Bob's request must use Bob's authenticated identity and Bob's own grant.
```

### End-to-end request 2: “Show my Microsoft profile.”

```text
1. Browser calls A with Microsoft T_A (aud=A).
2. A validates T_A and asks Entra for T_C using OBO.
3. A calls C with T_C (aud=C).
4. C validates T_C; C OBO-exchanges it for T_G (aud=Graph).
5. C calls Microsoft Graph /me using T_G.
6. C returns only allowed profile fields; A responds to Alice.
```

**What to observe without logging credentials:** request ID, stage name, authorization decision, user key (prefer a pseudonymous internal ID), caller service principal, target audience, requested scope, provider error category, and latency. Avoid logging bearer tokens, refresh tokens, authorization codes, full unredacted claims, or private Calendar events.

## 15. Suggested implementation boundaries and API contract

```text
multi-agent-auth-study/
  web/                 # OIDC login, callbacks, secure session, /chat
  auth/                # Entra client/API validation, OBO, Google OAuth
  policies/            # employee permissions and grant ownership
  broker/              # managed credential access and read-only operations
  agents/
    orchestrator/      # route safe requests; no direct token exposition to model
    calendar/          # Cloud Run B: Google Calendar specialist
    graph/             # Entra API C: Graph specialist
  tests/
    identity/          # wrong issuer/audience/scope, callback CSRF
    delegation/        # OBO, consent, revocation, cross-user isolation
    workload/          # Cloud Run IAM audience and caller permissions
  infra/               # app registrations, IAM, redirect URI definitions
```

**Minimal HTTP contract (illustrative, not a deployed API):**

| Endpoint | Caller and accepted credential | Responsibility |
|---|---|---|
| `GET /login` | Browser, no session yet | Start Entra auth code + PKCE |
| `GET /auth/entra/callback` | Entra redirect with bound state | Validate login, create app session |
| `POST /chat` | Web session or `T_A` depending on front-end topology | Authorize user and route agent work |
| `GET /auth/google/start` | Authenticated user session | Start separate Calendar OAuth grant |
| `GET /auth/google/callback` | Google redirect with bound state | Save per-user Google grant |
| `POST /agent-b/availability` | Cloud Run service identity + signed user context | Verify caller/owner; read Calendar |
| `POST /agent-c/profile` | Entra delegated `T_C` for C; optionally Cloud Run IAM | Validate C token; OBO to Graph |

**Data ownership:** The employee owns the intent and delegated permission; the Microsoft identity platform and Google issue their own credentials; the application owns its sessions and authorization policy; the broker controls access to stored refresh tokens; each API validates its own inbound token. An LLM output cannot override any of those checks.

## 16. Important corrections to the supplied source guides

Your four uploaded documents contain a useful single-agent calendar project, Entra test-user setup, ADK OAuth examples, and a SPIFFE extension. Use them as a **historical learning baseline**, not as a production security specification. These points need correction or stricter treatment:

| Existing pattern in supplied material | What this guide requires instead |
|---|---|
| Google OAuth `state=user_id` (Entra OID) | Random, unguessable, one-time `state` mapped **server-side** to the authenticated user/session and PKCE verifier. A user ID alone does not protect against CSRF. |
| Passing ID tokens or arbitrary Entra tokens to downstream APIs | Use a **resource-specific access token**; validate the recipient audience. ID tokens are for the client sign-in. |
| Treating Entra login + Google consent as one OBO chain | Keep them separate: Entra OBO is Microsoft identity-platform delegation; Calendar uses Google OAuth. |
| Showing an OAuth authorization code on the callback HTML page | Redeem the code only on the server, clean the redirect URL, and never expose it to the model or ordinary application output. |
| Hardcoded ADK `user1` or shared in-memory auth maps | Bind unique authenticated users to separate sessions and server-side credentials. Use a durable session store when distributed. |
| Using self-fetched SPIFFE SVID to authorize access to a file already readable by the same process | Enforce workload identity at an **independent** gateway, vault or broker boundary; otherwise it is only a self-check. |
| Assuming Google and Entra emails match | Make Google account linkage explicit and verify the grant's actual owner. Use Entra `(tid, oid)` as internal employee identity. |
| Assuming group claims are always present | Handle Entra group overage or choose a more direct application-role design. |
| Enabling implicit ID-token issuance for an authorization-code-only app | Do not add implicit flow settings unless a separate documented flow requires them. Use auth code + PKCE. |
| Treating old ADK auth examples as version-independent | Follow current official ADK `adk_request_credential` flow and pin library versions. |

## 17. Official reference map (checked 13 November 2026)

**Microsoft Entra / OAuth**

- **[M1]** [Microsoft identity platform — OAuth 2.0 On-Behalf-Of flow](https://learn.microsoft.com/en-us/entra/identity-platform/v2-oauth2-on-behalf-of-flow) — assertion audience, confidential middle tiers, delegated permissions.
- **[M2]** [Microsoft identity platform — authorization code flow](https://learn.microsoft.com/en-us/entra/identity-platform/v2-oauth2-auth-code-flow) — OIDC, PKCE, redirect processing, secrets/certificates.
- **[M3]** [Microsoft identity platform — access tokens](https://learn.microsoft.com/en-us/entra/identity-platform/access-tokens) and [claims validation](https://learn.microsoft.com/en-us/entra/identity-platform/claims-validation) — audience, issuer, tenant, scope, caller.
- **[M4]** [Microsoft identity platform — access-token claims reference](https://learn.microsoft.com/en-us/entra/identity-platform/access-token-claims-reference) — groups and overage handling.
- **[M5]** [Microsoft Entra Agent ID — agent OBO](https://learn.microsoft.com/en-us/entra/agent-id/agent-on-behalf-of-oauth-flow), [agent authentication protocols](https://learn.microsoft.com/en-us/entra/agent-id/agent-oauth-protocols) and [create a blueprint](https://learn.microsoft.com/en-us/entra/agent-id/create-blueprint) — advanced distinct product flow.

**Google / agent protocols**

- **[G1]** [Google OAuth — web-server applications](https://developers.google.com/identity/protocols/oauth2/web-server) — user consent, state, offline access and refresh.
- **[G2]** [Google Calendar API scopes](https://developers.google.com/workspace/calendar/api/auth) — `calendar.readonly`, `calendar.freebusy` and authorization choices.
- **[G3]** [Cloud Run — service-to-service authentication](https://docs.cloud.google.com/run/docs/authenticating/service-to-service) — Invoker IAM, ID-token audience and dual headers.
- **[G4]** [Google Cloud — Workload Identity Federation](https://docs.cloud.google.com/iam/docs/workload-identity-federation) and [Azure setup](https://docs.cloud.google.com/iam/docs/workload-identity-federation-with-other-clouds) — keyless external workload access.
- **[G5]** [Google Cloud — Agent Identity auth manager](https://docs.cloud.google.com/iam/docs/auth-manager-overview) — centralized outbound tool credentials and ADK integration.
- **[A1]** [Google ADK — tool authentication](https://adk.dev/tools-custom/authentication/) — credential request/resume and credential storage risks.
- **[A2]** [A2A protocol specification](https://a2a-protocol.org/latest/specification/) — discovery, declared security schemes, per-task authorization and auth-required states.

**Uploaded source material used as the starting point**

- `study_doc(1).md` — existing Calendar agent flow, Entra OBO, token store and SPIFFE explanation.
- `entra_user_guide(1).md` — test-user creation and end-to-end login sequence.
- `adk-entra-auth-guide(1).md` — ADK tool authentication, refresh and deployment notes; version-dependent examples require review.
- `_agent_auth_claude.md` — broader project evolution, linked Entra/Google consent, code paths and proposed workload identity additions.

**Scope note:** Vendor documentation changes. Verify current SDK/API signatures and tenant/product availability before building a production implementation. This guide describes security and architecture decisions rather than claiming that the full system has been implemented or tested.
