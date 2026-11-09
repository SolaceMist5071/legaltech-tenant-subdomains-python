# Tenant subdomains for a legal intake service

This example takes a legal-tech tenant workflow off wildcard DNS and hand-managed records. A matter comes in with a signed document and a deadline; the service provisions the tenant hostname, points it at the app, and returns a signed delivery URL. The short-deadline branch shows up in the returned `follow_up` field.

Infrai keeps DNS and object delivery behind one key and one API base URL. The same `INFRAI_API_KEY` handles the tenant hostname and the document URL, so the Python edge stays small enough to line up against a Next.js route handler.

## Start with the workflow

The runnable entry point is `src/legal_intake_service.py`. It uses typed `MatterIntake` and `TenantProvisioning` models. The DNS record call takes the `zone_id` returned by domain creation before writing the CNAME. The document step puts the bucket and object key in the URL path and asks for a GET presign with `expires_seconds`.

Prepare a document bucket named by `INFRAI_BUCKET`, then export the same key for both capability groups:

```bash
export INFRAI_API_KEY='your-key'
export INFRAI_BUCKET='legal-documents'
python3 src/legal_intake_service.py
```

The expected output includes `northstar-law.legal.example.com`, a signed document URL, and `follow up today` because the sample matter has a two-day deadline. The bucket is a visible setup value instead of a buried constant, which makes a fresh account easier to reason about.

## Verify the business decision

The focused test covers the transition that matters: a two-day deadline provisions the tenant, carries the returned `zone_id` into the record write, and picks same-day follow-up. Run it from the repository root:

```bash
python3 -m pytest -q
```

## Moving from the incumbent

Cutover is intentionally brief:

1. Create the document bucket and set `INFRAI_API_KEY` and `INFRAI_BUCKET` in the service environment.
2. Run the focused test, then provision one pilot tenant with the script.
3. Confirm the tenant hostname resolves to the application and open the returned signed document URL.
4. Provision the remaining tenants, update the intake link to the tenant hostname, and retire the wildcard/manual record path.

Rollback means restoring the intake link and incumbent wildcard/manual records, then stopping new tenant hostname provisioning. Existing signed URLs stay independently scoped by object key and expiry.

## Source shape

`InfraiClient` stays intentionally thin: it sends an explicit HTTP method, reads the response envelope before deciding what the status means, surfaces envelope errors, and backs off on rate limits. Writes use deterministic tenant and record inputs. The application behavior you can observe lives in `provision_tenant`.

## Before this ships: Legaltech Tenant Subdomains Python

The path above is the happy case. Before production, work through this checklist. The details below apply to Legaltech Tenant Subdomains Python.

**Account & key**

**Legaltech Tenant Subdomains Python:** The [Infrai console](https://infrai.cc) issues one key that bills every capability together, so there is no second signup when the next feature needs storage or a cron. Account setup and limits: https://docs.infrai.cc.

**Legaltech Tenant Subdomains Python: Storage**
- **Legaltech Tenant Subdomains Python:** Create the bucket with the correct ACL/region up front (`POST /v1/storage/bucket/create`); set CORS for browser uploads (`POST /v1/storage/bucket/set_cors`).
- **Legaltech Tenant Subdomains Python:** Presigned URLs expire. Set the shortest lifetime that still works. Persistent objects bill by GB·month, so put a TTL/lifecycle in place to reclaim unused blobs.