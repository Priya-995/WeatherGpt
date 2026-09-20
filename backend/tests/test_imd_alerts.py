from datetime import datetime, timedelta, timezone
from pathlib import Path
import pytest
import httpx
import respx

from app.main import app
from app.schemas.alerts import Alert, AlertArea
from app.schemas.geo import Place
from app.services.imd_alerts import (
    IMD_RSS_URL,
    cap_cache,
    feed_cache,
    get_current_alerts,
    match_location,
    parse_cap_xml,
)

FIXTURES_DIR = Path(__file__).parent / "fixtures" / "imd"


@pytest.fixture(autouse=True)
def clear_caches():
    feed_cache.clear()
    cap_cache.clear()
    yield
    feed_cache.clear()
    cap_cache.clear()


@pytest.fixture
def rss_bytes() -> bytes:
    return (FIXTURES_DIR / "rss.xml").read_bytes()


@pytest.fixture
def cap_1_bytes() -> bytes:
    return (FIXTURES_DIR / "cap_1.xml").read_bytes()


@pytest.fixture
def cap_2_bytes() -> bytes:
    return (FIXTURES_DIR / "cap_2.xml").read_bytes()


@pytest.mark.asyncio
@respx.mock
async def test_feed_and_cap_parsing(rss_bytes, cap_1_bytes, cap_2_bytes):
    respx.get(IMD_RSS_URL).respond(status_code=200, content=rss_bytes)
    respx.get("https://cap-sources.s3.amazonaws.com/in-imd-en/2026-09-15-07-05-04.xml").respond(
        status_code=200, content=cap_1_bytes
    )
    respx.get("https://cap-sources.s3.amazonaws.com/in-imd-en/2026-09-09-07-24-34.xml").respond(
        status_code=200, content=cap_2_bytes
    )

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/v1/alerts/imd")
        assert response.status_code == 200
        data = response.json()
        assert data["source"] == "IMD"
        assert "fetched_at" in data
        assert isinstance(data["count"], int)
        assert isinstance(data["alerts"], list)


def test_namespace_agnostic_cap_parsing():
    xml_content = b"""<?xml version="1.0" encoding="UTF-8"?>
    <cap:alert xmlns:cap="http://example.com/custom-cap">
        <cap:identifier>TEST-ID-123</cap:identifier>
        <cap:sender>test@imd.gov.in</cap:sender>
        <cap:sent>2026-09-20T10:00:00+05:30</cap:sent>
        <cap:status>Actual</cap:status>
        <cap:msgType>Alert</cap:msgType>
        <cap:scope>Public</cap:scope>
        <cap:info>
            <cap:category>Met</cap:category>
            <cap:event>Heavy Rain</cap:event>
            <cap:urgency>Immediate</cap:urgency>
            <cap:severity>Severe</cap:severity>
            <cap:certainty>Observed</cap:certainty>
            <cap:headline>Heavy Rain Warning</cap:headline>
            <cap:area>
                <cap:areaDesc>Delhi</cap:areaDesc>
            </cap:area>
        </cap:info>
    </cap:alert>"""
    alert = parse_cap_xml(xml_content)
    assert alert.identifier == "TEST-ID-123"
    assert alert.sender == "test@imd.gov.in"
    assert alert.event == "Heavy Rain"
    assert len(alert.areas) == 1
    assert alert.areas[0].area_desc == "Delhi"


@pytest.mark.asyncio
@respx.mock
async def test_draft_or_test_status_alert_dropped(rss_bytes):
    test_cap = b"""<?xml version="1.0" encoding="UTF-8"?>
    <alert xmlns="urn:oasis:names:tc:emergency:cap:1.2">
        <identifier>TEST-STATUS-ALERT</identifier>
        <sender>test@imd.gov.in</sender>
        <sent>2026-09-20T10:00:00+05:30</sent>
        <status>Test</status>
        <msgType>Alert</msgType>
        <scope>Public</scope>
        <info>
            <category>Met</category>
            <event>Test Event</event>
            <urgency>Past</urgency>
            <severity>Minor</severity>
            <certainty>Unlikely</certainty>
        </info>
    </alert>"""
    respx.get(IMD_RSS_URL).respond(status_code=200, content=rss_bytes)
    respx.get("https://cap-sources.s3.amazonaws.com/in-imd-en/2026-09-15-07-05-04.xml").respond(
        status_code=200, content=test_cap
    )
    respx.get("https://cap-sources.s3.amazonaws.com/in-imd-en/2026-09-09-07-24-34.xml").respond(
        status_code=200, content=test_cap
    )

    alerts, skipped = await get_current_alerts()
    assert len(alerts) == 0
    assert skipped == 2


@pytest.mark.asyncio
@respx.mock
async def test_expired_alert_dropped(rss_bytes):
    past_time = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
    expired_cap = f"""<?xml version="1.0" encoding="UTF-8"?>
    <alert xmlns="urn:oasis:names:tc:emergency:cap:1.2">
        <identifier>EXPIRED-ALERT-1</identifier>
        <sender>test@imd.gov.in</sender>
        <sent>2026-09-20T10:00:00+05:30</sent>
        <status>Actual</status>
        <msgType>Alert</msgType>
        <scope>Public</scope>
        <info>
            <category>Met</category>
            <event>Expired Flood</event>
            <expires>{past_time}</expires>
            <urgency>Past</urgency>
            <severity>Severe</severity>
            <certainty>Observed</certainty>
        </info>
    </alert>""".encode("utf-8")

    respx.get(IMD_RSS_URL).respond(status_code=200, content=rss_bytes)
    respx.get("https://cap-sources.s3.amazonaws.com/in-imd-en/2026-09-15-07-05-04.xml").respond(
        status_code=200, content=expired_cap
    )
    respx.get("https://cap-sources.s3.amazonaws.com/in-imd-en/2026-09-09-07-24-34.xml").respond(
        status_code=200, content=expired_cap
    )

    alerts, skipped = await get_current_alerts()
    assert len(alerts) == 0
    assert skipped == 2


@pytest.mark.asyncio
@respx.mock
async def test_cancel_handling():
    rss_xml = b"""<?xml version="1.0" encoding="UTF-8"?>
    <rss version="2.0">
        <channel>
            <item><link>http://example.com/alert1.xml</link></item>
            <item><link>http://example.com/cancel1.xml</link></item>
        </channel>
    </rss>"""

    future_expires = (datetime.now(timezone.utc) + timedelta(hours=5)).isoformat()

    alert1_cap = f"""<?xml version="1.0" encoding="UTF-8"?>
    <alert xmlns="urn:oasis:names:tc:emergency:cap:1.2">
        <identifier>ORIGINAL-ALERT-100</identifier>
        <sender>test@imd.gov.in</sender>
        <sent>2026-09-20T10:00:00+05:30</sent>
        <status>Actual</status>
        <msgType>Alert</msgType>
        <scope>Public</scope>
        <info>
            <category>Met</category>
            <event>Cyclone</event>
            <expires>{future_expires}</expires>
            <urgency>Immediate</urgency>
            <severity>Extreme</severity>
            <certainty>Observed</certainty>
        </info>
    </alert>""".encode("utf-8")

    cancel1_cap = f"""<?xml version="1.0" encoding="UTF-8"?>
    <alert xmlns="urn:oasis:names:tc:emergency:cap:1.2">
        <identifier>CANCEL-ALERT-101</identifier>
        <sender>test@imd.gov.in</sender>
        <sent>2026-09-20T11:00:00+05:30</sent>
        <status>Actual</status>
        <msgType>Cancel</msgType>
        <scope>Public</scope>
        <references>test@imd.gov.in,ORIGINAL-ALERT-100,2026-09-20T10:00:00+05:30</references>
        <info>
            <category>Met</category>
            <event>Cyclone Cancelled</event>
            <expires>{future_expires}</expires>
            <urgency>Past</urgency>
            <severity>Minor</severity>
            <certainty>Observed</certainty>
        </info>
    </alert>""".encode("utf-8")

    respx.get(IMD_RSS_URL).respond(status_code=200, content=rss_xml)
    respx.get("http://example.com/alert1.xml").respond(status_code=200, content=alert1_cap)
    respx.get("http://example.com/cancel1.xml").respond(status_code=200, content=cancel1_cap)

    alerts, skipped = await get_current_alerts()
    assert len(alerts) == 0
    assert skipped == 2


@pytest.mark.asyncio
@respx.mock
async def test_cap_link_500_skipped():
    rss_xml = b"""<?xml version="1.0" encoding="UTF-8"?>
    <rss version="2.0">
        <channel>
            <item><link>http://example.com/bad.xml</link></item>
            <item><link>http://example.com/good.xml</link></item>
        </channel>
    </rss>"""

    future_expires = (datetime.now(timezone.utc) + timedelta(hours=5)).isoformat()
    good_cap = f"""<?xml version="1.0" encoding="UTF-8"?>
    <alert xmlns="urn:oasis:names:tc:emergency:cap:1.2">
        <identifier>GOOD-ALERT-1</identifier>
        <sender>test@imd.gov.in</sender>
        <sent>2026-09-20T10:00:00+05:30</sent>
        <status>Actual</status>
        <msgType>Alert</msgType>
        <scope>Public</scope>
        <info>
            <category>Met</category>
            <event>Heavy Rain</event>
            <expires>{future_expires}</expires>
            <urgency>Immediate</urgency>
            <severity>Severe</severity>
            <certainty>Observed</certainty>
            <headline>Good Alert</headline>
        </info>
    </alert>""".encode("utf-8")

    respx.get(IMD_RSS_URL).respond(status_code=200, content=rss_xml)
    respx.get("http://example.com/bad.xml").respond(status_code=500, content=b"Server Error")
    respx.get("http://example.com/good.xml").respond(status_code=200, content=good_cap)

    alerts, skipped = await get_current_alerts()
    assert len(alerts) == 1
    assert skipped == 1



@pytest.mark.asyncio
@respx.mock
async def test_malformed_xml_skipped():
    rss_xml = b"""<?xml version="1.0" encoding="UTF-8"?>
    <rss version="2.0">
        <channel>
            <item><link>http://example.com/corrupt.xml</link></item>
        </channel>
    </rss>"""

    respx.get(IMD_RSS_URL).respond(status_code=200, content=rss_xml)
    respx.get("http://example.com/corrupt.xml").respond(status_code=200, content=b"<unclosed tag>abc")

    alerts, skipped = await get_current_alerts()
    assert len(alerts) == 0
    assert skipped == 1


@pytest.mark.asyncio
@respx.mock
async def test_empty_feed_returns_count_zero():
    empty_rss = b"""<?xml version="1.0" encoding="UTF-8"?>
    <rss version="2.0">
        <channel>
            <title>IMD Feed</title>
        </channel>
    </rss>"""

    respx.get(IMD_RSS_URL).respond(status_code=200, content=empty_rss)
    alerts, skipped = await get_current_alerts()
    assert len(alerts) == 0
    assert skipped == 0


def test_matching_polygon_district_state_and_no_match():
    # Construct a sample alert with a bounding box polygon over lat 20..25, lon 75..80
    polygon_coords = [(20.0, 75.0), (20.0, 80.0), (25.0, 80.0), (25.0, 75.0), (20.0, 75.0)]
    alert = Alert(
        identifier="ALERT-MATCH-TEST",
        sender="test@imd.gov.in",
        sent=datetime.now(timezone.utc),
        status="Actual",
        msg_type="Alert",
        scope="Public",
        event="Heavy Rain",
        category="Met",
        urgency="Immediate",
        severity="Severe",
        certainty="Observed",
        headline="Heavy Rainfall Warning in Uttar Pradesh, Ghaziabad",
        areas=[
            AlertArea(
                area_desc="Ghaziabad district, Uttar Pradesh",
                polygons=[polygon_coords]
            )
        ]
    )
    alerts = [alert]

    # 1. Polygon Match
    matches_poly = match_location(alerts, lat=22.0, lon=77.0)
    assert len(matches_poly) == 1
    assert matches_poly[0].match_method == "polygon"

    # 2. District Match (point lat 10, lon 10 outside polygon, but district 'Ghaziabad' matches)
    place_ghaziabad = Place(id=1, name="Ghaziabad", latitude=10.0, longitude=10.0, admin1="Uttar Pradesh", admin2="Ghaziabad")
    matches_dist = match_location(alerts, lat=10.0, lon=10.0, place=place_ghaziabad)
    assert len(matches_dist) == 1
    assert matches_dist[0].match_method == "district"

    # 3. State Match Fallback (place with admin1 'Uttar Pradesh' but unknown district)
    place_up = Place(id=2, name="Kanpur", latitude=10.0, longitude=10.0, admin1="Uttar Pradesh", admin2="Kanpur Nagar")
    # Kanpur Nagar is not in headline/area_desc of alert, but Uttar Pradesh matches state
    matches_state = match_location(alerts, lat=10.0, lon=10.0, place=place_up)
    assert len(matches_state) == 1
    assert matches_state[0].match_method == "state"

    # 4. No Match
    place_other = Place(id=3, name="Chennai", latitude=13.0, longitude=80.0, admin1="Tamil Nadu", admin2="Chennai")
    matches_none = match_location(alerts, lat=13.0, lon=80.0, place=place_other)
    assert len(matches_none) == 0


def test_lat_lon_order_shapely_regression():
    # Polygon with latitude range 20.0 to 25.0 and longitude range 75.0 to 80.0
    # CAP polygon string: "20.0,75.0 20.0,80.0 25.0,80.0 25.0,75.0 20.0,75.0"
    polygon_coords = [(20.0, 75.0), (20.0, 80.0), (25.0, 80.0), (25.0, 75.0), (20.0, 75.0)]
    alert = Alert(
        identifier="ORDER-TEST",
        sender="test@imd.gov.in",
        sent=datetime.now(timezone.utc),
        status="Actual",
        msg_type="Alert",
        scope="Public",
        event="Heavy Rain",
        category="Met",
        urgency="Immediate",
        severity="Severe",
        certainty="Observed",
        areas=[AlertArea(area_desc="Test Region", polygons=[polygon_coords])]
    )

    # Test point: lat=22.0, lon=77.0
    # In correct (lon, lat) Shapely order: Point(77.0, 22.0) is inside Polygon([(75,20), (80,20), (80,25), (75,25)])
    # If order was incorrectly (lat, lon): Point(22.0, 77.0) is OUTSIDE Polygon([(20,75), (20,80), ...]) because 22 is outside 75..80.
    matches = match_location([alert], lat=22.0, lon=77.0)
    assert len(matches) == 1
    assert matches[0].match_method == "polygon"


# ── Live Tests ─────────────────────────────────────────────────────────────

@pytest.mark.live
@pytest.mark.asyncio
async def test_live_imd_alerts_fetch():
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/v1/alerts/imd")
        assert response.status_code == 200
        data = response.json()
        assert data["source"] == "IMD"
        assert "fetched_at" in data
        assert "count" in data
        assert "skipped" in data
        assert "alerts" in data
        for alert in data["alerts"]:
            assert "identifier" in alert
            assert "event" in alert
            assert "expires" in alert
