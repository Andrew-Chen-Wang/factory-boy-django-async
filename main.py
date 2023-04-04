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

import inspect
import factory
from factory import errors, SubFactory, Faker
from factory.builder import StepBuilder, BuildStep, parse_declarations
from django.db import IntegrityError


class AsyncFactory(factory.django.DjangoModelFactory):
    @classmethod
    async def _generate(cls, strategy, params):
        if cls._meta.abstract:
            raise factory.errors.FactoryError(
                "Cannot generate instances of abstract factory %(f)s; "
                "Ensure %(f)s.Meta.model is set and %(f)s.Meta.abstract "
                "is either not set or False." % dict(f=cls.__name__))

        step = AsyncStepBuilder(cls._meta, params, strategy)
        return await step.build()

    class Meta:
        abstract = True  # Optional, but explicit.

    @classmethod
    async def _get_or_create(cls, model_class, *args, **kwargs):
        """Create an instance of the model through objects.get_or_create."""
        manager = cls._get_manager(model_class)

        assert 'defaults' not in cls._meta.django_get_or_create, (
            "'defaults' is a reserved keyword for get_or_create "
            "(in %s._meta.django_get_or_create=%r)"
            % (cls, cls._meta.django_get_or_create))

        key_fields = {}
        for field in cls._meta.django_get_or_create:
            if field not in kwargs:
                raise errors.FactoryError(
                    "django_get_or_create - "
                    "Unable to find initialization value for '%s' in factory %s" %
                    (field, cls.__name__))
            key_fields[field] = kwargs.pop(field)
        key_fields['defaults'] = kwargs

        try:
            instance, _created = await manager.aget_or_create(*args, **key_fields)
        except IntegrityError as e:
            get_or_create_params = {
                lookup: value
                for lookup, value in cls._original_params.items()
                if lookup in cls._meta.django_get_or_create
            }
            if get_or_create_params:
                try:
                    instance = await manager.aget(**get_or_create_params)
                except manager.model.DoesNotExist:
                    # Original params are not a valid lookup and triggered a create(),
                    # that resulted in an IntegrityError. Follow Django’s behavior.
                    raise e
            else:
                raise e

        return instance

    @classmethod
    async def _create(cls, model_class, *args, **kwargs):
        """Create an instance of the model, and save it to the database."""
        if cls._meta.django_get_or_create:
            return await cls._get_or_create(model_class, *args, **kwargs)

        manager = cls._get_manager(model_class)
        return await manager.acreate(*args, **kwargs)

    @classmethod
    async def create_batch(cls, size, **kwargs):
        """Create a batch of instances of the model, and save them to the database."""
        return [await cls.create(**kwargs) for _ in range(size)]

    @classmethod
    async def _after_postgeneration(cls, instance, create, results=None):
        """Save again the instance if creating and at least one hook ran."""
        if create and results:
            # Some post-generation hooks ran, and may have modified us.
            await instance.asave()


class AsyncBuildStep(BuildStep):
    async def resolve(self, declarations):
        self.stub = factory.builder.Resolver(
            declarations=declarations,
            step=self,
            sequence=self.sequence,
        )

        for field_name in declarations:
            attr = getattr(self.stub, field_name)
            if inspect.isawaitable(attr):
                attr = await attr
            self.attributes[field_name] = attr


class AsyncStepBuilder(StepBuilder):
    # Redefine build function that await for instance creation and awaitable postgenerations
    async def build(self, parent_step=None, force_sequence=None):
        """Build a factory instance."""
        # TODO: Handle "batch build" natively
        pre, post = parse_declarations(
            self.extras,
            base_pre=self.factory_meta.pre_declarations,
            base_post=self.factory_meta.post_declarations,
        )

        if force_sequence is not None:
            sequence = force_sequence
        elif self.force_init_sequence is not None:
            sequence = self.force_init_sequence
        else:
            sequence = self.factory_meta.next_sequence()

        step = AsyncBuildStep(
            builder=self,
            sequence=sequence,
            parent_step=parent_step,
        )
        await step.resolve(pre)

        args, kwargs = self.factory_meta.prepare_arguments(step.attributes)

        instance = await self.factory_meta.instantiate(
            step=step,
            args=args,
            kwargs=kwargs,
        )

        postgen_results = {}
        for declaration_name in post.sorted():
            declaration = post[declaration_name]
            declaration_result = declaration.declaration.evaluate_post(
                instance=instance,
                step=step,
                overrides=declaration.context,
            )
            if inspect.isawaitable(declaration_result):
                declaration_result = await declaration_result
            postgen_results[declaration_name] = declaration_result

        self.factory_meta.use_postgeneration_results(
            instance=instance,
            step=step,
            results=postgen_results,
        )
        return instance


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
