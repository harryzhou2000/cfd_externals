# CFD External Libs

For building some libraries that is inconvenient for integration by source+CMake.

Libraries to build:

- zlib
- hdf5
- cgns
- parmetis+metis
- cantera (chemistry, requires SCons)
- Caliper CPU instrumentation (mandatory, including selected-library builds)
- Optional Caliper NVTX/CUPTI services and single-device AMGX

The default remains a **CPU build**. It neither detects nor requires CUDA,
and it does not build AMGX. Caliper MPI services also require explicit opt-in.
Use `--build-root build-cuda --prefix install-cuda` to keep optional CUDA
builds separate from an existing CPU installation.

## Environment for building on Linux:

- build essentials including gcc, g++
- MPI SDK (including mpicc, mpicxx wrapper, for example apt package `libopenmpi-dev`)
- GNU Make
- CMake
- SCons (for Cantera)
- python3 interpreter

## Environment for building on Windows

- Visual Studio (msvc toolchain for C/C++)
- Intel OneAPI (need to activate its environment in the shell) (need MPI SDK)
- CMake
- python interpreter

## building

Clone this repo.

Update git submodules.

```bash
git submodule update --init --depth=1 --recursive
```

Then run the script to build.

```bash
python cfd_externals_build.py
```

Ninja is preferred for fresh build directories when available; existing build
generators are preserved. `JOBS` or `--jobs` controls build concurrency.

Build only mandatory CPU Caliper, or a selected base library plus Caliper:

```bash
python cfd_externals_build.py --libs caliper --jobs 16
python cfd_externals_build.py --libs zlib,hdf5 --jobs 16
```

Enable CUDA profiling and/or the optional AMGX provider explicitly:

```bash
python cfd_externals_build.py --libs caliper --caliper-cuda \
  --cuda-compiler /usr/local/cuda/bin/nvcc --jobs 16
python cfd_externals_build.py --libs caliper --amgx \
  --cuda-architectures '80;86' --cuda-compiler /usr/local/cuda/bin/nvcc \
  --cuda-host-compiler /usr/bin/g++-12 --jobs 16
```

`--caliper-mpi` adds Caliper MPI services against the selected cluster MPI.
`--caliper-cuda` enables both NVTX and CUPTI and requires that CUDA SDK support;
it is independent of `--amgx`. AMGX always builds **without MPI**, with explicit
device architectures. Its host compiler should be a CUDA-compatible ordinary
C++ compiler; `CC=mpicc CXX=mpicxx` can still select MPI for the other libraries.
`--dry-run` prints the selected commands without building or writing files.

### Dependency pins and installed contracts

`repos/caliper` pins Caliper 2.15.0. `repos/amgx` pins our public
[AMGX fork](https://github.com/harryzhou2000/AMGX), rather than applying a
downstream patch to NVIDIA's source during installation. Gitlinks and
`dependency_versions.json` identify immutable source revisions; an existing
modified/mismatched checkout is rejected, never reset. Source tarballs include
the dependencies and require no Git checkout for CMake dependencies.

The selected AMGX profile is single-device FP64 block aggregation using
`SIZE_2/LOW_DEG/BLOCK_JACOBI`. Its native-storage API and block catalog are
recorded in the manifest. See the fork's `doc/NativeStorage.md` for limitations
and qualification status; packaging does not establish numerical convergence,
arbitrary smoother support, or stream/graph compatibility.

Installed libraries and CMake packages share the usual `install` prefix.
`install/share/cfd_externals/{caliper,amgx}-build.json` records the source,
feature flags, compiler paths, configure options and library SHA-256 hashes.
These are external-provider manifests, not the transitional
`dndsr-amgx-build.json` patch contract. DNDSR's consumer migration is separate;
this release does not change DNDSR or make its old patch validator accept the
new installation automatically.

Then all files are locally installed in `install`.

**A pitfall**: if you need to specify a non-system compiler set, like /path/to/gcc-11, error in linking `libmpi.so` could occur.

Therefore, if you see something like conflicting `libmpi.so` in the final executable linking, or by `ldd` you see wrong mpi links, or the program crashes due to mpi, try this:

```bash
CC=mpicc CXX=mpicxx python cfd_externals_build.py
```

which will link mpi correctly if the problem is linking to a faulty mpi library.

To control which compiler the wrapper uses, consult the vendor (like openmpi or mpich). You can check compiler using `mpicc -v`.

## Making a thin bundle

tar --exclude='*.git*' -zcvf cfd_externals_expo.tar.gz cfd_externals_expo

## Redirect to local repos

### Prepare local repo mirroring Github

```bash
~/repo/github/
├── CGNS
│   └── CGNS.git
├── harryzhou2000
│   ├── cfd_externals.git
│   └── parmetis_fix
├── HDFGroup
│   └── hdf5.git
└── madler
    └── zlib
```

`xxx.git` or `xxx` are both ok, with `xxx.git` created with `git clone --bare <url>`

### Set url replacement

In ~/.gitconfig

```bash
[url "~/repo/github/"]
    insteadOf = https://github.com/
```

or

```bash
git config --global url."~/repo/github/".insteadOf "https://github.com/"
```

edit `~/.gitconfig` to reverse this setting.

Using global instead of local setting saves the trouble of recursively configuring submodule settings.

### Populate submodules

To update / init recursively:

```bash
git -c protocol.file.allow=always submodule update --init --recursive
```

update with remote:

```bash
git -c protocol.file.allow=always submodule update --init --remote --recursive
```
