from pathlib import Path
import sys
import subprocess
from typing import Dict
from unittest.mock import Mock

import pytest
from pytest_mock import MockerFixture

from qualitytests_utils import pyexe, join_resources_path
from cli import main
import config


class TestMain:
    testdir = Path(__file__).parent.parent.resolve()
    tpf = testdir.parent / "tp_framework/cli/main.py"

    def test_cli_help_1(self):
        # process call
        cmd = pyexe + " {0} -h".format(self.tpf)
        # DEBUG: useful in debugging mode to understand the discovery params
        test_tp_lib_path = join_resources_path("sample_patlib")
        test_lang = "PHP"
        tools = "sastA:saas sastB:2.1.1"
        cmd = pyexe + " {0} {1}".format(self.tpf, " ".join(['discovery', '--patterns', '1', '2', '3', '--tools', tools, '-l', test_lang, '--tp-lib', test_tp_lib_path]))
        #
        pr = subprocess.Popen(cmd, shell=False, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        (output, errdata) = pr.communicate()
        output = output.decode("utf-8")
        print(output)
        assert "[OPTIONS] COMMAND" in output


    def test_cli_help_2(self, tmp_path):
        sys.stdout = open(tmp_path / 'output.txt', 'w')
        try:
            main.main(['-h'])
        except SystemExit:
            sys.stdout.flush()
            with open(tmp_path / 'output.txt', 'r') as ofile:
                output = ofile.readlines()
            assert any("[OPTIONS] COMMAND" in oline for oline in output)


    def test_cli_discovery(self, tmp_path):
        test_tp_lib_path = join_resources_path("sample_patlib")
        test_lang = "PHP"
        tool1 = "sastA:saas"
        tool2 = "sastB:2.1.1"
        tp_range = "2-3"
        sys.stdout = open(tmp_path / 'output.txt', 'w')
        try:
            main.main(['discovery', '--pattern-range', tp_range, '--tools', tool1, tool2, '-l', test_lang, '--tp-lib', test_tp_lib_path])
            # TODO: to be continued with mocking the discovery functions + assert
        except SystemExit:
            sys.stdout.flush()
            with open(tmp_path / 'output.txt', 'r') as ofile:
                output = ofile.readlines()
            assert any("[OPTIONS] COMMAND" in oline for oline in output)


    def test_parse_tp_lib(self, tmp_path, capsys):
        # not specified tp_lib
        tp_lib_path = main.parse_tp_lib(None)
        assert tp_lib_path == Path(str(config.DEFAULT_TP_LIBRARY_ROOT_DIR)).resolve()
        # not existing tp_lib
        try:
            main.parse_tp_lib("/Wh4tEver/Y0uWaNt/ThatDoesNotExist/In/YourDisk")
            assert False
        except FileNotFoundError:
            pass
        # existing temp tp_lib
        tp_lib_path = main.parse_tp_lib(tmp_path)
        assert tp_lib_path == Path(str(tmp_path)).resolve()


    def test_parse_tool_list(self):
        # empty list
        assert [] == main.parse_tool_list([])
        # two tools
        tool1 = {"name": "sastA", "version" : "saas"}
        tool2 = {"name": "sastB", "version" : "2.1.1"}
        tools = [tool1["name"]+":"+tool1["version"],
                 tool2["name"]+":"+tool2["version"]]
        ptools = main.parse_tool_list(tools)
        assert tool1 in ptools
        assert tool2 in ptools
        # one tool
        ptools = main.parse_tool_list([tool1["name"]+":"+tool1["version"]])
        assert tool1 in ptools

    def test_parse_patterns(self):
        test_tp_lib_path = Path(join_resources_path("sample_patlib"))
        test_lang = "PHP"
        # one and only one mutual exclusion params: zero provided
        try:
            main.parse_patterns(False, "", [], test_tp_lib_path, test_lang)
        except AssertionError:
            pass
        # one and only one mutual exclusion params: pattern range
        tp_range = "2-3"
        tp_ids = main.parse_patterns(False, tp_range, [], test_tp_lib_path, test_lang)
        assert tp_ids == [2, 3]
        # one and only one mutual exclusion params: pattern ids
        itp_ids = [1,2,5,10]
        tp_ids = main.parse_patterns(False, "", itp_ids, test_tp_lib_path, test_lang)
        assert tp_ids == itp_ids
        # one and only one mutual exclusion params: all
        tp_ids = main.parse_patterns(True, "", [], test_tp_lib_path, test_lang)
        assert tp_ids == [1,2,3]
