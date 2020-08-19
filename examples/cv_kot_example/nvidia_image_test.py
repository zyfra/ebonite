import ebonite
from ebonite.build.builder.base import use_local_installation
from ebonite.ext.cv_streaming.server import CvStreamingServer

with use_local_installation():
    ebnt = ebonite.client.Ebonite.local(clear=True)
    task = ebnt.get_or_create_task('Proj', 'Task')
    model = ebnt.create_model(lambda x: x, 'test_input', 'model', task_name='Task')
    image = ebnt.create_image(model, 'image_name', server=CvStreamingServer, builder_args={'force_overwrite': True})
