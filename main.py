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
import asyncio

from app.models import User, Friend, Profile
from app.factory.declarations import SubFactory
from app.factory.faker import Faker
from app.factory.django import DjangoModelFactory


class UserFactory(DjangoModelFactory):
    name = Faker("name")

    class Meta:
        model = User


class ProfileFactory(DjangoModelFactory):
    user = SubFactory(UserFactory)

    class Meta:
        model = Profile


class FriendFactory(DjangoModelFactory):
    user = SubFactory(UserFactory)
    friend = SubFactory(UserFactory)

    class Meta:
        model = Friend


async def main():
    friends = await FriendFactory.acreate_batch(10)
    await ProfileFactory.create(user=friends[0].user)
    assert await Profile.objects.acount() == 1
    built_profile = await ProfileFactory.build()
    assert built_profile.pk is None
    assert await Profile.objects.acount() == 1


if __name__ == "__main__":
    asyncio.run(main())
