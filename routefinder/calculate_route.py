"""
Route calculater.
>>> from routefinder.calculate_data import RouteCalculater
"""
from typing import List, Optional, Callable
from geolib import geohash
from dijkstar import Graph, find_path
from dijkstar.algorithm import PathInfo, NoPathError
from .libraries import (
    GraphData,
    InfoData,
    Edge,
    NodeInfo,
    Position,
    RouteResult,
    NoResultError,
)

__all__ = ["RouteCalculater"]


def create_cost_func(
    dest: str,
) -> Callable[[str, str, Edge, Edge], float]:
    """
    Create a cost function.

    Parameters
    ----------
    dest : str
        Dest node name.

    Returns
    -------
    Callable[[str, str, Edge, Edge], float]
        The cost function.
    """

    def cost_func(_: str, next_node: str, edge: Edge, __: Edge) -> float:
        if len(next_node) == 4 and next_node != dest:
            return float("inf")
        return edge[0]

    return cost_func


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

    graph: Graph
    info_data: InfoData

    def __init__(self, graph_data: GraphData, info_data: InfoData) -> None:
        self.graph = Graph()
        self.graph._data = graph_data
        self.info_data = info_data

    @staticmethod
    def unhash(hashed_position: str) -> Position:
        """
        Unhash geohashed position.

        Parameters
        ----------
        hashed_position : str
            Geohashed position.

        Returns
        -------
        Position
            Position.
        """
        lat, lon = geohash.decode(hashed_position)
        return (round(float(lat), 6), round(float(lon), 6))

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
            path = find_path(self.graph, orig, dest, cost_func=create_cost_func(dest))
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
                node_position = self.unhash(nodename)
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
