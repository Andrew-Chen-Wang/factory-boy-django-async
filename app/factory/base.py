import inspect

import factory
from factory import errors, enums, builder
from factory.builder import parse_declarations
from factory.base import OptionDefault

from .builder import StepBuilder, BuildStep


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


class BaseFactory(factory.base.BaseFactory):
    """Factory base support for sequences, attributes and stubs."""

    @classmethod
    def _generate(cls, strategy, params):
        """generate the object.

        Args:
            params (dict): attributes to use for generating the object
            strategy: the strategy to use
        """
        if cls._meta.abstract:
            raise errors.FactoryError(
                "Cannot generate instances of abstract factory %(f)s; "
                "Ensure %(f)s.Meta.model is set and %(f)s.Meta.abstract "
                "is either not set or False." % dict(f=cls.__name__))

        step = builder.StepBuilder(cls._meta, params, strategy)
        return step.build()

    @classmethod
    async def _agenerate(cls, strategy, params):
        if cls._meta.abstract:
            raise factory.errors.FactoryError(
                "Cannot generate instances of abstract factory %(f)s; "
                "Ensure %(f)s.Meta.model is set and %(f)s.Meta.abstract "
                "is either not set or False." % dict(f=cls.__name__))

        step = StepBuilder(cls._meta, params, strategy)
        return await step.abuild()

    @classmethod
    def _after_postgeneration(cls, instance, create, results=None):
        """Hook called after post-generation declarations have been handled.

        Args:
            instance (object): the generated object
            create (bool): whether the strategy was 'build' or 'create'
            results (dict or None): result of post-generation declarations
        """
        pass

    @classmethod
    def _build(cls, model_class, *args, **kwargs):
        """Actually build an instance of the model_class.

        Customization point, will be called once the full set of args and kwargs
        has been computed.

        Args:
            model_class (type): the class for which an instance should be
                built
            args (tuple): arguments to use when building the class
            kwargs (dict): keyword arguments to use when building the class
        """
        return model_class(*args, **kwargs)

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        """Actually create an instance of the model_class.

        Customization point, will be called once the full set of args and kwargs
        has been computed.

        Args:
            model_class (type): the class for which an instance should be
                created
            args (tuple): arguments to use when creating the class
            kwargs (dict): keyword arguments to use when creating the class
        """
        return model_class(*args, **kwargs)

    @classmethod
    def build(cls, **kwargs):
        """Build an instance of the associated class, with overridden attrs."""
        return cls._generate(enums.BUILD_STRATEGY, kwargs)

    @classmethod
    def build_batch(cls, size, **kwargs):
        """Build a batch of instances of the given class, with overridden attrs.

        Args:
            size (int): the number of instances to build

        Returns:
            object list: the built instances
        """
        return [cls.build(**kwargs) for _ in range(size)]

    @classmethod
    def create(cls, **kwargs):
        """Create an instance of the associated class, with overridden attrs."""
        return cls._generate(enums.CREATE_STRATEGY, kwargs)

    @classmethod
    async def acreate(cls, **kwargs):
        """Create an instance of the associated class, with overridden attrs."""
        return await cls._agenerate(enums.CREATE_STRATEGY, kwargs)

    @classmethod
    def create_batch(cls, size, **kwargs):
        """Create a batch of instances of the given class, with overridden attrs.

        Args:
            size (int): the number of instances to create

        Returns:
            object list: the created instances
        """
        return [cls.create(**kwargs) for _ in range(size)]

    @classmethod
    async def acreate_batch(cls, size, **kwargs):
        """Create a batch of instances of the given class, with overridden attrs.

        Args:
            size (int): the number of instances to create

        Returns:
            object list: the created instances
        """
        return [await cls.acreate(**kwargs) for _ in range(size)]

    @classmethod
    def stub(cls, **kwargs):
        """Retrieve a stub of the associated class, with overridden attrs.

        This will return an object whose attributes are those defined in this
        factory's declarations or in the extra kwargs.
        """
        return cls._generate(enums.STUB_STRATEGY, kwargs)

    @classmethod
    def stub_batch(cls, size, **kwargs):
        """Stub a batch of instances of the given class, with overridden attrs.

        Args:
            size (int): the number of instances to stub

        Returns:
            object list: the stubbed instances
        """
        return [cls.stub(**kwargs) for _ in range(size)]

    @classmethod
    def generate(cls, strategy, **kwargs):
        """Generate a new instance.

        The instance will be created with the given strategy (one of
        BUILD_STRATEGY, CREATE_STRATEGY, STUB_STRATEGY).

        Args:
            strategy (str): the strategy to use for generating the instance.

        Returns:
            object: the generated instance
        """
        assert strategy in (enums.STUB_STRATEGY, enums.BUILD_STRATEGY, enums.CREATE_STRATEGY)
        action = getattr(cls, strategy)
        return action(**kwargs)

    @classmethod
    def generate_batch(cls, strategy, size, **kwargs):
        """Generate a batch of instances.

        The instances will be created with the given strategy (one of
        BUILD_STRATEGY, CREATE_STRATEGY, STUB_STRATEGY).

        Args:
            strategy (str): the strategy to use for generating the instance.
            size (int): the number of instances to generate

        Returns:
            object list: the generated instances
        """
        assert strategy in (enums.STUB_STRATEGY, enums.BUILD_STRATEGY, enums.CREATE_STRATEGY)
        batch_action = getattr(cls, '%s_batch' % strategy)
        return batch_action(size, **kwargs)

    @classmethod
    def simple_generate(cls, create, **kwargs):
        """Generate a new instance.

        The instance will be either 'built' or 'created'.

        Args:
            create (bool): whether to 'build' or 'create' the instance.

        Returns:
            object: the generated instance
        """
        strategy = enums.CREATE_STRATEGY if create else enums.BUILD_STRATEGY
        return cls.generate(strategy, **kwargs)

    @classmethod
    def simple_generate_batch(cls, create, size, **kwargs):
        """Generate a batch of instances.

        These instances will be either 'built' or 'created'.

        Args:
            size (int): the number of instances to generate
            create (bool): whether to 'build' or 'create' the instances.

        Returns:
            object list: the generated instances
        """
        strategy = enums.CREATE_STRATEGY if create else enums.BUILD_STRATEGY
        return cls.generate_batch(strategy, size, **kwargs)



class Factory(BaseFactory, factory.Factory):
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
    async def acreate_batch(cls, size, **kwargs):
        return [await cls.acreate(**kwargs) for _ in range(size)]


class AsyncStepBuilder(StepBuilder):
    # Redefine build function that await for instance creation and awaitable postgenerations
    async def abuild(self, parent_step=None, force_sequence=None):
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

        step = BuildStep(
            builder=self,
            sequence=sequence,
            parent_step=parent_step,
        )
        step.resolve(pre)

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

        await self.factory_meta.ause_postgeneration_results(
            instance=instance,
            step=step,
            results=postgen_results,
        )
        return instance
