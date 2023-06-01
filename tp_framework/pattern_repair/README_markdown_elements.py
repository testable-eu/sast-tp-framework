from tabulate import tabulate


class MarkdownElement:
    """Super class for all MarkdownElements used within generating README files for a testability pattern."""

    def __init__(self, content: str):
        self.content = content.strip()

    def linkable(self) -> str:
        """Makes it possible for a markdown Element to be used within a link.

        Returns:
            str: a string representation, that can be used in a markdown link.
        """
        raise NotImplementedError

    def to_markdown(self):
        raise NotImplementedError

    def strip(self):
        return self.to_markdown().strip()

    def __bool__(self):
        return bool(self.content)


class MarkdownCode(MarkdownElement):
    """A markdown code block.
    Syntax:

    ```<self.code_type>
    self.content
    ```

    """

    def __init__(self, content, code_type):
        super().__init__(content)
        self.code_type = code_type

    def to_markdown(self) -> str:
        return f"\n```{self.code_type}\n{self.content}\n```\n"


class MarkdownComment(MarkdownElement):
    """A markdown comment
    Syntax:

    [//]: # (<self.content>)

    """

    def to_markdown(self):
        self.content = self.content.replace("\\r\\n", " ")
        return f"\n[//]: # ({self.content})\n"


class MarkdownHeading(MarkdownElement):
    """A markdown heading, `self.level` indicates the number of '#'
    Syntax example:

    # <self.content>

    """

    def __init__(self, content, level: int):
        super().__init__(content)
        self.level = int(level)
        assert self.level >= 1

    def to_markdown(self) -> str:
        return f'\n{"#" * self.level} {self.content}\n'

    def linkable(self) -> str:
        return f'#{self.content.replace(" " , "-").lower()}'


class MarkdownCollapsible(MarkdownElement):
    """A markdown collapsible element.
    Syntax example:

    <details markdown="1">
    <summary>
    <self.heading><summary>

    <self.content>

    </details>
    """

    def __init__(self, content: list, heading: MarkdownElement, is_open: bool = False):
        self.content = content
        self.is_open = is_open
        self.heading = heading

    def to_markdown(self) -> str:
        final = f'\n<details markdown="1"{"open" if self.is_open else ""}>'
        heading = (
            self.heading.to_markdown().strip()
            if not isinstance(self.heading, MarkdownHeading)
            else self.heading.to_markdown()
        )
        final += f"\n<summary>\n{heading}</summary>\n\n"
        for element in self.content:
            final += element.to_markdown()
        final += f"\n</details>\n"
        return final


class MarkdownString(MarkdownElement):
    """Representation of a String, it is surrounded by newlines."""

    def to_markdown(self) -> str:
        return f"\n{self.content}\n"


class MarkdownLink(MarkdownElement):
    """A markdown link.
    Syntax:

    [self.content](self.link)

    """

    def __init__(self, content: str | MarkdownElement, link: MarkdownElement):
        super().__init__(content)
        assert isinstance(
            link, MarkdownElement
        ), "The link of a MarkdownLink must be a MarkdownElement."
        self.link = link.linkable()

    def to_markdown(self):
        return f"[{self.content.strip()}]({self.link.strip()})"


class MarkdownTable(MarkdownElement):
    """A markdown table
    Syntax:

    |   |   |
    |---|---|
    |   |   |

    The content must be provided as a dict, where the value for each key is a list.
    The key will be the header and the list contains values for that column.
    Columns will be sorted alphabetically, if you wish to sort columns yourself you can prefix them using <number>::.
    """

    def __init__(self, content: dict, style: str = ""):
        assert isinstance(
            content, dict
        ), "content for Markdown table must be provided as dict"
        assert all(
            [isinstance(v, list) for v in content.values()]
        ), "content for Markdowntable must have lists as values"
        self.headings = sorted(content.keys(), key=lambda x: x.lower())
        self.style = style
        num_rows = max([len(v) for v in content.values()])
        self.lines = [
            [None for _ in range(len(self.headings))] for _ in range(num_rows)
        ]
        for column_idx, key in enumerate(self.headings):
            for row_index, v in enumerate(content[key]):
                self.lines[row_index][column_idx] = v.strip() if v else ""

    def to_markdown(self):
        return f'\n{tabulate(self.lines, [h.split("::")[-1] if "::" in h else h for h in  self.headings], "github")}\n'


class MarkdownDocument(MarkdownElement):
    """A central point, where all markdown elements are collected into one single markdown document."""

    def __init__(self, content: list) -> None:
        self.content = content

    def to_markdown(self) -> str:
        final = ""
        for element in self.content:
            assert isinstance(element, MarkdownElement)
            final += element.to_markdown()
        import re

        final = re.sub("\n\n\n*", "\n\n", final)
        return (
            f"{final.strip()}\n"  # GitHub markdown likes a newline at the end of files
        )
