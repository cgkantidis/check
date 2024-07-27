from pathlib import Path

GCC_EXE = Path("/remote/dept5116t/gkan/.local/install/bin/g++")
CLANG_TIDY_EXE = Path("/remote/dept5116t/gkan/.local/install/bin/clang-tidy")
CPPCHECK_EXE = Path("/remote/dept5116t/gkan/.local/install/bin/cppcheck")
DEFINES = (
    "-DPLATFORM_LIBRARY_2",
    "-DUSE_PTMT_ALLOCATOR",
    "-DPTMT_ALLOCATOR_ENABLED",
    "-DPTMT_ALLOCATOR_TUNE",
    "-DMTT_LOCK_PROFILING",
    "-D_GLIBCXX_ASSERTIONS",
    "-DGPIO_USE_NETLIST_VIRTUAL",
    "-DGPIO_USE_READER_NON_VIRTUAL"
    # "-DGPIO_USE_READER_VIRTUAL",
    "-DGPIO_USE_WRITER_VIRTUAL",
    "-DSynopsys_Optimize",
    "-DSynopsys_amd64",
    "-DSynopsys_linux64",
    "-DSynopsys_linux",
    "-DSynopsys_Develop",
)
WARNINGS_COMMON = (
    "-Wall",
    "-Wextra",
    "-Wshadow",
    "-Wnon-virtual-dtor",
    "-pedantic",
    "-Wold-style-cast",
    "-Wcast-align",
    "-Wunused",
    "-Woverloaded-virtual",
    "-Wpedantic",
    "-Wconversion",
    "-Wsign-conversion",
    "-Wdouble-promotion",
    "-Wformat=2",
)
WARNINGS_GCC = (
    "-Wmisleading-indentation",
    "-Wduplicated-cond",
    "-Wduplicated-branches",
    "-Wlogical-op",
    "-Wnull-dereference",
    "-Wuseless-cast",
)
WARNINGS_CLANG = ("-Wimplicit-fallthrough",)
CLANG_CHECKS = (
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
)
