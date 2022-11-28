import os
import sys
import subprocess

pyexe = sys.executable
print("-- Python executable: {}".format(pyexe))
pr = subprocess.Popen([pyexe, "--version"], shell=False, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
(output, errdata) = pr.communicate()
print("-- Python version: {}".format(output.decode("utf-8").strip()))

resource_path="resources"

def join_resources_path(relativepath):
    dirname = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(dirname, resource_path, relativepath)