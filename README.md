# docsource: Parse, check and update doc-string documentation

*docsource* parses Python documentation strings (a.k.a. *doc-string*) for (data) classes and functions.

A doc-string is broken down into the following components:

* A short description, which is the first block of text in the documentation string, and ends with a double newline or a parameter block.
* A long description, which is the optional block of text following the short description, and ends with a parameter block.
* A parameter block of named parameter and description string pairs in ReST-style, each declared with `param`.
* A `returns` declaration, which adds explanation to the return value.
* A `raises` declaration, which adds explanation to the exception type raised by the function on error.

```py
class SampleClass:
    def instance_method(self, a: str, b: int | None) -> str:
        """
        Short description of an instance method.

        :param a: Short description for `a`.
        :param b: Short description for `b`.
        :returns: A return value.
        :raise TypeError: A type exception rarely raised.
        :raise ValueError: A value exception rarely raised.
        :raise CustomException: A custom exception.
        """
        return ""
```

When the doc-string is attached to a data class, it is understood as the documentation string of the class `__init__` method.

## Compliance

*docsource* verifies if

* parameters listed in the function doc-string have corresponding parameters in the function signature,
* parameters declared in a function signature have corresponding doc-string entries (strict mode only),
* data-class members listed in the function doc-string have corresponding member variables in the data-class definition,
* members declared in a data-class have corresponding doc-string entries (strict mode only).

## Enumerations

Python's own doc-string mechanism doesn't allow attaching a description to enumeration members. However, documentation toolchains such as Sphinx's `autodoc` support this with a string literal immediately following the enumeration member value assignment:

```py
@enum.unique
class EnumType(enum.Enum):
    ENABLED = "enabled"
    "Documents the enumeration member `ENABLED`."

    DISABLED = "disabled"
    "Documents the enumeration member `DISABLED`."
```

*docsource* can parse source code with Python's `ast` module to extract these description text strings.

## Documentation style

*docsource* can normalize code documentation by reading source code (with Python's `ast`), identifying doc-string literals, parsing doc-string text, and producing a standardized doc-string with short description, and ReST-style parameter, return value and exception declarations.

## Refer to the source

* The function `parse_type` parses a ReST-style doc-string attached to a class or function into doc-string components, encapsulated in the class `Docstring`.
* The function `parse_text` parses raw doc-string text into its components.
* `check_docstring` verifies data-class and function doc-string text.
* `enum_labels` extracts textual description for enumeration members.
* `update_docstring` standardizes doc-string literals in Python source code.
