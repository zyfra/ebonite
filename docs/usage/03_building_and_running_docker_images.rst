========================================
Building and running docker images
========================================

The easiest way to build docker image from :class:`~ebonite.core.objects.core.Model` is to use :func:`~ebonite.build.build_model_docker` helper function. Even with this function builds are pretty customizable, for example take a look at :func:`~ebonite.ext.flask.build_model_flask_docker`.
However if you need to customize even more, you can manually implement :class:`~ebonite.build.provider.ProviderBase` and :class:`~ebonite.build.builder.BuilderBase` classes.