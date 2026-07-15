import json
from pathlib import Path

from kcf.cli.main import run
from kcf.ingestion.normalized import PartLookupQuery
from kcf.ingestion.sources.digikey import result_from_product_details

FIXTURE = Path("tests/fixtures/ingestion/digikey_productdetails.json")


def test_digikey_productdetails_normalizes_to_source_fetch_result() -> None:
    payload = json.loads(FIXTURE.read_text(encoding="utf-8"))

    result = result_from_product_details(payload, query=PartLookupQuery(manufacturer_part_number="1751248"), retrieved_at="2026-07-15T00:00:00Z")

    assert result.source_name == "digikey"
    assert result.request_fingerprint
    assert len(result.raw_payload_sha256) == 64
    assert result.normalized.manufacturer == "Phoenix Contact"
    assert result.normalized.manufacturer_part_number == "1751248"
    assert result.normalized.distributor_part_numbers == ["277-1751248-ND"]
    assert result.normalized.datasheet_url == "https://example.test/1751248.pdf"
    assert result.normalized.distributor_category == "Connectors, Interconnects > Terminal Blocks"
    assert result.normalized.manufacturer_family == "COMBICON MKDS"
    assert result.normalized.technical_parameters[0].name == "Pitch"
    assert result.normalized.price_breaks[0].quantity == 1
    assert result.normalized.documents[0].retention_mode == "external_reference"
    assert result.normalized.cad_assets[0].kind == "3d model"


def test_cli_ingest_lookup_can_normalize_saved_digikey_json(tmp_path: Path) -> None:
    output = tmp_path / "digikey-result.json"

    code = run(["ingest", "lookup", "--source", "digikey", "--mpn", "1751248", "--raw-json", str(FIXTURE), "--output", str(output)])

    assert code == 0
    data = json.loads(output.read_text(encoding="utf-8"))
    assert data["source_name"] == "digikey"
    assert data["normalized"]["manufacturer"] == "Phoenix Contact"
    assert data["normalized"]["manufacturer_part_number"] == "1751248"
