"""
docsource: Parse, check and update doc-string documentation

Copyright 2025-2026, Levente Hunyadi

:see: https://github.com/hunyadi/docsource
"""

import enum
import inspect
import sys
from enum import Enum
from types import FunctionType, ModuleType
from typing import TypeGuard

if sys.version_info >= (3, 11):

    def is_type_enum(obj: object) -> TypeGuard[type[Enum]]:
        """
        True if the specified type is an enumeration type.

        :param obj: The object to test.
        :returns: True if the object is an enumeration type.
        """

        return isinstance(obj, enum.EnumType)

else:

    def is_type_enum(obj: object) -> TypeGuard[type[Enum]]:
        """
        True if the specified type is an enumeration type.

        :param obj: The object to test.
        :returns: True if the object is an enumeration type.
        """

        # use an explicit isinstance(..., type) check to filter out special forms like generics
        return isinstance(obj, type) and issubclass(obj, Enum)


def is_exception(obj: object) -> TypeGuard[type[BaseException]]:
    """
    Checks whether an object is an exception type.

    :param obj: The object to test.
    :returns: True if the object is an exception type.
    """

    return isinstance(obj, type) and issubclass(obj, BaseException)


def get_exceptions(module: ModuleType) -> dict[str, type[BaseException]]:
    """
    Returns all exception classes declared in a module.

    :param module: The module to scan.
    :returns: Exception classes declared in the specified module.
    """

    return {name: class_type for name, class_type in inspect.getmembers(module, is_exception)}


def get_module_classes(module: ModuleType) -> list[type]:
    """
    Returns all classes declared directly in a module.

    :param module: The module to scan.
    :returns: Classes declared in the specified module.
    """

    def is_class_member(member: object) -> TypeGuard[type]:
        return inspect.isclass(member) and member.__module__ == module.__name__

    return [class_type for _, class_type in inspect.getmembers(module, is_class_member)]


def get_module_functions(module: ModuleType) -> list[FunctionType]:
    """
    Returns all functions declared directly in a module.

    :param module: The module to scan.
    :returns: Functions declared in the specified module.
    """

    def is_function_member(member: object) -> TypeGuard[FunctionType]:
        return inspect.isfunction(member) and member.__module__ == module.__name__

    return [func_type for _, func_type in inspect.getmembers(module, is_function_member)]
