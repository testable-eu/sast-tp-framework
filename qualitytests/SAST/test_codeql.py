import pytest
import asyncio
pytest_plugins = ('pytest_asyncio',)

import qualitytests_utils

from SAST.codeql.codeql_v2_9_2.codeql import CodeQL_v_2_9_2


@pytest.mark.asyncio
class TestCodeQL:


    def test_inspector(self, tmp_path):
        sarif_file = qualitytests_utils.join_resources_path("sample_codeql/TPF_JS_codeql_2_9_2_1_instance_1_unset_element_array.sarif")
        language: str = "JS"
        inspection = CodeQL_v_2_9_2().inspector(sarif_file, language)
        assert inspection[0]["type"] == "xss"
        assert inspection[0]["line"] == 33


    async def test_launcher(self, tmp_path):
        # TODO
        pass
