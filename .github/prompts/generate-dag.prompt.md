---
name: Generate DAG
description: Generate the DAG from tasks.md or run the skf dag command.
agent: SpecKitFlow Implementation Agent
---

# Generate DAG

@speckit-flow Help me generate the DAG.

## Request

{{input}}

## Actions

Depending on implementation status:

### If `skf dag` is implemented:
Run the command to generate `specs/{branch}/dag.yaml`

### If not yet implemented:
1. Parse `specs/speckit-flow/tasks.md` manually
2. Extract task IDs, dependencies, and parallelization markers
3. Show the dependency graph structure
4. Identify parallel execution phases

Show the resulting phase breakdown with tasks grouped by execution order.
