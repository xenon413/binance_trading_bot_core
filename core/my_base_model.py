from pydantic import BaseModel, ConfigDict

class MyBaseModel(BaseModel):
    model_config = ConfigDict(
        extra='forbid',        # fuck the doc it's ass just run and figure out compatibility
        populate_by_name=True, # Allow using field names OR aliases
        # frozen=True
        # strict=True ### use strict to check later just in case pydantic converted something that shoulden't
    )

### define custom Decimal type
# 1. Define the logic once
# def to_decimal(v):
#     if isinstance(v, (float, int)):
#         return Decimal(str(v))
#     return Decimal(v)

# # 2. Create a reusable type "tag"
# SafeDecimal = Annotated[Decimal, BeforeValidator(to_decimal)]

__all__ = ["MyBaseModel"]