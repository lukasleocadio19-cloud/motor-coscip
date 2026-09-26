import sys

if "--verificar" in sys.argv[1:]:
    from coscip_mcp.diagnostico import run

    sys.exit(run())

from coscip_mcp.server import main

main()
