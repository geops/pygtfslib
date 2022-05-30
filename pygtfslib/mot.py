from functools import lru_cache
import typing


T_MOT = typing.Literal[
    "tram",
    "subway",
    "rail",
    "bus",
    "ferry",
    "cablecar",
    "gondola",
    "funicular",
    "coach",
]


GEOPS_TRAM: T_MOT = "tram"
GEOPS_SUBWAY: T_MOT = "subway"
GEOPS_RAIL: T_MOT = "rail"
GEOPS_BUS: T_MOT = "bus"
GEOPS_FERRY: T_MOT = "ferry"
GEOPS_CABLECAR: T_MOT = "cablecar"
GEOPS_GONDOLA: T_MOT = "gondola"
GEOPS_FUNICULAR: T_MOT = "funicular"
GEOPS_COACH: T_MOT = "coach"


SIMPLE_ROUTE_TYPE_TO_MOT: typing.Dict[int, T_MOT] = {
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
    route_type: int, fallback: typing.Optional[T_MOT] = None
) -> typing.Optional[T_MOT]:
    """Return geOps routing API mot from GTFS (extended) route type

    https://developers.google.com/transit/gtfs/reference/extended-route-types
    """
    if 100 <= route_type <= 117:
        route_type = 2
    elif 200 <= route_type <= 209:
        route_type = 200
    elif 400 <= route_type <= 405:
        route_type = 1
    elif 700 <= route_type <= 716:
        route_type = 3
    elif 900 <= route_type <= 906:
        route_type = 0
    elif route_type == 1000 or route_type == 1200:
        route_type = 4
    elif route_type == 1300:
        route_type = 6
    elif route_type == 1400:
        route_type = 7
    return SIMPLE_ROUTE_TYPE_TO_MOT.get(route_type) or fallback
