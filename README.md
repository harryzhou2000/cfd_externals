# CFD External Libs

For building some libraries that is inconvenient for integration by source+CMake.

Libraries to build:

- zlib
- hdf5
- cgns
- parmetis+metis

## Environment for building on Linux:

- build essentials including gcc, g++
- MPI SDK (including mpicc, mpicxx wrapper, for example apt package `libopenmpi-dev`)
- GNU Make
- CMake
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

### Populate submodules

To update / init recursively:

```bash
git -c protocol.file.allow=always submodule update --init --recursive
```
