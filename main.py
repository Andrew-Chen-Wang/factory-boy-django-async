############################################################################
## Django ORM Standalone Python Template
############################################################################
""" Here we'll import the parts of Django we need. It's recommended to leave
these settings as is, and skip to START OF APPLICATION section below """

# Turn off bytecode generation
import sys


sys.dont_write_bytecode = True

# Django specific settings
import os


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.base")
import django


django.setup()
############################################################################
## START OF APPLICATION
############################################################################
import asyncio  # noqa

from app.factories import FriendFactory, ProfileFactory  # noqa
from app.models import Friend, Profile  # noqa


async def main():
    friends = await FriendFactory.create_batch(10)
    assert await Friend.objects.acount() == 10
    await ProfileFactory.create(user=friends[0].user)
    assert await Profile.objects.acount() == 1
    built_profile = await ProfileFactory.build()
    assert built_profile.pk is None
    assert await Profile.objects.acount() == 1


if __name__ == "__main__":
    asyncio.run(main())
