from app.core import metadata
from app.core.database import Session
from atexit import register
from app.ai.vector.client import close
from app.ai.vector.sync import drain, reconcile

if __name__=="__main__":
    register(close)
    with Session() as db:
        reconcile(db)
        done=0
        while True:
            result=drain(db,100)
            done+=result["done"]
            if result["failed"]:
                raise SystemExit("Dong bo Qdrant chua thanh cong. Kiem tra cau hinh Qdrant/AI.")
            if not result["done"]:
                break
        print(f"Vector tasks processed: {done}")
