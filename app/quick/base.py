# From https://github.com/FactoryBoy/factory_boy/issues/679#issuecomment-995289117
# Kudos: @KharchenkoDmitriy

import inspect

import factory

from app.quick.builder import AsyncStepBuilder


class AsyncFactory(factory.Factory):
    @classmethod
    async def _agenerate(cls, strategy, params):
        if cls._meta.abstract:
            raise factory.errors.FactoryError(
                "Cannot generate instances of abstract factory %(f)s; "
                "Ensure %(f)s.Meta.model is set and %(f)s.Meta.abstract "
                "is either not set or False." % dict(f=cls.__name__))

        step = AsyncStepBuilder(cls._meta, params, strategy)
        return await step.abuild()

    @classmethod
    async def _acreate(cls, model_class, *args, **kwargs):
        for key, value in kwargs.items():
            if inspect.isawaitable(value):
                kwargs[key] = await value
        return await model_class.acreate(*args, **kwargs)

    @classmethod
    async def acreate(cls, **kwargs):
        return await cls._agenerate(factory.enums.CREATE_STRATEGY, kwargs)

    @classmethod
    async def acreate_batch(cls, size, **kwargs):
        return [await cls.acreate(**kwargs) for _ in range(size)]


class FactoryOptions(factory.base.FactoryOptions):
    async def ainstantiate(self, step, args, kwargs):
        model = self.get_model_class()

        if step.builder.strategy == factory.enums.BUILD_STRATEGY:
            return await self.factory._abuild(model, *args, **kwargs)
        elif step.builder.strategy == factory.enums.CREATE_STRATEGY:
            return await self.factory._acreate(model, *args, **kwargs)
        else:
            assert step.builder.strategy == factory.enums.STUB_STRATEGY
            return factory.base.StubObject(**kwargs)

    async def ause_postgeneration_results(self, step, instance, results):
        await self.factory._aafter_postgeneration(
            instance,
            create=step.builder.strategy == factory.enums.CREATE_STRATEGY,
            results=results,
        )
