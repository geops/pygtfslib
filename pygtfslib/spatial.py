import typing
import itertools
from operator import itemgetter

from .fast_csv import iter_rows


class ShapeRow(typing.NamedTuple):
    lon: float
    lat: float
    distance: typing.Optional[float]


class _FileRow(typing.NamedTuple):
    id: str
    sequence: int
    shape_row: ShapeRow


_T = typing.TypeVar("_T")


def read_shapes(
    directory: str,
    factory: typing.Callable[[typing.Iterable[ShapeRow]], _T],
    shape_ids: typing.Optional[typing.AbstractSet[str]] = None,
) -> typing.Dict[str, _T]:
    """Read shapes.txt as a dict mapping shape id to shape.

    `shape_ids` is an optional set for selecting only specific shape ids.
    The iterable passed to `factory` iterates over `ShapeRow` of a shape in the correct order.

    Attention: Each iterable passed to `factory` is not valid any more once `factory` has returned!
    """
    file_rows = [
        _FileRow(
            row["shape_id"],
            int(row["shape_pt_sequence"]),
            ShapeRow(
                float(row["shape_pt_lon"]),
                float(row["shape_pt_lat"]),
                float(row["shape_dist_traveled"])
                if row.get("shape_dist_traveled")
                else None,
            ),
        )
        for row in iter_rows(directory, "shapes.txt")
        if shape_ids is None or row["shape_id"] in shape_ids
    ]
    file_rows.sort(key=lambda row: row[:2])
    return {
        shape_id: factory(file_row.shape_row for file_row in group)
        for shape_id, group in itertools.groupby(file_rows, key=itemgetter(0))
    }
