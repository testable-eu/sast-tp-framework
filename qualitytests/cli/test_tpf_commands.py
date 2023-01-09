from pathlib import Path

import pytest

from qualitytests_utils import join_resources_path
from cli import tpf_commands
import config


class TestTPFCommands:
    testdir = Path(__file__).parent.parent.resolve()
    tpf = testdir.parent / "tp_framework/cli/tpf_commands.py"


    def test_parse_tp_lib(self, tmp_path, capsys):
        # not specified tp_lib
        tp_lib_path = tpf_commands.parse_tp_lib(None)
        assert tp_lib_path == Path(str(config.DEFAULT_TP_LIBRARY_ROOT_DIR)).resolve()
        # not existing tp_lib
        with pytest.raises(SystemExit):
            tpf_commands.parse_tp_lib("/Wh4tEver/Y0uWaNt/ThatDoesNotExist/In/YourDisk")
        # existing temp tp_lib
        tp_lib_path = tpf_commands.parse_tp_lib(tmp_path)
        assert tp_lib_path == Path(str(tmp_path)).resolve()


    def test_parse_tool_list(self):
        # empty list
        assert config.SAST_TOOLS_ENABLED == tpf_commands.parse_tool_list([])
        # two tools
        tool1 = {"name": "sastA", "version" : "saas"}
        tool2 = {"name": "sastB", "version" : "2.1.1"}
        tools = [tool1["name"]+":"+tool1["version"],
                 tool2["name"]+":"+tool2["version"]]
        ptools = tpf_commands.parse_tool_list(tools)
        assert tool1 in ptools
        assert tool2 in ptools
        # one tool
        ptools = tpf_commands.parse_tool_list([tool1["name"]+":"+tool1["version"]])
        assert tool1 in ptools


    def test_parse_patterns(self):
        test_tp_lib_path = Path(join_resources_path("sample_patlib"))
        test_lang = "PHP"
        # one and only one mutual exclusion params: zero provided
        with pytest.raises(SystemExit):
            tpf_commands.parse_patterns(False, "", [], test_tp_lib_path, test_lang)
        # one and only one mutual exclusion params: pattern range
        tp_range = "2-3"
        tp_ids = tpf_commands.parse_patterns(False, tp_range, [], test_tp_lib_path, test_lang)
        assert tp_ids == [2, 3]
        # one and only one mutual exclusion params: pattern ids
        itp_ids = [1,2,5,10]
        tp_ids = tpf_commands.parse_patterns(False, "", itp_ids, test_tp_lib_path, test_lang)
        assert tp_ids == itp_ids
        # one and only one mutual exclusion params: all
        tp_ids = tpf_commands.parse_patterns(True, "", [], test_tp_lib_path, test_lang)
        assert tp_ids == [1,2,3]
