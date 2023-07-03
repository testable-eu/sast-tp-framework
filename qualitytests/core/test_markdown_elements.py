from core.readme_markdown_elements import *


class TestMarkdownElements:

    def test_markdown_code(self):
        code = MarkdownCode('<?php\necho "Hello World";\n', "PHP")
        assert '\n```php\n<?php\necho "Hello World";\n```\n' == code.to_markdown()

    def test_markdown_comment(self):
        comment = MarkdownComment("This is a\ncomment")
        assert "\n[//]: # (This is a comment)\n" == comment.to_markdown()

    def test_markdown_heading(self):
        heading = MarkdownHeading("Heading", 2)
        assert "\n## Heading\n\n" == heading.to_markdown()

    def test_markdown_collapsible(self):
        coll = MarkdownCollapsible([MarkdownString("Hello")], MarkdownString("More"))
        assert '\n<details markdown="1">\n<summary>\nMore</summary>\n\n\nHello\n\n</details>\n' == coll.to_markdown()

    def test_markdown_string(self):
        s = MarkdownString("Test")
        assert "\nTest\n" == s.to_markdown()

    def test_markdown_link(self):
        link = MarkdownLink("Test", MarkdownHeading("Heading 1", 3))
        assert "[Test](#heading-1)" == link.to_markdown()

    def test_markdown_table(self):
        test_content = {"0::column1": ["value1", "value1.1"], "column2": ["value2"]}
        tab = MarkdownTable(test_content)
        expected_tab = "\n| column1   | column2   |\n"
        expected_tab += "|-----------|-----------|\n"
        expected_tab += "| value1    | value2    |\n"
        expected_tab += "| value1.1  |           |\n"
        assert expected_tab == tab.to_markdown()

    def test_markdown_document(self):
        coll = MarkdownCollapsible([MarkdownString("Hello")], MarkdownString("More"))
        doc = MarkdownDocument([coll])
        assert '<details markdown="1">\n<summary>\nMore</summary>\n\nHello\n\n</details>\n' == doc.to_markdown()

