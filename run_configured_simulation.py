"""Backward-compat shim. Use `dssat-sim simulate <crop>` going forward.

Forwards all args after the script name to `dssat-sim simulate`.
Examples:
    python run_configured_simulation.py rice     -> dssat-sim simulate rice
    python run_configured_simulation.py --list   -> dssat-sim simulate --list
"""
import sys
from dssat_sim.cli import main

sys.exit(main(["simulate"] + sys.argv[1:]))
