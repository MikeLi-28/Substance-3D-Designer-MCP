"""Search currently loaded packages and resources without UI scraping."""

from __future__ import annotations

from typing import Any, Dict, Optional

from ..serialization.references import make_library_resource_ref
from .resource_resolver import ResourceResolver, package_reference


class LibraryService:
    def __init__(self, resolver: ResourceResolver) -> None:
        self.resolver = resolver

    def search(self, query: str, category: Optional[str], limit: int) -> Dict[str, Any]:
        needle = query.casefold()
        category_needle = category.casefold() if category else None
        matches = []
        for package in self.resolver.packages():
            package_ref = package_reference(package)
            for resource in self.resolver.resources(package):
                identifier = str(resource.getIdentifier())
                runtime_url = str(resource.getUrl())
                resource_category = str(resource.getClassName())
                haystack = f"{identifier} {runtime_url} {resource_category}"
                if needle and needle not in haystack.casefold():
                    continue
                if category_needle and category_needle not in resource_category.casefold():
                    continue
                matches.append(
                    make_library_resource_ref(
                        package_ref["package_url"],
                        identifier,
                        runtime_url,
                        identifier,
                        resource_category,
                    )
                )
                if len(matches) >= limit:
                    return {"resources": matches, "truncated": True}
        return {"resources": matches, "truncated": False}
