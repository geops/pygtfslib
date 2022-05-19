from collections import defaultdict
import datetime
import logging
import math
from functools import lru_cache
import typing

from dateutil.tz import tzutc
from dateutil import rrule

from .fast_csv import iter_rows


logger = logging.getLogger(__name__)

GTFS_WEEKDAYS = (
    "monday",
    "tuesday",
    "wednesday",
    "thursday",
    "friday",
    "saturday",
    "sunday",
)
RRULE_WEEKDAYS = {d: getattr(rrule, d[:2].upper()) for d in GTFS_WEEKDAYS}
UNAWARE_NOON = datetime.time(hour=12)
TWELVE_HOURS = datetime.timedelta(hours=12)
UTC = tzutc()


# strptime is really slow
# we cache at least up to 365 days
@lru_cache(maxsize=512)
def parse_date(value):
    if not value:
        return None
    return datetime.datetime.strptime(value, "%Y%m%d").date()


# this is slow, we cache at least 24 * 60 minutes
@lru_cache(maxsize=2048)
def parse_timedelta(value):
    if not value:
        return None
    # we don't check lengths of parts
    hours, minutes, seconds = map(int, value.split(":"))
    return datetime.timedelta(hours=hours, minutes=minutes, seconds=seconds)


def parse_deltas(stop_time):
    st = stop_time
    arrival_delta = parse_timedelta(st.get("arrival_time"))
    departure_delta = parse_timedelta(st.get("departure_time"))

    if arrival_delta is None:
        arrival_delta = departure_delta
    if departure_delta is None:
        departure_delta = arrival_delta

    return arrival_delta, departure_delta


def utc_datetime(date, unaware_local_time, timezone):
    unaware_dt = datetime.datetime.combine(date, unaware_local_time)
    aware_dt = unaware_dt.replace(tzinfo=timezone)
    return aware_dt.astimezone(UTC)


# dateutil timezones are not hashable, so we need this helper class
# for the lru_cache to work
class TimeCache:
    """A cache for quickly converting GTFS times to datetimes for a fixed timezone."""

    def __init__(self, timezone, maxsize=512):

        # this is incredibly slow so we cache it
        @lru_cache(maxsize=maxsize)
        def get_reference_datetime(opday):
            return utc_datetime(opday, UNAWARE_NOON, timezone) - TWELVE_HOURS

        # one cache per instance with the lifetime of the instance
        self.get_reference_datetime = get_reference_datetime

    def gtfs_time_to_datetime(self, opday, delta):
        return self.get_reference_datetime(opday) + delta


def parse_calendar_row(
    row, first_opday=datetime.date.min, last_opday=datetime.date.max
):
    """Parse a row from calendar.txt.

    Return a set of operating days described by this row.
    The operating day range can be clipped by specifying first_/last_opday.
    """
    start_date = max(parse_date(row["start_date"]), first_opday)
    end_date = min(parse_date(row["end_date"]), last_opday)
    rrule_weekdays = [RRULE_WEEKDAYS[d] for d in GTFS_WEEKDAYS if row[d] == "1"]
    if rrule_weekdays:
        return {
            d.date()
            for d in rrule.rrule(
                freq=rrule.DAILY,
                dtstart=start_date,
                until=end_date,
                byweekday=rrule_weekdays,
            )
        }
    else:
        # if rrule_weekdays is empty, rrule assumes all days but no days is what we need
        return set()


def read_calendar(
    directory, first_opday=datetime.date.min, last_opday=datetime.date.max
):
    """Read GTFS calendar.txt and calendar_dates.txt from directory.

    Return a defaultdict mapping service_id to a set of operating days.
    The operating day range can be clipped by specifying first_/last_opday.

    If neither of the two files is present, an empty defaultdict(set) is returned.
    """
    service_id_to_dates = defaultdict(set)
    try:
        service_id_to_dates.update(
            (row["service_id"], parse_calendar_row(row, first_opday, last_opday))
            for row in iter_rows(directory, "calendar.txt")
        )
    except FileNotFoundError:
        logger.info("skipping calendar.txt (not found)")
    try:
        for row in iter_rows(directory, "calendar_dates.txt"):
            date = parse_date(row["date"])
            if not (first_opday <= date <= last_opday):
                continue
            exc_type = row["exception_type"]
            if exc_type == "1":
                service_id_to_dates[row["service_id"]].add(date)
            elif exc_type == "2":
                service_id_to_dates[row["service_id"]].discard(date)
            else:
                raise ValueError(f"invalid exception type: {exc_type!r}")
    except FileNotFoundError:
        logger.info("skipping calendar_dates.txt (not found)")
    return service_id_to_dates


def read_frequency_timedeltas(directory, frequency_based_log_level=logging.WARNING):
    """Read frequencies.txt from directory.

    Return a defaultdict mapping trip_id to a sorted list of timedeltas of the trip starting times.
    The timedeltas are in the usual GTFS sence and can be converted to a datetime using
    `TimeCache.gtfs_time_to_datetime` for a specific operating day.

    If frequencies.txt is not present, an empty defaultdict(list) is returned.

    Warning: Treats frequency based trips as schedule based.
             In reality, starting times of frequency based trips are
             only known in combination with GTFS-RT data.
    """
    trip_id_to_start_timedeltas = defaultdict(list)
    try:
        n_frequency_based = 0
        half_a_second = datetime.timedelta(seconds=0.5)
        for row in iter_rows(directory, "frequencies.txt"):
            trip_id = row["trip_id"]
            start = parse_timedelta(row["start_time"])
            end = parse_timedelta(row["end_time"])
            headway_secs = int(row["headway_secs"])
            if headway_secs <= 0:
                raise ValueError(f"headway_secs has to be > 0 (got {headway_secs})")
            headway = datetime.timedelta(seconds=headway_secs)
            exact_times = row.get("exact_times") or "0"
            if exact_times == "0":
                n_frequency_based += 1
            elif exact_times == "1":
                pass
            else:
                raise ValueError(f"illegal value for exact_times: {exact_times!r}")
            # end is exclusive and we have seconds resolution
            n_journeys = math.floor((end - start - half_a_second) / headway) + 1
            if n_journeys <= 0:
                logger.warning(
                    "found n_journeys = %d <= 0 for trip_id %r", n_journeys, trip_id
                )
            starts = (start + i * headway for i in range(n_journeys))
            trip_id_to_start_timedeltas[trip_id].extend(starts)
        if n_frequency_based:
            logger.log(
                frequency_based_log_level,
                "treated %d frequency-based frequencies as schedule based",
                n_frequency_based,
            )
    except FileNotFoundError:
        logger.info("skipping frequencies.txt (not found)")

    for start_timedeltas in trip_id_to_start_timedeltas.values():
        start_timedeltas.sort()
    return trip_id_to_start_timedeltas


class TripOpDayProvider:
    """Provide information about operating days specific trips run on."""

    trip_id_to_opdays: typing.Dict[str, typing.Set[datetime.date]]

    def __init__(
        self,
        trip_id_to_opdays: typing.Mapping[str, typing.AbstractSet[datetime.date]],
    ) -> None:
        self.trip_id_to_opdays = {k: set(v) for k, v in trip_id_to_opdays.items()}

    def load_directories(self, *directories: str) -> None:
        for directory in directories:
            calendar = read_calendar(directory)
            for row in iter_rows(directory, "trips.txt"):
                trip_id = row["trip_id"]
                opdays = calendar.get(row["service_id"], set())
                if trip_id in self.trip_id_to_opdays:
                    self.trip_id_to_opdays[trip_id] |= opdays
                else:
                    self.trip_id_to_opdays[trip_id] = set(opdays)

    def get_qualified_opdays(
        self,
        trip_ids: typing.Union[str, typing.AbstractSet[str]],
        criterion: typing.Callable[[datetime.datetime], bool],
    ) -> typing.Set[datetime.datetime]:
        if isinstance(trip_ids, str):
            trip_ids = {trip_ids}
        qualified_opdays: set = set()
        for trip_id in trip_ids:
            trip_opdays = self.trip_id_to_opdays[trip_id]
            qualified_opdays.update(filter(criterion, trip_opdays))
        return qualified_opdays
