import typing
import itertools
from operator import attrgetter

from .fast_csv import iter_rows_as_namedtuples


class ShapeRow(typing.NamedTuple):
    lon: float
    lat: float
    distance: typing.Optional[float]


_T = typing.TypeVar("_T")


def read_shapes(
    directory: str,
    factory: typing.Callable[[typing.Iterable[ShapeRow]], _T],
    shape_ids: typing.Optional[typing.AbstractSet[str]] = None,
    assume_sorted: bool = False,
) -> typing.Dict[str, _T]:
    """Read shapes.txt as a dict mapping shape id to shape.

    `shape_ids` is an optional set for selecting only specific shape ids.
    The iterable passed to `factory` iterates over `ShapeRow` of a shape in the correct order.

    Attention: Each iterable passed to `factory` is not valid any more once `factory` has returned!

    If `assume_sorted` is set to `True`, it is assumed that the rows in shapes.txt are sorted by
    shape_id and shape_pt_sequence. No check is performed whether data is really sorted.
    """
    iter_file_rows = iter_rows_as_namedtuples(
        directory, "shapes.txt", optional_fieldnames=["shape_dist_traveled"]
    )
    if shape_ids is not None:
        iter_file_rows = (row for row in iter_file_rows if row.shape_id in shape_ids)
    # type of rows is created dynamically
    file_rows: typing.Iterable[typing.Any]
    if assume_sorted:
        file_rows = iter_file_rows
    else:
        file_rows = list(iter_file_rows)
        file_rows.sort(key=lambda row: (row.shape_id, int(row.shape_pt_sequence)))
    return {
        shape_id: factory(
            ShapeRow(
                float(row.shape_pt_lon),
                float(row.shape_pt_lat),
                float(row.shape_dist_traveled) if row.shape_dist_traveled else None,
            )
            for row in group
        )
        for shape_id, group in itertools.groupby(file_rows, key=attrgetter("shape_id"))
    }
