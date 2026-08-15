## Reindex runbooks (enterprise pipeline)

On-demand (local stack running):

```bash
cd deploy
./deploy.sh reindex incremental   # or: full
```

API:

```bash
curl -X POST http://localhost:8092/v1/ingest/reindex \
  -H "Authorization: Bearer $INGESTION_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"mode":"incremental","sync_drive":true}'
```

**Midnight cron:** `RUNBOOK_CRON_SCHEDULE=0 0 * * *` — syncs Google Drive folder and incremental reindex.

Dev-only CLI (no ingestion service):

```bash
cd agent && python -m rag.build_index --mode full
```
