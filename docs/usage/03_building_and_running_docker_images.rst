========================================
Building and running docker images
========================================

The easiest way to build docker image from :class:`~ebonite.core.objects.core.Model` is to use :meth:`~ebonite.Ebonite.build_image`.
If you need more customizable solution and/or don't need image metadata persistence you can use ::class:`~ebonite.build.builder.DockerBuilder` class manually.
However if you need to customize even more, you can manually implement :class:`~ebonite.build.provider.ProviderBase` and :class:`~ebonite.build.builder.BuilderBase` classes.