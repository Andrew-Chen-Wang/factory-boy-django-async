import pytest

from app.factories import FriendFactory, ProfileFactory
from app.models import Friend, Profile


pytestmark = [pytest.mark.django_db(transaction=True), pytest.mark.asyncio]


async def test_creation():
    friends = await FriendFactory.create_batch(10)
    assert await Friend.objects.acount() == 10
    await ProfileFactory.create(user=friends[0].user)
    assert await Profile.objects.acount() == 1
    built_profile = await ProfileFactory.build()
    assert built_profile.pk is None
    assert await Profile.objects.acount() == 1
