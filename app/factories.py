from factory import Faker, SubFactory

from app.factory import AsyncFactory
from app.models import Friend, Profile, User


class UserFactory(AsyncFactory):
    name = Faker("name")

    class Meta:
        model = User


class ProfileFactory(AsyncFactory):
    user = SubFactory(UserFactory)

    class Meta:
        model = Profile


class FriendFactory(AsyncFactory):
    user = SubFactory(UserFactory)
    friend = SubFactory(UserFactory)

    class Meta:
        model = Friend
