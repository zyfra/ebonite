from typing import Dict, Type, Union

from ebonite.build.runner.base import RunnerBase
from ebonite.build.runner.docker import DockerRunner
from ebonite.core.objects import RuntimeInstance


class RunnersCatalog:
    """
    Catalog for all known :class:`.RunnerBase` implementations
    """

    _alias_runners: Dict[str, RunnerBase] = {
        'docker': DockerRunner()
    }
    _type_runners: Dict[Type[RuntimeInstance.Params], RunnerBase] = {
        r.instance_type(): r for r in _alias_runners.values()
    }

    @staticmethod
    def get(alias: Union[str, Type[RuntimeInstance.Params]]) -> RunnerBase:
        if isinstance(alias, str):
            runner = RunnersCatalog._alias_runners.get(alias, None)
            if runner is None:
                raise TypeError(f'No runner registered for alias `{alias}`')
        else:
            runner = RunnersCatalog._type_runners.get(alias, None)
            if runner is None:
                raise TypeError(f'No runner registered for type `{alias}`')
        return runner
