import xml.etree.ElementTree as ET
from scripts.vitrine_cover import cover

def test_stable_and_valid_svg():
    a=cover("Private medical device", "2.4.1", visibility="private")
    assert a==cover("Private medical device","2.4.1",visibility="private")
    assert 'VERSION 2.4.1' in a
    assert 'SOURCE CODE PRIVATE' in a
    assert 'NOT A SCREENSHOT' in a
    assert ET.fromstring(a).tag.endswith("svg")

def test_all_projects_get_styled_covers():
    assert cover("My project","1.0",visibility="public") != cover("Another project","1.0")
    assert "В РАЗРАБОТКЕ" in cover("Empty","0.0.0",mode="development")

def test_unsafe_text_is_xml_escaped():
    svg=cover('<script> & "cool"',"1.0",visibility="private")
    ET.fromstring(svg)
    assert "<script>" not in svg
