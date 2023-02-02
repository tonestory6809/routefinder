"""
Collection of types and errors.
"""
from typing import List, Optional, Tuple, Dict, TypedDict, NamedTuple
from geolib import geohash

# Tuple[Distance, Way]
Edge = Tuple[float, str]
# Dict[HashedPosition, Dict[HashedPosition, Edge]]
GraphData = Dict[str, Dict[str, Edge]]
# Tuple[Latitude, Longitude]
Position = Tuple[float, float]


__all__ = [
    "Edge",
    "GraphData",
    "Position",
    "HashedNodeInfo",
    "NodeInfo",
    "AirportProcedure",
    "AirportInfo",
    "InfoData",
    "RouteResult",
    "RouteFinderError",
    "NodeNotFoundError",
    "NoResultError",
    "DataNotReadyError",
    "ReadOrderError",
    "AlreadyReadError",
    "DataCorruptionError",
    "MiscellaneousError",
]


class Geohash:
    @staticmethod
    def hash(position: Position) -> str:
        """
        Hash position into geohash.

        Parameters
        ----------
        position : Position
            Position to hash.

        Returns
        -------
        str
            Geohashed position.
        """
        return geohash.encode(*position, 9)

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


class HashedNodeInfo(TypedDict):
    """
    Information about a waypoint or navaid with hashed position.

    Attributes
    ----------
    name : str
        Name of the node.
    frequency : float, optional
        Frequency of navaid. (None if the node isn't a navaid.)
    """

    name: str
    frequency: Optional[float]


class NodeInfo(HashedNodeInfo):
    """
    Information about a waypoint or navaid.

    Attributes
    ----------
    position : Position
        Position of this node.
    name : str
        Name of the node.
    frequency : float, optional
        Frequency of navaid. (None if the node isn't a navaid.)
    """

    position: Position


class AirportProcedure(TypedDict):
    """
    Information about a SID/STAR procedure.

    Attributes
    ----------
    name : str
        Name of the procedure.
    runway : str
        The runway used by the procedure.
    nodes : List[NodeInfo]
        All nodes of the procedure.
    """

    name: str
    runway: str
    nodes: List[NodeInfo]


class AirportInfo(TypedDict):
    """
    Information about an airport.

    Attributes
    ----------
    position : Position
        Position of this airport.
    sid : Dict[str, List[AirportProcedure]]
        Information on all SID procedures at the airport.
    star : Dict[str, List[AirportProcedure]]
        Information on all STAR procedures at the airport.
    """

    position: Position
    # Dict[EntryPoint, List[AirportProcedure]]
    sid: Dict[str, List[AirportProcedure]]
    # Dict[ExitPoint, List[AirportProcedure]]
    star: Dict[str, List[AirportProcedure]]


class InfoData(TypedDict):
    """
    Collection of airports and waypoints information.

    Attributes
    ----------
    airports : Dict[str, AirportInfo]
        Information for all airports.
    nodes : Dict[str, HashedNodeInfo]
        Information for all nodes.
    """

    # Dict[AirportICAO, AirportInfo]
    airports: Dict[str, AirportInfo]
    # Dict[HashedPosition, HashedNodeInfo]
    nodes: Dict[str, HashedNodeInfo]


class RouteResult(NamedTuple):
    """
    Route calculation results.

    Attributes
    ----------
    display_route : List[str]
        Route for input to the flight computer.
    distance : float
        Distance of the route.
    nodes_info : List[NodeInfo]
        Information on all nodes used by the route.
    sid : Dict[str, List[AirportProcedure]]
        Information on all SID procedures at the departure airport.
    star : Dict[str, List[AirportProcedure]]
        Information on all STAR procedures at the arrival airport.
    """

    # List[Node | Edge]
    display_route: List[str]
    # In nautical miles
    distance: float
    nodes_info: List[NodeInfo]
    sid: Dict[str, List[AirportProcedure]]
    star: Dict[str, List[AirportProcedure]]


class RouteFinderError(Exception):
    """Base error of Routefinder."""


class NodeNotFoundError(RouteFinderError):
    """Unable to find node."""


class NoResultError(RouteFinderError):
    """Unable to find path."""


class DataNotReadyError(RouteFinderError):
    """Data not ready.
    Probably because not all the data has been compiled yet."""


class ReadOrderError(RouteFinderError):
    """The order of reading data is wrong."""


class AlreadyReadError(RouteFinderError):
    """A part of data already read."""


class DataCorruptionError(RouteFinderError):
    """Data is corruption."""


class MiscellaneousError(RouteFinderError):
    """Miscellaneous errors."""
