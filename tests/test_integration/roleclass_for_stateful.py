from dataclasses import dataclass
from tortoise import fields
from tests.models import ArrayField, Guild, Roles
from hypothesis import given, strategies as st
import pytest


    
@given(st.integers(), st.integers())
@pytest.mark.asyncio
async def create_new_roles_obj(role: int, guild: int) -> None:
    await Roles.create(guild_id=guild, staff_roles=[role])

@pytest.mark.asyncio
@given(st.integers(), st.integers())
async def append_role_to_arrayfield(self, role: int, data) -> None:
    await self.roles.append("staff_roles", role)

async def remove_role_from_arrayfield(self, data: st.SearchStrategy) -> None:
    role = data.draw(st.sampled_from(self.roles.staff_roles))  # get a reference from line items to create similar
    await self.roles.remove("staff_roles", role)

async def remove_line_item_from_empty_order_raises_exception(self, data: st.SearchStrategy) -> None:
    rolempyt = data.draw(st.sampled_from(self.staff_roles))
    with pytest.raises(ValueError):
        await self.roles.remove("staff_roles", rolempyt)

def update_line_item_quantity(self, data: st.SearchStrategy, quantity: int) -> None:
    self.roles.get("staff_roles")

def total_agrees(self) -> None:
    assert sum(li.total for li in self.order.line_items) == self.order.total

def total_agrees_zero(self) -> None:
    assert self.order.total == 0


