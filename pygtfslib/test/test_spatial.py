from unittest.mock import patch

from pygtfslib.spatial import read_shapes, ShapeRow


def test_read_shapes():
    rows = [
        {
            "shape_id": "1",
            "shape_pt_sequence": "0",
            "shape_pt_lat": "10.1",
            "shape_pt_lon": "20.2",
        },
        {
            "shape_id": "2",
            "shape_pt_sequence": "3000",
            "shape_pt_lat": "70.7",
            "shape_pt_lon": "80.8",
            "shape_dist_traveled": "",
        },
        {
            "shape_id": "1",
            "shape_pt_sequence": "1",
            "shape_pt_lat": "30.3",
            "shape_pt_lon": "40.4",
            "shape_dist_traveled": "200.2",
        },
        {
            "shape_id": "2",
            "shape_pt_sequence": "20",
            "shape_pt_lat": "50.5",
            "shape_pt_lon": "60.6",
            "shape_dist_traveled": "300.3",
        },
    ]

    with patch("pygtfslib.spatial.iter_rows") as iter_rows_mock:
        iter_rows_mock.return_value = (row for row in rows)
        shapes = read_shapes("", factory=list)
    assert shapes == {
        "1": [ShapeRow(10.1, 20.2, None), ShapeRow(30.3, 40.4, 200.2)],
        "2": [ShapeRow(50.5, 60.6, 300.3), ShapeRow(70.7, 80.8, None)],
    }
