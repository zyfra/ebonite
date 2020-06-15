from typing import List

import ebonite.client.base
from ebonite import Ebonite
from ebonite.client.expose import ExposedMethod, get_exposed_method
from ebonite.core.objects import Image, Model, Pipeline, Project, RuntimeEnvironment, RuntimeInstance, Task
from ebonite.repository.metadata.base import MetadataRepository

AUTOGEN_CLASSES = {
    MetadataRepository: '#  ########## AUTOGEN META END #',
    Project: '#  ########## AUTOGEN PROJECT END #',
    Task: '#  ########## AUTOGEN TASK END #',
    Model: '#  ########## AUTOGEN MODEL END #',
    Pipeline: '#  ########## AUTOGEN PIPELINE END #',
    Image: '#  ########## AUTOGEN IMAGE END #',
    RuntimeInstance: '#  ########## AUTOGEN INSTANCE END #',
    RuntimeEnvironment: '#  ########## AUTOGEN ENVIRONMENT END #'
}

FILENAME = ebonite.client.base.__file__


def find_exposed_methods(base_class, new_only=True) -> List[ExposedMethod]:
    new_methods = []
    for name in dir(base_class):
        if name.startswith('_'):
            continue
        value = getattr(base_class, name)
        exposed = get_exposed_method(value)
        if exposed is not None and (not new_only or exposed.name not in Ebonite.__dict__):
            new_methods.append(exposed)
    return new_methods


def patch(classes, filename, dry_run=True):
    anchors = {a: cls for cls, a in AUTOGEN_CLASSES.items() if cls in classes}
    code = []
    with open(filename, 'r') as f:
        for line in f:
            strip = line.strip()
            if strip in anchors:
                base_class = anchors[strip]
                for exposed in find_exposed_methods(base_class):
                    code.append(exposed.generate_code() + '\n\n')
            code.append(line)

    if dry_run:
        print(''.join(code))
    else:
        with open(filename, 'w') as f:
            f.write(''.join(code))


def clear(filename, dry_run=True):
    code = []
    is_autogen = False
    with open(filename, 'r') as f:
        for line in f:
            sline = line.strip()
            if sline.startswith('#') and 'AUTOGEN' in sline:
                if 'END' in sline:
                    is_autogen = False
                else:
                    is_autogen = True
                    code.append(line + '\n')
            if not is_autogen:
                code.append(line)

    if dry_run:
        print(''.join(code))
    else:
        with open(filename, 'w') as f:
            f.write(''.join(code))


def main():
    dry_run = True
    # clear(FILENAME, dry_run)
    patch(AUTOGEN_CLASSES, FILENAME, dry_run)


if __name__ == '__main__':
    main()
