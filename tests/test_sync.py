import json
from plcodestore.providers import discover

class FakeProvider:
    def list_repos(self,owner):
        assert owner=="example"
        return [{"name":"public-app","url":"https://git.example/public-app","private":False},
                {"name":"private-app","url":"https://git.example/private-app","private":True}]
    def read_file(self,owner,repo,path):
        return json.dumps({"schema_version":"1.0","id":repo,"title":repo,"version":"1.0",
          "description":"Real software","tags":["Python"],"visibility":"private" if repo=="private-app" else "public",
          "publication":"disabled"})

def test_default_sync_skips_private():
    projects=discover(FakeProvider(),"example")
    assert [p["id"] for p in projects]==["public-app"]

def test_opt_in_private_sync_still_not_published():
    projects=discover(FakeProvider(),"example",include_private=True)
    assert len(projects)==2
    assert next(p for p in projects if p["id"]=="private-app")["publication"]=="disabled"
