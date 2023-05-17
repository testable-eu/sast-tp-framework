import asyncio
import json
import shutil
from pathlib import Path
from typing import Dict
import yaml

import logging
from core import loggermgr
logger = logging.getLogger(loggermgr.logger_name(__name__))

from core.sast import SAST
import config

SAST_ROOT_DIR: Path = config.ROOT_SAST_DIR
CODEQL_BUILD_TEMPLATE: Path = SAST_ROOT_DIR / "core/resources/_template_build.sh"

class CodeQL(SAST):
    tool = "codeql"

    CODEQL_SCRIPT_DIR: Path = None
    CODEQL_CONFIG_FILE: Path = None
    CODEQL_CONFIG: Dict = None

    async def launcher(self, src_dir: Path, language: str,
                       output_dir: Path, **kwargs) -> Path:
        self.logging(what="launcher", status="started...")
        # project_name: str = f"TPF_{language}_{src_dir.name}_{uuid.uuid4()}"
        project_name: str = SAST.build_project_name(src_dir.name, self.tool, language, timestamp=True)
        proj_dir_tmp: Path = output_dir / project_name
        proj_dir_tmp.mkdir(parents=True, exist_ok=True)
        shutil.copytree(src_dir, proj_dir_tmp / "src")
        src_root: Path = (proj_dir_tmp / "src").resolve()
        codeql_db_location: Path = (src_root / "ql_db").resolve()

        language = language.lower()
        if language == "js":
            language = "javascript"

        # Preparing the building command
        self.logging(what="launcher", message=f"building", status="started...")
        codeql_createdb_cmd = f"{self.CODEQL_CONFIG['installation_path']}/codeql database create {codeql_db_location} --source-root {src_root} --language {language}"
        if "lib_dir" in kwargs and kwargs["lib_dir"]:
            lib_dir: Path = Path(src_root / kwargs["lib_dir"]).resolve()
            # Read the build template command file and prepare it
            with open(CODEQL_BUILD_TEMPLATE, 'r') as build_template_file:
                build_filedata = build_template_file.read()
            build_filedata = build_filedata.replace("$PATTERNSRC", f"{src_root}/src")
            build_filedata = build_filedata.replace("$PATTERNLIB", f"{lib_dir}")
            build_filedata = build_filedata.replace("$TPFOUT", f"{proj_dir_tmp}")
            # Write the build command file
            with open(f"{proj_dir_tmp}/build.sh", 'w', 0o777) as build_file:
                build_file.write(build_filedata)
            pattern_build_cmd = f"\'{proj_dir_tmp}/build.sh\'"
            codeql_createdb_cmd += " --command={}".format(pattern_build_cmd)
        # if kwargs["measurement"]:
        #     pattern_build_cmd = f"\'find {src_root} -type f -name \"*.java\" -exec javac -cp ../lib/*.jar\'"
        #     codeql_createdb_cmd = f"{self.CODEQL_CONFIG['installation_path']}/codeql database create {codeql_db_location} --source-root {src_root} --language {language} --command={pattern_build_cmd}"

        codeql_createdb = await asyncio.create_subprocess_shell(codeql_createdb_cmd)
        await codeql_createdb.wait()
        self.logging(what="launcher", message=f"building", status="done.")

        self.logging(what="launcher", message=f"scanning", status="started...")
        codeql_analyze_cmd = f"{self.CODEQL_CONFIG['installation_path']}/codeql database analyze {codeql_db_location} --format=sarif-latest --output={proj_dir_tmp}/{project_name}.sarif"
        codeql_analyze = await asyncio.create_subprocess_shell(codeql_analyze_cmd)
        await codeql_analyze.wait()
        self.logging(what="launcher", message=f"scanning", status="done.")

        res = proj_dir_tmp / f"{project_name}.sarif"
        self.logging(what="launcher", message=f"result {res}", status="done.")
        return res


    def inspector(self, sast_res_file: Path, language: str) -> list[Dict]:
        self.logging(what="inspector", status="started...")
        with open(sast_res_file) as sarif_file:
            codeql_sarif_report: Dict = json.load(sarif_file)

        sarif_results: list[Dict] = codeql_sarif_report["runs"][0]["results"]
        supported_vulnerabilities = list(self.CODEQL_CONFIG["supported_vulnerability"].values())

        # TODO - SAST: are we properly mapping the vulns here?
        sarif_results = list(
            filter(lambda x: [SAST.vuln_match(vuln, x["ruleId"]) for vuln in supported_vulnerabilities], sarif_results)
        )

        findings: list[Dict] = []
        for sarif_res in sarif_results:
            for location in sarif_res["locations"]:
                finding: Dict = {
                    "type": SAST.get_norm_vuln(sarif_res['ruleId'], self.CODEQL_CONFIG["supported_vulnerability"]),
                    "type_orig": sarif_res['ruleId'],
                    "file": location["physicalLocation"]["artifactLocation"]["uri"].split("/")[-1],
                    "line": location["physicalLocation"]["region"]["startLine"]
                }
                findings.append(finding)
        self.logging(what="inspector", status="done.")
        return findings


    async def get_tool_version(self) -> str:
        return self.CODEQL_CONFIG["version"]