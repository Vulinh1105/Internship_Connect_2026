import argparse
from pathlib import Path
from sqlalchemy import select
from app.core import metadata
from app.core.database import Session
from app.ai.rag.ingest import ingest
from app.ai.vector.client import close
from app.ai.vector.sync import drain
from app.modules.auth.models import User

def main():
    parser=argparse.ArgumentParser(description="Import a local knowledge file")
    parser.add_argument("path",type=Path)
    parser.add_argument("--title")
    args=parser.parse_args()
    with Session() as db:
        user=db.scalar(select(User).where(User.role=="admin",User.active.is_(True)).limit(1))
        if not user:
            parser.error("Seed the database or activate an admin first")
        item=ingest(db,{"id":user.id,"role":user.role},args.path,args.title)
        print("Document:",item["id"],drain(db))
    close()

if __name__=="__main__":
    main()
