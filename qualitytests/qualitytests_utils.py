import sys
import subprocess
from pathlib import Path
from typing import Dict
import shutil

pyexe = sys.executable
print("-- Python executable: {}".format(pyexe))
pr = subprocess.Popen([pyexe, "--version"], shell=False, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
(output, errdata) = pr.communicate()
print("-- Python version: {}".format(output.decode("utf-8").strip()))

resource_path = "resources"
cpg_binary_rel_path = "sample_joern/cpg_binary.bin"


def join_resources_path(relativepath):
    dirname = Path(__file__).parent.resolve()
    return dirname / resource_path / relativepath


def create_mock_cpg(dst_file: Path):
    sample_cpg_binary: Path = join_resources_path(cpg_binary_rel_path)
    shutil.copy(sample_cpg_binary, dst_file)


def in_logfile(logfile: Path, target: str, lastNlines: int = None):
    if not lastNlines:
        lastNlines = 0
    with open(logfile, 'r') as lfile:
        for l in (lfile.readlines() [-lastNlines:]):
            if target in l:
                return True
    return False


def get_path_after_string_from_output(target: str, captured_out_lines: list[str]):
    path = None
    for l in captured_out_lines:
        if target in l:
            path = Path(l.split(target)[1])
    return path


def  get_result_output_dir(captured_out_lines):
    ## assume stdout comprises "results available here: DISCOVERY_OUTPUT_DIR"
    targ1 = "results available here: "
    return get_path_after_string_from_output(targ1, captured_out_lines)


def get_logfile_path(captured_out_lines):
    ## assume stdout comprises "log file available here: LOG_PATH"
    targ2 = "log file available here: "
    return get_path_after_string_from_output(targ2, captured_out_lines)


def init_measure_test(init, mocker):
    init["language"] = "PHP"
    init["tools"] = [
        {"name": "dummyTool", "version": "1"},
        {"name": "dummyTool", "version": "2"},
        {"name": "anotherDummyTool", "version": "1.2"}
    ]
    temp_meas = "../temp/measure/sample_patlib"
    init["tp_lib_path"] = join_resources_path(temp_meas).resolve()
    try:
        shutil.copytree(join_resources_path("sample_patlib"), init["tp_lib_path"])
    except:
        pass
    mocked_tool_interface: Dict = {
        "supported_languages": ["PHP"],
        "tool_interface": "qualitytests.core.sast_test.SastTest"
    }
    init["patterns"] = [1,2,3]
    mocker.patch("core.utils.load_sast_specific_config", return_value=mocked_tool_interface)