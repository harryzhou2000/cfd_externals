# CFD External Libs

For building some libraries that is inconvenient for integration by source+CMake.

Libraries to build:

- zlib
- hdf5
- cgns
- parmetis+metis
- cantera (chemistry, requires SCons)

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
