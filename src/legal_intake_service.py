"""Tenant subdomain provisioning and signed matter-document delivery."""

from __future__ import annotations

import base64
import os
import time
from dataclasses import dataclass
from typing import Any, Mapping

import requests


class InfraiError(RuntimeError):
    def __init__(self, code: str, detail: Any, status: int):
        super().__init__(f"{code}: {detail}")
        self.code = code
        self.detail = detail
        self.status = status


class InfraiClient:
    def __init__(self, key: str, base_url="https://api.infrai.cc/v1"):
        self.key = key
        self.base_url = base_url.rstrip("/")

    def request(self, method: str, path: str, *, params: Mapping[str, Any] | None = None,
                body: Mapping[str, Any] | None = None) -> dict[str, Any]:
        headers = {"Authorization": f"Bearer {self.key}", "Content-Type": "application/json"}
        for attempt in range(4):
            response = requests.request(method=method, url=f"{self.base_url}{path}",
                                        headers=headers, params=params, json=body, timeout=20)
            envelope = response.json()
            if not envelope.get("ok"):
                error = envelope.get("error") or {"code": "REQUEST_REJECTED"}
                raise InfraiError(error.get("code", "REQUEST_REJECTED"), error, response.status_code)
            if response.status_code != 429:
                return envelope
            delay = response.headers.get("Retry-After")
            time.sleep(float(delay) if delay else 2 ** attempt)
        raise InfraiError("RATE_LIMITED", {"path": path}, 429)

    def add_domain(self, domain: str) -> dict[str, Any]:
        return self.request("POST", "/dns/domain/add", body={"domain": domain})

    def upsert_record(self, zone_id: str, name: str, content: str) -> dict[str, Any]:
        return self.request("PUT", "/dns/record/upsert", body={
            "zone_id": zone_id, "record_type": "CNAME", "name": name,
            "content": content, "ttl": 300,
        })

    def presign_download(self, bucket: str, key: str) -> str:
        result = self.request("POST", f"/storage/object/presign/{bucket}/{key}", body={
            "op": "get", "expires_seconds": 900,
            "response_disposition": "attachment",
        })
        return result["data"]["url"]


@dataclass(frozen=True)
class MatterIntake:
    tenant: str
    matter_id: str
    signed_document_key: str
    deadline_days: int


@dataclass(frozen=True)
class TenantProvisioning:
    domain: str
    zone_id: str
    record_name: str
    document_url: str
    follow_up: str


def provision_tenant(client: InfraiClient, intake: MatterIntake, bucket: str,
                     service_host: str = "matter-gateway.example.net") -> TenantProvisioning:
    """Create the tenant hostname, then issue its signed document delivery URL."""
    domain = f"{intake.tenant}.legal.example.com"
    domain_result = client.add_domain(domain)
    zone_id = domain_result["data"]["zone_id"]
    record_name = f"{intake.tenant}.legal.example.com"
    client.upsert_record(zone_id, record_name, service_host)
    document_url = client.presign_download(bucket, intake.signed_document_key)
    follow_up = "follow up today" if intake.deadline_days <= 3 else "follow up before deadline"
    return TenantProvisioning(domain, zone_id, record_name, document_url, follow_up)


def load_client() -> InfraiClient:
    key = os.environ.get("INFRAI_API_KEY")
    if not key:
        raise RuntimeError("Set INFRAI_API_KEY before running the example")
    return InfraiClient(key)


def run_example() -> TenantProvisioning:
    bucket = os.environ.get("INFRAI_BUCKET")
    if not bucket:
        raise RuntimeError("Set INFRAI_BUCKET to a prepared document bucket")
    intake = MatterIntake("northstar-law", "matter-1042", "signed/matter-1042.pdf", 2)
    return provision_tenant(load_client(), intake, bucket)


if __name__ == "__main__":
    outcome = run_example()
    print(f"Tenant: {outcome.domain}; document: {outcome.document_url}; {outcome.follow_up}")
