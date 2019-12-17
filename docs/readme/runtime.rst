===============
Ebonite Runtime
===============

Runtime module is responsible for code that runs inside containers.

Here are runtime abstractions:

* :class:`~ebonite.runtime.Interface` - an object with some exposed methods. Builtin implementation: ``ModelInterface`` which is created dynamically with :func:`~ebonite.runtime.interface.ml_model.model_interface`.

* :class:`~ebonite.runtime.InterfaceLoader` - loads :class:`~ebonite.runtime.Interface` instance. Builtin implementation: :class:`~ebonite.runtime.interface.ml_model.ModelLoader`

* :class:`~ebonite.runtime.server.Server` - gets an instance of :class:`~ebonite.runtime.Interface` and exposes it's methods via some protocol. Builtin implementation: :class:`~ebonite.ext.flask.FlaskServer` - exposes methods as http POST endpoints.

Also, these helper functions are available:

* :func:`~ebonite.runtime.run_model_server` - create ``ModelInterface`` from model and runs debug :class:`~ebonite.runtime.server.Server`.