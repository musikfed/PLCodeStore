"""Read-only normalized REST adapters for public Git repositories."""
from __future__ import annotations
import base64
import json
from urllib.parse import quote, urlsplit
import httpx

class Provider:
    def __init__(self, api_url: str, token: str | None = None):
        self.base = api_url.rstrip("/")
        self.token = token
        p = urlsplit(self.base)
        if p.scheme != "https" or not p.hostname:
            raise ValueError("Provider API needs an explicit HTTPS endpoint")
        self.client = httpx.Client(timeout=12.0, follow_redirects=False, headers=self.headers())

    def headers(self):
        return {"Authorization": f"Bearer {self.token}"} if self.token else {}

    def get(self, path: str):
        response = self.client.get(self.base + path)
        response.raise_for_status()
        return response.json()

    def close(self):
        self.client.close()

    def list_repos(self, owner: str) -> list[dict]:
        raise NotImplementedError

    def read_file(self, owner: str, repo: str, path: str) -> str | None:
        raise NotImplementedError

class GitHub(Provider):
    def list_repos(self, owner):
        items=[]
        for page in range(1, 21):
            batch=self.get(f"/users/{quote(owner,safe='')}/repos?per_page=100&page={page}&type=owner")
            items.extend({"name":x["name"],"url":x["html_url"],"private":x.get("private",False)} for x in batch)
            if len(batch)<100: break
        return items

    def read_file(self, owner, repo, path):
        try:
            data=self.get(f"/repos/{quote(owner,safe='')}/{quote(repo,safe='')}/contents/{quote(path,safe='/')}")
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 404: return None
            raise
        if data.get("type") != "file": return None
        return base64.b64decode(data["content"]).decode("utf-8")

class GitLab(Provider):
    def list_repos(self, owner):
        items=[]
        for page in range(1,21):
            batch=self.get(f"/users/{quote(owner,safe='')}/projects?per_page=100&page={page}")
            items.extend({"name":x["path"],"url":x["web_url"],"private":x.get("visibility")!="public"} for x in batch)
            if len(batch)<100:break
        return items

    def read_file(self, owner, repo, path):
        project=quote(owner+"/"+repo,safe="")
        try:
            data=self.get(f"/projects/{project}/repository/files/{quote(path,safe='')}?ref=HEAD")
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 404:return None
            raise
        return base64.b64decode(data["content"]).decode("utf-8")

class Forgejo(Provider):
    def list_repos(self, owner):
        items=[]
        for page in range(1,21):
            batch=self.get(f"/users/{quote(owner,safe='')}/repos?limit=50&page={page}")
            items.extend({"name":x["name"],"url":x["html_url"],"private":x.get("private",False)} for x in batch)
            if len(batch)<50:break
        return items

    def read_file(self, owner, repo, path):
        try:
            data=self.get(f"/repos/{quote(owner,safe='')}/{quote(repo,safe='')}/contents/{quote(path,safe='/')}")
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 404:return None
            raise
        if data.get("type") != "file":return None
        return base64.b64decode(data["content"]).decode("utf-8")

ADAPTERS={"github":GitHub,"gitlab":GitLab,"forgejo":Forgejo}

def discover(provider: Provider, owner: str, *, include_private: bool = False):
    result=[]
    for repo in provider.list_repos(owner):
        if repo["private"] and not include_private:
            continue
        raw=provider.read_file(owner,repo["name"],"vitrine/meta.json")
        if raw:
            from .standards import validate
            try:
                meta=validate(json.loads(raw))
                meta["source_evidence"]={"provider_repo":repo["url"]}
                result.append(meta)
            except (ValueError, json.JSONDecodeError):
                continue
    return result
