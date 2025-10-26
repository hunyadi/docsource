"""
docsource: Parse, check and update doc-string documentation

Copyright 2025, Levente Hunyadi

:see: https://github.com/hunyadi/docsource
"""

import ast
import textwrap
from ast import AsyncFunctionDef, ClassDef, Constant, Expr, FunctionDef, Module
from collections.abc import Callable
from dataclasses import dataclass
from io import StringIO

from .docstring import Docstring, parse_text


@dataclass
class Location:
    """
    Location of an AST node in a source file.

    :param line: Zero-based index of line.
    :param col: Zero-based index of column.
    """

    __slots__ = ("line", "col")

    line: int
    col: int

    def __lt__(self, op: "Location") -> bool:
        return (self.line, self.col) < (op.line, op.col)

    def __gt__(self, op: "Location") -> bool:
        return (self.line, self.col) > (op.line, op.col)

    def offset(self, line_to_offset: list[int]) -> int:
        """
        Zero-based offset relative to the beginning of the source file.

        :param line_to_offset: Maps line numbers to file offsets.
        """

        return line_to_offset[self.line] + self.col


@dataclass
class OffsetSpan:
    """
    Zero-based offset span.

    :param start: Zero-based index of the beginning of the span.
    :param end: Zero-based index of the end of the span.
    """

    __slots__ = ("start", "end")

    start: int
    end: int


@dataclass
class LocationSpan:
    """
    Location span.

    :param start: Beginning of the span.
    :param end: End of the span.
    """

    __slots__ = ("start", "end")

    start: Location
    end: Location


@dataclass
class DocstringNode:
    """
    A doc-string node in a Python source file.

    :param span: Start and end of the doc-string literal.
    :param text: Text of the doc-string literal.
    """

    span: LocationSpan
    text: str


@dataclass
class Substitution:
    """
    Encapsulates information about a doc-string node to be replaced with a new text.

    :param span: Start and end of the doc-string literal.
    :param docstring: Information to substitute as a doc-string.
    """

    span: LocationSpan
    docstring: Docstring


def _get_docstring_span(
    node: AsyncFunctionDef | FunctionDef | ClassDef | Module,
) -> DocstringNode | None:
    if node.body and isinstance(node.body[0], Expr):
        doc_node = node.body[0].value
        if isinstance(doc_node, Constant) and isinstance(doc_node.value, str):
            if doc_node.end_lineno is None:
                raise ValueError("end line number is missing for doc-string")
            if doc_node.end_col_offset is None:
                raise ValueError("end column offset is missing for doc-string")

            return DocstringNode(
                LocationSpan(Location(doc_node.lineno - 1, doc_node.col_offset), Location(doc_node.end_lineno - 1, doc_node.end_col_offset)), doc_node.value
            )
    return None


def update_docstring(source: str, *, parser: Callable[[str], Docstring] | None = None) -> str:
    """
    Reads source code, identifies doc-string literals, parses doc-string text, and produces normalized (ReST-style) doc-string.

    :param source: Python module source code as a string.
    :param parser: A parser that takes raw doc-string text and returns doc-string components.
    :returns: Source code with doc-string replacements made.
    """

    if parser is None:
        parser = parse_text

    tree = ast.parse(source)
    substitutions: list[Substitution] = []
    for node in ast.walk(tree):
        if isinstance(node, (FunctionDef, AsyncFunctionDef, ClassDef, Module)):
            doc_node = _get_docstring_span(node)
            if doc_node:
                docstring = parser(doc_node.text)
                substitutions.append(Substitution(doc_node.span, docstring))

    substitutions.sort(key=lambda s: s.span.start)

    lines = source.splitlines(keepends=True)
    line_to_offset: list[int] = []
    rolling_sum: int = 0
    for line in lines:
        line_to_offset.append(rolling_sum)
        rolling_sum += len(line)

    s = StringIO()
    pos = 0
    for item in substitutions:
        offset_span = OffsetSpan(item.span.start.offset(line_to_offset), item.span.end.offset(line_to_offset))
        s.write(source[pos : offset_span.start])
        text = str(item.docstring)
        if "\n" in text:
            if '"""' not in text:
                delimiter = '"""'
            elif "'''" not in text:
                delimiter = "'''"
            else:
                raise ValueError("doc-string contains both types of triple-quoted delimiters")
            s.write(delimiter)
            s.write("\n")
            s.write(textwrap.indent(text, " " * item.span.start.col))
            s.write("\n")
            s.write(" " * item.span.start.col)
            s.write(delimiter)
        elif '"' not in text:
            s.write(f'"{text}"')
        elif "'" not in text:
            s.write(f"'{text}'")
        elif '"""' not in text:
            s.write(f'"""{text}"""')
        elif "'''" not in text:
            s.write(f"'''{text}'''")
        else:
            raise ValueError("doc-string contains both types of triple-quoted delimiters")
        pos = offset_span.end
    s.write(source[pos:])
    return s.getvalue()
