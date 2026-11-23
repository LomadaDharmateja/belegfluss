# ADR-0004: Background processing with Azure Storage Queue, DB status as source of truth

- **Status:** Proposed
- **Date:** 2026-11-23
- **Milestone:** M0 (implemented in M2)

## Context

Processing a document (parse or LLM extraction, validator call, checks) takes from a fraction of a second to tens of
seconds. It must not block the upload request, must survive restarts, must retry on transient errors, and should
scale to zero when idle to save money.

Facts checked: Azure Container Apps supports event-driven scaling with the KEDA `azure-queue` scaler and scale to
zero ([jobs](https://learn.microsoft.com/en-us/azure/container-apps/jobs),
[scaling](https://learn.microsoft.com/en-us/azure/container-apps/scale-app)). Storage Queue messages are limited
to 64 KB ([pricing page](https://azure.microsoft.com/en-us/pricing/details/storage/queues/)). Service Bus Basic has
queues but no topics ([pricing page](https://azure.microsoft.com/en-us/pricing/details/service-bus/)).

## Options

1. **FastAPI BackgroundTasks:** no infrastructure, but jobs are lost on restart, there are no retries, and the work
   can't scale separately.
2. **PostgreSQL as the queue** (`SELECT … FOR UPDATE SKIP LOCKED`, or the `procrastinate` library): transactional
   with our data (no dual write), but scaling a worker to zero needs a custom KEDA scaler, and polling adds DB load.
3. **Azure Storage Queue** (emulated by Azurite locally), with the document status in PostgreSQL as the source of
   truth.
4. **Azure Service Bus:** dead-lettering and sessions built in, but more than we need.
5. **Celery + Redis:** popular, but Redis must be operated, and it is not Azure-native.

## Decision

**Option 3.**
- The API inserts the document row (`status = received`) and then enqueues a message with only `{document_id}`.
- The worker takes a row lock, sets `processing`, does the work, and writes results with the pipeline version.
  It is **idempotent**: re-processing the same document replaces its derived data.
- A small **sweeper** re-enqueues documents stuck in `received` or `processing` longer than a threshold. This covers
  the dual-write gap (DB insert succeeded, enqueue failed) and crashed workers.
- After N failed deliveries the message goes to a **poison queue**, and the document becomes `failed` with a
  user-visible reason.
- Locally and in CI: Azurite. In Azure: a Storage Account queue with Managed Identity. In AKS (M8): same queue,
  KEDA ScaledObject.

Why not 2: transactional enqueue is attractive, but the KEDA/Container Apps scale-to-zero story is simpler and
cheaper with Storage Queue, and the dual-write gap is closed by the sweeper. Why not 4/5: features we don't need, or
extra infrastructure.

## Consequences

- One more emulator in Docker Compose (Azurite, which we need for Blob anyway).
- We must test the sweeper and the poison path (fault-injection tests in M2).
- If we later need ordering or sessions, Service Bus can replace the queue behind the same small interface (new ADR).

## Sources

Linked inline above (read 2026-11-23). Azurite emulator: https://learn.microsoft.com/en-us/azure/storage/common/storage-use-azurite
