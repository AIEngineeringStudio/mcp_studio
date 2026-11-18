# Service layers and persistence

**Outcome:** Separate MCP translation from business rules and durable storage.

**Prerequisites:** [05: Tools and their contracts](05-tool-contracts.md), [15: Async I/O and concurrent requests](15-async-concurrency.md).

## A growing handler

The initial handler can return a fixture directly. As requirements add access
checks, validation, updates, and history, a large handler becomes difficult to
test and reuse.

```
MCP handler --> application service --> repository --> storage
translation     business operation     data access
```

A service coordinates a business use case. A repository is an application
interface for retrieving and storing domain data. These are design choices,
not MCP-required layers.

## Evolve one operation

The first `get_ticket` handler delegates to `lookup_ticket`. A production
extension might introduce `TicketService.get(caller, ticket_id)`, which checks
access and asks a repository for the record.

The handler should translate the protocol input and result. The service should
not need to parse a JSON-RPC envelope. The repository should not decide how a
model sees a tool description.

This division supports a direct unit test of rules, a repository test against
a real test database, and a contract test through MCP.

## Add storage because of a requirement

An in-memory dictionary loses updates when the process exits. A durable
database becomes justified when changes must survive restart or be shared
across workers.

SQLite is useful for a small local exercise. PostgreSQL may fit concurrent
service workloads and shared deployments. Do not make a database a prerequisite
for learning discovery and dispatch.

A connection pool reuses open database connections. It does not make queries
correct, authorize rows, or remove the need to release connections.

## Transactions and concurrent updates

Suppose closing a ticket must also insert an audit entry. If both records
live in the same database, a transaction can make the update and audit insert
commit together. A failure rolls back both rather than leaving half the
business operation.

A separate email API is outside that database transaction. A durable outbox or
another delivery design is needed if notification delivery must be reconciled.
Do not claim a local transaction provides exactly-once behavior across unrelated
systems.

## Define the data boundary

Use parameterized queries. Apply tenant and ownership constraints in the
data-access path. Select only needed fields. For concurrent changes, decide
whether optimistic version checks, locking, or another strategy matches the
business rule.

A useful failure experiment is “the database write fails after validation.”
The user should receive a controlled failure, and a subsequent read should
show that no partial database change escaped.

**Professional articulation:**

> “The MCP handler is an adapter. The service owns the use case, and the
> repository owns the persistence boundary.”

## Sources and next step

- [Archive: conversations/chatgpt/4_ServiceLayer_Persistence_AsyncIO.md](../../conversations/chatgpt/4_ServiceLayer_Persistence_AsyncIO.md)
- [Archive: _learning_resources/walkthrough_doc.md](../../_learning_resources/walkthrough_doc.md)
- [Official reference](https://www.postgresql.org/docs/current/tutorial-transactions.html) — checked 2026-11-15.

Next: [Application lifespan and dependency ownership](17-application-lifespan.md).

