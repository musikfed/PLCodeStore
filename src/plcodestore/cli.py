"""Command-line interface; safe defaults and explicit publication."""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
from .parser import initialize, load, detect_project
from .standards import validate
from .review import ReviewStore
from .delivery import build
from .providers import ADAPTERS, discover

def main(argv: list[str] | None = None):
    p=argparse.ArgumentParser(prog="plcodestore")
    p.add_argument("--db",type=Path,default=Path(".plcodestore")/"review.sqlite3")
    sub=p.add_subparsers(dest="command",required=True)
    for cmd in ("init","scan","stage","validate"):
        arg=sub.add_parser(cmd)
        arg.add_argument("directory",type=Path,nargs="?",default=Path("."))
        if cmd=="init":arg.add_argument("--dry-run",action="store_true")
    sync=sub.add_parser("sync")
    sync.add_argument("--config",type=Path,default=Path("config.json"))
    sync.add_argument("--dry-run",action="store_true")
    review=sub.add_parser("review")
    review.add_argument("--host",default="127.0.0.1")
    review.add_argument("--port",type=int,default=8077)
    pub=sub.add_parser("publish")
    pub.add_argument("project_id")
    b=sub.add_parser("build")
    b.add_argument("--out",type=Path,default=Path("output"))
    b.add_argument("--title",default="PL Code Store")
    ls=sub.add_parser("status")
    args=p.parse_args(argv)
    if args.command=="init":
        meta,created=initialize(args.directory,dry_run=args.dry_run)
        print(json.dumps({"created":created,"dry_run":args.dry_run,"meta":meta},ensure_ascii=False,indent=2))
    elif args.command=="scan":
        print(json.dumps(detect_project(args.directory),ensure_ascii=False,indent=2))
    elif args.command=="validate":
        print(json.dumps(validate(load(args.directory)),ensure_ascii=False,indent=2))
    elif args.command=="stage":
        digest=ReviewStore(args.db).stage(load(args.directory))
        print(json.dumps({"staged":True,"digest":digest}))
    elif args.command=="sync":
        settings=json.loads(args.config.read_text(encoding="utf-8"))
        discovered=[]
        for cfg in settings.get("providers",[]):
            kind=cfg.get("type")
            if kind not in ADAPTERS:
                p.error(f"Unknown provider: {kind}")
            token=os.environ.get(cfg.get("token_env","")) if cfg.get("token_env") else None
            provider=ADAPTERS[kind](cfg["api_url"],token)
            try:
                discovered.extend(discover(provider,cfg["owner"],include_private=cfg.get("include_private",False)))
            finally:
                provider.close()
        staged=[]
        for meta in discovered:
            if not args.dry_run:
                ReviewStore(args.db).stage(meta)
            staged.append({"id":meta["id"],"title":meta["title"],"visibility":meta["visibility"]})
        print(json.dumps({"dry_run":args.dry_run,"count":len(staged),"projects":staged},ensure_ascii=False,indent=2))
    elif args.command=="status":
        store=ReviewStore(args.db)
        print(json.dumps({"drafts":store.cards(),"published":store.published()},ensure_ascii=False,indent=2))
    elif args.command=="publish":
        print(json.dumps(ReviewStore(args.db).publish(args.project_id),ensure_ascii=False,indent=2))
    elif args.command=="build":
        n=build(ReviewStore(args.db).published(),args.out,title=args.title)
        print(f"Built {n} approved project pages in {args.out}")
    elif args.command=="review":
        if args.host not in ("127.0.0.1","::1","localhost"):
            p.error("Review Studio binds to loopback only; use a trusted SSH tunnel or VPN")
        from .studio import configure
        configure(args.db)
        import uvicorn
        uvicorn.run("plcodestore.studio:app",host=args.host,port=args.port)
if __name__=="__main__":
    main()
