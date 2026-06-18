import os, sys
import platform
import argparse
import shutil
import shlex

parser = argparse.ArgumentParser("cfd_externals_builder")
parser.add_argument("-l", "--libs", help="libs to build", default="")
args = parser.parse_args()

if len(args.libs):
    libs = eval(args.libs)
else:
    libs = ["zlib", "hdf5", "cgns", "parmetis_fix", "cantera"]

print(f"starting to build libs: {libs}")

workingDir = os.getcwd()
installDir = "install"
buildDirPrefix = "build"
npBuild = int(os.getenv("JOBS", "8"))
installDirFull = os.path.join(workingDir, installDir)

environDelim = ":"
if platform.system() == "Windows":
    environDelim = ";"
if "CMAKE_PREFIX_PATH" in os.environ:
    os.environ["CMAKE_PREFIX_PATH"] = (
        installDirFull + environDelim + os.environ["CMAKE_PREFIX_PATH"]
    )
else:
    os.environ["CMAKE_PREFIX_PATH"] = installDirFull


repos = {
    "zlib": "repos/zlib",
    "hdf5": "repos/hdf5",
    "cgns": "repos/cgns",
    "parmetis_fix": "repos/parmetis_fix",
    "cantera": "repos/cantera",
}

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

boostIncDir = os.path.abspath(os.path.join(workingDir, "..", "boost"))
if os.path.isdir(boostIncDir):
    settings["cantera"].append(("boost_inc_dir", boostIncDir))


os.makedirs(installDirFull, exist_ok=True)


def run_or_die(cmd):
    ret = os.system(cmd)
    if ret != 0:
        print(f"ERROR: command failed (exit code {ret}): {cmd}")
        sys.exit(1)

for lib in libs:
    curRepoPath = os.path.join(workingDir, repos[lib])
    lw = min((os.get_terminal_size()[0] if sys.stdout.isatty() else 10), 200)
    print("#" * lw)
    print(f"doing lib {lib}")

    if lib == "cantera":
        missing = []
        if not shutil.which("scons"):
            missing.append("scons")
        try:
            import packaging
        except ImportError:
            missing.append("packaging")
        try:
            from ruamel import yaml
        except ImportError:
            missing.append("ruamel.yaml")
        if missing:
            print(f"ERROR: missing Python packages required to build cantera: {missing}")
            print(f"  Install them with: pip install {' '.join(missing)}")
            sys.exit(1)

        os.chdir(curRepoPath)
        run_or_die("git submodule update --init --depth=1 --recursive")
        sconsFlags = " ".join([f"{setting[0]}={shlex.quote(str(setting[1]))}" for setting in settings[lib]])
        run_or_die(f"scons build prefix={installDirFull} {sconsFlags} -j{npBuild}")
        run_or_die(f"scons install")
        canteraLib = os.path.join(installDirFull, "lib", "libcantera_shared.so")
        if os.path.isfile(canteraLib):
            if not shutil.which("patchelf"):
                print("WARNING: patchelf not found, cannot strip omp/gomp dependency")
            else:
                needed = os.popen(f"readelf -d {canteraLib}").read()
                for omp in ["libomp.so", "libgomp.so"]:
                    if omp in needed:
                        print(f"  stripping {omp} from {canteraLib}")
                        os.system(f"patchelf --remove-needed {omp} {canteraLib}")
    else:
        curBuildDirFull = os.path.join(workingDir, buildDirPrefix + "_" + lib)
        os.makedirs(curBuildDirFull, exist_ok=True)
        os.chdir(curBuildDirFull)
        cmakeConfigureCmd = (
            f"cmake {curRepoPath} -DCMAKE_INSTALL_PREFIX={installDirFull} "
            + f"-DCMAKE_PREFIX_PATH={installDirFull} "
            + "".join([f" -D{setting[0]}={setting[1]} " for setting in settings[lib]])
        )
        print(cmakeConfigureCmd)
        run_or_die(cmakeConfigureCmd)
        run_or_die(f"cmake --build . --config release --parallel {npBuild}")
        run_or_die(f"cmake --install .")

    print("#" * lw)
