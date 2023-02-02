"""
Route calculater.
>>> from routefinder.calculate_data import RouteCalculater
"""
from typing import List, Dict, Optional
from dijkstar import Graph, find_path
from dijkstar.algorithm import PathInfo, NoPathError
from .libraries import (
    AirportInfo,
    DataCorruptionError,
    Geohash,
    GraphData,
    HashedNodeInfo,
    InfoData,
    Edge,
    MiscellaneousError,
    NodeInfo,
    NodeNotFoundError,
    Position,
    RouteResult,
    NoResultError,
)

__all__ = ["CostFunc", "RouteCalculater"]


class CostFunc:
    """
    Classify cost function.

    Attributes
    ----------
    dest : str
        The name or geohashed position of the dest node.
    dest_is_airport : bool
        Whether the dest node is an airport.
    sid_node : str, optional
        Restrict exit node for departure airport's SID.
    sid_node : str, optional
        Restrict entry node for arrival airport's STAR.
    """

    dest: str
    dest_is_airport: bool
    sid_node: Optional[str]
    star_node: Optional[str]

    def __init__(
        self,
        orig: str,
        dest: str,
        sid_node: Optional[str] = None,
        star_node: Optional[str] = None,
    ) -> None:
        """
        Create a CostFunc instance.

        Parameters
        ----------
        orig : str
            The name or geohashed position of the orig node.
        dest : str
            The name or geohashed position of the dest node.
        sid_node : str, optional
            Specify exit node for departure airport.
        star_node : str, optional
            Specify entry node for arrival airport.
        """
        if len(orig) != 4 and sid_node is not None:
            raise MiscellaneousError("Cannot specify exit node for non-airport.")
        if len(dest) != 4 and star_node is not None:
            raise MiscellaneousError("Cannot specify entry node for non-airport.")
        self.dest = dest
        self.dest_is_airport = len(dest) == 4
        self.sid_node = sid_node
        self.star_node = star_node

    def __call__(self, prev_node: str, next_node: str, edge: Edge, __: Edge) -> float:
        """
        The "cost func".

        Parameters
        ----------
        prev_node : str
            The name or geohashed position of the prev node.
        next_node : str
            The name or geohashed position of the next node.
        edge : Edge
            Edge from prev_node to next_node.
        prev_edge : Edge
            Edge from node before prev_node to prev_node.
        """
        distance, edgename = edge
        if edgename == "SID" and self.sid_node is not None:
            if not next_node == self.sid_node:
                return float("inf")
        elif edgename == "STAR":
            if not self.dest_is_airport:
                return float("inf")
            elif next_node != self.dest:
                return float("inf")
            elif self.star_node is not None and self.star_node != prev_node:
                return float("inf")
        return distance


class RouteCalculater:
    """
    Route calculater.

    Attributes
    ----------
    graph : Graph
        Dijkstar graph.
    info_data : InfoData
        Information for all airports and nodes.
    """

    graph: Graph = Graph()
    info_data: InfoData

    def __init__(self, graph_data: GraphData, info_data: InfoData) -> None:
        """
        Create a RouteCalculater instance.

        Parameters
        ----------
        graph_data : GraphData
            Dijkstar graph data.
        info_data : InfoData
            Information for all airports and nodes.
        """
        if not list(info_data.keys()) == ["airports", "nodes"]:
            raise DataCorruptionError("Info data is corrupted.")
        self.graph._data = graph_data
        self.info_data = info_data

    def get_airport_info(self, icao: str) -> AirportInfo:
        """
        Get info of specified airport.

        Parameters
        ----------
        icao : str
            ICAO of airport.

        Returns
        -------
        AirportInfo
            Info of airport.
        """
        if icao not in self.info_data["airports"]:
            raise NodeNotFoundError(f"Cannot find airport {icao}.")
        return self.info_data["airports"][icao]

    def find_node(self, name: str) -> Dict[str, HashedNodeInfo]:
        """
        Find node by name.

        Parameters
        ----------
        name : str

        Returns
        -------
        Dict[str, HashedNodeInfo]
            Dict of result. str is geohashed position.
        """
        result: Dict[str, HashedNodeInfo] = {}
        for hashed_position in self.info_data["nodes"]:
            node = self.info_data["nodes"][hashed_position]
            if node["name"] == name:
                result[hashed_position] = node
        if len(result) == 0:
            raise NodeNotFoundError(f"Cannot find node {name}.")
        return result

    def calculate(self, orig: str, dest: str) -> RouteResult:
        """
        Calculate route.

        Parameters
        ----------
        orig : str
            ICAO of departure airport.
        dest : str
            ICAO of arrival airport.

        Returns
        -------
        RouteResult
            Result of route.
        """
        if (
            orig not in self.info_data["airports"]
            or dest not in self.info_data["airports"]
        ):
            raise NoResultError("Airport not found.")
        path: Optional[PathInfo] = None
        try:
            path = find_path(
                self.graph, orig, dest, cost_func=CostFunc(orig, dest, None, None)
            )
        except NoPathError:
            pass
        if not path or path.total_cost == float("inf"):
            raise NoResultError(f"Unable to find a path from {orig} to {dest}.")
        display_route: List[str] = []
        prev_edgename: str = ""
        full_nodes: List[NodeInfo] = []
        for i, nodename in enumerate(path.nodes):
            edgename: Optional[str]
            try:
                _, edgename = path.edges[i]
            except IndexError:
                edgename = None
            nodename_length: int = len(nodename)
            node_position: Position = (0, 0)
            node_frequency: Optional[float] = None
            if nodename_length == 4:
                if nodename in (orig, dest):
                    node_position = self.info_data["airports"][nodename]["position"]
                elif nodename == "STAR":
                    pass
                else:
                    raise KeyError("Unexpected node:", nodename)
            elif nodename == "SID":
                pass
            elif nodename_length == 9:
                node = self.info_data["nodes"][nodename]
                node_position = Geohash.unhash(nodename)
                node_frequency = node["frequency"]
                nodename = node["name"]
            else:
                raise KeyError("Unexpected node:", nodename)
            if edgename != prev_edgename:
                display_route.append(nodename)
                if edgename is not None:
                    display_route.append(edgename)
                    prev_edgename = edgename
            if nodename not in ["SID", "STAR"]:
                full_nodes.append(
                    {
                        "position": node_position,
                        "name": nodename,
                        "frequency": node_frequency,
                    }
                )
        return RouteResult(
            display_route,
            path.total_cost,
            full_nodes,
            self.info_data["airports"][orig]["sid"],
            self.info_data["airports"][dest]["star"],
        )
