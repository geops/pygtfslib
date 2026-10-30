import datetime
from zoneinfo import ZoneInfo

import pytest

from pygtfslib.temporal import (
    DEFAULT_MAX_OPDAY_SHIFT,
    MIN_INVALID_GTFS_TIMEDELTA,
    ONE_DAY,
    ONE_SECOND,
    ZERO_TIMEDELTA,
    OpDayTime,
    OpDayTimes,
    StopTime,
    TimeCache,
    TripOpDayProvider,
    format_timedelta,
    get_seconds_without_waiting_times,
    parse_timedelta,
)

BERLIN = ZoneInfo("Europe/Berlin")
# a regular opday without a dst switch
REGULAR_OPDAY = datetime.date(2022, 5, 18)
# an opday with a dst switch forward (23 hours long)
DST_FORWARD_OPDAY = datetime.date(2022, 3, 27)
# an opday with a dst switch backward (25 hours long)
DST_BACKWARD_OPDAY = datetime.date(2022, 10, 30)
MAX_VALID_GTFS_TIMEDELTA = MIN_INVALID_GTFS_TIMEDELTA - ONE_SECOND


def hours(value: float) -> datetime.timedelta:
    return datetime.timedelta(hours=value)


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


# the datetimes to convert are given as offsets from the GTFS reference time of the
# opday that is passed in, i.e. as the GTFS timedeltas that opday would give if GTFS
# could express them
@pytest.mark.parametrize(
    "opday,offsets,expected_shift,expected_gtfs_times",
    [
        pytest.param(REGULAR_OPDAY, [hours(10.5)], 0, ["10:30:00"], id="single time"),
        pytest.param(
            REGULAR_OPDAY,
            [hours(26), hours(0), hours(10)],
            0,
            ["26:00:00", "00:00:00", "10:00:00"],
            id="order of times is preserved",
        ),
        pytest.param(
            DST_FORWARD_OPDAY,
            [hours(2), hours(24.5)],
            0,
            ["02:00:00", "24:30:00"],
            id="dst switch forward",
        ),
        pytest.param(
            DST_BACKWARD_OPDAY,
            [hours(1), hours(25.5)],
            0,
            ["01:00:00", "25:30:00"],
            id="dst switch backward",
        ),
        pytest.param(
            REGULAR_OPDAY,
            [ZERO_TIMEDELTA, MAX_VALID_GTFS_TIMEDELTA],
            0,
            ["00:00:00", "99:59:59"],
            id="bounds of the valid range",
        ),
        pytest.param(
            DST_BACKWARD_OPDAY,
            [hours(-1)],
            -1,
            ["24:00:00"],
            id="negative time shifts the opday backward",
        ),
        pytest.param(
            REGULAR_OPDAY,
            [hours(-2), hours(20)],
            -1,
            ["22:00:00", "44:00:00"],
            id="valid time is shifted along with the negative one",
        ),
        pytest.param(
            REGULAR_OPDAY,
            [hours(100)],
            1,
            ["76:00:00"],
            id="too large time shifts the opday forward",
        ),
        pytest.param(
            REGULAR_OPDAY,
            [hours(101), hours(25), hours(50)],
            1,
            ["77:00:00", "01:00:00", "26:00:00"],
            id="valid times are shifted along with the too large one",
        ),
        pytest.param(
            REGULAR_OPDAY,
            [hours(125)],
            2,
            ["77:00:00"],
            id="more than one shift",
        ),
    ],
)
def test_datetimes_to_gtfs_times(
    opday: datetime.date,
    offsets: list[datetime.timedelta],
    expected_shift: int,
    expected_gtfs_times: list[str],
    caplog: pytest.LogCaptureFixture,
) -> None:
    tc = TimeCache(BERLIN)
    dts = [tc.gtfs_time_to_datetime(opday, offset) for offset in offsets]

    result = tc.datetimes_to_gtfs_times(opday, dts)

    assert result.opday == opday + expected_shift * ONE_DAY
    assert [format_timedelta(delta) for delta in result.deltas] == expected_gtfs_times
    assert_describes_datetimes(tc, dts, result)
    # the opday is shifted only if necessary, and never without a warning
    assert bool(caplog.records) == bool(expected_shift)
    if expected_shift:
        assert f"using operating day {result.opday} instead" in caplog.text


def assert_describes_datetimes(
    tc: TimeCache, dts: list[datetime.datetime], result: OpDayTimes
) -> None:
    """Assert the result is a valid and faithful GTFS representation of `dts`."""
    assert all(
        ZERO_TIMEDELTA <= delta < MIN_INVALID_GTFS_TIMEDELTA for delta in result.deltas
    )
    assert [
        tc.gtfs_time_to_datetime(result.opday, delta) for delta in result.deltas
    ] == dts


@pytest.mark.parametrize(
    "offsets,match",
    [
        pytest.param(
            [ZERO_TIMEDELTA, MIN_INVALID_GTFS_TIMEDELTA],
            "100 hours or more apart",
            id="times too far apart for any opday",
        ),
        pytest.param(
            [hours(-2), hours(78)],
            "cannot express",
            id="shifting fixes one end but breaks the other",
        ),
        pytest.param(
            [hours(24 * (DEFAULT_MAX_OPDAY_SHIFT + 5))],
            f"within {DEFAULT_MAX_OPDAY_SHIFT} days",
            id="valid opday too far away",
        ),
    ],
)
def test_datetimes_to_gtfs_times_raises(
    offsets: list[datetime.timedelta], match: str
) -> None:
    tc = TimeCache(BERLIN)
    dts = [tc.gtfs_time_to_datetime(REGULAR_OPDAY, offset) for offset in offsets]

    with pytest.raises(ValueError, match=match):
        tc.datetimes_to_gtfs_times(REGULAR_OPDAY, dts)


@pytest.mark.parametrize(
    "offsets,max_lookups",
    [
        # no opday whatsoever can work, so not a single shifted one is tried
        pytest.param(
            [ZERO_TIMEDELTA, MIN_INVALID_GTFS_TIMEDELTA],
            2,
            id="times too far apart for any opday",
        ),
        # the first shifted opday already shows that the times cannot both be in the
        # valid range, shifting further only makes it worse
        pytest.param(
            [hours(-2), hours(78)],
            3,
            id="shifting fixes one end but breaks the other",
        ),
    ],
)
def test_datetimes_to_gtfs_times_gives_up_early(
    offsets: list[datetime.timedelta], max_lookups: int
) -> None:
    tc = TimeCache(BERLIN)
    dts = [tc.gtfs_time_to_datetime(REGULAR_OPDAY, offset) for offset in offsets]
    looked_up_opdays = record_reference_datetime_lookups(tc)

    with pytest.raises(ValueError):
        # even a huge max_opday_shift must not lead to trying every opday
        tc.datetimes_to_gtfs_times(REGULAR_OPDAY, dts, max_opday_shift=1000)

    assert len(looked_up_opdays) <= max_lookups


def record_reference_datetime_lookups(tc: TimeCache) -> list[datetime.date]:
    """Make `tc` record the opdays it looks up and return the recording list."""
    get_reference_datetime = tc.get_reference_datetime
    looked_up_opdays: list[datetime.date] = []

    def record_and_get(opday: datetime.date) -> datetime.datetime:
        looked_up_opdays.append(opday)
        return get_reference_datetime(opday)

    # the cached function is just an instance attribute, so it can be wrapped
    tc.get_reference_datetime = record_and_get  # type: ignore[assignment]
    return looked_up_opdays


def test_datetimes_to_gtfs_times_without_datetimes() -> None:
    tc = TimeCache(BERLIN)

    assert tc.datetimes_to_gtfs_times(REGULAR_OPDAY, []) == (REGULAR_OPDAY, [])


@pytest.mark.parametrize(
    "opday,offset",
    [
        pytest.param(REGULAR_OPDAY, hours(10.5), id="no shift"),
        pytest.param(DST_BACKWARD_OPDAY, hours(-1), id="shift backward"),
        pytest.param(REGULAR_OPDAY, hours(100), id="shift forward"),
    ],
)
def test_datetime_to_gtfs_time_is_the_single_datetime_case(
    opday: datetime.date, offset: datetime.timedelta
) -> None:
    tc = TimeCache(BERLIN)
    dt = tc.gtfs_time_to_datetime(opday, offset)

    result = tc.datetime_to_gtfs_time(opday, dt)

    expected_opday, expected_deltas = tc.datetimes_to_gtfs_times(opday, [dt])
    assert isinstance(result, OpDayTime)
    assert result == OpDayTime(expected_opday, expected_deltas[0])


def test_datetime_to_gtfs_time_forwards_max_opday_shift() -> None:
    tc = TimeCache(BERLIN)
    dt = tc.gtfs_time_to_datetime(REGULAR_OPDAY, hours(170))

    result = tc.datetime_to_gtfs_time(REGULAR_OPDAY, dt, max_opday_shift=3)

    assert result.opday == REGULAR_OPDAY + 3 * ONE_DAY
    assert format_timedelta(result.delta) == "98:00:00"
    with pytest.raises(ValueError, match="within 2 days"):
        tc.datetime_to_gtfs_time(REGULAR_OPDAY, dt, max_opday_shift=2)


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
