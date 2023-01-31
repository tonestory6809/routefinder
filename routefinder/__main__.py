"""
Cli entry. Require that graph.pickle and info.pickle exist in the current directory.
Usage: python -m routefinder <ICAO of orig> <ICAO of dest>.
"""

import pickle
import sys
import os
from .calculate_route import RouteCalculater
from .libraries import InfoData, GraphData

__all__ = []

args = sys.argv[1:]
if len(args) != 2:
    print("Usage: python -m routefinder <ICAO of orig> <ICAO of dest>.")
else:
    graph_data: GraphData
    info_data: InfoData
    orig, dest = args
    try:
        with open(os.path.join(os.getcwd(), "graph.pickle"), "rb") as graph_file:
            graph_data = pickle.load(graph_file)
        with open(os.path.join(os.getcwd(), "info.pickle"), "rb") as info_file:
            info_data = pickle.load(info_file)
    except Exception as error:
        print(f"Unable to load data: {error}")
    else:
        routeCalculater = RouteCalculater(graph_data, info_data)
        print(routeCalculater.calculate(orig, dest))
