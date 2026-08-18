"""Offline, deterministic LegalKural weekly-journal foundation."""

from .manifest import (
    JournalManifestError,
    canonical_json_bytes,
    compute_manifest_sha256,
    finalize_manifest,
    validate_finalized_manifest,
)

__all__ = [
    "JournalManifestError",
    "canonical_json_bytes",
    "compute_manifest_sha256",
    "finalize_manifest",
    "validate_finalized_manifest",
]

from .discovery import (
    JournalDiscoveryError,
    discover_articles,
    inspect_case,
    select_articles,
)

__all__ += [
    "JournalDiscoveryError",
    "discover_articles",
    "inspect_case",
    "select_articles",
]

from .assembly import (
    JournalAssemblyError,
    assemble_journal,
    compute_assembly_sha256,
    validate_assembly,
)

__all__ += [
    "JournalAssemblyError",
    "assemble_journal",
    "compute_assembly_sha256",
    "validate_assembly",
]
