import json
from scripts.build_pages import approved_record, collect, build

def repo(private=False):
    return {"name":"sensor","private":private,"html_url":"https://github.com/musikfed/sensor",
      "default_branch":"main","owner":{"login":"musikfed"},
      "created_at":"2026-01-20T12:00:00Z","size":12}
def metadata(private=False):
    return {"schema_version":"1.0","id":"sensor","title":"Sensor Studio","version":"1.2.7",
      "description":"Hardware sensor processing suite","tags":["Python","IoT"],
      "visibility":"private" if private else "public","publication":"approved",
      "public_private_approved":private,"screenshots":["docs/screenshots/main.png"],"display_mode":"interface"}

def test_public_code_and_real_image():
    p=approved_record(repo(),metadata())
    assert p["repo_url"]=="https://github.com/musikfed/sensor"
    assert p["image"].startswith("https://raw.githubusercontent.com/musikfed/sensor/")

def test_private_cover_without_source(tmp_path):
    p=approved_record(repo(True),metadata(True))
    assert p["repo_url"] is None and p["image"] is None
    build([p],tmp_path)
    page=(tmp_path/"projects"/"sensor"/"index.html").read_text()
    assert "Sensor Studio" in page and "1.2.7" in page
    assert "Исходный код" not in page
    assert "github.com/musikfed/sensor" not in page
    cover=(tmp_path/"assets"/"covers"/"sensor.svg").read_text()
    assert "Sensor Studio" in cover and "1.2.7" in cover
    assert "SOURCE CODE PRIVATE" in cover
    data=json.loads((tmp_path/"data"/"projects.json").read_text())
    assert data["projects"][0]["repo_url"] is None

def test_private_needs_explicit_release():
    m=metadata(True)
    m["public_private_approved"]=False
    assert approved_record(repo(True),m) is None
    m["public_private_approved"]=True
    m["publication"]="review_required"
    assert approved_record(repo(True),m) is None

def test_no_legacy_catalog(tmp_path):
    assert build([],tmp_path)==0
    assert (tmp_path/"index.html").is_file()
    assert "view_my_prj" not in (tmp_path/"data"/"projects.json").read_text()

def test_escape(tmp_path):
    m=metadata()
    m["title"]="<script>alert(1)</script>"
    build([approved_record(repo(),m)],tmp_path)
    html=(tmp_path/"index.html").read_text()
    assert "&lt;script&gt;" in html
    assert "<script>alert(1)</script>" not in html

def test_collect_live_approved_only():
    class FakeGit:
        used=0
        budget=160
        def repos(self,owner):
            return [repo(private=True)]
        def file(self,owner,name,path):
            assert path=="vitrine/meta.json"
            return json.dumps(metadata(private=True))
    assert collect(FakeGit(),"musikfed")[0]["visibility"]=="private"
