"""Parser for OpenSTA-style timing reports.

A report is a sequence of path blocks, each starting with "Startpoint:".
Every block has two timing sections: the data arrival section (launch clock
edge through the logic chain) and the data required section (capture clock
edge minus setup / plus hold), followed by the slack line.
"""

import re
from typing import List, Optional

from .schemas import ChainStage, TimingPath

# Chain lines look like:  "   0.26    0.26 v r2/Q (DFF_X1)"
# (delay, cumulative time, rise/fall edge, instance pin, cell name). With
# `report_checks -fields {fanout cap slew}` OpenSTA prepends extra numeric
# columns, so we capture all leading numbers and map them using the header.
_CHAIN_LINE = re.compile(
    r"^\s*((?:-?\d+(?:\.\d+)?\s+)+)([\^v])\s+(\S+)\s+\((\S+)\)"
)

# Column header:  "Fanout     Cap    Slew   Delay    Time   Description"
_HEADER_LINE = re.compile(r"^\s*((?:[A-Za-z]+\s+)+)Description\s*$")
_DEFAULT_COLUMNS = ["fanout", "cap", "slew", "delay", "time"]

# Delay then time, then the label:  "-1.00    4.00   output external delay"
_EXTERNAL_DELAY = re.compile(r"(-?\d+\.\d+)\s+-?\d+\.\d+\s+[\^v]?\s*(?:input|output) external delay")

# Slack lines look like:  "          -0.18   slack (VIOLATED)"
_SLACK_LINE = re.compile(r"(-?\d+\.\d+)\s+slack\s+\((VIOLATED|MET)\)")

# Clock edge lines look like:  "  10.00   10.00   clock clk (rise edge)"
# (with extra slew/cap columns there can be more than two numbers in front)
_CLOCK_EDGE_LINE = re.compile(
    r"^\s*(?:-?\d+\.\d+\s+)*(-?\d+\.\d+)\s+(-?\d+\.\d+)\s+clock\s+\S+\s+\((?:rise|fall) edge\)"
)

_CLOCK_NETWORK_LINE = re.compile(
    r"^\s*(?:-?\d+\.\d+\s+)*(-?\d+\.\d+)\s+(-?\d+\.\d+)\s+clock network delay"
)

_FLOAT_PREFIX = re.compile(r"^\s*(-?\d+\.\d+)\s")


def _leading_float(line: str) -> Optional[float]:
    match = _FLOAT_PREFIX.match(line)
    return float(match.group(1)) if match else None


class STAParser:
    def __init__(self, report_text: str):
        self.report_text = report_text
        self.skipped = 0   # blocks dropped as unparseable (set by parse())

    def parse(self) -> List[TimingPath]:
        paths = []
        self.skipped = 0
        # Each path block starts with "Startpoint:" at the beginning of a line;
        # text before the first one (headers, tool banners) is ignored.
        blocks = re.split(r"^[ 	]*Startpoint:", self.report_text, flags=re.MULTILINE)
        for block in blocks[1:]:
            path = self._parse_block(block)
            if path is not None:
                paths.append(path)
            else:
                self.skipped += 1
        return paths

    def _parse_block(self, block: str) -> Optional[TimingPath]:
        lines = block.splitlines()
        if not lines:
            return None

        startpoint = self._strip_annotation(lines[0])
        endpoint = ""
        path_group = ""
        path_type = ""
        corner = None
        launch_clock_latency = None
        capture_clock_latency = None
        capture_edge = None
        data_arrival = None
        data_required = None
        slack = None
        status = "MET"
        external_delay = None
        columns = _DEFAULT_COLUMNS
        saw_hold_check = saw_setup_check = False
        chain: List[ChainStage] = []

        # The block reads top-to-bottom: header, arrival section, required
        # section. Only arrival-section pin lines belong to the logic chain.
        section = "arrival"

        for line in lines[1:]:
            stripped = line.strip()

            if stripped.startswith("Endpoint:"):
                endpoint = self._strip_annotation(stripped[len("Endpoint:"):])
            elif stripped.startswith("Path Group:"):
                path_group = stripped[len("Path Group:"):].strip()
            elif stripped.startswith("Path Type:"):
                path_type = stripped[len("Path Type:"):].strip()
            elif stripped.startswith("Corner:"):
                corner = stripped[len("Corner:"):].strip()
            elif _HEADER_LINE.match(line):
                columns = [c.lower() for c in _HEADER_LINE.match(line).group(1).split()]
            elif _EXTERNAL_DELAY.search(stripped):
                if external_delay is None:
                    external_delay = abs(float(_EXTERNAL_DELAY.search(stripped).group(1)))
            elif "library hold time" in stripped:
                saw_hold_check = True
            elif "library setup time" in stripped:
                saw_setup_check = True
            elif "data arrival time" in stripped:
                if section == "arrival" and data_arrival is None:
                    data_arrival = _leading_float(stripped)
                    section = "required"
            elif "data required time" in stripped:
                if data_required is None:
                    data_required = _leading_float(stripped)
            elif _SLACK_LINE.search(stripped):
                match = _SLACK_LINE.search(stripped)
                slack = float(match.group(1))
                status = "VIOLATED" if match.group(2) == "VIOLATED" else "MET"
            elif _CLOCK_NETWORK_LINE.match(line):
                latency = float(_CLOCK_NETWORK_LINE.match(line).group(1))
                if section == "arrival" and launch_clock_latency is None:
                    launch_clock_latency = latency
                elif section == "required" and capture_clock_latency is None:
                    capture_clock_latency = latency
            elif _CLOCK_EDGE_LINE.match(line):
                if section == "required" and capture_edge is None:
                    capture_edge = float(_CLOCK_EDGE_LINE.match(line).group(2))
            elif section == "arrival":
                match = _CHAIN_LINE.match(line)
                if match:
                    chain.append(self._chain_stage(match, columns))

        if not startpoint or slack is None:
            return None

        # Some reports omit "Path Type:"; the setup/hold library line tells us.
        if not path_type:
            if saw_hold_check:
                path_type = "min"
            elif saw_setup_check:
                path_type = "max"

        return TimingPath(
            startpoint=startpoint,
            endpoint=endpoint,
            path_group=path_group,
            path_type=path_type,
            corner=corner,
            launch_clock_latency=launch_clock_latency,
            capture_clock_latency=capture_clock_latency,
            capture_edge=capture_edge,
            external_delay=external_delay,
            data_arrival_time=data_arrival,
            data_required_time=data_required,
            slack=slack,
            status=status,
            logic_chain=chain,
        )

    @staticmethod
    def _chain_stage(match, columns: List[str]) -> ChainStage:
        numbers = match.group(1).split()
        # Numbers are right-aligned under the header, so a line with fewer
        # numbers than columns is missing the leftmost ones.
        names = columns[len(columns) - len(numbers):] if len(numbers) <= len(columns) else columns
        values = dict(zip(names, numbers[-len(names):]))
        fanout = values.get("fanout")
        return ChainStage(
            delay=float(values.get("delay", numbers[-2] if len(numbers) > 1 else numbers[-1])),
            time=float(values.get("time", numbers[-1])),
            edge="rise" if match.group(2) == "^" else "fall",
            instance=match.group(3),
            cell=match.group(4),
            fanout=int(float(fanout)) if fanout is not None else None,
            cap=float(values["cap"]) if "cap" in values else None,
            slew=float(values["slew"]) if "slew" in values else None,
        )

    @staticmethod
    def _strip_annotation(text: str) -> str:
        """Drop the parenthesized description: "r1 (rising edge...)" -> "r1"."""
        return text.split("(")[0].strip()
