
import re
import mariadb

from dataclasses import dataclass


MARIADB_CONFIG = {
    "user": "",
    "password": "",
    "host": "localhost",
    "port": 3306,
    "database": ""
}
SOURCE_TABLE = "plv"

LEQ_REGEX = re.compile(r"<=(?P<bound>\d+(?:,\d+)?)")
MEQ_REGEX = re.compile(r">=(?P<bound>\d+(?:,\d+)?)")

class Filter:
    def check(self, value: float) -> bool:
        ...

@dataclass
class MoreEqualThan(Filter):
    bound: float

    def check(self, value: float) -> bool:
        return value >= self.bound
    
@dataclass
class LessEqualThan(Filter):
    bound: float

    def check(self, value: float) -> bool:
        return value <= self.bound
    
@dataclass
class Conjunction(Filter):
    filters: tuple[Filter, ...]

    def check(self, value: float) -> bool:
        return all(f.check(value) for f in self.filters)

def probably_contains_filter(filter_str: str) -> bool:
    return any(char in filter_str for char in ("<", ">", "="))

def make_filter(filter_str: str) -> Filter|None:
    sub_filters: list[Filter] = []
    leq_match = LEQ_REGEX.match(filter_str)

    if leq_match:
        bound = float(leq_match.group("bound"))
        sub_filters.append(LessEqualThan(bound=bound))

    meq_match = MEQ_REGEX.match(filter_str)

    if meq_match:
        bound = float(meq_match.group("bound"))
        sub_filters.append(MoreEqualThan(bound=bound))

    if not sub_filters and probably_contains_filter(filter_str):
        raise ValueError(f"Filter string '{filter_str}' could not be parsed even though it contains filter characters.")

    if not sub_filters:
        return None

    return Conjunction(filters=tuple(sub_filters))


def main():
    conn = mariadb.connect(**MARIADB_CONFIG)

    for row in conn.cursor().execute(f"SELECT (refqual, limitequal, valtraduite) FROM {SOURCE_TABLE}"):
        refqual: str = row[0]
        limitequal: str = row[1]
        valtraduite: float = float(row[2])

        limit_filter = make_filter(limitequal)
        ref_filter = make_filter(refqual)

        limit_check = limit_filter.check(valtraduite) if limit_filter else None
        ref_check = ref_filter.check(valtraduite) if ref_filter else None

        conn.cursor().execute(
            f"UPDATE Mesure SET limit_check = ?, ref_check = ? WHERE (refqual, limitequal, valtraduite) = (?, ?, ?)",
            (limit_check, ref_check, refqual, limitequal, valtraduite)
        )


if __name__ == "__main__":
    main()
