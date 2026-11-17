# Dependency update validation (2026-11-17)

- Three build-policy tests pass: mandatory CPU Caliper, explicit CUDA/AMGX
  options and immutable fork pins.
- Caliper 2.15.0 builds and installs with GCC 12.4/Ninja, 16 build workers,
  MPI/NVTX/CUPTI OFF. A separate CMake consumer finds its installed package,
  links and executes begin/end-region annotations successfully.
- A separate Caliper installation builds with NVTX/CUPTI ON against CUDA 13.2.
  This checks compilation/linkage, not hardware counter availability.
- The pinned AMGX fork configures with CUDA 13.2, GCC 12, architectures 80/86
  and MPI OFF. Optional build commands and selection are tested; AMGX was not
  rebuilt or run as part of this packaging task. The fork's existing numerical
  qualification and ongoing downstream work remain separate evidence.
- Existing HDF5/CGNS/ParMETIS/Cantera recipes retain their settings. Their full
  builds were not repeated for this update.

The source release includes dependencies, not local build directories or
installed binary artifacts. Build the CPU or optional CUDA profile on the
target system; no new DNDSR consumer integration is included here.
