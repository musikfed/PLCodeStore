import json
from pathlib import Path
import pytest
from plcodestore.review import ReviewStore, CHECKS
from plcodestore.delivery import build
from plcodestore.standards import public_snapshot

def meta(**kw):
    return dict(schema_version="1.0",id="sample",title="Sample",version="1.0",description="A useful project",tags=["Python"],visibility="public",publication="approved",repo_url="https://github.com/example/sample",screenshots=[],**kw)

def test_review_requires_checklist_and_revision(tmp_path):
    store=ReviewStore(tmp_path/"review.sqlite3")
    m=meta()
    digest=store.stage(m)
    with pytest.raises(ValueError,match="checks"):
        store.decide("sample",digest,"approved",checks=[])
    store.decide("sample",digest,"approved",checks=list(CHECKS))
    assert len(store.history("sample"))==1
    m["description"]="Revised version"
    digest2=store.stage(m)
    assert digest2!=digest
    with pytest.raises(ValueError,match="Stale"):
        store.decide("sample",digest,"approved",checks=list(CHECKS))
    with pytest.raises(ValueError,match="not approved"):
        store.publish("sample")
    store.decide("sample",digest2,"approved",checks=list(CHECKS))
    item=store.publish("sample")
    assert item["description"]=="Revised version"
    assert len(store.published())==1
    assert build(store.published(),tmp_path/"output")==1
    index=(tmp_path/"output"/"index.html").read_text()
    assert "Sample" in index
    assert (tmp_path/"output"/"projects"/"sample"/"index.html").is_file()

def test_rejection_must_have_comment(tmp_path):
    store=ReviewStore(tmp_path/"r.db");digest=store.stage(meta())
    with pytest.raises(ValueError,match="Comment"):
        store.decide("sample",digest,"changes_requested")
    store.decide("sample",digest,"changes_requested",comment="Change screenshot")
    assert store.cards()[0]["state"]=="changes_requested"

def test_private_never_auto_publish(tmp_path):
    m=meta()
    m["visibility"]="private"
    with pytest.raises(ValueError,match="consent"):
        public_snapshot(m)
    m["public_private_approved"]=True
    assert public_snapshot(m)["repo_url"] is None
    m["publication"]="review_required"
    with pytest.raises(ValueError,match="not enabled"):
        public_snapshot(m)

def test_output_is_escaped_and_safe(tmp_path):
    m=meta();m["title"]="<script>alert(1)</script>";m["repo_url"]="file:///etc/passwd"
    item=public_snapshot(m)
    assert item["repo_url"] is None
    build([item],tmp_path/"site")
    contents=(tmp_path/"site"/"index.html").read_text()
    assert "&lt;script&gt;" in contents
    assert "<script>alert(1)</script>" not in contents
