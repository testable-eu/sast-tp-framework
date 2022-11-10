import csv
import json
import os
import subprocess
import sys
import uuid
from pathlib import Path
from typing import Dict, Tuple

import config
from core import utils, measurement
from core.exceptions import DiscoveryMethodNotSupported, MeasurementNotFound, CPGGenerationError, \
    CPGLanguageNotSupported, JoernQueryError
from core.measurement import Measurement


def generate_cpg(rel_src_dir_path: Path, language: str, build_name: str, timeout_sec: int = 0) -> Path:
    try:
        language_cpg_conf: Dict = config.CPG_GEN_CONFIG["cpg_gen"][language.lower()]
    except KeyError as e:
        raise CPGLanguageNotSupported(e)
    gen_cpg_with_params_cmd: str = language_cpg_conf['command']
    cpg_tmp_dir: Path = config.RESULT_DIR / "cpg_tmp"
    cpg_tmp_dir.mkdir(parents=True, exist_ok=True)
    binary_out: Path = cpg_tmp_dir / f"cpg_{build_name}.bin"

    # TODO: this may not this safe
    src_dir: Path = config.ROOT_DIR / rel_src_dir_path
    gen_cpg_with_params_cmd = gen_cpg_with_params_cmd.replace("$SRC_DIR", str(src_dir.resolve()))
    gen_cpg_with_params_cmd = gen_cpg_with_params_cmd.replace("$BINARY_OUT", str(binary_out))

    if timeout_sec > 0:
        gen_cpg_with_params_cmd = f"timeout {timeout_sec} {gen_cpg_with_params_cmd}"

    os.chdir(config.ROOT_DIR / language_cpg_conf['installation_dir'])
    try:
        os.system(gen_cpg_with_params_cmd)
    except:
        raise CPGGenerationError()

    try:
        run_joern_scala_query_for_test = f"joern --script {Path(__file__).parent.resolve()}/cpgTest.sc --params name={binary_out}"
        cpg_gen_test_result: str = subprocess.check_output(run_joern_scala_query_for_test, shell=True).decode(
            'utf-8-sig')
        if "Error in CPG generation" in cpg_gen_test_result:
            raise CPGGenerationError()
    except:
        raise CPGGenerationError()
    os.chdir(config.ROOT_DIR)
    return binary_out


def run_discovery_rule(cpg: Path, discovery_rule: Path, discovery_method: str) -> Tuple[str, str, list[Dict]]:
    if discovery_method == "joern":
        run_joern_scala_query = f"joern --script {discovery_rule} --params name={cpg}"
        try:
            findings_str: str = subprocess.check_output(run_joern_scala_query, shell=True).decode('utf-8-sig')
        except subprocess.CalledProcessError as e:
            raise JoernQueryError(e)

        parsed_findings: list[str] = findings_str[1:-1].split(",")[2:]
        findings_dec: list[str] = list(map(lambda s: f"{s},", parsed_findings[:-1]))

        cpg_file_name: str = findings_str[1:-1].split(",")[:2][0]
        query_name: str = findings_str[1:-1].split(",")[:2][1]

        if findings_dec:
            findings_dec.append(parsed_findings[-1][:-1])
            findings: list[Dict] = json.loads(''.join(findings_dec))

            return cpg_file_name, query_name, findings
        else:
            return cpg_file_name, query_name, []
    else:
        raise DiscoveryMethodNotSupported(discovery_method=discovery_method)


def discovery_for_tool(cpg: Path, pattern_instances: list[Measurement], tool: Dict, language: str,
                       tp_lib_dir: Path):
    if tool is {}:
        pattern_not_supported_by_tool: list[Measurement] = pattern_instances
    else:
        pattern_not_supported_by_tool: list[Measurement] = list(
            filter(lambda meas: not meas.result and meas.tool == tool["name"], pattern_instances)
        )

    collected_discovery_rules: list[Tuple[Path, Measurement]] = []
    discovery_rules_to_run: Dict = {}
    findings: list[Dict] = []
    for pattern_meas in pattern_not_supported_by_tool:
        instance_dir: str = utils.get_instance_dir_name_from_pattern(
            pattern_meas.instance.name,
            pattern_meas.instance.pattern_id,
            pattern_meas.instance.instance_id)
        pattern_dir: str = utils.get_pattern_dir_name_from_name(
            pattern_meas.instance.name,
            pattern_meas.instance.pattern_id)
        discovery_rule: Path = (
                tp_lib_dir / language / pattern_dir / instance_dir / pattern_meas.instance.discovery_rule).resolve()

        collected_discovery_rules.append((discovery_rule, pattern_meas))

    for d in collected_discovery_rules:
        discovery_rules_to_run[d[0]] = []

    for d in collected_discovery_rules:
        discovery_rules_to_run[d[0]] = discovery_rules_to_run[d[0]] + [d[1]]

    for discovery_rule in discovery_rules_to_run.keys():
        pattern_meas = discovery_rules_to_run[discovery_rule][0]
        try:
            cpg_file_name, query_name, findings_for_pattern = run_discovery_rule(
                cpg, discovery_rule,
                pattern_meas.instance.discovery_method
            )

            findings_for_pattern_refined: list[Dict] = []
            for f in findings_for_pattern:
                f_ref = {
                    "filename": f["filename"],
                    "methodFullName": f["methodFullName"],
                    "lineNumber": f["lineNumber"],
                    "patternId": pattern_meas.instance.pattern_id,
                    "instanceId": [d.instance.instance_id for d in discovery_rules_to_run[discovery_rule]],
                    "patternName": pattern_meas.instance.name,
                    "queryFile": str(discovery_rule)

                }

                findings_for_pattern_refined.append(f_ref)

            findings = findings + findings_for_pattern_refined

        except DiscoveryMethodNotSupported as e:
            print(
                f"{pattern_meas.instance.instance_id}_instance_{pattern_meas.instance.pattern_id}_{pattern_meas.instance.name}: {e}",
                file=sys.stderr)

    return findings


def discovery(src_dir: Path, list_patterns_id_to_disc: list[int], tp_lib_dir: Path, tools: list[Dict],
              language: str):
    build_name: str = f"{language}_{src_dir.name}_{uuid.uuid4()}"
    cpg: Path = generate_cpg(src_dir, language, build_name)

    meas_lang_dir: Path = tp_lib_dir / "measurements" / language
    meas_p_id_path_list: Dict = dict(zip(
        map(lambda d: int(d.name.split("_")[0]), list(meas_lang_dir.iterdir())),
        list(meas_lang_dir.iterdir())
    ))

    # Get input patterns' paths and then use utils to read from pattern the instances
    # p_lang_dir: Path = tp_lib_dir / language
    # p_id_path_list: Dict = dict(zip(
    #     map(lambda d: int(d.name.split("_")[0]), list(p_lang_dir.iterdir())),
    #     list(p_lang_dir.iterdir())
    # ))

    last_meas: list[Measurement] = []

    for p_id in list_patterns_id_to_disc:
        try:
            p_path: Path = Path(meas_p_id_path_list[p_id])
        except KeyError:
            # TODO: print rather than raise, p_id needs to be removed
            raise MeasurementNotFound(p_id)

        meas_inst_path_list = list(p_path.iterdir())
        for inst_path in meas_inst_path_list:
            last_meas = last_meas + measurement.load_from_metadata(
                utils.get_last_measurement_for_pattern_instance(inst_path), language)

    findings_for_tools: list[Dict] = []
    if tools is []:
        discovery_for_tool(cpg, last_meas, {}, language, tp_lib_dir)
    else:
        for tool in tools:
            findings_for_tools = findings_for_tools + discovery_for_tool(cpg, last_meas, tool, language, tp_lib_dir)

    for f in findings_for_tools:
        f["instanceId"] = (''.join(f'{iid}, ' for iid in f["instanceId"]))[:-2]

    findings: list[Dict] = [dict(t) for t in {tuple(d.items()) for d in findings_for_tools}]

    with open(config.RESULT_DIR / f"discovery_{build_name}.csv", "w") as report:
        fields = ["filename", "lineNumber", "methodFullName", "patternId", "instanceId", "patternName", "queryFile"]
        writer = csv.DictWriter(report, fieldnames=fields)
        writer.writeheader()
        for f in findings:
            writer.writerow(f)


def manual_discovery(src_dir: Path, discovery_method: str, discovery_rules: list[Path], language: str, timeout_sec: int = 0):
    build_name: str = f"{language}_{src_dir.name}_{uuid.uuid4()}"
    try:
        cpg: Path = generate_cpg(src_dir, language, build_name, timeout_sec)
    except CPGGenerationError:
        raise
    findings: list[dict] = []
    for discovery_rule in discovery_rules:
        try:
            cpg_file_name, query_name, findings_for_rule = run_discovery_rule(cpg, discovery_rule, discovery_method)
            if len(findings_for_rule) == 0:
                findings.append({
                    "filename": None,
                    "methodFullName": None,
                    "lineNumber": None,
                    "queryName": query_name,
                    "queryFile": str(discovery_rule),
                    "result": "NO_RESULT"
                })

            for f in findings_for_rule:
                findings.append({
                    "filename": f["filename"],
                    "methodFullName": f["methodFullName"],
                    "lineNumber": f["lineNumber"],
                    "queryName": query_name,
                    "queryFile": str(discovery_rule),
                    "result": None
                })
        except JoernQueryError as e:
            findings.append({
                "filename": None,
                "methodFullName": None,
                "lineNumber": None,
                "queryName": None,
                "queryFile": str(discovery_rule),
                "result": e.message
            })
            continue

    with open(config.RESULT_DIR / f"manual_discovery_{build_name}.csv", "w") as report:
        fields = ["filename", "lineNumber", "methodFullName", "queryName", "queryFile", "result"]
        writer = csv.DictWriter(report, fieldnames=fields)
        writer.writeheader()
        for f in findings:
            writer.writerow(f)
