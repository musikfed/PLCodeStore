"""Static GitHub Pages must show only genuine, public Pull Request proposals."""
import base64
import json
from scripts.review_queue import review_items
from scripts.build_pages import build

def repository(name, private=False):
    return {"name":name,"private":private,"owner":{"login":"musikfed"}}

class FakeGit:
    used=0
    budget=160
    def api(self, method, path, missing_ok=False):
        self.used+=1
        if "/pulls?" in path:
            return [
                {"number":7,"head":{"ref":"plcodestore/vitrine-proposal",
                                    "sha":"a"*40,"repo":{"full_name":"musikfed/visible"}}},
                {"number":8,"head":{"ref":"random-branch",
                                    "sha":"b"*40,"repo":{"full_name":"musikfed/visible"}}},
            ]
        if "/contents/vitrine/meta.json" in path:
            meta={"id":"visible","visibility":"public","publication":"review_required",
                  "title":"Visible UI","description":"Real project","version":"0.7",
                  "tags":["Python","React"]}
            return {"encoding":"base64",
                    "content":base64.b64encode(json.dumps(meta).encode()).decode()}
        return None

def test_real_queue_excludes_private_and_random_prs():
    gh=FakeGit()
    queue=review_items(gh,"musikfed",[repository("visible"),repository("secret",True)])
    assert len(queue)==1
    item=queue[0]
    assert item["number"]==7
    assert item["edit_url"].startswith("https://github.com/musikfed/visible/edit/")
    assert "secret" not in json.dumps(queue)
    assert gh.used==2

def test_pages_contains_real_studio_and_auth_free_queue(tmp_path):
    gh=FakeGit()
    queue=review_items(gh,"musikfed",[repository("visible")])
    assert build([],tmp_path,review=queue)==0
    data=json.loads((tmp_path/"data"/"review_queue.json").read_text())
    assert data["items"][0]["title"]=="Visible UI"
    assert data["public_only"] is True
    assert (tmp_path/"review"/"index.html").is_file()
    assert (tmp_path/"assets"/"covers"/"review-visible.svg").is_file()
    assert "review/" in (tmp_path/"index.html").read_text()

def test_requires_author_pr_source_same_repo():
    class Forged(FakeGit):
        def api(self,method,path,missing_ok=False):
            if "/pulls?" in path:
                self.used+=1
                return [{"number":1,"head":{"ref":"plcodestore/vitrine-proposal",
                         "sha":"a"*40,"repo":{"full_name":"attacker/visible"}}}]
            return super().api(method,path,missing_ok)
    assert review_items(Forged(),"musikfed",[repository("visible")])==[]
