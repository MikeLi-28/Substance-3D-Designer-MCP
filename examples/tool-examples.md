# Tool examples

Read the active graph first, then reuse its structured `graph` object:

```json
{"name":"sd_get_active_graph","arguments":{}}
```

Create a verified atomic node without connecting it:

```json
{
  "name": "sd_create_node",
  "arguments": {
    "graph": {
      "package_url": "file:///C:/materials/demo.sbs",
      "graph_identifier": "main",
      "graph_type": "substance"
    },
    "definition_id": "sbs::compositing::uniform",
    "position": [0.0, 0.0]
  }
}
```

Delete explicit nodes only after reviewing them:

```json
{
  "name": "sd_delete_nodes",
  "arguments": {
    "graph": {
      "package_url": "file:///C:/materials/demo.sbs",
      "graph_identifier": "main",
      "graph_type": "substance"
    },
    "node_identifiers": ["node-id-from-a-read-tool"],
    "confirm": true
  }
}
```

Create an Output node with metadata that is actually written into Designer:

```json
{
  "name": "sd_create_graph_output",
  "arguments": {
    "graph": {
      "package_url": "file:///C:/materials/demo.sbs",
      "graph_identifier": "main",
      "graph_type": "substance"
    },
    "identifier": "basecolor",
    "label": "Base Color",
    "description": "Material base color",
    "group": "Material",
    "usages": [
      {"name": "baseColor", "components": "RGBA", "color_space": "sRGB"}
    ],
    "position": [640.0, 0.0]
  }
}
```

Dry-run an additive patch before applying the identical payload:

```json
{
  "name": "sd_validate_graph_patch",
  "arguments": {
    "graph": {
      "package_url": "file:///C:/materials/demo.sbs",
      "graph_identifier": "main",
      "graph_type": "substance"
    },
    "patch": {
      "version": "1.0",
      "nodes": [
        {
          "alias": "source",
          "kind": "atomic",
          "definition_id": "sbs::compositing::uniform",
          "position": [0.0, 0.0]
        }
      ],
      "parameters": [],
      "connections": []
    }
  }
}
```

Identifiers and URLs shown here are illustrative. Never guess them in a real session; obtain them
from the read and search tools.
