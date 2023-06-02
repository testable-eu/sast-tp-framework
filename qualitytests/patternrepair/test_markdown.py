import pytest

from qualitytests.qualitytests_utils import join_resources_path

from pattern_repair.README_markdown_elements import *
from pattern_repair.README_generator import READMEGenerator


class TestMarkdownPatternRepair:

    def test_markdown_code(self):
        code = MarkdownCode('<?php\necho "Hello World";\n', "PHP")
        assert f'\n```php\n<?php\necho "Hello World";\n```\n' == code.to_markdown()
    
    def test_markdown_comment(self):
        comment = MarkdownComment("This is a comment")
        assert "\n[//]: # (This is a comment)\n" == comment.to_markdown()
    
    def test_markdown_heading(self):
        heading = MarkdownHeading("Heading", 2)
        assert "\n## Heading\n" == heading.to_markdown()
    
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

    def test_README_generation_one_instance(self):
        path_to_test_pattern = join_resources_path("sample_patlib/PHP/2_global_variables")
        path_to_tplib = join_resources_path("sample_patlib")
        instance_jsons = [path_to_test_pattern / "1_instance_2_global_variables" / "1_instance_2_global_variables.json"]
        md_doc = READMEGenerator(path_to_test_pattern, 'php', path_to_tplib, instance_jsons)._generate_README_elements()
        
        assert 14 == len(md_doc.content)
        assert isinstance(md_doc.content[0], MarkdownComment)
        assert isinstance(md_doc.content[1], MarkdownHeading)       # Global Variables
        assert isinstance(md_doc.content[2], MarkdownString)        # Tags: ...
        assert isinstance(md_doc.content[3], MarkdownString)        # Version: ...
        assert isinstance(md_doc.content[4], MarkdownHeading)       # Description
        assert isinstance(md_doc.content[5], MarkdownString)        # <pattern_description>
        assert isinstance(md_doc.content[6], MarkdownHeading)       # Overview
        assert isinstance(md_doc.content[7], MarkdownTable)         # <overview_table>
        assert isinstance(md_doc.content[8], MarkdownHeading)       # Instance 1
        assert isinstance(md_doc.content[9], MarkdownHeading)       # Code
        assert isinstance(md_doc.content[10], MarkdownCode)         # <instance_code>
        assert isinstance(md_doc.content[11], MarkdownHeading)      # Instance Properties
        assert isinstance(md_doc.content[12], MarkdownTable)        # <instance_properties table>
        assert isinstance(md_doc.content[13], MarkdownCollapsible)  # More

        assert 2 == len(md_doc.content[13].content)
        assert isinstance(md_doc.content[13].content[0], MarkdownCollapsible)       # Compile
        assert 1 == len(md_doc.content[13].content[0].content)
        assert isinstance(md_doc.content[13].content[0].content[0], MarkdownCode)   # <bash_code>

        assert isinstance(md_doc.content[13].content[1], MarkdownCollapsible)       # Discovery
        assert 3 == len(md_doc.content[13].content[1].content)
        assert isinstance(md_doc.content[13].content[1].content[0], MarkdownString) # <discovery_string>
        assert isinstance(md_doc.content[13].content[1].content[1], MarkdownCode)   # <discovery_code>
        assert isinstance(md_doc.content[13].content[1].content[2], MarkdownTable)  # <discovery_table>