# Data ingestion plan for distributor and manufacturer sources

## Recommendation

The right first direction is to build deterministic API/schema ingestion before adding autonomous agents. The first production path should be source adapters, a canonical mapper, and provenance/validation. Agents can be introduced later as a fallback for PDFs, missing fields, and source conflicts, but they should not be the primary mechanism for pulling known distributor/manufacturer data.

This recommendation fits KiCad Component Factory's current architecture: deterministic component generation from canonical YAML, source manifests with hashes, and human review gates. The ingestion system should therefore preserve traceability and repeatability rather than hide decisions behind open-ended browsing or agent behavior.

## Research snapshot, July 2026

| Source | Public integration surface | Useful data for this app | Initial recommendation |
| --- | --- | --- | --- |
| DigiKey | Official API developer portal. Product Information V4 supports product search by part number, description, manufacturer, or category; ProductDetails supports single-product details and exposes related endpoints such as manufacturers, categories, media, pricing, substitutions, associations, alternate packaging, and product change notifications. Uses OAuth flows and sandbox/production applications. | Strong for distributor SKU, manufacturer, MPN, description, categories, datasheet/media links, lifecycle-ish catalog status, parameters, pricing/availability, alternates, and product-change notifications. Less reliable for final footprint geometry. | Implement first as the primary distributor adapter because the API surface is explicit and broad. Store raw response hashes and map only fields with stable semantics. |
| Mouser | Official Search API documentation exists and advertises product data, cart, and ordering capabilities. Terms emphasize API keys, call limits, attribution, no bulk caching/prefetching, and restrictions on building independent databases from Mouser data. | Strong for search-by-part-number, manufacturer, availability, datasheet/product URL, RoHS, pricing, and parametric attributes. Need terms-aware retention: keep source references/hashes and derived canonical fields, not a bulk Mouser mirror. | Implement after DigiKey, with a license/retention review before caching any response bodies. Use it as a corroborating distributor source. |
| RS Online / RS Group | Publicly discoverable pages emphasize eProcurement/PunchOut and enterprise integrations more than an open catalog API. Third-party references suggest API-key based integrations exist, but official public product-data API documentation was not clearly available in the quick research pass. | Potentially useful for stock, pricing, distributor SKUs, datasheet links, and industrial/electromechanical parts, but access model and terms need confirmation. | Treat as a second-wave adapter. Start with a manual discovery spike: contact RS/eProcurement or use approved account integration. Do not build scrapers as the first approach. |
| Phoenix Contact | Official API page lists Product Commercial API, Product Information API, and Asset Administration Shell API. Product Information API covers general information, technical details, classifications, approvals, declarations, and certificates. AAS API exposes product information using IEC 63278-1 for non-exclusive catalog products and selected manufactured instances. | Very strong for manufacturer-authoritative metadata, technical details, classifications, approvals, declarations, certificates, and possibly structured engineering data. Likely best source of truth for Phoenix Contact parts. | Implement as the first manufacturer adapter, especially for terminal blocks/connectors. Prefer Product Information/AAS data over distributor-parametric data when conflicts occur. |
| Weidmuller | Public pages emphasize digital engineering, engineering data, interfaces, eShop, OCI, EDI, eCAD data, configurators, product catalogs, and support-center downloads. Public open product-data API documentation was not clearly identified in the quick research pass. | Useful manufacturer-authoritative product data likely exists through engineering-data downloads, eCAD data, WMC/configurator workflows, EDI/eShop interfaces, and support-center assets. May provide datasheets, 3D models, and EDA/eCAD data, but integration may be less direct than Phoenix Contact. | Treat as a manufacturer source with an engineering-data/download adapter first, not an API adapter unless an official API is obtained. Do a focused access/format spike. |
| EPLAN Data Portal | Public API documentation exists for Data Portal access/maintenance of parts data and uses bearer-token authorization, but it appears oriented toward EPLAN P8 server/device data workflows rather than direct unrestricted catalog harvesting. | Potentially useful for ECAD metadata and manufacturer data, including Weidmuller/Phoenix Contact ecosystem data, but licensing and user-interaction auth constraints may limit automation. | Evaluate as an optional enrichment source only after direct manufacturer/distributor paths are working. |


## Other ideas to make component information search easier

The distributor/manufacturer adapter path is still the best release path, but component discovery can be made easier by adding a search/enrichment layer in front of it. The purpose of this layer is to find candidates, aliases, CAD assets, and corroborating metadata faster; it should not replace the canonical mapper or review rules.

### 1. Add a federated component search index

Build a local, private index from allowed metadata rather than querying every source every time. The index can store normalized, terms-safe facts such as manufacturer name, MPN, aliases, category/family, datasheet URL, product URL, known distributor SKUs, package family, pitch, pin count, and source IDs.

Suggested flow:

```text
query: "5.08mm 3 pos phoenix terminal block"
        ↓
local normalized index
        ↓
ranked candidate MPNs and source records
        ↓
source adapters refetch/refresh authoritative records
        ↓
canonical mapper + validation
```

This makes search feel fast while keeping final data fresh and auditable. For licensing safety, the index should store derived canonical fields and source references, not unrestricted mirrors of supplier catalogs.

### 2. Use aggregator APIs for discovery, not authority

Nexar/Octopart is a strong candidate for cross-distributor discovery because the Octopart API has moved into the Nexar GraphQL API, which advertises supply-chain data plus design/manufacturing data. Use this kind of aggregator to find candidate MPNs, alternate distributor SKUs, datasheets, lifecycle/compliance hints, and second-source suggestions. Do not let it override manufacturer geometry.

SiliconExpert and Z2Data-style platforms are better suited for lifecycle, compliance, risk, alternates, and BOM intelligence than footprint generation. They can improve component search by answering questions such as "is this part obsolete?", "is there a drop-in alternate?", or "does this part create compliance risk?" These services are typically commercial/account-gated, so design them as optional enrichment adapters.

### 3. Use CAD-library sources as geometry candidates

SnapMagic Search/SnapEDA, Ultra Librarian, and SamacSys/Component Search Engine can make geometry search much easier because they provide symbols, footprints, and 3D models for large numbers of parts. They should be treated as candidate CAD sources, not automatic truth.

Recommended use:

- search by MPN to discover whether a symbol/footprint/3D model already exists,
- import or parse CAD assets into a review sandbox,
- compare pad count, pitch, body outline, courtyard, and 3D dimensions against manufacturer evidence,
- use mismatches as validation findings,
- retain links and hashes according to provider terms.

This can reduce manual part creation time substantially, but generated KiCad output should still pass local rules and human review.

### 4. Mine existing KiCad and vendor KiCad libraries

The official KiCad libraries are structured repositories for symbols, footprints, 3D models, source files, and templates. They are useful as reference patterns for naming, style, and common footprints. Vendor-specific KiCad libraries, such as Espressif's KiCad libraries, can also be good sources for already-modeled vendor parts.

Recommended use:

- build a local reference index of official KiCad symbol/footprint names,
- map package families to known KiCad footprints where possible,
- detect when a generated footprint is equivalent to an existing KiCad footprint,
- use KiCad Library Convention checks as style constraints,
- avoid copying third-party vendor library data without reviewing license terms.

### 5. Add classification standards for better semantic search

Industrial component search gets easier when parts are mapped to standard classification systems such as ETIM and ECLASS. ETIM is an international classification standard for technical products, and ECLASS provides standardized product classification and property vocabularies. These are especially useful for terminal blocks, industrial connectors, enclosures, sensors, power supplies, and controls.

Recommended use:

- add optional `classification.external_classes[]` in a future schema revision,
- map manufacturer/distributor categories to ETIM/ECLASS classes,
- use class-specific property names and units to normalize searches,
- drive family-template selection from class codes,
- improve search synonyms across suppliers and languages.

### 6. Use Asset Administration Shell and BMEcat where manufacturers provide them

Phoenix Contact's Asset Administration Shell API is particularly interesting because AAS is designed for standardized digital-twin/product information exchange. Some industrial manufacturers also expose product catalogs through BMEcat, ETIM, ECLASS, OCI, EDI, or downloadable engineering-data packages even when they do not advertise a simple public REST API.

Recommended use:

- add an `engineering_data` adapter type for AAS/BMEcat/download packages,
- prioritize these sources for industrial parts over generic distributor parameters,
- preserve the original class/property identifiers in evidence,
- use them to bootstrap family templates and unit normalization.

### 7. Add an interactive narrowing workflow

Instead of asking the user for an exact MPN up front, support a guided search workflow:

```bash
kcf ingest search "terminal block 5.08mm 3 position green phoenix"
kcf ingest candidates --family terminal_block --pitch 5.08 --positions 3
kcf ingest explain-candidate phoenix-contact-1751248
kcf ingest build-spec --candidate phoenix-contact-1751248 --sources manufacturer,digikey,nexar
```

The command should show why each candidate ranked highly: matched pitch, positions, family, manufacturer, distributor availability, existing CAD model, datasheet confidence, and geometry evidence coverage.

### 8. Add a confidence score for search readiness

Before attempting generation, calculate whether a candidate is ready:

| Signal | Impact |
| --- | --- |
| Manufacturer record found | Strong positive |
| Manufacturer datasheet found | Strong positive |
| Structured pitch/pin count found | Strong positive |
| Existing CAD model found | Medium positive, still needs validation |
| Distributor-only match | Medium, discovery only |
| Conflicting pitch/body data | Strong negative |
| No source-document URL | Strong negative |
| No package-family template | Strong negative |

This helps users choose parts that are likely to generate cleanly and avoids wasting time on under-specified components.

### Structured data sources worth evaluating

| Source type | Examples | Best use | Caveat |
| --- | --- | --- | --- |
| Aggregator/search APIs | Nexar/Octopart | Cross-distributor discovery, alternates, datasheets, availability, supply-chain context | Treat as discovery/corroboration, not manufacturer geometry authority. |
| Lifecycle/compliance intelligence | SiliconExpert, Z2Data-style platforms | Obsolescence, risk, compliance, alternates, BOM health | Commercial/account-gated; optional enrichment. |
| ECAD model libraries | SnapMagic Search/SnapEDA, Ultra Librarian, SamacSys/Component Search Engine | Existing symbols, footprints, 3D models, CAD candidate comparison | Must validate against manufacturer evidence and provider license terms. |
| Official KiCad libraries | KiCad symbols, footprints, packages3d, templates | Style reference, reusable standard footprints, naming conventions | Not a full product catalog; license/style review still required. |
| Vendor KiCad libraries | Espressif and other manufacturer GitHub/library releases | Already-modeled vendor-specific parts | Coverage is uneven and license terms vary. |
| Industrial classification standards | ETIM, ECLASS | Semantic search, property normalization, family-template selection | Class/property mapping work required. |
| Industrial catalog exchange | AAS, BMEcat, OCI, EDI, manufacturer engineering-data downloads | Manufacturer-authoritative structured engineering data | Access paths differ by vendor and may require accounts. |
| Internal knowledge base | Approved generated specs, source manifests, reviewed assumptions | Fast reuse, duplicate detection, preferred footprints | Needs careful versioning and invalidation on source updates. |

## Layer 1: source adapters

### Goal

Create deterministic adapters that fetch source records and normalize them into a source-neutral intermediate model without generating KiCad artifacts directly.

### Proposed package structure

```text
src/kcf/ingestion/
  __init__.py
  sources/
    __init__.py
    base.py
    digikey.py
    mouser.py
    phoenix_contact.py
    rs_online.py
    weidmuller.py
  normalized.py
  credentials.py
  cache.py
```

### Adapter contract

Each adapter should expose a narrow contract:

```python
class SourceAdapter(Protocol):
    source_name: str

    def lookup_part(self, query: PartLookupQuery) -> SourceFetchResult:
        ...
```

`SourceFetchResult` should contain:

- `source_name`: stable source identifier, such as `digikey`.
- `retrieved_at`: UTC date/time.
- `request_fingerprint`: hash of the canonical request excluding secrets.
- `raw_payload_sha256`: hash of the raw response body when retention permits.
- `raw_payload_ref`: optional local path, object-store key, or omitted restricted reference.
- `normalized`: the source-neutral data extracted from the response.
- `license_notes`: any retention/attribution constraints.
- `warnings`: source-specific quality warnings.

### Normalized model

Keep this intermediate model broader than the final component schema:

```text
NormalizedPart
  identity
    manufacturer
    manufacturer_part_number
    distributor_part_numbers[]
    product_url
    datasheet_url
    image_url
    description
    lifecycle_status
  commercial
    availability
    price_breaks[]
    minimum_order_quantity
    packaging
  compliance
    rohs
    reach
    approvals[]
    declarations[]
  taxonomy
    distributor_category
    manufacturer_family
    keywords[]
  technical_parameters[]
    name
    value
    unit
    source_field
  documents[]
    title
    kind
    url
    revision
    retrieved_at
    retention_mode
  cad_assets[]
    kind
    url_or_ref
    format
    retention_mode
```

### Adapter priority

1. `digikey.py`: primary distributor proof of concept.
2. `phoenix_contact.py`: primary manufacturer proof of concept for terminal blocks/connectors.
3. `mouser.py`: second distributor/corroboration source.
4. `weidmuller.py`: engineering-data/download adapter; API adapter only if official access is available.
5. `rs_online.py`: account/eProcurement discovery spike before implementation.

### Credential handling

- Load API credentials from environment variables or local private config, never committed files.
- Support sandbox vs production base URLs where the provider offers them.
- Log request fingerprints, never API keys or OAuth tokens.
- Add a `kcf ingestion doctor` command later to confirm credentials without fetching arbitrary catalog data.

### Retention policy

Source terms matter. For every adapter, classify source data into one of the existing retention modes:

- `embedded`: safe to keep in project metadata.
- `external_reference`: store URL, retrieval date, and hash/provenance, but not the whole payload.
- `restricted`: store minimal provenance and require refetch.
- `local_only`: keep only in private local cache.

Mouser in particular needs careful treatment because its terms restrict caching, bulk downloads, modification, and use for independent databases. The implementation should be designed to make these constraints source-configurable rather than hard-coded as an afterthought.

## Layer 2: canonical schema mapper

### Goal

Convert one or more normalized source records into the existing canonical component specification used by the generator.

### Mapping strategy

Use explicit field mapping, not agent reasoning:

| Canonical area | Source fields | Confidence |
| --- | --- | --- |
| `identity.manufacturer` | manufacturer API first, distributor second | High if exact match |
| `identity.manufacturer_part_number` | manufacturer MPN / supplier MPN | High |
| `identity.description` | manufacturer short description, distributor description fallback | Medium/high |
| `classification.family` | manufacturer family, category taxonomy, configured family rules | Medium |
| `classification.risk_level` | rule-based by category, voltage/current, mains/safety flags | Medium |
| `symbol.reference_prefix` | family template rules | High for known families |
| `symbol.pins` | package-family template, datasheet/CAD evidence, user input | Medium unless manufacturer CAD data is explicit |
| `footprint.pitch_mm` | manufacturer technical detail / datasheet / family template | Medium/high |
| `footprint.body` | manufacturer technical detail / drawing / datasheet | Medium |
| `footprint.pads` | package-family template + terminal count + pitch + drill rules | Medium |
| `sources[]` | document and API provenance from all adapters | High |
| `assumptions[]` | missing/derived/conflicting values | High |

### Source precedence

Use a conflict-resolution policy rather than whichever source returns first:

1. Manufacturer authoritative API or engineering data.
2. Manufacturer datasheet/technical drawing.
3. Distributor structured product data.
4. Distributor datasheet mirror.
5. Known family template.
6. Human-provided override.
7. Agent/PDF extraction fallback proposal.

### Family templates

For the first release, narrow the domain. Terminal blocks and PCB connectors are a good fit because manufacturers like Phoenix Contact and Weidmuller have structured families and recurring pitch/pin-count patterns.

Add package-family templates such as:

```text
terminal_block_tht_1row
terminal_block_tht_2row
pluggable_terminal_header
pluggable_terminal_plug
wire_to_board_connector_basic
```

Each template should define:

- supported pin-count patterns,
- reference-prefix default,
- symbol layout strategy,
- pad-shape rules,
- drill sizing rules,
- body/courtyard derivation rules,
- fields that must come from manufacturer evidence,
- fields allowed to be assumptions.

### CLI flow

A future CLI flow should look like:

```bash
kcf ingest lookup --source digikey --mpn 1751248
kcf ingest lookup --source phoenix-contact --mpn 1751248
kcf ingest build-spec --component-key phoenix-contact-1751248 --sources build/ingestion/*.json --output spec.yaml
kcf validate spec.yaml
kcf generate spec.yaml --output-root build/example
```

## Layer 3: validation, evidence, and provenance

### Goal

Every canonical field that affects symbol or footprint output should be traceable to a source, rule, template, assumption, or human override.

### Evidence model

The current schema already allows a free-form `evidence` object. Use it initially before expanding the schema.

Recommended shape:

```yaml
evidence:
  identity.manufacturer_part_number:
    source_id: phoenix-contact-product-information
    source_type: api
    field_path: product.itemNumber
    confidence: high
  footprint.pitch_mm:
    source_id: phoenix-contact-datasheet
    source_type: document
    page: 4
    confidence: high
  footprint.pads[0].drill_mm:
    source_id: terminal_block_tht_1row_template
    source_type: template_rule
    confidence: medium
```

### Validation checks

Add ingestion-aware validation findings before generation:

- Required canonical fields are present.
- Every footprint-affecting field has evidence or an approved assumption.
- Manufacturer MPN agrees across sources or conflict is recorded.
- Pitch/body/pad units are normalized to millimeters.
- Datasheet/product-document URLs are present for manufacturer-sourced parts where available.
- Source retrieval dates are present.
- Retention mode is compatible with provider terms.
- High-risk, mains-rated, or safety-related parts require explicit human review.
- Distributor data cannot override manufacturer-authoritative geometry without a finding.
- Known-family template constraints match the imported part category.

### Source manifest integration

The existing source manifest should remain the release anchor. Ingestion should create `sources[]` entries that can be rendered into `source-manifest.json` with deterministic hashes. If a provider disallows retained payloads, store the allowed external reference, retrieval date, and response/request hash where permitted.

### Review behavior

If imported data is incomplete or conflicting, the mapper should add assumptions and open questions instead of silently guessing. Examples:

- `footprint.body.height_mm` missing from API and not needed for 2D footprint: assumption can be optional.
- `footprint.pitch_mm` conflicts between Mouser and manufacturer: block release until resolved.
- pad drill derived from family template rather than drawing: require review for high-risk parts.

## Development milestones

### Milestone 0: access and compliance spike

- Create provider accounts/API applications for DigiKey, Mouser, and Phoenix Contact.
- Confirm RS and Weidmuller access paths with account reps or support portals.
- Record provider retention/caching rules in adapter configuration.
- Select 5-10 representative parts, preferably terminal blocks/connectors from Phoenix Contact and Weidmuller available on DigiKey/Mouser.

### Milestone 1: adapter framework

- Add ingestion package skeleton.
- Add source adapter protocol and normalized dataclasses.
- Add credential loader.
- Add deterministic request fingerprinting.
- Add restricted/local cache abstraction.
- Add unit tests with recorded sanitized fixtures.

### Milestone 2: DigiKey adapter

- Implement OAuth/client setup.
- Implement part-number lookup.
- Normalize identity, documents, categories, parameters, media, pricing/availability.
- Store `SourceFetchResult` fixture.
- Map to current canonical schema where possible.

### Milestone 3: Phoenix Contact adapter

- Implement Product Information/AAS access if credentials are available.
- Normalize technical details, approvals, declarations, and certificates.
- Compare manufacturer data against DigiKey results for the same MPN.
- Prefer manufacturer evidence in mapper.

### Milestone 4: mapper and evidence

- Implement deterministic mapper for one terminal-block family.
- Add evidence object generation.
- Add source precedence rules.
- Emit assumptions for missing geometry.
- Add tests from fixed fixtures to canonical YAML.

### Milestone 5: validation rules

- Add ingestion-specific validation finding codes.
- Block generation/release on unresolved critical conflicts.
- Require approval for geometry assumptions.
- Confirm generated source manifests are stable.

### Milestone 6: Mouser corroboration

- Implement terms-aware Mouser source adapter.
- Use Mouser as corroborating distributor data.
- Add conflict reports against DigiKey and manufacturer source data.

### Milestone 7: RS and Weidmuller spikes

- RS: confirm official account/API/eProcurement route and supported product fields.
- Weidmuller: prototype engineering-data/eCAD/download ingestion; add API path only if official docs/access are available.

## Feedback on direction

This is the right direction for development if the first supported component families are intentionally narrow. The deterministic adapter/schema/evidence approach will be easier to test, audit, and release than agent-first ingestion. It also aligns with the project's existing canonical YAML, source manifest, validation, and approval workflow.

The main risk is assuming distributor APIs contain enough geometry for correct KiCad footprints. They probably do not. Distributor APIs are excellent for identity, metadata, datasheet links, pricing, availability, and parametric search; manufacturer data and datasheets remain the authority for footprint geometry. Therefore, the first implementation should treat distributors as discovery/corroboration sources and manufacturers as the geometry authority whenever possible.

Agents should be added later, but only behind guardrails:

- never write directly to released specs,
- propose extracted values with evidence locations,
- mark every proposal as an assumption until validated,
- compare against deterministic rules/templates,
- require human approval for geometry-changing assumptions.

## Source links reviewed

- DigiKey API Developer Portal: https://developer.digikey.com/
- DigiKey Product Information V4: https://developer.digikey.com/products/product-information-v4
- DigiKey ProductDetails endpoint page: https://developer.digikey.com/products/product-information-v4/productsearch/productdetails
- Mouser Search API documentation: https://api.mouser.com/api/docs/ui/index
- Mouser API Terms: https://www.mouser.co.il/apiterms/
- Phoenix Contact APIs: https://www.phoenixcontact.com/en-ca/service-and-support/data-provisioning/phoenix-contact-apis
- Weidmuller Digital Engineering: https://www.weidmueller.com/int/service/engineering_data.jsp
- Weidmuller Digital Ordering Options: https://www.weidmueller.com/int/service/digital_ordering_options/index.jsp
- EPLAN Data Portal API documentation: https://dataportal.eplan.com/api/doc
- Nexar API: https://nexar.com/api
- Octopart API transition to Nexar: https://octopart.com/business/api/v4/api-transition
- SiliconExpert API: https://www.siliconexpert.com/products/api/
- SnapMagic Search API: https://www.snapeda.com/get-api/
- Ultra Librarian: https://www.ultralibrarian.com/
- SamacSys / Component Search Engine: https://supplyframe.com/samacsys
- KiCad library downloads: https://www.kicad.org/libraries/download/
- ETIM International: https://www.etim-international.com/
- ECLASS technical specification: https://eclass.eu/support/technical-specification/structure-and-elements/classification-class
