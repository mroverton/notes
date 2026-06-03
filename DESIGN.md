# Design & Operations Notes

This document addresses the operational questions from `NOTES.md`. The code
itself is intentionally a *minimal base*; this is where we reason about what
production would actually require. Several items below are described rather than
implemented — that's deliberate.

---

## 1. How would you deploy this service to production?

**Build & artifact.** The app already ships as a container (`Dockerfile`). CI
builds the image, runs the test suite, and pushes a tagged image to a registry.

**Run it.** Run the stateless app container on a managed platform (ECS/Fargate,
Cloud Run, or Kubernetes). Because auth is JWT-based and the app holds no
session state, you can run **N identical replicas** behind a load balancer and
scale horizontally.

**Database.** Use a **managed Postgres** (e.g. RDS / Cloud SQL) rather than a
container — you get backups, point-in-time recovery, failover, and patching.
The app connects via `DATABASE_URL` from the environment.

**Configuration & secrets.** All config comes from the environment (12-factor).
`JWT_SECRET` and DB credentials come from a **secrets manager**, injected at
runtime — never baked into the image or committed.

**Edge.** Terminate TLS at a load balancer / API gateway in front of the app so
all traffic is HTTPS. Optionally do rate limiting and WAF there.

**Schema.** Run migrations as a **separate step** in the deploy pipeline (see §3)
— *not* `create_all` on startup, which is only used here for simplicity.

---

## 2. What would you monitor or alert on?

**The four "golden signals":**
- **Latency** — p50/p95/p99 response time per endpoint. Alert on p99 regressions.
- **Traffic** — requests/sec, to understand load and spot anomalies.
- **Errors** — rate of 5xx (server faults) and a watch on 4xx spikes (e.g. a
  flood of 401s can mean a broken client or a credential-stuffing attack).
- **Saturation** — CPU/memory of app replicas, and especially **DB connection
  pool usage** (exhaustion is a classic outage cause).

**Database:** slow-query log, replication lag (if using replicas), disk usage,
and connection count.

**Application-specific & security:** failed-login rate and per-IP/per-user
auth-failure spikes (brute-force / stuffing signals), and 403/404 spikes on
notes routes (possible enumeration attempts).

**Health:** the `/health` endpoint feeds liveness/readiness probes; alert if
replicas go unhealthy or fail to start.

Implementation: structured JSON logs shipped to a log store, metrics to
Prometheus/CloudWatch with dashboards + alerts, and distributed tracing
(OpenTelemetry) to find where latency is spent.

---

## 3. How would you handle database migrations over time?

`Base.metadata.create_all()` on startup (what this base does) **only creates
missing tables** — it can't alter columns, add indexes, or backfill data, and
running schema changes from app startup is racy with multiple replicas.

For production, introduce **Alembic** (SQLAlchemy's migration tool):

1. Each schema change is a versioned, reviewed migration script in `migrations/`,
   committed to git alongside the model change.
2. Migrations are **forward-only** and **backward-compatible** where possible, so
   old and new app versions can run simultaneously during a rolling deploy
   (e.g. add a nullable column first, backfill, then enforce constraints later).
3. Migrations run as a **dedicated pipeline step** before the new app version
   starts — never on app startup.
4. For large tables, use online/non-blocking patterns (create indexes
   concurrently, batch backfills) to avoid long locks.

This makes schema evolution auditable, repeatable across environments, and safe
to roll back.

---

## 4. What would change to support 10,000 concurrent users?

The app is already stateless, which is the key enabler. The realistic
bottlenecks become the database and connection management:

- **Horizontal scaling of the app** — run many replicas behind the load
  balancer; autoscale on CPU/latency. No code change required.
- **Database connections** — 10k clients must not mean 10k DB connections. Put
  **PgBouncer** (or RDS Proxy) in front of Postgres to pool/multiplex
  connections, and size SQLAlchemy's pool per replica accordingly.
- **Read scaling** — listing/reading notes dominates. Add **read replicas** and
  route read-only queries to them; keep writes on the primary.
- **Caching** — cache hot, read-heavy data (e.g. a user's note list) in Redis
  with sensible invalidation on write.
- **Pagination** — `GET /notes` must paginate (limit/offset or keyset) so a
  single response can't grow unbounded.
- **Indexes** — ensure indexes on the columns we filter/join on (`notes.owner_id`,
  `shares.note_id`, `shares.shared_with_user_id` — already present in the models).
- **Async I/O** — move to FastAPI's async routes with an async DB driver so each
  worker handles many concurrent requests while waiting on the DB.
- **Rate limiting & backpressure** — protect the system from abusive clients at
  the gateway.
- **Token strategy** — short-lived access tokens + refresh tokens, and a
  revocation list (e.g. in Redis) if immediate logout is required.

The theme: scale the **stateless tier** out freely, and protect/scale the
**stateful database tier** with pooling, replicas, caching, and good indexes.
