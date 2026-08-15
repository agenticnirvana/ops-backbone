# Design packs

Each subdirectory is a **stack overlay** the shared console loads.

```
designs/
  d1/stack.js + logos/   Grafana · Prometheus · Langfuse
  d2/stack.js + logos/   Kibana · VictoriaMetrics · Phoenix · Weaviate
  d3/stack.js + logos/   OpenSearch · Mimir
```

`../designs.js` merges `window.ARCH_DESIGN_PACKS`. Do not put D1 tool names in D2 `stack.js`.
