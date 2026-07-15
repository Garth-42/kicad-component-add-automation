from __future__ import annotations

import base64
import json
import os
from dataclasses import dataclass
from typing import Any
from urllib import request
from urllib.error import HTTPError, URLError

from kcf.ingestion.normalized import (
    CadAsset,
    NormalizedPart,
    PartLookupQuery,
    PriceBreak,
    SourceFetchResult,
    SourceLink,
    TechnicalParameter,
    sha256_json,
    utc_now_iso,
)


class DigiKeyApiError(RuntimeError):
    pass


@dataclass(frozen=True)
class DigiKeyCredentials:
    client_id: str
    client_secret: str

    @classmethod
    def from_env(cls) -> DigiKeyCredentials:
        client_id = os.environ.get("DIGIKEY_CLIENT_ID") or os.environ.get("DIGIKEY_CLIENTID")
        client_secret = os.environ.get("DIGIKEY_CLIENT_SECRET") or os.environ.get("DIGIKEY_CLIENTSECRET")
        if not client_id or not client_secret:
            raise DigiKeyApiError("DIGIKEY_CLIENT_ID and DIGIKEY_CLIENT_SECRET are required for live DigiKey lookups")
        return cls(client_id=client_id, client_secret=client_secret)


@dataclass(frozen=True)
class DigiKeySettings:
    sandbox: bool = False
    locale_site: str = "US"
    locale_language: str = "en"
    locale_currency: str = "USD"

    @property
    def api_base_url(self) -> str:
        return "https://sandbox-api.digikey.com" if self.sandbox else "https://api.digikey.com"


class DigiKeyClient:
    """Small stdlib-only client for DigiKey Product Information V4 lookups.

    DigiKey's Product Information V4 APIs use OAuth bearer tokens plus the
    X-DIGIKEY-Client-Id header. Sandbox lookups use the same paths on the
    sandbox host.
    """

    def __init__(self, credentials: DigiKeyCredentials, settings: DigiKeySettings | None = None) -> None:
        self.credentials = credentials
        self.settings = settings or DigiKeySettings()

    def access_token(self) -> str:
        token_url = f"{self.settings.api_base_url}/v1/oauth2/token"
        body = b"grant_type=client_credentials"
        basic = base64.b64encode(f"{self.credentials.client_id}:{self.credentials.client_secret}".encode("utf-8")).decode("ascii")
        req = request.Request(
            token_url,
            data=body,
            headers={"Authorization": f"Basic {basic}", "Content-Type": "application/x-www-form-urlencoded"},
            method="POST",
        )
        payload = self._json_request(req)
        token = payload.get("access_token")
        if not isinstance(token, str) or not token:
            raise DigiKeyApiError("DigiKey token response did not contain access_token")
        return token

    def product_details(self, product_number: str) -> dict[str, Any]:
        token = self.access_token()
        url = f"{self.settings.api_base_url}/products/v4/search/{product_number}/productdetails"
        req = request.Request(url, headers=self._product_headers(token), method="GET")
        return self._json_request(req)

    def keyword_search(self, keyword: str, limit: int = 10) -> dict[str, Any]:
        token = self.access_token()
        url = f"{self.settings.api_base_url}/products/v4/search/keyword"
        body = json.dumps({"Keywords": keyword, "Limit": limit}).encode("utf-8")
        req = request.Request(url, data=body, headers={**self._product_headers(token), "Content-Type": "application/json"}, method="POST")
        return self._json_request(req)

    def _product_headers(self, token: str) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {token}",
            "X-DIGIKEY-Client-Id": self.credentials.client_id,
            "X-DIGIKEY-Locale-Site": self.settings.locale_site,
            "X-DIGIKEY-Locale-Language": self.settings.locale_language,
            "X-DIGIKEY-Locale-Currency": self.settings.locale_currency,
            "Accept": "application/json",
        }

    def _json_request(self, req: request.Request) -> dict[str, Any]:
        try:
            with request.urlopen(req, timeout=30) as response:  # nosec: user-configured official API endpoint
                data = response.read().decode("utf-8")
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise DigiKeyApiError(f"DigiKey HTTP {exc.code}: {detail}") from exc
        except URLError as exc:
            raise DigiKeyApiError(f"DigiKey request failed: {exc.reason}") from exc
        parsed = json.loads(data)
        if not isinstance(parsed, dict):
            raise DigiKeyApiError("DigiKey response was not a JSON object")
        return parsed


class DigiKeyAdapter:
    source_name = "digikey"
    license_notes = "DigiKey API data should be retained according to the DigiKey API User Agreement; default to external references plus hashes."

    def __init__(self, client: DigiKeyClient) -> None:
        self.client = client

    @classmethod
    def from_env(cls, *, sandbox: bool = False) -> DigiKeyAdapter:
        return cls(DigiKeyClient(DigiKeyCredentials.from_env(), DigiKeySettings(sandbox=sandbox)))

    def lookup_part(self, query: PartLookupQuery) -> SourceFetchResult:
        product_number = query.source_part_number or query.manufacturer_part_number
        payload = self.client.product_details(product_number)
        return result_from_product_details(payload, query=query)


def result_from_product_details(payload: dict[str, Any], query: PartLookupQuery | None = None, retrieved_at: str | None = None) -> SourceFetchResult:
    retrieved = retrieved_at or utc_now_iso()
    q = query or PartLookupQuery(manufacturer_part_number=str(_first(_dig(payload, "Product", "ManufacturerProductNumber"), _dig(payload, "ManufacturerProductNumber"), "unknown")))
    normalized, warnings = normalize_product_details(payload, retrieved_at=retrieved)
    return SourceFetchResult(
        source_name="digikey",
        retrieved_at=retrieved,
        request_fingerprint=q.fingerprint(),
        raw_payload_sha256=sha256_json(payload),
        normalized=normalized,
        license_notes=DigiKeyAdapter.license_notes,
        warnings=warnings,
    )


def normalize_product_details(payload: dict[str, Any], retrieved_at: str | None = None) -> tuple[NormalizedPart, list[str]]:
    retrieved = retrieved_at or utc_now_iso()
    product = _product_object(payload)
    warnings: list[str] = []
    if product is payload and "Product" not in payload:
        warnings.append("DigiKey payload did not contain a Product object; normalized from top-level fields")

    manufacturer = _string(_dig(product, "Manufacturer", "Name")) or _string(_dig(product, "Manufacturer", "Value")) or _string(_dig(product, "ManufacturerName"))
    mpn = _string(_first(_dig(product, "ManufacturerProductNumber"), _dig(product, "ManufacturerPartNumber")))
    dk_number = _string(_first(_dig(product, "ProductNumber"), _dig(product, "DigiKeyProductNumber")))
    description = _string(_first(_dig(product, "Description", "ProductDescription"), _dig(product, "Description", "DetailedDescription"), _dig(product, "ProductDescription"), _dig(product, "DetailedDescription")))
    datasheet = _string(_first(_dig(product, "DatasheetUrl"), _dig(product, "PrimaryDatasheet"), _dig(product, "Documents", "DatasheetUrl")))
    product_url = _string(_first(_dig(product, "ProductUrl"), _dig(product, "ProductDetailUrl")))
    image_url = _string(_first(_dig(product, "PhotoUrl"), _dig(product, "PrimaryPhoto")))
    status = _string(_dig(product, "ProductStatus", "Status")) or _string(_dig(product, "ProductStatus"))
    category = _category_path(product)
    parameters = _parameters(product)
    price_breaks = _price_breaks(product)
    documents = []
    if datasheet:
        title = f"{mpn or dk_number or 'DigiKey'} datasheet"
        documents.append(SourceLink(title=title, kind="datasheet", url=datasheet, retrieved_at=retrieved, retention_mode="external_reference"))
    if product_url:
        documents.append(SourceLink(title=f"{mpn or dk_number or 'DigiKey'} product page", kind="product_page", url=product_url, retrieved_at=retrieved, retention_mode="external_reference"))

    rohs = _parameter_value(parameters, "rohs") or _string(_dig(product, "Classifications", "RohsStatus"))
    reach = _parameter_value(parameters, "reach") or _string(_dig(product, "Classifications", "ReachStatus"))

    part = NormalizedPart(
        manufacturer=manufacturer,
        manufacturer_part_number=mpn,
        distributor_part_numbers=[dk_number] if dk_number else [],
        product_url=product_url,
        datasheet_url=datasheet,
        image_url=image_url,
        description=description,
        lifecycle_status=status,
        availability=_int(_first(_dig(product, "QuantityAvailable"), _dig(product, "QuantityAvailableForPackageType"))),
        price_breaks=price_breaks,
        minimum_order_quantity=_int(_dig(product, "MinimumOrderQuantity")),
        packaging=_string(_dig(product, "Packaging", "Value")) or _string(_dig(product, "Packaging", "Name")) or _string(_dig(product, "Packaging")),
        rohs=rohs,
        reach=reach,
        distributor_category=category,
        manufacturer_family=_parameter_value(parameters, "series"),
        keywords=[item for item in [category, _parameter_value(parameters, "series")] if item],
        technical_parameters=parameters,
        documents=documents,
        cad_assets=_cad_assets(product),
    )
    if not part.manufacturer_part_number:
        warnings.append("Manufacturer part number missing from DigiKey payload")
    if not part.manufacturer:
        warnings.append("Manufacturer missing from DigiKey payload")
    return part, warnings


def _product_object(payload: dict[str, Any]) -> dict[str, Any]:
    product = payload.get("Product")
    if isinstance(product, dict):
        return product
    products = payload.get("Products")
    if isinstance(products, list) and products and isinstance(products[0], dict):
        return products[0]
    return payload


def _parameters(product: dict[str, Any]) -> list[TechnicalParameter]:
    items = product.get("Parameters") or product.get("ProductVariations") or []
    params: list[TechnicalParameter] = []
    if isinstance(items, list):
        for index, item in enumerate(items):
            if not isinstance(item, dict):
                continue
            name = _string(_first(item.get("ParameterText"), item.get("Parameter"), item.get("Name")))
            value = _string(_first(item.get("ValueText"), item.get("Value"), item.get("ParameterValue")))
            unit = _string(_first(item.get("Unit"), item.get("Units")))
            if name and value:
                params.append(TechnicalParameter(name=name, value=value, unit=unit, source_field=f"Product.Parameters[{index}]"))
    return params


def _price_breaks(product: dict[str, Any]) -> list[PriceBreak]:
    items = product.get("StandardPricing") or product.get("Pricing") or []
    prices: list[PriceBreak] = []
    if isinstance(items, list):
        for item in items:
            if not isinstance(item, dict):
                continue
            quantity = _int(_first(item.get("BreakQuantity"), item.get("Quantity")))
            unit_price = _string(_first(item.get("UnitPrice"), item.get("UnitPriceText"), item.get("Price")))
            if quantity is not None and unit_price:
                prices.append(PriceBreak(quantity=quantity, unit_price=unit_price, currency=_string(item.get("Currency"))))
    return prices


def _cad_assets(product: dict[str, Any]) -> list[CadAsset]:
    assets: list[CadAsset] = []
    media = product.get("MediaLinks") or product.get("Media") or []
    if isinstance(media, list):
        for item in media:
            if not isinstance(item, dict):
                continue
            title = (_string(item.get("Title")) or _string(item.get("MediaType")) or "").lower()
            url = _string(_first(item.get("Url"), item.get("URL"), item.get("Value")))
            if url and any(token in title for token in ["cad", "3d", "model", "eda"]):
                assets.append(CadAsset(kind=title or "media", url_or_ref=url, retention_mode="external_reference"))
    return assets


def _category_path(product: dict[str, Any]) -> str | None:
    category = product.get("Category")
    if isinstance(category, dict):
        names = []
        parent = category
        while isinstance(parent, dict):
            name = _string(_first(parent.get("Name"), parent.get("Value")))
            if name:
                names.append(name)
            parent = parent.get("Parent")
        return " > ".join(reversed(names)) if names else None
    return _string(category)


def _parameter_value(parameters: list[TechnicalParameter], needle: str) -> str | None:
    lowered = needle.lower()
    for param in parameters:
        if lowered in param.name.lower():
            return param.value
    return None


def _dig(data: Any, *keys: str) -> Any:
    current = data
    for key in keys:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def _first(*values: Any) -> Any:
    for value in values:
        if value not in (None, "", []):
            return value
    return None


def _string(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value.strip() or None
    return str(value)


def _int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
