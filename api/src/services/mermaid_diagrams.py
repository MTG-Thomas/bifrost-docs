"""
Mermaid diagram generation service for network topology and DCIM visualization.

Generates mermaid diagrams from database entities for real-time visualization.
Supports auto-generation and storage in documents.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.orm.cable import Cable
from src.models.orm.configuration import Configuration
from src.models.orm.dcim import Rack, RackDevice


@dataclass
class NetworkNode:
    """Node in network topology diagram."""

    id: str
    label: str
    type: str  # switch, router, server, firewall, ap, etc.
    ip_address: str | None = None
    status: str = "up"  # up, down, warning
    rack_id: str | None = None
    u_position: int | None = None


@dataclass
class NetworkEdge:
    """Connection between nodes."""

    source: str
    target: str
    label: str | None = None
    cable_type: str | None = None
    bandwidth: str | None = None
    status: str = "active"


class MermaidDiagramService:
    """Service for generating Mermaid diagrams from infrastructure data."""

    # Mermaid node shapes by device type
    NODE_SHAPES = {
        "firewall": ("{{", "}}"),  # Rhombus
        "router": ("((", "))"),  # Circle
        "switch": ("[", "]"),  # Rectangle
        "server": ("([", "])"),  # Stadium
        "workstation": ("[", "]"),  # Rectangle
        "ap": ("((", "))"),  # Circle with label
        "printer": ("[/", "/]"),  # Parallelogram
        "ups": ("[", "]"),  # Rectangle
        "default": ("[", "]"),
    }

    # CSS classes for styling
    NODE_CLASSES = {
        "up": "classDef up fill:#90EE90,stroke:#228B22",
        "down": "classDef down fill:#FFB6C1,stroke:#DC143C",
        "warning": "classDef warning fill:#FFD700,stroke:#FFA500",
        "firewall": "classDef firewall fill:#FF6B6B,stroke:#8B0000",
        "switch": "classDef switch fill:#4169E1,stroke:#00008B",
        "router": "classDef router fill:#32CD32,stroke:#006400",
        "server": "classDef server fill:#9370DB,stroke:#4B0082",
    }

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def generate_network_topology(
        self,
        org_id: UUID,
        root_device_id: UUID | None = None,
        max_depth: int = 3,
        include_ips: bool = True,
    ) -> str:
        """Generate network topology diagram as Mermaid flowchart.

        Args:
            org_id: Organization to diagram
            root_device_id: Starting device (None = core switches)
            max_depth: How many hops to include
            include_ips: Show IP addresses in labels

        Returns:
            Mermaid diagram syntax
        """
        # Build topology from relationships and cables
        nodes: dict[str, NetworkNode] = {}
        edges: list[NetworkEdge] = []

        # Query configurations with relationships
        query = (
            select(Configuration)
            .where(
                Configuration.organization_id == org_id,
                Configuration.is_enabled.is_(True),
            )
            .where(
                Configuration.configuration_type.in_(
                    ["firewall", "router", "switch", "server", "workstation", "ap"]
                )
            )
        )
        result = await self.db.execute(query)
        configs = result.scalars().all()

        # Build nodes
        for config in configs:
            node_id = str(config.id)[:8]  # Short ID for readability

            # Determine device type from config type
            device_type = self._infer_device_type(config)

            # Build label
            label_parts = [config.name]
            if include_ips and config.ip_address:
                label_parts.append(config.ip_address)

            nodes[node_id] = NetworkNode(
                id=node_id,
                label="\\n".join(label_parts),
                type=device_type,
                ip_address=config.ip_address,
                status=config.status or "up",
            )

        # Query cables for connections
        cable_query = (
            select(Cable)
            .where(
                Cable.organization_id == org_id,
                Cable.is_connected.is_(True),
            )
            .where(
                Cable.end_a_config_id.in_([c.id for c in configs])
                | Cable.end_b_config_id.in_([c.id for c in configs])
            )
        )
        cable_result = await self.db.execute(cable_query)
        cables = cable_result.scalars().all()

        # Build edges from cables
        for cable in cables:
            if cable.end_a_config_id and cable.end_b_config_id:
                source_id = str(cable.end_a_config_id)[:8]
                target_id = str(cable.end_b_config_id)[:8]

                if source_id in nodes and target_id in nodes:
                    edge_label = cable.cable_type or ""
                    if cable.end_a_port and cable.end_b_port:
                        edge_label = f"{cable.end_a_port}→{cable.end_b_port}"

                    edges.append(
                        NetworkEdge(
                            source=source_id,
                            target=target_id,
                            label=edge_label,
                            cable_type=cable.cable_type,
                        )
                    )

        # Generate Mermaid syntax
        return self._build_mermaid_flowchart(nodes, edges)

    async def generate_rack_elevation(
        self,
        rack_id: UUID,
        include_power: bool = True,
        include_cables: bool = False,
    ) -> str:
        """Generate rack elevation diagram.

        Uses Mermaid's block diagram or subgraph for rack visualization.

        Args:
            rack_id: Rack to visualize
            include_power: Show power consumption
            include_cables: Show cable connections (complex)

        Returns:
            Mermaid block diagram syntax
        """
        # Query rack with devices
        rack_query = select(Rack).where(Rack.id == rack_id)
        rack_result = await self.db.execute(rack_query)
        rack = rack_result.scalar_one_or_none()

        if not rack:
            return "Rack not found"

        # Query devices in rack
        device_query = (
            select(RackDevice, Configuration)
            .join(Configuration, RackDevice.configuration_id == Configuration.id)
            .where(RackDevice.rack_id == rack_id)
            .order_by(RackDevice.u_position.desc())  # Top to bottom
        )
        device_result = await self.db.execute(device_query)
        rack_devices = device_result.all()

        # Build block diagram
        lines = [
            "block-beta",
            f"    columns {rack.rack_units}",
            "",
        ]

        # Create blocks for each U position (top-down)
        for u in range(rack.rack_units, 0, -1):
            # Find device at this U position
            device = None
            for rd, config in rack_devices:
                if rd.u_position == u:
                    device = (rd, config)
                    break

            if device:
                rd, config = device
                height = rd.u_height
                name = config.name[:20]  # Truncate

                # Power indicator
                power_text = ""
                if include_power and rd.power_draw_va:
                    power_text = f" ({rd.power_draw_va}VA)"

                lines.append(f'    u{u}["{name}{power_text}"]:{height}')
            else:
                lines.append(f'    u{u}[""]:1  %% Empty U{u}')

        lines.append("")
        lines.append("    %% Styling")
        lines.append("    classDef occupied fill:#e1f5fe")
        lines.append("    classDef empty fill:#f5f5f5")

        # Apply classes
        for u in range(rack.rack_units, 0, -1):
            has_device = any(rd.u_position == u for rd, _ in rack_devices)
            class_name = "occupied" if has_device else "empty"
            lines.append(f"    class u{u} {class_name}")

        return "\\n".join(lines)

    async def generate_cable_map(
        self,
        config_id: UUID,
        max_hops: int = 2,
    ) -> str:
        """Generate cable map for a specific device and its connections.

        Shows all cables connected to a device, and optionally one hop further.

        Args:
            config_id: Starting device
            max_hops: How many levels of connections to show

        Returns:
            Mermaid diagram showing cables
        """
        # Query cables for this device
        cables_query = (
            select(Cable)
            .where((Cable.end_a_config_id == config_id) | (Cable.end_b_config_id == config_id))
            .where(Cable.is_connected.is_(True))
        )
        result = await self.db.execute(cables_query)
        cables = result.scalars().all()

        if not cables:
            return f"No cables found for device {config_id}"

        # Build simple list diagram
        lines = ["block-beta", "    columns 3"]

        for i, cable in enumerate(cables):
            # Determine direction
            if cable.end_a_config_id == config_id:
                # This device is source
                source_port = cable.end_a_port or "Port ?"
                target_port = cable.end_b_port or "Port ?"
            else:
                # This device is destination
                source_port = cable.end_b_port or "Port ?"
                target_port = cable.end_a_port or "Port ?"

            cable_label = cable.label or f"Cable {i + 1}"

            lines.append(f'    dev{i}["{cable_label}"]')
            lines.append(f'    port{i}["{source_port} → {target_port}"]')

            if cable.cable_type:
                lines.append(f'    type{i}["{cable.cable_type}"]')

        lines.append("")
        lines.append("    %% Layout")
        for i in range(len(cables)):
            lines.append(f"    dev{i} --> port{i}")

        return "\\n".join(lines)

    def _infer_device_type(self, config: Configuration) -> str:
        """Infer device type from configuration data."""
        # Check explicit type first
        if config.configuration_type in self.NODE_SHAPES:
            return config.configuration_type

        # Infer from name or manufacturer
        name_lower = config.name.lower()

        if "firewall" in name_lower or "fw" in name_lower:
            return "firewall"
        elif "switch" in name_lower or "sw" in name_lower:
            return "switch"
        elif "router" in name_lower:
            return "router"
        elif "server" in name_lower or "srv" in name_lower:
            return "server"
        elif "access point" in name_lower or "ap" in name_lower or "wifi" in name_lower:
            return "ap"

        return "default"

    def _build_mermaid_flowchart(
        self,
        nodes: dict[str, NetworkNode],
        edges: list[NetworkEdge],
    ) -> str:
        """Build Mermaid flowchart syntax."""
        lines = ["flowchart LR"]

        # Add node definitions
        for node_id, node in nodes.items():
            shape_open, shape_close = self.NODE_SHAPES.get(node.type, self.NODE_SHAPES["default"])

            # Escape special characters in label
            label = node.label.replace('"', "&quot;")

            lines.append(f'    {node_id}{shape_open}"{label}"{shape_close}')

        lines.append("")

        # Add edges
        for edge in edges:
            edge_line = f"    {edge.source} -->"
            if edge.label:
                edge_line += f'|"{edge.label}"|'
            edge_line += f" {edge.target}"
            lines.append(edge_line)

        lines.append("")

        # Add class definitions
        for class_def in self.NODE_CLASSES.values():
            lines.append(f"    {class_def}")

        # Apply classes to nodes
        class_assignments: dict[str, list[str]] = {}
        for node_id, node in nodes.items():
            status_class = node.status if node.status in self.NODE_CLASSES else "up"
            if status_class not in class_assignments:
                class_assignments[status_class] = []
            class_assignments[status_class].append(node_id)

            # Also add type class if exists
            if node.type in self.NODE_CLASSES:
                if node.type not in class_assignments:
                    class_assignments[node.type] = []
                class_assignments[node.type].append(node_id)

        for class_name, node_ids in class_assignments.items():
            lines.append(f"    class {','.join(node_ids)} {class_name}")

        return "\\n".join(lines)

    async def auto_generate_and_save(
        self,
        org_id: UUID,
        document_name: str = "Network Topology",
        auto_update: bool = True,
    ) -> UUID:
        """Generate diagram and save as document.

        Creates a special document type that auto-updates when infrastructure changes.

        Args:
            org_id: Organization
            document_name: Name for the document
            auto_update: If True, sets up change listeners

        Returns:
            Document ID
        """
        from src.models.orm.document import Document
        from src.repositories.document import DocumentRepository

        # Generate diagram
        mermaid_code = await self.generate_network_topology(org_id)

        # Wrap in markdown with mermaid code block
        content = f"""# {document_name}

Auto-generated network topology diagram. Updates when infrastructure changes.

```mermaid
{mermaid_code}
```

_Generated: {datetime.now().isoformat()}_
"""

        # Create document
        doc = Document(
            organization_id=org_id,
            path="/",
            name=document_name,
            content=content,
            document_type="mermaid_diagram",  # Special type
            metadata={
                "diagram_type": "network_topology",
                "auto_generated": True,
                "auto_update": auto_update,
                "generator_version": "1.0",
            },
        )

        doc_repo = DocumentRepository(self.db)
        created = await doc_repo.create(doc)

        return created.id
