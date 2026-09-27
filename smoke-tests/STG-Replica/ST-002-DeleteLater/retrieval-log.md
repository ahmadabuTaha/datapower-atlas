# ST-002 Retrieval Log

## START

1. Used the three-row `index/STG-REPLICA/service_journey_summary.csv` enumeration.
2. Selected `DeleteLater` as a bounded 79-operation service with configured and programmatic routing evidence.
3. Retrieved only its record from `index/STG-REPLICA/service_journeys.jsonl`.

## SUPPORTING RETRIEVAL

1. Aggregated only operation records whose parent service is `DeleteLater` to validate the 79-operation policy-wide distribution.
2. Inspected three representative operation patterns in detail:
   - confirmed XSLT `dp:sql-execute` database egress;
   - confirmed GatewayScript `urlopen.open` HTTP egress;
   - candidate response/error backside paths.
3. Retrieved only the `DeleteLater` rows from `service_journey_findings.csv`.
4. Queried the `local/WPS/WPS.JS` inventory, relationship, and sensitivity rows only.

## REFERENCED FILES

Opened narrowly:

- `local/MOL_SPs_Ext/Qiwa_Insert_UnifiedNumber.xsl` — verify exact `dp:sql-execute` syntax.
- `local/WPS/WPS.JS` — verify `var://service/URI`, dynamic target, POST, and `urlopen.open`; sensitive header value omitted.
- `local/NonXMLProcessing.xsl` — verify absence of outbound behavior in the candidate response operation.

## RAW CFG

**NOT OPENED.**

Reason: the Journey and operation bundles contain consistent STG-Replica CFG line pointers, and the referenced artifacts directly resolve operation semantics.

## RETRIEVAL AUDIT

- No STG-domain evidence was consulted.
- No cross-domain comparison or resolution occurred.
- No full flattened CSV was loaded into reasoning context.
- No unrelated STG-Replica artifact was opened.
- No full CFG read occurred.
- No pipeline stage was rerun.
- No parser, taxonomy, mapping, resolver, index, schema, or Journey output was modified.
- No unnecessary broad retrieval occurred.

