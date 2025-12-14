"""
TaskConductor-style scaffolding for Historical Echo queue + broker.

This package is opt-in and does not alter existing hosts/pipelines. It provides
lightweight helpers to enqueue echo jobs (using the canonical runner) and to
serve immutable CAS artifacts with validation and ETags.
"""
