from routefinder.compile_data import DataCompiler
from routefinder.calculate_route import RouteCalculater
from routefinder.libraries import GraphData, InfoData

graph_data: GraphData
info_data: InfoData


def test_compile():
    global graph_data, info_data
    print()
    compiler = DataCompiler("/tmp/navigraph_for_aerosoft_ONLY_FOR_TEST", True)
    compiler.compile()
    graph_data = compiler.get_graph_data()
    info_data = compiler.get_info_data()


def test_calculate_short_route():
    global graph_data, info_data
    print()
    calculater = RouteCalculater(graph_data, info_data)
    result = calculater.calculate("ZSFZ", "ZSPD")
    assert result.display_route == [
        "ZSFZ",
        "SID",
        "DST",
        "B221",
        "PAMVU",
        "V74",
        "BK",
        "STAR",
        "ZSPD",
    ]
