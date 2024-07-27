#!/usr/bin/env python3

import json
import logging
from pathlib import Path
import subprocess as sp
import sys
from termcolor import colored
import os
import re
from check_const import (
    GCC_EXE,
    CLANG_TIDY_EXE,
    CPPCHECK_EXE,
    DEFINES,
    WARNINGS_COMMON,
    WARNINGS_GCC,
    WARNINGS_CLANG,
    CLANG_CHECKS,
)

sys.path.append("/u/gkan/scripts/perforce")
from p4_utils import P4Wrapper


logging.basicConfig(format="%(message)s", level=logging.INFO)


class Check:
    filename: str
    lines: list[tuple[int, int]]
    command: list[str]
    proc: sp.Popen

    def __init__(self, filename: str, lines: list[tuple[int, int]], command: list[str], proc: sp.Popen, check_fn):
        self.filename = filename
        self.lines = lines
        self.command = command
        self.proc = proc
        self.check_fn = check_fn


def main():
    to_check = get_p4_diff()
    filename_to_checks = {}
    for filename, lines in to_check.items():
        filename_to_checks[filename] = (
            run_gcc(filename, lines),
            run_clang_tidy(filename, lines),
            run_cppcheck(filename, lines),
        )

    for filename, checks in filename_to_checks.items():
        print("=" * 120)
        logging.info(f"FILENAME: {filename}")
        for check in checks:
            check.check_fn(check)
            logging.info("-" * 120)
        print()

    print_footer()


def get_p4_diff() -> dict[str, list[tuple[int, int]]]:
    to_check = {}
    with P4Wrapper() as p4:
        result = p4.run("diff", "-du0")
        idx = 0
        num_items = len(result)
        while idx < num_items:
            item = result[idx]
            assert type(item) is dict

            filename = item["clientFile"]
            assert Path(filename).is_file()

            idx += 1
            to_check_lst = []
            while idx < num_items:
                chunk = result[idx]
                if type(chunk) is not str:
                    break

                if not chunk.startswith("@"):
                    idx += 1
                    continue

                _, after = chunk.strip("@ ").split()

                # if we removed some lines, we don't need to check
                if after.startswith("-"):
                    idx += 1
                    continue

                assert after.startswith("+")
                line_num, chunk_size = map(int, after.lstrip("+").split(","))
                # if we didn't add any lines, we don't need to check
                if chunk_size == 0:
                    idx += 1
                    continue

                to_check_lst.append((line_num, line_num + chunk_size))
                idx += 1

            if len(to_check_lst) != 0:
                to_check[filename] = to_check_lst

    return to_check


def print_file_line(filename: str, line_begin: int, line_end: int, col_begin: int, col_end: int):
    with open(filename, "r", encoding="latin-1") as infile:
        for i in range(line_begin - 1):
            next(infile)
        for i in range(line_end - line_begin + 1):
            logging.info(next(infile).rstrip())
            logging.info(" " * (col_begin - 1) + "^" + "~" * (col_end - col_begin))


def is_line_in_lines(line: int, lines: list[tuple[int, int]]) -> bool:
    for begin_line, end_line in lines:
        if line < begin_line:
            return False

        if line < end_line:
            return True

    return False


def get_includes(filename: str) -> list[str]:
    p4_root = Path(os.environ["P4_ROOT"])
    filename = Path(filename)
    includes = [f"-I{filename.parent}"]
    for parent in filename.parents[1:]:
        if parent == p4_root:
            break
        includes.append(f"-I{parent}/include")
    includes.append(f"-I{p4_root}/nwtn/src/include")
    includes.append(f"-I{p4_root}/includex")
    includes.append(f"-I{p4_root}/includex/common")
    includes.append(f"-I{p4_root}/snps/include")

    for include in includes:
        if not Path(include[2:]).is_dir():
            print(f"{include[2:]} is not a directory")
            sys.exit(1)

    return includes


def get_severity_color(severity: str) -> str:
    match severity:
        case "error":
            return "red"
        case "style":
            return "magenta"
        case "warning":
            return "magenta"
        case "note":
            return "cyan"
        case _:
            print(f"UNKNOWN SEVERITY: {severity}")
            return "yellow"


def run_gcc(filename: str, lines: list[tuple[int, int]]) -> Check:
    cmd = [
        GCC_EXE,
        "-fdiagnostics-format=json",
        *("-x", "c++"),
        "-std=c++17",
        *get_includes(filename),
        *DEFINES,
        *WARNINGS_COMMON,
        *WARNINGS_GCC,
        "-c",
        *("-o", "/dev/null"),
        filename,
    ]
    return Check(filename, lines, list(map(str, cmd)), sp.Popen(cmd, stdout=sp.PIPE, stderr=sp.PIPE), check_gcc)


def check_gcc(check: Check):
    if logging.root.level == logging.DEBUG:
        logging.debug(f'COMMAND: {" ".join(check.command)}')
    else:
        logging.info(f"COMMAND: {check.command[0]}")

    stdout, stderr = check.proc.communicate()
    logging.debug("STDOUT")
    logging.debug(stdout.decode("utf-8"))
    logging.debug("STDERR")
    logging.debug(stderr.decode("utf-8"))

    if check.proc.returncode == 0:
        return

    diagnostics = json.loads(stderr.decode("utf-8"))
    for diagnostic in diagnostics:
        for location in diagnostic["locations"]:
            # from pprint import pprint
            # pprint(location)
            filename = location.get("start", location["caret"])["file"]
            line_begin = location.get("start", location["caret"])["line"]
            line_end = location.get("finish", location.get("start", location["caret"]))["line"]
            col_begin = location.get("start", location["caret"])["column"]
            col_end = location.get("finish", location.get("start", location["caret"]))["column"]

            if filename != check.filename:
                continue

            if any(is_line_in_lines(line, check.lines) for line in range(line_begin, line_end + 1)):
                logging.info(
                    colored(f"{filename}:{line_begin}:{col_begin}: ", attrs=["bold"])
                    + colored(f"{diagnostic['kind']}: ", get_severity_color(diagnostic["kind"]), attrs=["bold"])
                    + colored(f"{diagnostic['message']}", attrs=["bold"])
                )
                print_file_line(filename, line_begin, line_end, col_begin, col_end)


def run_clang_tidy(filename: str, lines: list[tuple[int, int]]):
    line_filter = json.dumps([{"name": filename, "lines": lines}])
    cmd = [
        CLANG_TIDY_EXE,
        "--header-filter=foobarbaz",
        "--use-color",
        f"--checks={','.join(CLANG_CHECKS)}",
        f"--line-filter={line_filter}",
        filename,
        "--",
        "-ferror-limit=0",
        *("-x", "c++"),
        "-std=c++17",
        *get_includes(filename),
        *DEFINES,
        *WARNINGS_COMMON,
        *WARNINGS_CLANG,
        "-c",
        *("-o", "/dev/null"),
    ]
    return Check(
        filename,
        lines,
        list(map(str, cmd)),
        sp.Popen(cmd, stdout=sp.PIPE, stderr=sp.PIPE),
        check_clang_tidy,
    )


def check_clang_tidy(check: Check):
    if logging.root.level == logging.DEBUG:
        logging.debug(f'COMMAND: {" ".join(check.command)}')
    else:
        logging.info(f"COMMAND: {check.command[0]}")

    stdout, stderr = check.proc.communicate()
    logging.debug("STDOUT")
    logging.debug(stdout.decode("utf-8"))
    logging.debug("STDERR")
    logging.debug(stderr.decode("utf-8"))

    logging.info(colored(f"{check.filename}", attrs=["bold"]))
    logging.info(stdout.decode("utf-8"))


def run_cppcheck(filename: str, lines: list[tuple[int, int]]):
    cmd = [
        CPPCHECK_EXE,
        *DEFINES,
        "-D__cplusplus",
        "--std=c++17",
        "--enable=all",
        "--force",
        "--language=c++",
        "--suppress=missingIncludeSystem",
        "--suppress=checkersReport",
        "--suppress=unusedFunction",
        "--suppress=unknownMacro",
        "--suppress=unmatchedSuppression",
        "--platform=unix64",
        "--quiet",
        filename,
    ]
    return Check(
        filename,
        lines,
        list(map(str, cmd)),
        sp.Popen(cmd, stdout=sp.PIPE, stderr=sp.PIPE),
        check_cppcheck,
    )


CPPCHECK_RE = re.compile(
    r"(?P<filename>[^:]+):(?P<linenum>\d+):(?P<column>\d+): (?P<severity>\w+): (?P<message>.+) \[(?P<id>\w+)\]"
)


def check_cppcheck(check: Check):
    if logging.root.level == logging.DEBUG:
        logging.debug(f'COMMAND: {" ".join(check.command)}')
    else:
        logging.info(f"COMMAND: {check.command[0]}")

    stdout, stderr = check.proc.communicate()
    logging.debug("STDOUT")
    logging.debug(stdout.decode("utf-8"))
    logging.debug("STDERR")
    logging.debug(stderr.decode("utf-8"))

    in_error = False
    for line in stderr.decode("utf-8").split("\n"):
        match = CPPCHECK_RE.match(line)
        if match:
            if match.group("severity") != "note":
                in_error = is_line_in_lines(int(match.group("linenum")), check.lines)
                if in_error:
                    print("-" * 80)
                    logging.info(
                        colored(
                            f"{match.group('filename')}:{match.group('linenum')}:{match.group('column')}: ",
                            attrs=["bold"],
                        )
                        + colored(
                            f"{match.group('severity')}: ", get_severity_color(match.group("severity")), attrs=["bold"]
                        )
                        + colored(f"{match.group('message')}", attrs=["bold"])
                        + colored(f" [{match.group('id')}]", attrs=["bold"])
                    )
        else:
            if not in_error:
                continue

            logging.info(line)


def print_footer():
    msg = "For any issues please contact gkan@synopsys.com"
    logging.info("=" * len(msg))
    logging.info(msg)
    logging.info("=" * len(msg))


if __name__ == "__main__":
    main()
