#!/usr/bin/env python3
"""Build the CPU bundle by default; CUDA profiling and single-device AMGX opt in."""
import argparse
import ast
import hashlib
import json
import os
from pathlib import Path
import platform
import shlex
import shutil
import subprocess

BASE_LIBS = ["zlib", "hdf5", "cgns", "parmetis_fix", "cantera"]
ROOT = Path(__file__).resolve().parent


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-l", "--libs", default="", help="base libraries, comma separated or legacy Python list; Caliper is always included")
    parser.add_argument("--caliper-cuda", action="store_true", help="enable Caliper NVTX and CUPTI services (requires CUDA)")
    parser.add_argument("--caliper-mpi", action="store_true", help="enable Caliper MPI services using the selected MPI")
    parser.add_argument("--amgx", action="store_true", help="build the pinned AMGX fork without MPI")
    parser.add_argument("--cuda-architectures", help="explicit AMGX architectures, e.g. '80;86'")
    parser.add_argument("--cuda-compiler", type=Path, help="nvcc path for optional CUDA dependencies")
    parser.add_argument("--cuda-host-compiler", type=Path, help="non-MPI C++ compiler for AMGX/nvcc")
    parser.add_argument("--jobs", type=int, default=int(os.getenv("JOBS", "8")))
    parser.add_argument("--prefix", type=Path, default=ROOT / "install")
    parser.add_argument("--build-root", type=Path, default=ROOT, help="parent of per-library build directories; separate CPU/CUDA variants")
    parser.add_argument("--dry-run", action="store_true", help="print commands without building or writing files")
    args = parser.parse_args(argv)
    if args.jobs < 1:
        parser.error("--jobs must be positive")
    if args.amgx and not args.cuda_architectures:
        parser.error("--amgx requires explicit --cuda-architectures")
    if args.libs.startswith("["):
        try:
            libs = ast.literal_eval(args.libs)
        except (ValueError, SyntaxError):
            parser.error("--libs must be a list of library names or a comma-separated string")
    else:
        libs = args.libs.split(",") if args.libs else BASE_LIBS
    if not isinstance(libs, list) or any(not isinstance(x, str) or x not in BASE_LIBS + ["caliper", "amgx"] for x in libs):
        parser.error("unknown library in --libs")
    if "amgx" in libs and not args.amgx:
        parser.error("AMGX selection requires --amgx and --cuda-architectures")
    args.libs = list(dict.fromkeys(["caliper"] + libs + (["amgx"] if args.amgx else [])))
    return args


def base_settings(root):
    shared_flag = "ON"
    if os.name == "nt":
        shared_flag = "OFF"

    settings = {}
    settings["zlib"] = [
        ("CMAKE_BUILD_TYPE", "RELEASE"),
    ]

    settings["hdf5"] = [
        ("CMAKE_BUILD_TYPE", "RELEASE"),
        ("HDF5_ENABLE_PARALLEL", "ON"),
        ("HDF5_ENABLE_Z_LIB_SUPPORT", "ON"),
        ("BUILD_TESTING", "OFF"),
    ]

    settings["cgns"] = [
        ("CMAKE_BUILD_TYPE", "RELEASE"),
        ("CGNS_BUILD_SHARED", shared_flag),
        ("CGNS_ENABLE_HDF5", "ON"),
        ("CGNS_ENABLE_LFS", "ON"),
        ("CGNS_ENABLE_PARALLEL", "ON"),
        ("HDF5_NEED_MPI", "ON"),
        ("HDF5_NEED_ZLIB", "ON"),
    ]

    settings["parmetis_fix"] = [
        ("CMAKE_BUILD_TYPE", "RELEASE"),
        ("BUILD_SHARED_LIBS", shared_flag),
        ("CMAKE_POLICY_VERSION_MINIMUM", "3.5"),
    ]

    settings["cantera"] = [
        ("python_package", "n"),
        ("f90_interface", "n"),
        ("googletest", "none"),
        ("doxygen_docs", "n"),
        ("sphinx_docs", "n"),
        ("system_eigen", "n"),
        ("system_fmt", "n"),
        ("system_yamlcpp", "n"),
        ("system_sundials", "n"),
        ("system_highfive", "n"),
        ("hdf_support", "n"),
        ("layout", "compact"),
        ("optimize", "y"),
        ("cxx_flags", "-std=c++17 -DEIGEN_DONT_PARALLELIZE"),
    ]

    boostIncDir = os.path.abspath(os.path.join(str(root), "..", "boost"))
    if os.path.isdir(boostIncDir):
        settings["cantera"].append(("boost_inc_dir", boostIncDir))


    return settings


def cmake_options(lib, args):
    options = {"CMAKE_BUILD_TYPE": "Release", "CMAKE_INSTALL_PREFIX": str(args.prefix.resolve())}
    if lib == "caliper":
        options.update(BUILD_SHARED_LIBS="ON", BUILD_TESTING="OFF", BUILD_DOCS="OFF",
                       WITH_MPI="ON" if args.caliper_mpi else "OFF",
                       WITH_NVTX="ON" if args.caliper_cuda else "OFF",
                       WITH_CUPTI="ON" if args.caliper_cuda else "OFF",
                       WITH_FORTRAN="OFF", WITH_PYTHON_BINDINGS="OFF")
        if args.caliper_cuda and args.cuda_compiler:
            options["CUDAToolkit_ROOT"] = str(args.cuda_compiler.resolve().parent.parent)
    elif lib == "amgx":
        options.update(CMAKE_NO_MPI="ON", AMGX_NO_RPATH="ON",
                       CMAKE_CUDA_ARCHITECTURES=args.cuda_architectures)
        if args.cuda_compiler:
            options["CMAKE_CUDA_COMPILER"] = str(args.cuda_compiler.resolve())
        if args.cuda_host_compiler:
            options["CMAKE_CXX_COMPILER"] = str(args.cuda_host_compiler.resolve())
            options["CMAKE_CUDA_HOST_COMPILER"] = str(args.cuda_host_compiler.resolve())
    else:
        options.update(base_settings(ROOT)[lib])
    return options


def run(command, args, env, cwd=None):
    print(shlex.join([str(x) for x in command]), flush=True)
    if not args.dry_run:
        subprocess.run([str(x) for x in command], cwd=cwd, env=env, check=True)


def verify_source(lib, source, pin):
    if not (source / "CMakeLists.txt").is_file():
        raise RuntimeError(f"{lib} source is absent; initialize its submodule or unpack the source bundle")
    if (source / ".git").exists():
        revision = subprocess.check_output(["git", "-C", str(source), "rev-parse", "HEAD"], text=True).strip()
        dirty = subprocess.check_output(["git", "-C", str(source), "status", "--porcelain", "--untracked-files=no"], text=True).strip()
        if revision != pin["revision"] or dirty:
            raise RuntimeError(f"{lib} source does not match its clean pinned revision; it was not modified")


def write_manifest(lib, args, pin, options):
    libraries = {}
    for directory in (args.prefix / "lib", args.prefix / "lib64"):
        for path in directory.glob("lib" + ("amgx" if lib == "amgx" else "caliper") + "*"):
            if path.is_file():
                libraries[path.name] = hashlib.sha256(path.read_bytes()).hexdigest()
    if not libraries:
        raise RuntimeError(f"{lib} installation produced no library")
    cache = args.build_root / ("build_" + lib) / "CMakeCache.txt"
    toolchain = {}
    for line in cache.read_text().splitlines():
        if any(line.startswith(key + ":") for key in ("CMAKE_C_COMPILER", "CMAKE_CXX_COMPILER", "CMAKE_CUDA_COMPILER", "CMAKE_CUDA_HOST_COMPILER", "CUDAToolkit_NVCC_EXECUTABLE")):
            key, value = line.split("=", 1)
            toolchain[key.split(":")[0]] = value
    manifest = dict(pin, configure=options, toolchain=toolchain, libraries_sha256=libraries)
    manifest["compiler_versions"] = {}
    for key, compiler in toolchain.items():
        result = subprocess.run([compiler, "--version"], text=True, capture_output=True)
        manifest["compiler_versions"][key] = result.stdout.strip() if result.returncode == 0 else "unavailable"
    if lib == "amgx":
        manifest.update(mpi=False, architectures=args.cuda_architectures)
    else:
        manifest.update(cpu=True, mpi=args.caliper_mpi, nvtx=args.caliper_cuda, cupti=args.caliper_cuda)
    destination = args.prefix / "share" / "cfd_externals"
    destination.mkdir(parents=True, exist_ok=True)
    (destination / (lib + "-build.json")).write_text(json.dumps(manifest, indent=2) + "\n")


def main(argv=None):
    args = parse_args(argv)
    args.prefix = args.prefix.resolve()
    args.build_root = args.build_root.resolve()
    env = os.environ.copy()
    env["CMAKE_PREFIX_PATH"] = str(args.prefix) + (os.pathsep + env["CMAKE_PREFIX_PATH"] if env.get("CMAKE_PREFIX_PATH") else "")
    pins = json.loads((ROOT / "dependency_versions.json").read_text())
    for lib in args.libs:
        source = ROOT / "repos" / lib
        if lib in pins:
            verify_source(lib, source, pins[lib])
        if lib == "cantera":
            if not args.dry_run:
                if not shutil.which("scons"):
                    raise RuntimeError("Cantera requires scons; install requirements.txt")
            if (source / ".git").exists():
                run(["git", "submodule", "update", "--init", "--depth=1", "--recursive"], args, env, source)
            flags = [f"{key}={value}" for key, value in base_settings(ROOT)[lib]]
            run(["scons", "build", f"prefix={args.prefix}", *flags, f"-j{args.jobs}"], args, env, source)
            run(["scons", "install"], args, env, source)
            # Preserve the existing Cantera package's OpenMP dependency policy.
            library = args.prefix / "lib" / "libcantera_shared.so"
            if not args.dry_run and library.is_file():
                if not shutil.which("patchelf"):
                    print("WARNING: patchelf not found, cannot strip omp/gomp dependency")
                else:
                    needed = subprocess.check_output(["readelf", "-d", str(library)], text=True)
                    for runtime in ("libomp.so", "libgomp.so"):
                        if runtime in needed:
                            run(["patchelf", "--remove-needed", runtime, library], args, env)
            continue
        build = args.build_root / ("build_" + lib)
        options = cmake_options(lib, args)
        configure = ["cmake", "-S", source, "-B", build]
        # Preserve existing generators. Prefer Ninja only for a fresh directory.
        if not (build / "CMakeCache.txt").exists() and not env.get("CMAKE_GENERATOR") and shutil.which("ninja"):
            configure += ["-G", "Ninja"]
        configure += [f"-D{key}={value}" for key, value in options.items()]
        run(configure, args, env)
        command = ["cmake", "--build", build, "--config", "Release", "--parallel", args.jobs]
        if lib == "amgx":
            command += ["--target", "amgx", "amgxsh", "amgx_capi"]
        run(command, args, env)
        run(["cmake", "--install", build, "--config", "Release"], args, env)
        if lib in pins and not args.dry_run:
            write_manifest(lib, args, pins[lib], options)


if __name__ == "__main__":
    main()
