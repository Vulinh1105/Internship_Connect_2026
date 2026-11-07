from datetime import date, datetime
from sqlalchemy import inspect, select
from fastapi import HTTPException

def record(obj, *fields):
    names = fields or tuple(a.key for a in inspect(obj).mapper.column_attrs)
    return {key: value.isoformat() if isinstance(value := getattr(obj, key), (date, datetime)) else value
            for key in names}

def require(obj, message="Không tìm thấy dữ liệu"):
    if obj is None:
        raise HTTPException(404, message)
    return obj

def first(db, model, **filters):
    return db.scalar(select(model).filter_by(**filters))

def put(db, model, keys, **values):
    item = first(db, model, **keys)
    if item is None:
        item = model(**keys, **values)
        db.add(item)
    else:
        for field, value in values.items():
            setattr(item, field, value)
    db.flush()
    return item
