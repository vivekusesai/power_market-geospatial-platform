"""GeoJSON data ingestion utilities."""
import json
from pathlib import Path
from typing import Dict, List, Optional

from geoalchemy2.functions import ST_GeomFromGeoJSON, ST_Multi
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.zone import Zone, ZoneType


class GeoJSONLoader:
    """Load zone boundaries from GeoJSON files."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def load_zones(
        self,
        file_path: Path,
        iso_region: str,
        zone_type: ZoneType,
        id_property: str = "id",
        name_property: str = "name",
        fill_color: Optional[str] = None,
        stroke_color: Optional[str] = None,
        fill_opacity: float = 0.3,
    ) -> int:
        """
        Load zones from a GeoJSON file.

        The GeoJSON should be a FeatureCollection with polygon/multipolygon features.
        Each feature's properties should include an ID and name field.
        """
        with open(file_path, "r") as f:
            geojson = json.load(f)

        if geojson.get("type") != "FeatureCollection":
            raise ValueError("GeoJSON must be a FeatureCollection")

        zones = []
        for feature in geojson.get("features", []):
            properties = feature.get("properties", {})
            geometry = feature.get("geometry")

            if not geometry:
                continue

            zone_id = str(properties.get(id_property, ""))
            zone_name = str(properties.get(name_property, zone_id))

            if not zone_id:
                continue

            # Convert geometry to MultiPolygon if needed
            geom_type = geometry.get("type")
            if geom_type == "Polygon":
                # Wrap in MultiPolygon
                geometry = {
                    "type": "MultiPolygon",
                    "coordinates": [geometry["coordinates"]],
                }

            zone = Zone(
                zone_id=f"{iso_region}_{zone_id}",
                zone_name=zone_name,
                zone_type=zone_type,
                iso_region=iso_region,
                description=properties.get("description"),
                fill_color=fill_color or properties.get("fill_color", "#3388ff"),
                stroke_color=stroke_color or properties.get("stroke_color", "#3388ff"),
                fill_opacity=fill_opacity,
                geom=ST_GeomFromGeoJSON(json.dumps(geometry)),
            )
            zones.append(zone)

        self.db.add_all(zones)
        await self.db.flush()
        return len(zones)

    async def load_iso_boundaries(
        self,
        file_path: Path,
        color_map: Optional[Dict[str, str]] = None,
    ) -> int:
        """
        Load ISO boundary zones from a GeoJSON file.

        Expects features with 'iso_region' property.
        """
        default_colors = {
            "PJM": "#1f77b4",
            "MISO": "#ff7f0e",
            "SPP": "#2ca02c",
            "ERCOT": "#d62728",
            "NYISO": "#9467bd",
            "ISONE": "#8c564b",
            "CAISO": "#e377c2",
        }

        if color_map:
            default_colors.update(color_map)

        with open(file_path, "r") as f:
            geojson = json.load(f)

        zones = []
        for feature in geojson.get("features", []):
            properties = feature.get("properties", {})
            geometry = feature.get("geometry")

            if not geometry:
                continue

            iso_region = properties.get("iso_region") or properties.get("ISO") or properties.get("name")
            if not iso_region:
                continue

            # Convert to MultiPolygon
            geom_type = geometry.get("type")
            if geom_type == "Polygon":
                geometry = {
                    "type": "MultiPolygon",
                    "coordinates": [geometry["coordinates"]],
                }

            color = default_colors.get(iso_region.upper(), "#999999")

            zone = Zone(
                zone_id=f"{iso_region.upper()}_BOUNDARY",
                zone_name=f"{iso_region} ISO/RTO Boundary",
                zone_type=ZoneType.ISO_BOUNDARY,
                iso_region=iso_region.upper(),
                fill_color=color,
                stroke_color=color,
                fill_opacity=0.2,
                geom=ST_GeomFromGeoJSON(json.dumps(geometry)),
            )
            zones.append(zone)

        self.db.add_all(zones)
        await self.db.flush()
        return len(zones)

    async def load_from_dict(
        self,
        geojson_dict: dict,
        iso_region: str,
        zone_type: ZoneType,
        zone_id: str,
        zone_name: str,
        fill_color: str = "#3388ff",
        stroke_color: str = "#3388ff",
        fill_opacity: float = 0.3,
    ) -> Zone:
        """Load a single zone from a GeoJSON dict."""
        geometry = geojson_dict.get("geometry") or geojson_dict

        # Ensure MultiPolygon
        if geometry.get("type") == "Polygon":
            geometry = {
                "type": "MultiPolygon",
                "coordinates": [geometry["coordinates"]],
            }

        zone = Zone(
            zone_id=zone_id,
            zone_name=zone_name,
            zone_type=zone_type,
            iso_region=iso_region,
            fill_color=fill_color,
            stroke_color=stroke_color,
            fill_opacity=fill_opacity,
            geom=ST_GeomFromGeoJSON(json.dumps(geometry)),
        )

        self.db.add(zone)
        await self.db.flush()
        await self.db.refresh(zone)
        return zone
