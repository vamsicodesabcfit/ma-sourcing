"""Shared constants for ABC Fitness M&A sourcing."""

from __future__ import annotations

# Regions supported for mandate / discovery / enrichment (multi-select in UI).
GEO_REGIONS: tuple[str, ...] = ("US", "EU", "India", "AUS", "LATAM", "Japan")

# Deal size band for prompts and filtering (USD millions, implied enterprise value / check size).
DEAL_SIZE_MIN_M_USD = 10
DEAL_SIZE_MAX_M_USD = 600
