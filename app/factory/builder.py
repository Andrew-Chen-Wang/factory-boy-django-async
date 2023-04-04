"""Build factory instances."""

from factory import errors
from factory.builder import (
    parse_declarations, BuildStep as BaseBuildStep, StepBuilder as BaseStepBuilder
)


class BuildStep(BaseBuildStep):
    async def arecurse(self, factory, declarations, force_sequence=None):
        from . import base
        if not issubclass(factory, base.BaseFactory):
            raise errors.AssociatedClassError(
                "%r: Attempting to recursing into a non-factory object %r"
                % (self, factory))
        builder = self.builder.recurse(factory._meta, declarations)
        return await builder.abuild(parent_step=self, force_sequence=force_sequence)


class StepBuilder(BaseStepBuilder):
    """A factory instantiation step.

    Attributes:
    - parent: the parent StepBuilder, or None for the root step
    - extras: the passed-in kwargs for this branch
    - factory: the factory class being built
    - strategy: the strategy to use
    """
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
            postgen_results[declaration_name] = declaration.declaration.evaluate_post(
                instance=instance,
                step=step,
                overrides=declaration.context,
            )
        self.factory_meta.use_postgeneration_results(
            instance=instance,
            step=step,
            results=postgen_results,
        )
        return instance

    # async def recurse(self, factory_meta, extras):
    #     """Recurse into a sub-factory call."""
    #     return self.__class__(factory_meta, extras, strategy=self.strategy)
