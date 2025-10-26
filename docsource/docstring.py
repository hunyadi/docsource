"""
docsource: Parse, check and update doc-string documentation

Copyright 2025, Levente Hunyadi

:see: https://github.com/hunyadi/docsource
"""

import builtins
import dataclasses
import inspect
import re
from dataclasses import dataclass
from io import StringIO
from typing import Any, Callable, Protocol, TypeVar

from .inspection import get_exceptions, is_type_enum

T = TypeVar("T")


@dataclass
class DocstringParam:
    """
    A parameter declaration in a parameter block.

    :param name: The name of the parameter.
    :param description: The description text for the parameter.
    :param param_type: The Python type of the parameter.
    """

    name: str
    description: str
    param_type: Any = inspect.Signature.empty

    def __str__(self) -> str:
        return f":param {self.name}: {self.description}"


@dataclass
class DocstringReturns:
    """
    A `returns` declaration extracted from a doc-string.

    :param description: The description text for the return value.
    :param return_type: The Python type of the return value.
    """

    description: str
    return_type: type = inspect.Signature.empty

    def __str__(self) -> str:
        return f":returns: {self.description}"


@dataclass
class DocstringRaises:
    """
    A `raises` declaration extracted from a doc-string.

    :param typename: The type name of the exception raised.
    :param description: The description associated with the exception raised.
    :param raise_type: The Python type of the exception raised.
    """

    typename: str
    description: str
    raise_type: type = inspect.Signature.empty

    def __str__(self) -> str:
        return f":raises {self.typename}: {self.description}"


@dataclass
class DocstringSeeAlso:
    """
    A `see` declaration extracted from a doc-string.

    Interpretation of the reference text is up to the user. For example, a documentation generator may interpret
    the text as a Python package, class or function reference and convert the text into a link.

    :param text: Reference text.
    """

    text: str

    def __str__(self) -> str:
        return f":see: {self.text}"


@dataclass
class Docstring:
    """
    Represents the documentation string (a.k.a. doc-string) for a type such as a (data) class or function.

    A doc-string is broken down into the following components:
    * A short description, which is the first block of text in the documentation string, and ends with a double
      newline or a parameter block.
    * A long description, which is the optional block of text following the short description, and ends with
      a parameter block.
    * A parameter block of named parameter and description string pairs in ReST-style.
    * A `returns` declaration, which adds explanation to the return value.
    * A `raises` declaration, which adds explanation to the exception type raised by the function on error.

    When the doc-string is attached to a data class, it is understood as the documentation string of the class
    `__init__` method.

    :param short_description: The short description text parsed from a doc-string.
    :param long_description: The long description text parsed from a doc-string.
    :param params: The parameter block extracted from a doc-string.
    :param returns: The returns declaration extracted from a doc-string.
    :param raises: The exception declaration block extracted from a doc-string.
    :param see_also: Zero or more see-also declarations extracted from a doc-string.
    """

    short_description: str | None = None
    long_description: str | None = None
    params: dict[str, DocstringParam] = dataclasses.field(default_factory=dict[str, DocstringParam])
    returns: DocstringReturns | None = None
    raises: dict[str, DocstringRaises] = dataclasses.field(default_factory=dict[str, DocstringRaises])
    see_also: list[DocstringSeeAlso] = dataclasses.field(default_factory=list[DocstringSeeAlso])

    @property
    def full_description(self) -> str | None:
        if self.short_description and self.long_description:
            return f"{self.short_description}\n\n{self.long_description}"
        elif self.short_description:
            return self.short_description
        else:
            return None

    @property
    def empty(self) -> bool:
        return (
            self.short_description is None
            and self.long_description is None
            and not self.params
            and self.returns is None
            and not self.raises
            and not self.see_also
        )

    def __str__(self) -> str:
        output = StringIO()

        has_description = self.short_description or self.long_description
        has_blocks = self.params or self.returns or self.raises or self.see_also

        if has_description:
            if self.short_description and self.long_description:
                output.write(self.short_description)
                output.write("\n\n")
                output.write(self.long_description)
            elif self.short_description:
                output.write(self.short_description)

        if has_blocks:
            if has_description:
                output.write("\n")

            for param in self.params.values():
                output.write("\n")
                output.write(str(param))
            if self.returns:
                output.write("\n")
                output.write(str(self.returns))
            for raises in self.raises.values():
                output.write("\n")
                output.write(str(raises))
            for see in self.see_also:
                output.write("\n")
                output.write(str(see))

        s = output.getvalue()
        output.close()
        return s


class SupportsDoc(Protocol):
    __doc__: str | None


def parse_type(typ: SupportsDoc) -> Docstring:
    """
    Parse the doc-string of a type into its components.

    :param typ: The type whose documentation string to parse.
    :returns: Components of the documentation string.
    """

    doc = get_docstring(typ)
    if doc is None:
        return Docstring()

    docstring = parse_text(doc)
    check_docstring(typ, docstring)

    # assign parameter and return types
    if isinstance(typ, type) and dataclasses.is_dataclass(typ):
        properties = {field.name: field.type for field in dataclasses.fields(typ)}

        for name, param in docstring.params.items():
            param.param_type = properties[name]

    elif inspect.isfunction(typ):  # pyright: ignore[reportUnknownArgumentType]
        signature = inspect.signature(typ, eval_str=True)
        for name, param in docstring.params.items():
            param.param_type = signature.parameters[name].annotation
        if docstring.returns:
            docstring.returns.return_type = signature.return_annotation

    # assign exception types
    defining_module = inspect.getmodule(typ)  # pyright: ignore[reportUnknownArgumentType]
    if defining_module:
        context: dict[str, type] = {}
        context.update(get_exceptions(builtins))
        context.update(get_exceptions(defining_module))
        for exc_name, exc in docstring.raises.items():
            raise_type = context.get(exc_name)
            if raise_type is None:
                type_name = getattr(typ, "__qualname__", None) or getattr(typ, "__name__", None) or None  # pyright: ignore[reportUnknownArgumentType]
                raise TypeError(f"doc-string exception type `{exc_name}` is not an exception defined in the context of `{type_name}`")

            exc.raise_type = raise_type

    return docstring


def parse_text(text: str) -> Docstring:
    """
    Parse a ReST-style doc-string into its components.

    :param text: The documentation string to parse, typically acquired as `type.__doc__`.
    :returns: Components of the documentation string.
    """

    if not text:
        return Docstring()

    # find block that starts object metadata block (e.g. `:param p:` or `:returns:`)
    text = inspect.cleandoc(text)
    match = re.search("^:", text, flags=re.MULTILINE)
    if match:
        desc_chunk = text[: match.start()]
        meta_chunk = text[match.start() :]  # noqa: E203
    else:
        desc_chunk = text
        meta_chunk = ""

    # split description text into short and long description
    parts = desc_chunk.split("\n\n", 1)

    # ensure short description has no newlines
    short_description = parts[0].strip().replace("\n", " ") or None

    # ensure long description preserves its structure (e.g. preformatted text)
    if len(parts) > 1:
        long_description = parts[1].strip() or None
    else:
        long_description = None

    params: dict[str, DocstringParam] = {}
    raises: dict[str, DocstringRaises] = {}
    returns = None
    see_also: list[DocstringSeeAlso] = []
    for match in re.finditer(r"(^:.*?)(?=^:|\Z)", meta_chunk, flags=re.DOTALL | re.MULTILINE):
        chunk = match.group(0)
        if not chunk:
            continue

        args_chunk, desc_chunk = chunk.lstrip(":").split(":", 1)
        args = args_chunk.split()
        desc = re.sub(r"\s+", " ", desc_chunk.strip())

        if len(args) > 0:
            kw = args[0]
            if len(args) == 2:
                if kw == "param":
                    params[args[1]] = DocstringParam(
                        name=args[1],
                        description=desc,
                    )
                elif kw == "raise" or kw == "raises":
                    raises[args[1]] = DocstringRaises(
                        typename=args[1],
                        description=desc,
                    )

            elif len(args) == 1:
                if kw == "return" or kw == "returns":
                    returns = DocstringReturns(description=desc)
                elif kw == "see" or kw == "seealso":
                    see_also.append(DocstringSeeAlso(desc))

    return Docstring(
        long_description=long_description,
        short_description=short_description,
        params=params,
        returns=returns,
        raises=raises,
        see_also=see_also,
    )


def has_default_docstring(typ: SupportsDoc) -> bool:
    """
    Check if class has the auto-generated string assigned by `@dataclass` or `enum.Enum`.

    :param typ: The Python type whose doc-string to inspect.
    :returns: True if the class has the default text assigned by `@dataclass` or `enum.Enum`.
    """

    if not isinstance(typ, type):
        return False

    if dataclasses.is_dataclass(typ):
        return typ.__doc__ is not None and re.match(f"^{re.escape(typ.__name__)}[(].*[)]$", typ.__doc__) is not None

    if is_type_enum(typ):  # pyright: ignore[reportUnknownArgumentType]
        return typ.__doc__ is not None and typ.__doc__ == "An enumeration."

    return False


def has_docstring(typ: SupportsDoc) -> bool:
    """
    Check if class has a documentation string other than the auto-generated string assigned by @dataclass.

    :param typ: The Python type whose doc-string to inspect.
    :returns: True if the class has its own doc-string text.
    """

    if has_default_docstring(typ):
        return False

    return bool(typ.__doc__)


def get_docstring(typ: SupportsDoc) -> str | None:
    """
    Retrieves the raw doc-string text for a Python type.

    :param typ: The Python type whose doc-string to extract.
    :returns: Raw doc-string text or `None`.
    """

    if typ.__doc__ is None:
        return None

    if has_default_docstring(typ):
        return None

    return typ.__doc__


def check_docstring(typ: SupportsDoc, docstring: Docstring, strict: bool = False) -> None:
    """
    Verifies the doc-string of a type.

    :param typ: The Python type whose doc-string to verify.
    :param docstring: Parsed components of the doc-string.
    :param strict: Whether to raise errors when a parameter or return value in the signature lacks its corresponding doc-string.
    :raises TypeError: Raised on a mismatch between doc-string parameters, and function or type signature.
    """

    if isinstance(typ, type) and dataclasses.is_dataclass(typ):
        check_dataclass_docstring(typ, docstring, strict)
    elif inspect.isfunction(typ):  # pyright: ignore[reportUnknownArgumentType]
        check_function_docstring(typ, docstring, strict)


def check_dataclass_docstring(typ: type[T], docstring: Docstring, strict: bool = False) -> None:
    """
    Verifies the doc-string of a data-class type.

    :param typ: The Python data-class type whose doc-string to verify.
    :param docstring: Parsed components of the doc-string.
    :param strict: Whether to check if all data-class members have doc-strings.
    :raises TypeError: Raised on a mismatch between doc-string parameters and data-class members.
    """

    if not dataclasses.is_dataclass(typ):
        raise TypeError(f"`{typ.__name__}` is not a data-class type")

    base_props: set[str] = set()
    for base in inspect.getmro(typ):
        if base is typ:
            continue
        if dataclasses.is_dataclass(base):
            for field in dataclasses.fields(base):
                base_props.add(field.name)

    properties: list[str] = []
    for field in dataclasses.fields(typ):
        if field.name not in base_props:
            properties.append(field.name)

    class_name = typ.__name__

    for name in docstring.params:
        if name not in properties:
            raise TypeError(f"doc-string parameter `{name}` is not a member of the data-class `{class_name}`")

    if not strict:
        return

    for name in properties:
        if name not in docstring.params:
            raise TypeError(f"member `{name}` in data-class `{class_name}` is missing its doc-string")


def check_function_docstring(fn: Callable[..., Any], docstring: Docstring, strict: bool = False) -> None:
    """
    Verifies the doc-string of a function or member function.

    :param fn: The Python function whose doc-string to verify.
    :param docstring: Parsed components of the doc-string.
    :param strict: Whether to check if all function parameters and the return type have doc-strings.
    :raises TypeError: Raised on a mismatch between doc-string parameters and function signature.
    """

    signature = inspect.signature(fn, eval_str=True)
    func_name = fn.__qualname__

    for name in docstring.params:
        if name not in signature.parameters:
            raise TypeError(f"doc-string parameter `{name}` is absent from signature of function `{func_name}`")

    if docstring.returns is not None and signature.return_annotation is inspect.Signature.empty:
        raise TypeError(f"doc-string has returns description in function `{func_name}` with no return type annotation")

    if not strict or docstring.empty:
        return

    for name, param in signature.parameters.items():
        # ignore `self` in member function signatures
        if name == "self" and (param.kind is inspect.Parameter.POSITIONAL_ONLY or param.kind is inspect.Parameter.POSITIONAL_OR_KEYWORD):
            continue

        if name not in docstring.params:
            raise TypeError(f"function parameter `{name}` in `{func_name}` is missing its doc-string")

    if signature.return_annotation is not inspect.Signature.empty and signature.return_annotation is not None and docstring.returns is None:
        raise TypeError(f"function `{func_name}` has no returns description in its doc-string")
