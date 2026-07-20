"""Verified SD 16.0.3 value and base-type adapter."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from sd.api.sbs.sdsbsarexporter import SDCompressionMode, SDSBSARExporter
from sd.api.sbs.sdsbscompgraph import SDSBSCompGraph
from sd.api.sdbasetypes import ColorRGBA, float2, float3, float4
from sd.api.sdhistoryutils import SDHistoryUtils
from sd.api.sdproperty import SDPropertyCategory
from sd.api.sdresource import EmbedMethod
from sd.api.sdresourcebitmap import SDResourceBitmap
from sd.api.sdtypeusage import SDTypeUsage
from sd.api.sdusage import SDUsage
from sd.api.sdvaluearray import SDValueArray
from sd.api.sdvaluebool import SDValueBool
from sd.api.sdvaluecolorrgba import SDValueColorRGBA
from sd.api.sdvalueenum import SDValueEnum
from sd.api.sdvaluefloat import SDValueFloat
from sd.api.sdvaluefloat2 import SDValueFloat2
from sd.api.sdvaluefloat3 import SDValueFloat3
from sd.api.sdvaluefloat4 import SDValueFloat4
from sd.api.sdvalueint import SDValueInt
from sd.api.sdvaluestring import SDValueString
from sd.api.sdvalueusage import SDValueUsage


class SD16Adapter:
    """Keep concrete Adobe types out of the transport and service interfaces."""

    INPUT = SDPropertyCategory.Input
    OUTPUT = SDPropertyCategory.Output
    ANNOTATION = SDPropertyCategory.Annotation

    @staticmethod
    def float2(x: float, y: float) -> Any:
        return float2(x, y)

    @staticmethod
    def new_compositing_graph(package: Any) -> Any:
        return SDSBSCompGraph.sNew(package)

    @staticmethod
    def supported_graph_types(graph: Any) -> List[str]:
        graph_type = type(graph)
        count = int(graph_type.getSupportedGraphTypeCount())
        return [str(graph_type.getSupportedGraphTypeAt(index)) for index in range(count)]

    @staticmethod
    def string_value(value: str) -> Any:
        return SDValueString.sNew(value)

    @staticmethod
    def usage_array(usages: List[Dict[str, str]]) -> Any:
        value = SDValueArray.sNew(SDTypeUsage.sNew(), 0)
        if value is None:
            raise RuntimeError("Designer did not create the usage array.")
        for item in usages:
            usage = SDUsage.sNew(item["name"], item["components"], item["color_space"])
            usage_value = SDValueUsage.sNew(usage)
            if usage_value is None:
                raise RuntimeError("Designer did not create an output usage value.")
            value.pushBack(usage_value)
        return value

    @staticmethod
    def undo_group(name: str) -> Any:
        return SDHistoryUtils.UndoGroup(name)

    @staticmethod
    def import_bitmap(package: Any, file_path: str, embed_method: str) -> Any:
        methods = {
            "binary_embedded": EmbedMethod.BinaryEmbedded,
            "copied_and_linked": EmbedMethod.CopiedAndLinked,
            "linked": EmbedMethod.Linked,
        }
        return SDResourceBitmap.sNewFromFile(package, file_path, methods[embed_method])

    @staticmethod
    def export_package_sbsar(package: Any, file_path: str, settings: Dict[str, Any]) -> None:
        modes = {
            "auto": SDCompressionMode.Auto,
            "best": SDCompressionMode.Best,
            "none": SDCompressionMode.NoCompression,
        }
        exporter = SDSBSARExporter.sNew()
        exporter.setCompressionMode(modes[settings["compression_mode"]])
        exporter.setExposeOutputSize(settings["expose_output_size"])
        exporter.setExposePixelSize(settings["expose_pixel_size"])
        exporter.setExposeRandomSeed(settings["expose_random_seed"])
        exporter.setIconEnabled(settings["icon_enabled"])
        try:
            exporter.exportPackageToSBSAR(package, file_path)
        finally:
            exporter.release()

    @staticmethod
    def _sequence(value: Any, size: int) -> List[float]:
        if not isinstance(value, (list, tuple)) or len(value) != size:
            raise TypeError(f"Expected a numeric vector of size {size}.")
        if any(isinstance(item, bool) or not isinstance(item, (int, float)) for item in value):
            raise TypeError("Vector members must be numbers.")
        return [float(item) for item in value]

    @staticmethod
    def serialize_value(value: Any) -> Optional[Dict[str, Any]]:
        if value is None:
            return None
        sd_type = value.getType()
        type_id = str(sd_type.getId()) if sd_type is not None else value.getClassName()
        raw = value.get()
        if all(hasattr(raw, item) for item in ("r", "g", "b", "a")):
            raw = [float(raw.r), float(raw.g), float(raw.b), float(raw.a)]
        elif all(hasattr(raw, item) for item in ("x", "y")):
            raw = [float(raw.x), float(raw.y)]
            if hasattr(value.get(), "z"):
                raw.append(float(value.get().z))
            if hasattr(value.get(), "w"):
                raw.append(float(value.get().w))
        return {"type": type_id, "value": raw}

    @classmethod
    def to_sd_value(cls, type_id: str, value: Any, sd_type: Any) -> Any:
        normalized = type_id.lower()
        if normalized == "bool":
            if not isinstance(value, bool):
                raise TypeError("Expected bool.")
            return SDValueBool.sNew(value)
        if normalized == "int":
            if isinstance(value, bool) or not isinstance(value, int):
                raise TypeError("Expected int.")
            return SDValueInt.sNew(value)
        if normalized in {"float", "double"}:
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise TypeError("Expected float.")
            return SDValueFloat.sNew(float(value))
        if normalized in {"string", "str"}:
            if not isinstance(value, str):
                raise TypeError("Expected string.")
            return SDValueString.sNew(value)
        if normalized == "float2":
            parts = cls._sequence(value, 2)
            return SDValueFloat2.sNew(float2(*parts))
        if normalized == "float3":
            parts = cls._sequence(value, 3)
            return SDValueFloat3.sNew(float3(*parts))
        if normalized == "float4":
            parts = cls._sequence(value, 4)
            return SDValueFloat4.sNew(float4(*parts))
        if normalized in {"color", "colorrgba"}:
            parts = cls._sequence(value, 4)
            return SDValueColorRGBA.sNew(ColorRGBA(*parts))
        if "enum" in normalized:
            if not isinstance(value, str):
                raise TypeError("Expected enum value identifier.")
            return SDValueEnum.sFromValueId(str(sd_type.getId()), value)
        raise ValueError(f"Unsupported SDValue type: {type_id}")
