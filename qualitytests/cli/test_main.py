from pathlib import Path
import sys
import subprocess

import pytest

from qualitytests_utils import pyexe, join_resources_path
from cli import main


class TestMain:
    testdir = Path(__file__).parent.parent.resolve()
    tpf = testdir.parent / "tp_framework/cli/main.py"


    def test_cli_help_1(self):
        # process call
        cmd = pyexe + " {0} -h".format(self.tpf)
        pr = subprocess.Popen(cmd, shell=False, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        (output, errdata) = pr.communicate()
        output = output.decode("utf-8")
        print(output)
        assert "[OPTIONS] COMMAND" in output


    def test_cli_help_2(self, tmp_path):
        sys.stdout = open(tmp_path / 'output.txt', 'w')
        with pytest.raises(SystemExit):
            main.main(['-h'])
            sys.stdout.flush()
            with open(tmp_path / 'output.txt', 'r') as ofile:
                output = ofile.readlines()
            assert any("[OPTIONS] COMMAND" in oline for oline in output)


    def test_cli_discovery_1(self, tmp_path, mocker):
        test_tp_lib_path = join_resources_path("sample_patlib")
        test_lang = "PHP"
        tool1 = "sastA:saas"
        tool2 = "sastB:2.1.1"
        tp_range = "2-3"
        # Mock discovery.discovery
        mocker.patch("cli.interface.run_discovery_for_pattern_list", return_value=None)
        # Test1: input parameter --target is required
        print("Test1: input parameter `--target` is required")
        with pytest.raises(SystemExit):
            main.main(['discovery', '--pattern-range', tp_range, '--tools', tool1, tool2, '-l', test_lang, '--tp-lib', str(test_tp_lib_path)])
        # Test2: valid parameters
        print("Test2: valid parameters")
        main.main(['discovery', '--target', str(tmp_path), '--pattern-range', tp_range, '--tools', tool1, tool2, '-l', test_lang, '--tp-lib', str(test_tp_lib_path)])
        assert(True)


    def test_cli_manual_discovery_1(self, tmp_path, mocker):
        test_lang = "PHP"
        r1 = str(tmp_path / "rule_1.sc")
        r2 = str(tmp_path / "rule_2.sc")
        r3 = str(tmp_path / "whatever/rule_3.sc")
        # Mock manual discovery
        mocker.patch("cli.interface.manual_discovery", return_value=None)
        # Test1: input parameter --target is required
        print("Test1: input parameter `--target` is required")
        with pytest.raises(SystemExit):
            main.main(['manual-discovery',
                       '--rules', r1, r2, r3,
                       '--method', 'joern', '-l', test_lang, '--output-dir', str(tmp_path)])
        # Test2: valid parameters
        main.main(['manual-discovery', '--target', str(tmp_path),
                   '--rules', r1, r2, r3,
                   '--method', 'joern', '-l', test_lang, '--output-dir', str(tmp_path)])
        assert(True)


    def _init_cli_various(self):
        self.test_lang = "PHP"
        self.tool1 = "sastA:saas"
        self.tool2 = "sastB:2.1.1"
        self.tp_range = "2-3"
        self.tp1 = "1"
        self.tp2 = "4"


    def _init_cli_measure(self, mocker):
        self._init_cli_various()
        mocker.patch("cli.interface.measure_list_patterns", return_value=None)


    def test_cli_measure_1(self, tmp_path, mocker):
        self._init_cli_measure(mocker)
        # Tests: input patterns' parameters in mutual exclusion
        with pytest.raises(SystemExit):
            main.main(['measure',
                       '--pattern-range', self.tp_range, '-p', self.tp1, self.tp2,
                       '--tools', self.tool1, self.tool2, '-l', self.test_lang,
                       '--tp-lib', str(tmp_path)])


    def test_cli_measure_2(self, tmp_path, mocker):
        self._init_cli_measure(mocker)
        # Tests: input patterns' parameters in mutual exclusion
        with pytest.raises(SystemExit):
            main.main(['measure',
                       '--pattern-range', self.tp_range, '-a',
                       '--tools', self.tool1, self.tool2, '-l', self.test_lang,
                       '--tp-lib', str(tmp_path)])


    def test_cli_measure_3(self, tmp_path, mocker):
        self._init_cli_measure(mocker)
        # Tests: input patterns' parameters in mutual exclusion
        with pytest.raises(SystemExit):
            main.main(['measure',
                       '-p', self.tp1, self.tp2, '-a',
                       '--tools', self.tool1, self.tool2, '-l', self.test_lang,
                       '--tp-lib', str(tmp_path)])


    def test_cli_measure_4(self, tmp_path, mocker):
        self._init_cli_measure(mocker)
        # Tests: wrong tools input
        with pytest.raises(SystemExit):
            main.main(['measure',
                       '-p', self.tp1, self.tp2,
                       '--tools', self.tool1, 'whatever', '-l', self.test_lang,
                       '--tp-lib', str(tmp_path)])


    def test_cli_measure_5(self, tmp_path, mocker):
        self._init_cli_measure(mocker)
        # Test: valid params
        main.main(['measure',
                   '-p', self.tp1, self.tp2,
                   '--tools', self.tool1, self.tool2, '-l', self.test_lang,
                   '--tp-lib', str(tmp_path)])


    def _init_cli_report(self, mocker):
        self._init_cli_various()
        mocker.patch("cli.interface.report_sast_measurement_for_pattern_list", return_value=None)


    def test_cli_report_1(self, tmp_path, mocker):
        self._init_cli_report(mocker)
        # Test: invalid params, missing (--print | --export EXPORTFILE)
        with pytest.raises(SystemExit):
            main.main(['sastreport',
                       '-p', self.tp1, self.tp2,
                       '--tools', self.tool1, self.tool2, '-l', self.test_lang,
                       '--tp-lib', str(tmp_path)])


    def test_cli_report_2(self, tmp_path, mocker):
        self._init_cli_report(mocker)
        # Test: valid params, --print
        main.main(['sastreport',
                   '--print',
                   '-p', self.tp1, self.tp2,
                   '--tools', self.tool1, self.tool2, '-l', self.test_lang,
                   '--tp-lib', str(tmp_path)])


    def test_cli_report_3(self, tmp_path, mocker):
        self._init_cli_report(mocker)
        # Test: invalid params, --export without filename
        with pytest.raises(SystemExit):
            main.main(['sastreport',
                       '--export',
                       '-p', self.tp1, self.tp2,
                       '--tools', self.tool1, self.tool2, '-l', self.test_lang,
                       '--tp-lib', str(tmp_path)])


    def test_cli_report_4(self, tmp_path, mocker):
        self._init_cli_report(mocker)
        # Test: valid params, --export with filename
        main.main(['sastreport',
                   '--export', 'whatever.csv',
                   '-a',
                   '--tools', self.tool1, self.tool2, '-l', self.test_lang,
                   '--tp-lib', str(tmp_path),
                   '--output-dir', str(tmp_path)
                   # '--output-dir', str(tmp_path),
                   # '--only-last-measurement'
                   ])


    def test_cli_report_5(self, tmp_path, mocker):
        self._init_cli_report(mocker)
        # Test: valid params, no tools i.e., get all measurements
        main.main(['sastreport',
                   '--export', 'whatever.csv',
                   '-a',
                   '-l', self.test_lang,
                   '--tp-lib', str(tmp_path),
                   '--output-dir', str(tmp_path)
                   # '--output-dir', str(tmp_path),
                   # '--only-last-measurement'
                   ])