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


def test_show_existing_repo_artwork_not_generated_cover():
    from scripts.review_queue import public_original_image
    source="https://raw.githubusercontent.com/musikfed/achewiw/main/docs/media/achewiw-home.svg"
    assert public_original_image([source],"musikfed","achewiw","main")==source
    assert public_original_image([source],"musikfed","other-project","main") is None
    assert public_original_image(["https://example.com/screen.png"],"musikfed","achewiw","main") is None
    assert public_original_image(["https://raw.githubusercontent.com/musikfed/achewiw/main/../../secret.svg"],
                                 "musikfed","achewiw","main") is None

def test_review_queue_includes_verified_original_images():
    source="https://raw.githubusercontent.com/musikfed/visible/main/docs/media/visible-home.svg"
    class RealSources(FakeGit):
        def api(self,method,path,missing_ok=False):
            if "/contents/vitrine/meta.json" in path:
                self.used+=1
                meta={"id":"visible","visibility":"public","publication":"review_required",
                      "title":"Visible UI","description":"Real source project","version":"—",
                      "screenshots":[source,"https://example.com/tracker.svg"],"tags":["Python"]}
                return {"encoding":"base64",
                        "content":base64.b64encode(json.dumps(meta).encode()).decode()}
            return super().api(method,path,missing_ok)
    records=review_items(RealSources(),"musikfed",[repository("visible")])
    assert len(records)==1
    assert records[0]["image"]==source
    assert records[0]["images"]==[source]
    assert records[0]["image_caption"]=="Векторный макет из исходного репозитория"
