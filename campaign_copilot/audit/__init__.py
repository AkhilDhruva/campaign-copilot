"""Append-only, hash-chained JSONL audit log."""

from campaign_copilot.audit.log import AuditLog, verify

__all__ = ["AuditLog", "verify"]
