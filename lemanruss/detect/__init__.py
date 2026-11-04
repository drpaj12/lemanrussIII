"""Detector baselines on Seeker v2.0 (spec docs/specs/2026-11-01-detector-baselines-design.md).

A detector sees one released circuit at a time (`CircuitFile`); labels and base/form metadata
live in the answer key and are read by the harness for splitting and scoring only.
"""
