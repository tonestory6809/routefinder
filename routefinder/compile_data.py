"""
Compile Aerosoft navigraph data.
$ python -m routefinder.compile_data <Path of Navigraph data for Aerosoft>
>>> from routefinder.compile_data import DataCompiler
"""

import pickle
import csv
import sys
import os
from typing import Iterable, Literal, Optional, List, Tuple, Dict
from haversine import haversine, Unit
from tqdm import tqdm
from dijkstar import Graph
from .libraries import (
    DataCorruptionError,
    Geohash,
    AirportInfo,
    AirportProcedure,
    DataNotReadyError,
    InfoData,
    GraphData,
    HashedNodeInfo,
    NodeInfo,
    Position,
    AlreadyReadError,
    ReadOrderError,
)


__all__ = ["DataCompiler"]


class DataCompiler:
    """
    Data compile helper.

    Attributes
    ----------
    asdata_path : str
        Path of asdata navigraph data.
    log : bool
        Print log.
    graph : Graph
        Dijkstar graph.
    airport_info : Dict[str, AirportInfo]
        Information for all airports.
    node_info : Dict[str, HashedNodeInfo]
        Information for all nodes.
    """

    asdata_path: str
    log: bool
    graph: Graph = Graph()
    node_info: Dict[str, HashedNodeInfo] = {}
    airport_info: Dict[str, AirportInfo] = {}
    _navaid_frequency: Dict[str, float] = {}
    _navaids_read: bool = False
    _edge_read: bool = False
    _airport_read: bool = False

    def __init__(self, asdata_path: str, log: bool) -> None:
        """
        Create a DataCompiler instance.

        Parameters
        ----------
        asdata_path : str
            Path of asdata navigraph data.
        log : bool
            Print log.
        """
        self.asdata_path = asdata_path
        self.log = log

    @staticmethod
    def get_distance(position1: Position, position2: Position) -> float:
        """Calculate distance between two nodes.

        Parameters
        ----------
        position1 : Position
            Position of first node.
        position2 : Position
            Position of second node.

        Returns
        -------
        float
            Distance between two nodes.
        """
        return haversine(position1, position2, unit=Unit.NAUTICAL_MILES)

    def get_graph_data(self) -> GraphData:
        """Get graph data.

        Returns
        -------
        GraphData
            Graph data.
        """
        if not self._edge_read or not self._airport_read:
            raise DataNotReadyError("Haven't read edges and airports yet.")
        return self.graph.get_data()

    def get_info_data(self) -> InfoData:
        """Get info data.

        Returns
        -------
        InfoData
            Info data.
        """
        if not self._edge_read or not self._airport_read:
            raise DataNotReadyError("Haven't read edges and airports yet.")
        return {"airports": self.airport_info, "nodes": self.node_info}

    def compile(self) -> None:
        """Read all data."""
        self.read_navaids()
        self.read_edge()
        self.read_airport()

    def read_navaids(self) -> None:
        """Read navaids frequency."""
        lines: List[str]
        navaids_iter: Iterable
        if self._navaids_read:
            raise AlreadyReadError("Navaids already read.")
        if self.log:
            print("Reading navaids")
        with open(os.path.join(self.asdata_path, "Navaids.txt"), "r") as navaids_file:
            lines = navaids_file.readlines()
        if self.log:
            navaids_iter = tqdm(csv.reader(lines), total=len(lines), unit="navaid")
        else:
            navaids_iter = iter(lines)
        for row in navaids_iter:
            navaid_hashed_position = Geohash.hash((float(row[6]), float(row[7])))
            self._navaid_frequency[navaid_hashed_position] = float(row[2])
        self._navaids_read = True

    def read_edge(self) -> None:
        """Read edges."""
        if self._edge_read:
            raise AlreadyReadError("Edge already read.")
        if not self._navaids_read:
            raise ReadOrderError("The navaids must be read before the edge reading.")
        if self.log:
            print("Reading edge")
        edgename: Optional[str] = None
        with open(os.path.join(self.asdata_path, "ATS.txt"), "r") as ats_file:
            ats_lines: List[str] = ats_file.read().splitlines()
        if self.log:
            ats_iter = tqdm(csv.reader(ats_lines), total=len(ats_lines), unit="edge")
        else:
            ats_iter = csv.reader(ats_lines)
        for row in ats_iter:
            if not row:
                continue
            if row[0] == "A":
                edgename = row[1]
                continue
            if row[0] == "S":
                if edgename is None:
                    raise DataCorruptionError("ATS.txt is corrupted.")
                start_point_name: str = row[1]
                start_point_hashed_position: str = Geohash.hash(
                    (float(row[2]), float(row[3]))
                )
                start_point_frequency: Optional[float] = None
                if start_point_hashed_position in self._navaid_frequency:
                    start_point_frequency = self._navaid_frequency[
                        start_point_hashed_position
                    ]
                end_point_name: str = row[4]
                end_point_hashed_position: str = Geohash.hash(
                    (float(row[5]), float(row[6]))
                )
                end_point_frequency: Optional[float] = None
                if end_point_hashed_position in self._navaid_frequency:
                    end_point_frequency = self._navaid_frequency[
                        end_point_hashed_position
                    ]
                distance: float = float(row[9])
                # TODO: heading is row[7] or row[8]? inbound? outbound?
                # heading: int = int(row[7] if row[7] != '0' else row[8])
                self.graph.add_edge(
                    start_point_hashed_position,
                    end_point_hashed_position,
                    (distance, edgename),
                )
                self.node_info[start_point_hashed_position] = {
                    "name": start_point_name,
                    "frequency": start_point_frequency,
                }
                self.node_info[end_point_hashed_position] = {
                    "name": end_point_name,
                    "frequency": end_point_frequency,
                }
        self._edge_read = True

    def read_airport(self):
        """Read airports."""
        invaild_procedure_type: List[str] = [
            "CA",
            "CD",
            "CI",
            "CR",
            "VA",
            "VD",
            "VI",
            "VM",
            "VR",
        ]
        if self._airport_read:
            raise AlreadyReadError("Airport already read.")
        if self.log:
            print("Reading airport sid & star")
        # Airport block:
        # A,airport icao,airport name,lat,lng
        # SID or STAR......,(too long to write, go see for yourself)
        for home, _, files in os.walk(os.path.join(self.asdata_path, "proc")):
            if self.log:
                files_iter = tqdm(files, position=0, unit="airport")
            else:
                files_iter = iter(files)
            for filename in files_iter:
                ap_icao: Optional[str] = None
                ap_position: Tuple[float, float] = (0.0, 0.0)
                ap_sid: Dict[str, List[AirportProcedure]] = {}
                ap_star: Dict[str, List[AirportProcedure]] = {}
                blocks: List[str]
                block_iter: Iterable
                if not filename.endswith(".txt"):
                    continue
                with open(os.path.join(home, filename), "r") as ap_file:
                    blocks = ap_file.read().split("\n\n")
                if self.log:
                    block_iter = tqdm(blocks, position=1, leave=False, unit="procedure")
                else:
                    block_iter = iter(blocks)
                for block in block_iter:
                    if not block:
                        continue
                    lines: List[str] = block.splitlines()
                    if lines[0].startswith("A,"):
                        split_line: List[str] = lines[0].split(",")
                        ap_icao = split_line[1]
                        ap_position = (float(split_line[3]), float(split_line[4]))
                        continue
                    if lines[0].startswith("SID,") or lines[0].startswith("STAR,"):
                        proc_type: Literal["SID", "STAR"] = (
                            "SID" if lines[0].startswith("SID,") else "STAR"
                        )
                        proc_nodes: List[NodeInfo] = []
                        _, proc_name, proc_runway, _ = lines[0].split(",")
                        if ap_icao is None:
                            raise DataCorruptionError(f"proc/{filename} is corrupted.")
                        for row in csv.reader(lines):
                            if (
                                row[0] == "SID"
                                or row[0] == "STAR"
                                or row[0] in invaild_procedure_type
                            ):
                                continue
                            node_position: Position = (float(row[2]), float(row[3]))
                            node_frequency: Optional[float] = None
                            node_hashed_position: str = Geohash.hash(node_position)
                            if node_hashed_position in self._navaid_frequency:
                                node_frequency = self._navaid_frequency[
                                    node_hashed_position
                                ]
                            proc_nodes.append(
                                {
                                    "name": row[1],
                                    "position": node_position,
                                    "frequency": node_frequency,
                                }
                            )
                        # If this SID/STAR procedure has no nodes,
                        # it is invalid
                        if len(proc_nodes) != 0:
                            if proc_type == "SID":
                                last_node: NodeInfo = proc_nodes[-1]
                                last_node_name: str = last_node["name"]
                                last_node_position: Position = last_node["position"]
                                if last_node_name not in ap_sid:
                                    last_node_hashed_position = Geohash.hash(
                                        last_node_position
                                    )
                                    last_node_frequency = last_node["frequency"]
                                    if last_node_hashed_position not in self.node_info:
                                        self.node_info[last_node_hashed_position] = {
                                            "name": last_node_name,
                                            "frequency": (last_node_frequency),
                                        }
                                    ap_sid[last_node_name] = []
                                    self.graph.add_edge(
                                        ap_icao,
                                        Geohash.hash(last_node_position),
                                        (
                                            self.get_distance(
                                                ap_position, last_node_position
                                            ),
                                            proc_type,
                                        ),
                                    )
                                ap_sid[last_node_name].append(
                                    {
                                        "name": proc_name,
                                        "runway": proc_runway,
                                        "nodes": proc_nodes,
                                    }
                                )
                            else:
                                first_node: NodeInfo = proc_nodes[0]
                                first_node_name: str = first_node["name"]
                                first_node_position: Position = first_node["position"]
                                if first_node_name not in ap_star:
                                    first_node_hashed_position = Geohash.hash(
                                        first_node_position
                                    )
                                    first_node_frequency = first_node["frequency"]
                                    if first_node_hashed_position not in self.node_info:
                                        self.node_info[first_node_hashed_position] = {
                                            "name": first_node_name,
                                            "frequency": first_node_frequency,
                                        }
                                    ap_star[first_node_name] = []
                                    self.graph.add_edge(
                                        Geohash.hash(first_node_position),
                                        ap_icao,
                                        (
                                            self.get_distance(
                                                ap_position, first_node_position
                                            ),
                                            proc_type,
                                        ),
                                    )
                                ap_star[first_node_name].append(
                                    {
                                        "name": proc_name,
                                        "runway": proc_runway,
                                        "nodes": proc_nodes,
                                    }
                                )

                        continue
                if ap_icao is not None:
                    self.node_info[Geohash.hash(ap_position)] = {
                        "name": ap_icao,
                        "frequency": None,
                    }
                    self.airport_info[ap_icao] = {
                        "position": ap_position,
                        "sid": ap_sid,
                        "star": ap_star,
                    }
        self._airport_read = True


if __name__ == "__main__":
    args = sys.argv[1:]
    if len(args) != 1:
        print(
            "Usage: python -m routefinder.compile_data",
            "<Path of Navigraph data for Aerosoft>",
        )
    else:
        dataCompiler = DataCompiler(args[0], True)
        dataCompiler.compile()
        print("Saving....")
        with open(os.path.join(os.getcwd(), "graph.pickle"), "wb") as graph_file:
            pickle.dump(dataCompiler.get_graph_data(), graph_file)
        with open(os.path.join(os.getcwd(), "info.pickle"), "wb") as info_file:
            pickle.dump(dataCompiler.get_info_data(), info_file)
        print("Saved graph.pickle and info.pickle.")
