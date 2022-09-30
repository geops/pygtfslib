import datetime

from dateutil.tz import gettz

from pygtfslib.temporal import TimeCache, get_seconds_without_waiting_times, StopTime


def test_time_cache_regular_opday():
    tz = gettz("Europe/Berlin")
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
    tz = gettz("Europe/Berlin")
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
