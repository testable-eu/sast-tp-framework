import json
import re
from typing import Dict
from pathlib import Path

from core import utils
import logging
from core import loggermgr

logger = logging.getLogger(loggermgr.logger_name(__name__))

mand_finding_joern_keys = ["filename", "lineNumber"]

discovery_result_strings = {
    "no_discovery": "NO_DISCOVERY",
    "discovery": "DISCOVERY",
    "error": "ERROR_DISCOVERY",
    "supported": "SUPPORTED_BY_SAST"
}

# Could be outsourced into its own file
# Container for a Discovery result, that can be converted to CSV or to JSON
# Equality comparison is implemented so that the set operation can be performed on a list of DiscoveryResults
class DiscoveryResult:
    def __init__(self, rule_name: str, 
                 instances: list, 
                 cpg_path: str, 
                 result: list[Dict],
                 rule_id: str, 
                 query_file: str = None,
                 error: str = None) -> None:
        self.cpg_path = cpg_path.strip()
        self.instances = instances
        # raw result dict
        self.result = result
        self.rule_name = rule_name.strip()
        self.rule_id = rule_id.strip()
        self.queryFile = query_file
        self.discovery_method = None

        # stores information about what was wrong with this discovery result
        self.error = error
        # one of the values of `discovery_result_strings`
        self.status = None

    @staticmethod
    def csv_headers():
        return ["patternId","instanceId", "instanceName", "sast_measurement", "method", "queryFile", "queryHash", 
                "queryName", "queryAccuracy", "queryAlreadyExecuted", "discovery", "filename", "lineNumber", "methodFullName"]

    @staticmethod
    def checkdiscoveryrules_headers():
        return ["pattern_id","instance_id", "instance_path", "pattern_name", "language", "discovery_rule", "successful"]

    def to_csv(self) -> list:
        # patternId,instanceId,instanceName,sast_measurement,method,queryFile,queryHash,queryName,queryAccuracy,queryAlreadyExecuted,discovery,filename,lineNumber,methodFullName
        res = []
        assert isinstance(self.result, dict) or self.result is None
        base_dict = {
            "method": self.discovery_method,
            "queryFile": str(self.queryFile), 
            "queryHash": utils.get_file_hash(self.queryFile) if self.queryFile else "",
            "queryName": self.rule_name,
            "queryAlreadyExecuted": not bool(self.error), 
            "discovery": bool(self.result) if not self.error else "failure", 
            "filename": self.result["filename"] if self.result else None, 
            "lineNumber": self.result["lineNumber"] if self.result else None,
            "methodFullName": self.result["methodFullName"] if self.result and "methodFullName" in self.result else None
        }

        # special case, as manual discovery does not have instances
        if not self.instances:
            return [base_dict]
        
        for idx, instance in enumerate(self.instances):
            res += [{
                "patternId": instance.pattern_id,
                "instanceId": instance.instance_id, 
                "instanceName": instance.name, 
                "sast_measurement": self.sast_measurement[idx], 
                **base_dict,
                "queryAccuracy": instance.discovery_rule_accuracy,
                "method": instance.discovery_method,
                "queryAlreadyExecuted": not bool(self.error) and idx != 0,
            }]
        return res

    def to_checkdiscoveryresults_csv(self) -> list:
        return [{
            "pattern_id": instance.pattern_id, 
            "instance_id": instance.instance_id,
            "instance_path": instance.path,
            "pattern_name": "",
            "language": instance.language,
            "discovery_rule": instance.discovery_rule,
            "successful": utils.translate_bool(bool(self.result)) if not self.error else "failure"
            } for instance in self.instances]

    def to_json(self) -> dict:
        # discovery, filename, lineNumber, methodFullName, queryFile, queryName
        return {
            "discovery": bool(self.result),
            "filename": self.result["filename"] if self.result else None,
            "lineNumber": self.result["lineNumber"] if self.result else None,
            "methodFullName": self.result["methodFullName"] if "methodFullName" in self.result else None,
            "queryFile": str(self.queryFile),
            "queryName": self.rule_name
        }

    def __str__(self) -> str:
        return f"{self.instances}_{len(self.result)}"
    
    def _hashable(self, unhashable_list: list[Dict]):
        return tuple(t for d in unhashable_list for t in d.items())

    def __hash__(self) -> int:
        # if we want to remove duplicates in a list of DiscoveryResults, we need to implement some comparison
        # nevertheless, this code smells, is there a better solution?
        return hash((self._hashable(self.to_csv()), 
                     tuple(self.to_json().items()), 
                     self._hashable(self.to_checkdiscoveryresults_csv())))
    
    def __eq__(self, __value: object) -> bool:
        if not isinstance(__value, DiscoveryResult):
            return False
        return self.to_csv() == __value.to_csv() and \
                self.to_json() == __value.to_json() and \
                self.to_checkdiscoveryresults_csv() == __value.to_checkdiscoveryresults_csv()


def evaluate_discovery_rule_results(raw_findings: str, 
                                    rule_id_instance_mapping: dict, 
                                    invalid_instances: dict,
                                    discovery_method: str,
                                    output_dir: Path,
                                    build_name: str,
                                    query_file: Path,
                                    sast_measurement: dict = None,
                                    export_results: bool = True) -> list[DiscoveryResult]:
    logger.info(f"\033[92m{rule_id_instance_mapping}\033[0m")
    # parse raw findings into DiscoveryResults
    findings = _process_raw_findings(raw_findings, rule_id_instance_mapping, query_file)

    # process raw results according to discovery method
    positive_res = []
    if discovery_method == "joern":
        positive_res, error_instances = _process_joern_results(findings)
        invalid_instances["joern output error"] = error_instances
    else:
        logger.error("Discovery method not yet supported")

    # figure out, which results are missing 
    misssing_instances = _process_missing_instances(positive_res, rule_id_instance_mapping)
    invalid_instances["parsing error"] = misssing_instances

    # process error results
    negative_res = _process_negative_instances(invalid_instances)

    # add measurement
    l_d_res = positive_res + negative_res
    l_d_res = _add_measurement(l_d_res, sast_measurement)

    # remove duplicates
    l_d_res = list(set(l_d_res))

    if export_results:
        # export results
        logger.info("Discovery - Exporting results")
        _export_findings_file(positive_res, output_dir, build_name)
        csv_file = _export_csv_file(sorted(l_d_res, key=lambda x: x.rule_name), output_dir, build_name)
    return l_d_res


def _parse_finding_line(raw_finding_line: str, rule_id_instance_mapping: dict, query_file: Path):
    # <rule_id>: (<path_to_cpg_used>, <rule_name>, <results as JSON>)\n
    raw_finding_line = raw_finding_line.strip()
    # get rule_id
    rule_id = raw_finding_line.split(":")[0]
    # get the actual result tuple
    tuple_result = raw_finding_line[len(rule_id)+1:].strip()
    tuple_result = tuple_result[1:-1] # remove ()
    splitted_results = tuple_result.split(",")
    # extract cpg_path, rule_name and result from tuple
    cpg_path = splitted_results[0]
    rule_name = splitted_results[1]
    result = tuple_result[len(cpg_path)+len(rule_name)+2:]
    # load it as json
    result_list = json.loads(result)
    logger.info(f'#{result_list}')
    instances = rule_id_instance_mapping[rule_id.strip()]
    logger.info(f'#{result_list}')
    # return a discovery_result
    return DiscoveryResult(rule_name, instances, cpg_path, result_list, rule_id, query_file=query_file)


def _process_raw_findings(raw_findings: str, rule_id_instance_mapping: dict, query_file: Path) -> list[DiscoveryResult]:
    # raw findings are exepcted to be in the following format
    # <rule_id>: (<path_to_cpg_used>, <rule_name>, <results_as_list_of_JSON>)\n
    if not raw_findings:
        return []
    all_findings = raw_findings.strip().split("\n")
    d_results = []
    for finding in all_findings:
        if not re.match(r"^[^:]+: \(.*\)$", finding):
            logger.info(f"\033[92mSkipping line {finding} in output, does not meet the required format.\033[0m")
        try:
            d_results += [_parse_finding_line(finding, rule_id_instance_mapping, query_file)]
        except json.JSONDecodeError:
            logger.error(f"Could not parse result {finding}. The JSON result is corrupt.")
        except IndexError:
            logger.error(f"Could not parse '{finding}'. The result should be of the form (<path_to_cpg_used>, <rule_name>, <results_as_list_of_JSON>)\\n")
        except:
            logger.error(f"Something went wrong by parsing this line '{finding}'. Skipping...")
    logger.info("Discovery - rule execution done and raw output parsed.")
    return d_results


def _process_joern_results(list_of_discovery_results: list):
    error_instances = []
    all_findings = []
    d_result: DiscoveryResult
    for d_result in list_of_discovery_results:
        json_result = d_result.result
        d_result.discovery_method = "joern"
        if not json_result:
            d_result.result = {}
            d_result.status = discovery_result_strings["no_discovery"]
            all_findings += [d_result]
            continue
        for finding in json_result:
            if any(k not in finding for k in mand_finding_joern_keys):
                error = f"Discovery - finding {finding} does not include some mandatory keys ({mand_finding_joern_keys}). Please fix the rule {d_result.rule_name} and re-run. Often this amount to use `location.toJson`"
                logger.error(error)
                error_instances += d_result.instances
                continue
            finding_result = DiscoveryResult(d_result.rule_name, d_result.instances, d_result.cpg_path, 
                                             finding, d_result.rule_id, d_result.queryFile)
            finding_result.status = discovery_result_strings["discovery"]
            all_findings += [finding_result]
    return all_findings, error_instances


def _add_measurement(result_list: list, sast_measurement: dict or None):
    res = []
    d_res: DiscoveryResult
    for d_res in result_list:
        d_res.sast_measurement = []
        if not sast_measurement:
            d_res.sast_measurement = ["ignored"] * len(d_res.instances)
        else:
            for instance in d_res.instances:
                d_res.sast_measurement += [sast_measurement[repr(instance)]]
        res += [d_res]
    return res


def _process_missing_instances(all_positive_results: list, rule_id_instance_mapping: dict):
    # The rule_id_instance_mapping should contain all instances whose discovery rule is included in the large discovery rule.
    # An instance could go missing, for example in _process_raw_findings, as we cannot tell, which instances the failing line affected
    # This function aims to collect all instances, that are in the rule_id_instance_mapping but not in the positive results
    missing_instances = []
    for rule_id, instances in rule_id_instance_mapping.items():
        res_with_this_id = list(filter(lambda res: res.rule_id == rule_id, all_positive_results))
        if not res_with_this_id:
            missing_instances += instances
    return missing_instances


def _process_negative_instances(dict_error_instances: dict):
    # There are different types of errors, that can occur during the discovery and the evaluation.
    # The instances, that are affected by this error have to be included in the results as well.
    # Possible error messages are: `invalid discovery rule`, `error while parsing discovery rule`, `discovery method not supported`, 
    # `supported by SAST`, `no meas result`, `joern output error`, `parsing error`
    # At the moment this results in either `ERROR_DISCOVERY` or (for `supported by SAST`) `SUPPORTED_BY_SAST`
    # Maybe we can think of an option that provides a better feedback to the user about the different error categories? 
    d_res = []
    for error, instances in dict_error_instances.items():
        if not instances:
            continue
        result = DiscoveryResult("", instances, "", {}, "")
        result.status = discovery_result_strings["supported"] if "supported" in error else discovery_result_strings["error"]
        result.error = error
        d_res += [result]
    return d_res


def _export_findings_file(list_of_results: list, disc_output_dir: Path, build_name: str):
    # Exports all discoveries (positive results) as a JSON file.
    findings = []
    d_res: DiscoveryResult
    for d_res in list_of_results:
        if d_res.status == "DISCOVERY":
            findings += [d_res.to_json()]
    ofile_csv = disc_output_dir / f"findings_{build_name}.json"
    with open(ofile_csv, "w") as json_file:
        json.dump(findings, json_file, sort_keys=True, indent=4)
    return ofile_csv


def _export_csv_file(list_of_results: list, disc_output_dir: Path, build_name: str) -> Path:
    # Exports all results to a csv file
    rows = []
    d_res: DiscoveryResult
    for d_res in list_of_results:
        rows += d_res.to_csv()
    if not rows:
        logger.warning('Could not find results to write a csv file.')
        return
    if "patternId" in rows[0].keys() and "instanceId" in rows[0].keys():
        rows = sorted(rows, key=lambda d: (d["patternId"], d["instanceId"]))
    headers = list(filter(lambda h: h in set(rows[0].keys()), DiscoveryResult.csv_headers()))
    ofile_csv = disc_output_dir / f"discovery_{build_name}.csv"
    utils.write_csv_file(ofile_csv, headers, rows)
    return ofile_csv
