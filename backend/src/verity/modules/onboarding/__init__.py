"""Guided onboarding: Get Started status and the decisions a person makes about its steps.

Plan: docs/product/guided-onboarding/. Spec: openspec/changes/guided-onboarding/.
This module owns no compliance record. It reads other modules through their services and
computes every step's state from their records, so a step can never read done on a click.
"""
