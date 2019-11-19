from ebonite.utils.classproperty import classproperty


class MyClass:
    @classproperty
    def prop1(self):
        return 'a'

    @classproperty
    @classmethod
    def prop2(self):
        return 'b'


def test_classproperty__get():
    assert MyClass.prop1 == 'a'
    assert MyClass.prop2 == 'b'
