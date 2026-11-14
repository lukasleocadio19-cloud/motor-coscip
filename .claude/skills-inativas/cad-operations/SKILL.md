---
name: cad-operations
description: Unified local CAD operations skill for creating, editing, validating, and exporting CAD deliverables. Use when the user asks for CAD/DWG/DXF/PDF/SVG/PNG drafting, AutoCAD/Core Console, FreeCAD/FreeCAD MCP, SolidWorks/SolidWorks MCP/COM/VBA/C# automation, SLDPRT/SLDASM/STEP/STL files, electrical main single-line diagrams/电气主接线图/一次接线图/SLD, pavement structure drawings/路面结构图, or any local CAD workflow that should use installed CAD tools, scripts, and MCP assets.
---

# CAD Operations

## Purpose

Use this as a single entry point for CAD work. Route each task to the narrowest reproducible workflow, prefer generated/interchange files before manual edits, and verify outputs with live files or rendered previews before delivery.

## First decisions

1. **Identify the CAD family**
   - Electrical main wiring / SLD / 变电站主接线 / 一次接线图 → read `references/electrical-main-sld.md`, use `scripts/make_main_sld.py`.
   - Pavement / road layer cross-section / 路面结构图 → read `references/pavement-structure-cad.md`, use `scripts/generate_pavement_cad_ezdxf.py`.
   - SolidWorks parts, assemblies, drawings, STEP/STL/SLDPRT/SLDASM, feature creation, mates, rebuilds → read `references/solidworks-mcp.md`.
   - Generic 2D DWG/DXF editing, plotting, conversion, or AutoCAD/FreeCAD use → read `references/autocad-freecad.md`.
   - Unsure or environment-sensitive → read `references/local-cad-environment.md`.

2. **Choose the output source of truth**
   - Prefer **DXF** for editable 2D CAD interchange.
   - Prefer **SLDPRT/SLDASM/SLDDRW** for native SolidWorks work, then export STEP/STL/DXF/PDF as requested.
   - Use **PDF/SVG/PNG previews** for review; do not rely on DXF syntax alone for layout correctness.
   - DWG is proprietary: generate/modify DXF first, then convert or save as DWG through AutoCAD/ODA/LibreCAD/SolidWorks when explicitly required.

3. **Keep work reproducible**
   - Create specs/scripts in the active workspace, not in the skill directory.
   - Keep originals separate from generated files.
   - Prefer editing a JSON spec or script and regenerating rather than hand-patching many coordinates.
   - For destructive edits to native CAD files, save a copy/backup first unless the user explicitly requests in-place modification.

## Quick commands

Electrical SLD:

```powershell
python scripts/make_main_sld.py examples/electrical_sld_spec.json --outdir output/sld --stem main_sld
```

Pavement structure DXF:

```powershell
python scripts/generate_pavement_cad_ezdxf.py examples/pavement_structure_spec.json --out output/pavement
```

Open a generated CAD file in AutoCAD when configured:

```powershell
& $env:AUTOCAD_EXE "output\pavement\pavement_structure.dxf"
```

Start a local SolidWorks MCP server for diagnostics when installed:

```powershell
Set-Location -LiteralPath $env:SOLIDWORKS_MCP_HOME
& ".\.venv\Scripts\python.exe" -m solidworks_mcp.server
```

## Verification rules

Before final response on any CAD deliverable:

- Confirm every requested output file exists and is non-empty.
- For DXF, validate with `ezdxf.readfile` when possible.
- For PDF/SVG/PNG, render or inspect the latest preview when visual layout matters.
- For SolidWorks, require live rebuild/status evidence plus saved native/export files; mock-mode MCP results are not engineering truth.
- Report exact paths and any assumptions about units, dimensions, standards, topology, or missing source data.

## Bundled resources

- `scripts/make_main_sld.py` — parameterized electrical main single-line diagram generator; outputs DXF/PDF/SVG.
- `scripts/generate_pavement_cad_ezdxf.py` — lightweight pavement structure DXF generator using `ezdxf`.
- `scripts/generate_pavement_cad.py` — dependency-light fallback pavement CAD generator.
- `scripts/audit_sld.py` — generic DXF audit helper for generated SLD drawings.
- `references/local-cad-environment.md` — environment variables, tool discovery, and MCP status checks.
- `references/electrical-main-sld.md` — SLD workflow, symbols, topology, checks.
- `references/pavement-structure-cad.md` — pavement JSON schema and workflow.
- `references/solidworks-mcp.md` — SolidWorks MCP, COM/VBA fallback, verification.
- `references/autocad-freecad.md` — AutoCAD/Core Console and FreeCAD notes.

