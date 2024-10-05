import os
import platform
import argparse

parser = argparse.ArgumentParser("cfd_externals_builder")
parser.add_argument("-l", "--libs", help="libs to build", default="")
args = parser.parse_args()

if len(args.libs):
    libs = eval(args.libs)
else:
    libs = ["zlib", "hdf5", "cgns"]
    
print(f"starting to build libs: {libs}")

workingDir = os.getcwd()
installDir = "install"
buildDirPrefix = "build"
npBuild = 8
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
}

settings = {}
settings["zlib"] = []

settings["hdf5"] = [
    ("HDF5_ENABLE_PARALLEL", "ON"),
    ("HDF5_ENABLE_Z_LIB_SUPPORT", "ON"),
    ("BUILD_TESTING", "OFF"),
]

settings["cgns"] = [
    ("CGNS_BUILD_SHARED", "OFF"),
    ("CGNS_ENABLE_HDF5", "ON"),
    ("CGNS_ENABLE_LFS", "ON"),
    ("CGNS_ENABLE_PARALLEL", "ON"),
    # ("HDF5_NEED_MPI", "ON")
    # ("HDF5_NEED_ZLIB", "ON")
]


os.makedirs(installDirFull, exist_ok=True)


# zlib

for lib in libs:
    curBuildDirFull = os.path.join(workingDir, buildDirPrefix + "_" + lib)
    os.makedirs(curBuildDirFull, exist_ok=True)
    os.chdir(curBuildDirFull)
    cmakeConfigureCmd = (
        f"cmake {os.path.join(workingDir, repos[lib])} -DCMAKE_INSTALL_PREFIX={installDirFull} "
        + "".join([f" -D{setting[0]}={setting[1]} " for setting in settings[lib]])
    )
    print("#" * min(os.get_terminal_size()[0], 200))
    print(f"doing lib {lib} with command: ")
    print(cmakeConfigureCmd)
    print("#" * min(os.get_terminal_size()[0], 200))
    os.system(cmakeConfigureCmd)
    os.system(f"cmake --build . --config release --parallel {npBuild}")
    os.system(f"cmake --install .")
