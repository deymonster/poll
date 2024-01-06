from sqlalchemy.ext.declarative import declarative_base, declared_attr
from pydantic import BaseModel


def is_pydantic(obj: object):
    """Checks whether an object is pydantic."""
    return type(obj).__class__.__name__ == "ModelMetaclass"


class CustomBase:
    # Generate __tablename__ automaticaly
    @declared_attr
    def __tablename__(cls):
        return cls.__name__.lower()

    @classmethod
    def from_dto(cls, dto: BaseModel):
        obj = cls()
        properties = dict(dto)
        for key, value in properties.items():
            try:
                if is_pydantic(value):
                    value = getattr(cls, key).property.mapper.class_.from_dto(value)
                setattr(obj, key, value)
            except AttributeError as e:
                raise AttributeError(e)
        return obj


Base = declarative_base(cls=CustomBase)
