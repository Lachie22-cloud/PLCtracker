"""SAP OData client — paginated MARA + MARC extraction via httpx."""
from __future__ import annotations

import logging
from typing import Any, Dict, Generator, Optional

import httpx

from ..config import settings

logger = logging.getLogger(__name__)

# Fields to select from OData MARA entity
MARA_SELECT = "Material,MaterialType,IndustrySector,MaterialName,BaseUnit,MaterialGroup,CreationDate,LastChangeDate"

# Fields to select from OData MARC entity — maps to tracked governance fields
MARC_SELECT = (
    "Material,Plant,"
    "PlantSpecificMaterialStatus,MRPProfile,MRPType,MRPController,"
    "ProcurementType,SpecialProcurementType,PurchasingGroup,MRPGroup,"
    "SafetyStockQuantity,ReorderThresholdQuantity,FixedLotSizeQuantity,"
    "PlannedDeliveryDurationInDays,GoodsReceiptDuration,"
    "IssueStorageLocation,StorageLocationForExternalProcmt,"
    "SchedulingFloatProfile,IsBulkMaterialComponent,"
    "MRPPlanningCalendar,AvailabilityCheckType,MRPProductionVersion"
)

# Map OData property name → Marc model attribute name
MARC_FIELD_MAP: Dict[str, str] = {
    "PlantSpecificMaterialStatus": "mmsta",
    "MRPProfile": "dispr",
    "MRPType": "dismm",
    "MRPController": "dispo",
    "ProcurementType": "beskz",
    "SpecialProcurementType": "sobsl",
    "PurchasingGroup": "ekgrp",
    "MRPGroup": "disgr",
    "SafetyStockQuantity": "eisbe",
    "ReorderThresholdQuantity": "minbe",
    "FixedLotSizeQuantity": "losfx",
    "PlannedDeliveryDurationInDays": "plifz",
    "GoodsReceiptDuration": "webaz",
    "IssueStorageLocation": "lgpro",
    "StorageLocationForExternalProcmt": "lgfsb",
    "SchedulingFloatProfile": "fhori",
    "IsBulkMaterialComponent": "schgt",
    "MRPPlanningCalendar": "perkz",
    "AvailabilityCheckType": "mtvfp",
    "MRPProductionVersion": "strgr",
}

PAGE_SIZE = 500


class SapODataClient:
    """httpx-based client for SAP S/4HANA OData v2/v4 services.

    Instantiate with a custom transport for testing:
        client = SapODataClient(transport=MockTransport())
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        user: Optional[str] = None,
        password: Optional[str] = None,
        transport: Optional[httpx.BaseTransport] = None,
    ) -> None:
        self._base_url = (base_url or settings.sap_odata_base_url).rstrip("/")
        auth = (user or settings.sap_odata_user, password or settings.sap_odata_password)
        self._client = httpx.Client(
            base_url=self._base_url,
            auth=auth if auth[0] else None,
            headers={"Accept": "application/json"},
            timeout=120.0,
            transport=transport,
        )

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "SapODataClient":
        return self

    def __exit__(self, *_: Any) -> None:
        self.close()

    def _get_json(self, entity: str, params: Dict[str, str]) -> Dict[str, Any]:
        params.setdefault("$format", "json")
        resp = self._client.get(f"/{entity}", params=params)
        resp.raise_for_status()
        return resp.json()

    def _paginate(
        self,
        entity: str,
        select: str,
        delta_filter: Optional[str] = None,
    ) -> Generator[Dict[str, Any], None, None]:
        """Yield all rows from an OData entity set, paginating with $top/$skip."""
        skip = 0
        while True:
            params: Dict[str, str] = {
                "$top": str(PAGE_SIZE),
                "$skip": str(skip),
                "$select": select,
            }
            if delta_filter:
                params["$filter"] = delta_filter

            data = self._get_json(entity, params)
            # Support both OData v2 (d.results) and v4 (value)
            rows = data.get("d", {}).get("results") or data.get("value") or []
            if not rows:
                break
            yield from rows
            if len(rows) < PAGE_SIZE:
                break
            skip += PAGE_SIZE
            logger.debug("OData %s: fetched %d rows (skip=%d)", entity, len(rows), skip)

    def iter_mara(
        self, delta_filter: Optional[str] = None
    ) -> Generator[Dict[str, Any], None, None]:
        yield from self._paginate(
            settings.sap_odata_mara_entity,
            select=MARA_SELECT,
            delta_filter=delta_filter,
        )

    def iter_marc(
        self, delta_filter: Optional[str] = None
    ) -> Generator[Dict[str, Any], None, None]:
        yield from self._paginate(
            settings.sap_odata_marc_entity,
            select=MARC_SELECT,
            delta_filter=delta_filter,
        )
