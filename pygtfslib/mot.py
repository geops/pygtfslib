from functools import lru_cache
import typing


GEOPS_TRAM = "tram"
GEOPS_SUBWAY = "subway"
GEOPS_RAIL = "rail"
GEOPS_BUS = "bus"
GEOPS_FERRY = "ferry"
GEOPS_CABLECAR = "cablecar"
GEOPS_GONDOLA = "gondola"
GEOPS_FUNICULAR = "funicular"
GEOPS_COACH = "coach"


SIMPLE_ROUTE_TYPE_TO_MOT: typing.Dict[int, str] = {
    0: GEOPS_TRAM,
    1: GEOPS_SUBWAY,
    2: GEOPS_RAIL,
    3: GEOPS_BUS,
    4: GEOPS_FERRY,
    5: GEOPS_CABLECAR,
    6: GEOPS_GONDOLA,
    7: GEOPS_FUNICULAR,
    200: GEOPS_COACH,
}


@lru_cache(maxsize=512)
def route_type_to_mot(
    route_type: int, fallback: typing.Optional[str] = None
) -> typing.Optional[str]:
    """Return geOps routing API mot from GTFS (extended) route type

    https://developers.google.com/transit/gtfs/reference/extended-route-types
    """
    if 100 <= route_type <= 117 or route_type == 1503:
        route_type = 2
    elif 200 <= route_type <= 209:
        route_type = 200
    elif 400 <= route_type <= 405:
        route_type = 1
    elif 700 <= route_type <= 716 or route_type in {1500, 1501, 1505, 1506, 1507}:
        route_type = 3
    elif 900 <= route_type <= 906:
        route_type = 0
    elif route_type in {1000, 1200, 1502}:
        route_type = 4
    elif route_type == 1300:
        route_type = 6
    elif route_type == 1400:
        route_type = 7
    return SIMPLE_ROUTE_TYPE_TO_MOT.get(route_type) or fallback
