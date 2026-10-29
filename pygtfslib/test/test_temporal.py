import datetime
from zoneinfo import ZoneInfo

import pytest

from pygtfslib.temporal import (
    MAX_OPDAY_SHIFT,
    StopTime,
    TimeCache,
    TripOpDayProvider,
    format_timedelta,
    get_seconds_without_waiting_times,
    parse_timedelta,
)


def test_time_cache_regular_opday():
    tz = ZoneInfo("Europe/Berlin")
    tc = TimeCache(tz)
    opday = datetime.date(2022, 5, 18)

    # on a regular opdary (no dst switch), the GTFS reference time is midnight
    assert tc.get_reference_datetime(opday) == datetime.datetime(
        2022, 5, 18, 0, 0, 0, tzinfo=tz
    )

    # if there is no dst switch, the GTFS timedelta is effectively the local time:
    delta = datetime.timedelta(hours=10, minutes=30, seconds=15)
    result = tc.gtfs_time_to_datetime(opday, delta)
    assert result == datetime.datetime(2022, 5, 18, 10, 30, 15, tzinfo=tz)

    # does using more than 24 hours work?
    delta = datetime.timedelta(hours=26, minutes=20, seconds=45)
    result = tc.gtfs_time_to_datetime(opday, delta)
    assert result == datetime.datetime(2022, 5, 19, 2, 20, 45, tzinfo=tz)


def test_time_cache_dst_switch_opday():
    tz = ZoneInfo("Europe/Berlin")
    tc = TimeCache(tz)
    opday = datetime.date(2022, 3, 27)

    # the GTFS reference time "noon minus 12 hours" is not midnight on that day since
    # one hour is "missing" between midnight and noon due to dst switch
    assert tc.get_reference_datetime(opday) == datetime.datetime(
        2022, 3, 26, 23, 0, 0, tzinfo=tz
    )

    # when we sweep past the dst switch, the effect cancels:
    delta = datetime.timedelta(hours=10, minutes=30, seconds=15)
    result = tc.gtfs_time_to_datetime(opday, delta)
    assert result == datetime.datetime(2022, 3, 27, 10, 30, 15, tzinfo=tz)

    # when we stay before the dst switch,
    # GTFS timedelta is shifted by one hour compared to local time:
    delta = datetime.timedelta(hours=2, minutes=10, seconds=7)
    result = tc.gtfs_time_to_datetime(opday, delta)
    assert result == datetime.datetime(2022, 3, 27, 1, 10, 7, tzinfo=tz)


@pytest.mark.parametrize(
    "opday,gtfs_time",
    [
        # regular opday
        (datetime.date(2022, 5, 18), "10:30:15"),
        (datetime.date(2022, 5, 18), "26:20:45"),
        # opday with a dst switch forward (23 hours long)
        (datetime.date(2022, 3, 27), "02:10:07"),
        (datetime.date(2022, 3, 27), "10:30:15"),
        (datetime.date(2022, 3, 27), "24:30:00"),
        # opday with a dst switch backward (25 hours long)
        (datetime.date(2022, 10, 30), "01:00:00"),
        (datetime.date(2022, 10, 30), "10:30:15"),
        (datetime.date(2022, 10, 30), "25:30:00"),
        # the largest GTFS time that can be expressed
        (datetime.date(2022, 5, 18), "99:59:59"),
    ],
)
def test_datetime_to_gtfs_time_roundtrip(opday: datetime.date, gtfs_time: str) -> None:
    tc = TimeCache(ZoneInfo("Europe/Berlin"))
    delta = parse_timedelta(gtfs_time)
    assert delta is not None
    dt = tc.gtfs_time_to_datetime(opday, delta)

    result_opday, delta = tc.datetime_to_gtfs_time(opday, dt)

    assert result_opday == opday
    assert format_timedelta(delta) == gtfs_time


def test_datetime_to_gtfs_time_shifts_negative_timedelta(
    caplog: pytest.LogCaptureFixture,
) -> None:
    tz = ZoneInfo("Europe/Berlin")
    tc = TimeCache(tz)
    # the dst switch backward makes the reference time of that opday 01:00 local time,
    # so local midnight cannot be expressed as a GTFS time of that opday
    opday = datetime.date(2022, 10, 30)
    dt = datetime.datetime(2022, 10, 30, tzinfo=tz)

    result_opday, delta = tc.datetime_to_gtfs_time(opday, dt)

    assert result_opday == datetime.date(2022, 10, 29)
    assert format_timedelta(delta) == "24:00:00"
    assert "using operating day 2022-10-29 instead" in caplog.text


def test_datetime_to_gtfs_time_shifts_too_large_timedelta(
    caplog: pytest.LogCaptureFixture,
) -> None:
    tc = TimeCache(ZoneInfo("Europe/Berlin"))
    opday = datetime.date(2022, 5, 18)
    dt = tc.gtfs_time_to_datetime(opday, datetime.timedelta(hours=100))

    result_opday, delta = tc.datetime_to_gtfs_time(opday, dt)

    assert result_opday == datetime.date(2022, 5, 19)
    assert format_timedelta(delta) == "76:00:00"
    assert "using operating day 2022-05-19 instead" in caplog.text


def test_datetime_to_gtfs_time_gives_up_eventually() -> None:
    tc = TimeCache(ZoneInfo("Europe/Berlin"))
    opday = datetime.date(2022, 5, 18)
    dt = tc.gtfs_time_to_datetime(opday, datetime.timedelta(days=MAX_OPDAY_SHIFT + 5))

    with pytest.raises(ValueError, match="cannot express"):
        tc.datetime_to_gtfs_time(opday, dt)


@pytest.mark.parametrize(
    "delta,expected",
    [
        (datetime.timedelta(0), "00:00:00"),
        (datetime.timedelta(hours=1, minutes=2, seconds=3), "01:02:03"),
        (datetime.timedelta(days=1, hours=1, minutes=30), "25:30:00"),
        # sub-seconds are truncated
        (datetime.timedelta(seconds=1, microseconds=999999), "00:00:01"),
    ],
)
def test_format_timedelta(delta: datetime.timedelta, expected: str) -> None:
    assert format_timedelta(delta) == expected
    assert parse_timedelta(expected) == datetime.timedelta(
        seconds=int(delta.total_seconds())
    )


@pytest.mark.parametrize(
    "delta",
    [
        datetime.timedelta(seconds=-1),
        datetime.timedelta(hours=100),
    ],
)
def test_format_timedelta_out_of_range(delta: datetime.timedelta) -> None:
    with pytest.raises(ValueError, match="out of range"):
        format_timedelta(delta)


def test_travel_times():
    def st(s1, s2):
        stop_time = StopTime.__new__(StopTime)
        stop_time.arrival_time = (
            datetime.timedelta(seconds=s1) if s1 is not None else None
        )
        stop_time.departure_time = (
            datetime.timedelta(seconds=s2) if s2 is not None else None
        )
        return stop_time

    travel_seconds = get_seconds_without_waiting_times(
        [
            st(None, 15),
            st(None, 25),
            st(None, None),
            st(45, 70),
            st(70, None),
        ]
    )
    assert travel_seconds == [0, 10, None, 30, 30]

    travel_seconds = get_seconds_without_waiting_times(
        [
            st(16, 15),
            st(17, 18),
        ]
    )
    assert travel_seconds == [None, None]

    travel_seconds = get_seconds_without_waiting_times(
        [
            st(15, 16),
            st(15, 18),
        ]
    )
    assert travel_seconds == [None, None]


def test_trip_opday_provider():
    feb_1st = datetime.date(2023, 2, 1)
    feb_2nd = datetime.date(2023, 2, 2)
    feb_3rd = datetime.date(2023, 2, 3)
    feb_4th = datetime.date(2023, 2, 4)
    trip_id_to_opdays = {
        "A": {feb_1st, feb_2nd, feb_3rd},
        "B": {feb_1st, feb_4th},
        "C": {feb_2nd},
    }
    provider = TripOpDayProvider(trip_id_to_opdays)

    def is_feb_1st_or_4th(d: datetime.date) -> bool:
        return d in {feb_1st, feb_4th}

    assert provider.get_qualified_opdays(
        trip_id_to_opdays.keys(), is_feb_1st_or_4th
    ) == {feb_1st, feb_4th}
    assert provider.has_qualified_opdays(trip_id_to_opdays.keys(), is_feb_1st_or_4th)

    assert provider.get_qualified_opdays({"A"}, is_feb_1st_or_4th) == {feb_1st}
    assert provider.has_qualified_opdays({"A"}, is_feb_1st_or_4th)

    assert provider.get_qualified_opdays("C", is_feb_1st_or_4th) == set()
    assert not provider.has_qualified_opdays("C", is_feb_1st_or_4th)
