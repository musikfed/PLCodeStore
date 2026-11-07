"""IssueOps approvals never require authors to edit vitrine/meta.json manually."""
import base64
import json
import pytest
from scripts.author_decision import parse_decision, verify_source, apply_decision, DecisionError

A="a"*40
B="b"*40

def event(action="APPROVE", author="musikfed", checks="3/3", note=""):
    return {"action":"opened","issue":{
        "number":11,"state":"open","user":{"login":author},
        "title":f"PLCS REVIEW {action} musikfed/achewiw#18",
        "body":f"Revision: {A}\nChecks: {checks}\n\nЗамечания (необязательно):\n{note}"}}

def test_only_owner_can_issue_approval():
    assert parse_decision(event(),"musikfed")["action"]=="APPROVE"
    with pytest.raises(DecisionError,match="owner"):
        parse_decision(event(author="other"),"musikfed")
    with pytest.raises(DecisionError,match="three"):
        parse_decision(event(checks="2/3"),"musikfed")
    e=event()
    e["issue"]["title"]="PLCS REVIEW APPROVE bad/other#19"
    with pytest.raises(DecisionError):
        parse_decision(e,"musikfed")

def test_rework_note_is_optional():
    d=parse_decision(event(action="REWORK",checks="not required"),"musikfed")
    assert d["note"]==""
    assert d["action"]=="REWORK"

class FakeAPI:
    def __init__(self,paths=None,private=False):
        self.calls=[]
        self.sha=A
        self.paths=paths or ["vitrine/meta.json","vitrine/generated/cover.svg"]
        self.private=private
        self.meta={"id":"achewiw","visibility":"public","publication":"review_required",
                   "public_private_approved":False,"title":"ACHEWIW",
                   "screenshots":[]}
    def repo(self,owner,project,suffix="",method="GET",data=None):
        self.calls.append((method,suffix,data))
        if not suffix:return {"owner":{"login":"musikfed"},"default_branch":"main","private":self.private}
        if suffix=="/pulls/18":
            return {"state":"open","changed_files":len(self.paths),
                    "head":{"ref":"plcodestore/vitrine-proposal","sha":self.sha,
                            "repo":{"full_name":"musikfed/achewiw"}},
                    "base":{"ref":"main"}}
        if suffix=="/pulls/18/files?per_page=100":
            return [{"filename":path} for path in self.paths]
        if suffix.startswith("/contents/vitrine/meta.json?ref="):
            return {"encoding":"base64","sha":"meta-blob",
                    "content":base64.b64encode(json.dumps(self.meta).encode()).decode()}
        if suffix=="/contents/vitrine/meta.json" and method=="PUT":
            self.meta=json.loads(base64.b64decode(data["content"]).decode())
            self.sha=B
            assert data["branch"]=="plcodestore/vitrine-proposal"
            return {"commit":{"sha":B}}
        if suffix=="/pulls/18/merge" and method=="PUT":
            assert data["sha"]==self.sha
            assert self.meta["publication"]=="approved"
            return {"merged":True}
        if suffix=="/issues/18/comments" and method=="POST":
            return {"id":123}
        raise AssertionError((method,suffix))

def test_approve_updates_only_metadata_and_merges_specific_pr():
    d=parse_decision(event(),"musikfed")
    api=FakeAPI()
    repo,pr=verify_source(api,d)
    result=apply_decision(api,d,repo,pr)
    assert "объединён" in result
    assert api.meta["publication"]=="approved"
    assert any(method=="PUT" and suffix=="/pulls/18/merge" for method,suffix,_ in api.calls)

def test_rework_without_comment_does_not_merge():
    d=parse_decision(event(action="REWORK",checks="not required"),"musikfed")
    api=FakeAPI()
    repo,pr=verify_source(api,d)
    result=apply_decision(api,d,repo,pr)
    assert "оставлен открытым" in result
    assert api.meta["publication"]=="review_required"
    assert not any(method=="PUT" for method,_,_ in api.calls)

def test_no_other_files_or_stale_revision():
    d=parse_decision(event(),"musikfed")
    with pytest.raises(DecisionError,match="source code"):
        verify_source(FakeAPI(paths=["vitrine/meta.json",".github/workflows/unsafe.yml"]),d)
    stale=FakeAPI()
    stale.sha=B
    with pytest.raises(DecisionError,match="changed"):
        verify_source(stale,d)

def test_private_project_needs_explicit_public_metadata_permission():
    d=parse_decision(event(),"musikfed")
    api=FakeAPI(private=True)
    repo,pr=verify_source(api,d)
    with pytest.raises(DecisionError,match="Closed-source"):
        apply_decision(api,d,repo,pr)
    assert api.meta["publication"]=="review_required"
