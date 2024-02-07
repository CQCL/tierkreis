import re

import pydantic as pyd

# regex pattern to find capital letters in a string (excluding the first character)
SNAKE_PATTERN: re.Pattern = re.compile(r"(?<!^)(?=[A-Z])")


def _to_snake_case(s: str) -> str:
    # insert underscore before capital letters and convert to lower case
    return SNAKE_PATTERN.sub("_", s).lower()


class OpaqueModel(pyd.BaseModel):
    """A type that is opaque to the Tierkreis system. Mapped to a StructType
    with a single field (field name may be customise by overloading
    `tierkreis_field`) with a string value holding the JSON serialized
    model."""

    @classmethod
    def tierkreis_field(cls) -> str:
        """Return the name of the field that will hold the JSON serialized string"""
        return "__tk_opaque_" + _to_snake_case(cls.__name__)
