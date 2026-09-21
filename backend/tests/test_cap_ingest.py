"""
Pytest suite for CAP XML Ingestion & Alert Service.

Covers:
- CAP severity mapping (Extreme, Severe, Moderate, Minor, Unknown -> Minor)
- Expiry datetime parsing & fallback (cap:expires or sent + 24h)
- Uttar Pradesh areaDesc filtering ("UTTAR PRADESH", "EAST UTTAR PRADESH", "WEST UTTAR PRADESH")
- Point-in-polygon ray casting logic
- Skipping bulletins with status != "Actual"
- Empty feed returning []
"""

from datetime import datetime, timedelta, timezone
import pytest

from app.schemas.alert import Alert, AlertSeverity, AlertType
from app.services.cap_ingest import (
    is_uttar_pradesh_alert,
    map_cap_severity,
    parse_cap_xml,
    point_in_polygon,
)


REAL_CAP_XML_SAMPLE = """<?xml version="1.0" encoding="UTF-8"?>
<cap:alert xmlns:cap="urn:oasis:names:tc:emergency:cap:1.2">
  <cap:identifier>urn:oid:2.49.0.1.356.0.2026.9.15.7.5.4</cap:identifier>
  <cap:sender>rainfallnwfc@gmail.com</cap:sender>
  <cap:sent>2026-09-15T12:35:04+05:30</cap:sent>
  <cap:status>Actual</cap:status>
  <cap:msgType>Alert</cap:msgType>
  <cap:scope>Public</cap:scope>
  <cap:info>
    <cap:language>en</cap:language>
    <cap:category>Met</cap:category>
    <cap:event>Extremely heavy</cap:event>
    <cap:urgency>Expected</cap:urgency>
    <cap:severity>Severe</cap:severity>
    <cap:certainty>Likely</cap:certainty>
    <cap:onset>2026-09-15T07:00:00+05:30</cap:onset>
    <cap:expires>2026-09-16T07:00:00+05:30</cap:expires>
    <cap:senderName>NWFC DIVISION, IMD, NEW DELHI</cap:senderName>
    <cap:headline>Heavy to very heavy with extremely heavy rainfall</cap:headline>
    <cap:description>Isolated extremely rainfall likely over EAST UTTAR PRADESH on 15th September.</cap:description>
    <cap:instruction>Avoid waterlogged areas and drive carefully.</cap:instruction>
    <cap:area>
      <cap:areaDesc>EAST UTTAR PRADESH</cap:areaDesc>
      <cap:polygon>26.85,80.91 27.00,81.00 26.50,81.50 26.00,80.50 26.85,80.91</cap:polygon>
    </cap:area>
  </cap:info>
</cap:alert>
"""


def test_cap_severity_mapping():
    assert map_cap_severity("Extreme") == AlertSeverity.EXTREME
    assert map_cap_severity("Severe") == AlertSeverity.SEVERE
    assert map_cap_severity("Moderate") == AlertSeverity.MODERATE
    assert map_cap_severity("Minor") == AlertSeverity.MINOR
    # Unknown -> Minor fallback
    assert map_cap_severity("Unknown") == AlertSeverity.MINOR
    assert map_cap_severity("") == AlertSeverity.MINOR


def test_expiry_parsing_and_fallback():
    # Test with explicit cap:expires
    alerts, _ = parse_cap_xml(REAL_CAP_XML_SAMPLE)
    assert len(alerts) == 1
    alert = alerts[0]
    expected_expiry = datetime.fromisoformat("2026-09-16T07:00:00+05:30")
    assert alert.expiry_time == expected_expiry

    # Test fallback when cap:expires is missing
    no_expires_xml = REAL_CAP_XML_SAMPLE.replace(
        "<cap:expires>2026-09-16T07:00:00+05:30</cap:expires>", ""
    )
    alerts_no_exp, _ = parse_cap_xml(no_expires_xml)
    assert len(alerts_no_exp) == 1
    sent_dt = datetime.fromisoformat("2026-09-15T12:35:04+05:30")
    assert alerts_no_exp[0].expiry_time == sent_dt + timedelta(hours=24)


def test_up_area_desc_filter():
    alerts, _ = parse_cap_xml(REAL_CAP_XML_SAMPLE)
    alert = alerts[0]
    assert is_uttar_pradesh_alert(alert) is True

    # Test non-UP alert
    odisha_xml = REAL_CAP_XML_SAMPLE.replace("EAST UTTAR PRADESH", "ODISHA")
    odisha_alerts, _ = parse_cap_xml(odisha_xml)
    assert is_uttar_pradesh_alert(odisha_alerts[0]) is False


def test_point_in_polygon():
    # Square polygon around Lucknow: (26.0, 80.0) to (27.0, 81.0)
    polygon = [(26.0, 80.0), (27.0, 80.0), (27.0, 81.0), (26.0, 81.0), (26.0, 80.0)]

    # Inside point (Lucknow: 26.85, 80.91)
    assert point_in_polygon(26.85, 80.91, polygon) is True

    # Outside point (Delhi: 28.61, 77.21)
    assert point_in_polygon(28.61, 77.21, polygon) is False

    # Empty polygon
    assert point_in_polygon(26.85, 80.91, []) is False


def test_ignoring_status_not_actual():
    # Test status="Draft" or status="Test"
    test_xml = REAL_CAP_XML_SAMPLE.replace("<cap:status>Actual</cap:status>", "<cap:status>Test</cap:status>")
    alerts, _ = parse_cap_xml(test_xml)
    assert len(alerts) == 0

    draft_xml = REAL_CAP_XML_SAMPLE.replace("<cap:status>Actual</cap:status>", "<cap:status>Draft</cap:status>")
    alerts_draft, _ = parse_cap_xml(draft_xml)
    assert len(alerts_draft) == 0


def test_empty_feed_case():
    empty_xml = "<?xml version='1.0'?><rss><channel></channel></rss>"
    alerts, cancelled_ids = parse_cap_xml(empty_xml)
    assert alerts == []
    assert cancelled_ids == set()
