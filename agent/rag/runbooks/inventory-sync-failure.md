# Inventory sync failure

**Service:** inventory-service  
**Severity:** P1  
**Triggers:** stock mismatch alerts, oversell incidents, ERP sync job failed

## Diagnosis

1. Check last successful ERP sync timestamp (`inventory_erp_last_sync_age`)
2. Review failed sync job logs in Loki for API auth or timeout errors
3. Compare warehouse DB counts vs ERP source for sample SKUs
4. Identify if checkout completed orders for zero-stock items
5. Verify no duplicate sync workers running (race condition)

## Remediation

- Trigger manual full sync from ERP — **requires HITL approval** during peak hours
- Enable oversell protection mode (`INVENTORY_HARD_STOP=true`) until sync completes
- Pause marketing campaigns driving traffic to affected SKUs
- Reconcile negative stock records before re-enabling sales

## Verification

- ERP sync job success logged within last 15 minutes
- Stock counts match ERP for audited sample of 50 SKUs
- No new oversell alerts for 1 hour

## Escalation

Notify commerce ops and page fulfillment lead if customer orders affected.
