from legal_intake_service import MatterIntake, TenantProvisioning, provision_tenant


class FakeClient:
    def __init__(self):
        self.calls = []

    def add_domain(self, domain):
        self.calls.append(("domain", domain))
        return {"data": {"zone_id": "zone-7"}}

    def upsert_record(self, zone_id, name, content):
        self.calls.append(("record", zone_id, name, content))
        return {"data": {"record_id": "record-7"}}

    def presign_download(self, bucket, key):
        self.calls.append(("presign", bucket, key))
        return "https://objects.example/signed/matter-1042.pdf"


def test_short_deadline_creates_hostname_and_same_tenant_delivery():
    client = FakeClient()
    result = provision_tenant(
        client,
        MatterIntake("northstar-law", "matter-1042", "signed/matter-1042.pdf", 2),
        "legal-documents",
    )

    assert isinstance(result, TenantProvisioning)
    assert result.domain == "northstar-law.legal.example.com"
    assert result.zone_id == "zone-7"
    assert result.follow_up == "follow up today"
    assert client.calls == [
        ("domain", "northstar-law.legal.example.com"),
        ("record", "zone-7", "northstar-law.legal.example.com", "matter-gateway.example.net"),
        ("presign", "legal-documents", "signed/matter-1042.pdf"),
    ]
