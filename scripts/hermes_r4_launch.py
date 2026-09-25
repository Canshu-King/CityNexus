from __future__ import annotations

import runpy
import sys

from hermes_r4_socket_guard import install


install()
module = sys.argv[1]
sys.argv = [module, *sys.argv[2:]]
if module == "citynexus_mcp.server":
    from citynexus_mcp.server import main

    main()
else:
    runpy.run_module(module, run_name="__main__", alter_sys=True)
