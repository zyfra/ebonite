"""This module contains code for your custom model.
It consists of user-defined class MyLinReg, global variable mdl with instance of this class
and function run, which uses this global variable.
Also, this module depends on requests module (for demo purposes)"""

# noinspection PyUnresolvedReferences
import requests  # noqa


class MyLinReg:
    def __init__(self, a, b):
        self.a = a
        self.b = b

    def apply_model(self, data):
        return data * self.a + self.b


mdl = MyLinReg(6, 1)


def run_my_model(data):
    return mdl.apply_model(data)
