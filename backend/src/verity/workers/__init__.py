"""Celery application, the beat schedule, and the platform-level tasks.

A module's own tasks live in that module's ``tasks.py``. This package holds the Celery
app they register against and the scheduled jobs that are not owned by one module.
"""
