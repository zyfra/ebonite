from typing import Dict
from pyjackson.core import Comparable
from pyjackson.utils import get_class_fields


class EboniteParams(Comparable):
    """
    Base class for Ebonite parameter classes
    """
    def update(self, update_dict: Dict):
        for field in get_class_fields(self.__class__):
            if field.name in update_dict:
                try:
                    setattr(self, field.name, update_dict[field.name])
                except AttributeError:
                    continue
        return self

