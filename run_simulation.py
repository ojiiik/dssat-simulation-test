"""Backward-compat shim. Use `dssat-sim simulate rice` going forward."""
import sys
from dssat_sim.cli import main

sys.exit(main(["simulate", "rice"]))
