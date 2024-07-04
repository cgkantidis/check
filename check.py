#!/usr/bin/env python3

import json
import logging
from pathlib import Path
import subprocess as sp
import sys
from termcolor import colored

logging.basicConfig(format="%(message)s", level=logging.DEBUG)

GCC_EXE = Path("/bin/g++")
CLANG_TIDY_EXE = Path("/bin/clang-tidy")
CPPCHECK_EXE = Path("/bin/cppcheck")


def main():
    for filename in sys.argv[1:]:
        logging.info(f"Checking {filename}")
        check_gcc(filename, None, None)
        check_clang_tidy(filename, None, None)
        check_cppcheck(filename, None, None)


def print_file_line(filename: str, line_begin: int, line_end: int, col_begin: int, col_end: int):
    with open(filename, "r") as infile:
        for i in range(line_begin - 1):
            next(infile)
        for i in range(line_end - line_begin + 1):
            logging.info(next(infile).rstrip())
            logging.info(" " * (col_begin - 1) + "^" + "~" * (col_end - col_begin))


def check_gcc(filename: str, begin: int, end: int):
    cmd = [
        GCC_EXE,
        "-fdiagnostics-format=json",
        "-c",
        *"-o /dev/null".split(),
        "-Wall",
        "-Wextra",
        "-Wshadow",
        "-Wnon-virtual-dtor",
        "-pedantic",
        "-Wold-style-cast",
        "-Wcast-align",
        "-Wunused",
        "-Woverloaded-virtual",
        "-Wconversion",
        "-Wsign-conversion",
        "-Wmisleading-indentation",
        "-Wnull-dereference",
        "-Wdouble-promotion",
        "-Wformat=2",
        "-Wimplicit-fallthrough",
        "-std=c++20",
        filename,
    ]
    proc = sp.run(cmd, capture_output=True)
    if proc.returncode == 0:
        return

    logging.debug(f'COMMAND: {" ".join(map(str, cmd))}')

    diagnostics = json.loads(proc.stderr.decode("utf-8"))
    for diagnostic in diagnostics:
        if diagnostic["kind"] == "error":
            color = "red"
        elif diagnostic["kind"] == "warning":
            color = "magenda"
        else:
            color = "white"

        for location in diagnostic["locations"]:
            line_begin = location["caret"]["line"]
            line_end = location["finish"]["line"]
            col_begin = location["caret"]["column"]
            col_end = location["finish"]["column"]
            if begin is None or end is None or (line_begin >= begin and line_end < end):
                logging.info(
                    colored(f"{filename}:{line_begin}:{col_begin}: ", attrs=["bold"])
                    + colored(f"{diagnostic['kind']}: ", color, attrs=["bold"])
                    + colored(f"{diagnostic['message']}", attrs=["bold"])
                )
                print_file_line(filename, line_begin, line_end, col_begin, col_end)


def check_clang_tidy(filename: str, begin: int, end: int):
    if begin is None or end is None:
        line_filter = json.dumps([{"name": filename}])
    else:
        line_filter = json.dumps([{"name": filename, "lines": [[begin, end]]}])

    checks = [
        "*",
        "-abseil-*",
        "-altera-*",
        "-android-*",
        "-darwin-*",
        "-fuchsia-*",
        "-google-*",
        "-llvm-*",
        "-llvmlibc-*",
        "-modernize-use-trailing-return-type",
        "-mpi-*",
        "-objc-*",
        "-openmp-*",
        "-readability-identifier-length",
        "-zircon-*",
    ]
    cmd = [
        CLANG_TIDY_EXE,
        "--header-filter=.*",
        "--use-color",
        f"--checks={','.join(checks)}",
        f"--line-filter={line_filter}",
        filename,
        "--",
        "-std=c++20",
        "-Wall",
        "-Wextra",
        "-Wshadow",
        "-Wnon-virtual-dtor",
        "-pedantic",
        "-Wold-style-cast",
        "-Wcast-align",
        "-Wunused",
        "-Woverloaded-virtual",
        "-Wconversion",
        "-Wsign-conversion",
        "-Wmisleading-indentation",
        "-Wnull-dereference",
        "-Wdouble-promotion",
        "-Wformat=2",
        "-Wimplicit-fallthrough",
    ]
    proc = sp.run(cmd, capture_output=True)

    logging.debug(f'COMMAND: {" ".join(map(str, cmd))}')
    logging.info(colored(f"{filename}", attrs=["bold"]))
    logging.info(proc.stdout.decode("utf-8"))


def check_cppcheck(filename: str, begin: int, end: int):
    cmd = [
        CPPCHECK_EXE,
        "--enable=all",
        "--suppress=missingIncludeSystem",
        "--suppress=unusedFunction",
        "--suppress=checkersReport",
        "--platform=unix64",
        filename,
    ]
    proc = sp.run(cmd, capture_output=True)
    if proc.returncode == 0:
        return

    logging.debug(f'COMMAND: {" ".join(map(str, cmd))}')
    logging.info(colored(f"{filename}", attrs=["bold"]))
    logging.info(proc.stdout.decode("utf-8"))


if __name__ == "__main__":
    main()
