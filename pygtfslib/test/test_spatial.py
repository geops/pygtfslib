from collections import namedtuple

from unittest.mock import patch

from pygtfslib.spatial import read_shapes, ShapeRow


def test_read_shapes():
    Row = namedtuple(
        "Row",
        [
            "shape_id",
            "shape_pt_sequence",
            "shape_pt_lat",
            "shape_pt_lon",
            "shape_dist_traveled",
        ],
        defaults=[None] * 5,
    )
    rows = [
        Row(
            shape_id="1",
            shape_pt_sequence="0",
            shape_pt_lat="10.1",
            shape_pt_lon="20.2",
        ),
        Row(
            shape_id="2",
            shape_pt_sequence="3000",
            shape_pt_lat="70.7",
            shape_pt_lon="80.8",
            shape_dist_traveled="",
        ),
        Row(
            shape_id="1",
            shape_pt_sequence="1",
            shape_pt_lat="30.3",
            shape_pt_lon="40.4",
            shape_dist_traveled="200.2",
        ),
        Row(
            shape_id="2",
            shape_pt_sequence="20",
            shape_pt_lat="50.5",
            shape_pt_lon="60.6",
            shape_dist_traveled="300.3",
        ),
    ]

    with patch("pygtfslib.spatial.iter_rows_as_namedtuples") as iter_rows_mock:
        iter_rows_mock.return_value = (row for row in rows)
        shapes = read_shapes("", factory=list)
    assert shapes == {
        "1": [
            ShapeRow(lat=10.1, lon=20.2, distance=None),
            ShapeRow(lat=30.3, lon=40.4, distance=200.2),
        ],
        "2": [
            ShapeRow(lat=50.5, lon=60.6, distance=300.3),
            ShapeRow(lat=70.7, lon=80.8, distance=None),
        ],
    }
