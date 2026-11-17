import importlib.util
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("builder", ROOT / "cfd_externals_build.py")
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)


class BuildPolicyTest(unittest.TestCase):
    def test_default_is_cpu_with_mandatory_caliper(self):
        args = builder.parse_args([])
        self.assertEqual(args.libs, ["caliper"] + builder.BASE_LIBS)
        flags = builder.cmake_options("caliper", args)
        self.assertEqual((flags["WITH_NVTX"], flags["WITH_CUPTI"], flags["WITH_MPI"]), ("OFF", "OFF", "OFF"))
        self.assertNotIn("CMAKE_CUDA_COMPILER", flags)
        self.assertIn("caliper", builder.parse_args(["--libs", "['zlib']"]).libs)

    def test_cuda_and_amgx_are_explicit(self):
        with self.assertRaises(SystemExit):
            builder.parse_args(["--amgx"])
        args = builder.parse_args(["--libs", "caliper", "--caliper-cuda", "--amgx", "--cuda-architectures", "80;86"])
        self.assertEqual(args.libs, ["caliper", "amgx"])
        self.assertEqual(builder.cmake_options("caliper", args)["WITH_CUPTI"], "ON")
        flags = builder.cmake_options("amgx", args)
        self.assertEqual(flags["CMAKE_NO_MPI"], "ON")
        self.assertEqual(flags["CMAKE_CUDA_ARCHITECTURES"], "80;86")

    def test_fork_and_pins_are_immutable(self):
        pins = json.loads((ROOT / "dependency_versions.json").read_text())
        self.assertEqual(pins["amgx"]["repository"], "https://github.com/harryzhou2000/AMGX.git")
        for pin in pins.values():
            self.assertRegex(pin["revision"], r"^[0-9a-f]{40}$")


if __name__ == "__main__":
    unittest.main()
