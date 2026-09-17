from pathlib import Path

from diagrams import Cluster, Diagram, Edge
from diagrams.k8s.compute import Pod
from diagrams.k8s.network import Service
from diagrams.onprem.client import Users
from diagrams.onprem.container import Docker
from diagrams.onprem.database import PostgreSQL


ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / "assets" / "arquitectura-hibrida"

graph_attr = {
    "bgcolor": "white",
    "pad": "0.35",
    "ranksep": "0.75",
    "nodesep": "0.5",
    "fontname": "Arial",
    "fontsize": "18",
}
node_attr = {"fontname": "Arial", "fontsize": "12"}
edge_attr = {"fontname": "Arial", "fontsize": "10", "color": "#1E7A57"}


with Diagram(
    "Banco Choco - arquitectura hibrida",
    filename=str(OUTPUT),
    outformat="png",
    show=False,
    direction="LR",
    graph_attr=graph_attr,
    node_attr=node_attr,
    edge_attr=edge_attr,
):
    users = Users("Navegador")

    with Cluster("AWS - EC2 publica - Docker Compose"):
        frontend = Docker("Frontend + BFF")

    with Cluster("Tailnet privada"):
        tailnet = Service("Tailscale")

    with Cluster("Kubernetes local"):
        service = Service("bank-core")
        pods = [Pod("core 1"), Pod("core 2")]
        database = PostgreSQL("PostgreSQL + PVC")

    users >> Edge(label="HTTP :80", color="#1E7A57") >> frontend
    frontend >> Edge(label="API privada", color="#6F42C1") >> tailnet
    tailnet >> service
    service >> pods
    pods >> Edge(label="SQL", color="#31465F") >> database
