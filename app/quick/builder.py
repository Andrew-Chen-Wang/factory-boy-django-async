import inspect

from factory import errors, enums
from factory.builder import StepBuilder, BuildStep, parse_declarations, Resolver


class AsyncBuildStep(BuildStep):
    async def aresolve(self, declarations):
        self.stub = AsyncResolver(
            declarations=declarations,
            step=self,
            sequence=self.sequence,
        )

        for field_name in declarations:
            self.attributes[field_name] = await self.stub.aget(field_name)

    async def arecurse(self, factory, declarations, force_sequence=None):
        from app.quick.base import AsyncFactory

        if not issubclass(factory, AsyncFactory):
            raise errors.AssociatedClassError(
                "%r: Attempting to recursing into a non-factory object %r"
                % (self, factory))
        builder = self.builder.recurse(factory._meta, declarations)
        return await builder.abuild(parent_step=self, force_sequence=force_sequence)


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

        step = AsyncBuildStep(
            builder=self,
            sequence=sequence,
            parent_step=parent_step,
        )
        await step.aresolve(pre)

        args, kwargs = self.factory_meta.prepare_arguments(step.attributes)

        instance = await self.factory_meta.ainstantiate(
            step=step,
            args=args,
            kwargs=kwargs,
        )

        postgen_results = {}
        for declaration_name in post.sorted():
            declaration = post[declaration_name]
            declaration_result = await declaration.declaration.aevaluate_post(
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


class AsyncResolver(Resolver):
    """Resolve a set of declarations.

    Attributes are set at instantiation time, values are computed lazily.

    Attributes:
        __initialized (bool): whether this object's __init__ as run. If set,
            setting any attribute will be prevented.
        __declarations (dict): maps attribute name to their declaration
        __values (dict): maps attribute name to computed value
        __pending (str list): names of the attributes whose value is being
            computed. This allows to detect cyclic lazy attribute definition.
        __step (BuildStep): the BuildStep related to this resolver.
            This allows to have the value of a field depend on the value of
            another field
    """

    __initialized = False

    def __init__(self, declarations, step, sequence):
        self.__declarations = declarations
        self.__step = step

        self.__values = {}
        self.__pending = []

        self.__initialized = True

    @property
    def factory_parent(self):
        return self.__step.parent_step.stub if self.__step.parent_step else None

    def __repr__(self):
        return '<Resolver for %r>' % self.__step

    async def aget(self, name):
        """Retrieve an attribute's value.

        This will compute it if needed, unless it is already on the list of
        attributes being computed.
        """
        if name in self.__pending:
            raise errors.CyclicDefinitionError(
                "Cyclic lazy attribute definition for %r; cycle found in %r." %
                (name, self.__pending))
        elif name in self.__values:
            return self.__values[name]
        elif name in self.__declarations:
            declaration = self.__declarations[name]
            value = declaration.declaration
            if enums.get_builder_phase(value) == enums.BuilderPhase.ATTRIBUTE_RESOLUTION:
                self.__pending.append(name)
                try:
                    value = await value.aevaluate_pre(
                        instance=self,
                        step=self.__step,
                        overrides=declaration.context,
                    )
                finally:
                    last = self.__pending.pop()
                assert name == last

            self.__values[name] = value
            return value
        else:
            raise AttributeError(
                "The parameter %r is unknown. Evaluated attributes are %r, "
                "definitions are %r." % (name, self.__values, self.__declarations))

    async def aset(self, name, value):
        """Prevent setting attributes once __init__ is done."""
        if not self.__initialized:
            return await super().aset(name, value)
        else:
            raise AttributeError('Setting of object attributes is not allowed')
