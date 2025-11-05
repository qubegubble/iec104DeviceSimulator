from dataclasses import dataclass

@dataclass
class DataPoint:
    name: str
    io_address: int
    type_iec: int | None
    unit: str | None
    raw: dict
