"""Pydantic models shared by the parser, rule engine, and API."""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel


# ---------- parsing ----------

class ChainStage(BaseModel):
    instance: str          # e.g. "u2/ZN"
    cell: str              # e.g. "AND2_X1", or "in"/"out" for ports
    delay: float           # incremental delay of this stage (ns)
    time: float            # cumulative arrival time at this pin (ns)
    edge: str              # "rise" or "fall"
    fanout: Optional[int] = None     # only present with report_checks -fields fanout
    cap: Optional[float] = None      # load capacitance on the driven net
    slew: Optional[float] = None     # transition time at this pin (ns)


class TimingPath(BaseModel):
    startpoint: str
    endpoint: str
    path_group: str
    path_type: str                          # "max" (setup) or "min" (hold)
    corner: Optional[str] = None
    launch_clock_latency: Optional[float] = None
    capture_clock_latency: Optional[float] = None
    capture_edge: Optional[float] = None    # capture clock edge time (~period)
    data_arrival_time: Optional[float] = None
    data_required_time: Optional[float] = None
    external_delay: Optional[float] = None  # |input/output external delay| from the SDC (ns)
    slack: float
    status: str                             # "MET" or "VIOLATED"
    logic_chain: List[ChainStage]


# ---------- rule engine output ----------

class Suggestion(BaseModel):
    rule_id: str = ""      # which rule produced this (see rules.py)
    fix: str
    priority: str          # "high", "medium", "low"
    reason: str


class PathDiagnosis(BaseModel):
    check_type: str                          # "setup" or "hold"
    severity: Optional[str] = None           # only for violated paths
    logic_depth: int
    total_logic_delay: float
    bottleneck_instance: Optional[str] = None
    bottleneck_cell: Optional[str] = None
    bottleneck_delay: Optional[float] = None
    bottleneck_share: Optional[float] = None  # fraction of total logic delay
    clock_skew: Optional[float] = None        # capture latency - launch latency
    # Setup only: how much of the combinational delay must go to close the path.
    required_speedup: Optional[float] = None
    # Longest run of consecutive stages built from the same cell family.
    repeated_cell: Optional[str] = None
    repeated_run: int = 0
    repeated_delay: Optional[float] = None
    suggestions: List[Suggestion] = []


class AnalyzedPath(BaseModel):
    path: TimingPath
    diagnosis: PathDiagnosis


class ReportSummary(BaseModel):
    total_paths: int
    violated_paths: int
    met_paths: int
    wns: Optional[float] = None    # worst negative slack
    tns: float = 0.0               # total negative slack
    setup_violations: int = 0
    hold_violations: int = 0
    skipped_blocks: int = 0        # "Startpoint:" blocks too broken to parse


class ViolationGroup(BaseModel):
    """Violating paths that share a root cause, so one fix can clear several."""
    kind: str                      # shared_logic | endpoint_bus | startpoint | bottleneck_cell
    key: str
    check_type: str                # setup | hold
    path_indices: List[int]        # indices into AnalysisResult.paths
    count: int
    worst_slack: float
    tns: float                     # sum of the group's negative slacks
    tns_share: float               # group tns / report tns
    detail: str


class AnalysisResult(BaseModel):
    summary: ReportSummary
    paths: List[AnalyzedPath]
    groups: List[ViolationGroup] = []   # default keeps older saved analyses loadable


# ---------- comparing two reports ----------

class PathDelta(BaseModel):
    startpoint: str
    endpoint: str
    check_type: str
    before: Optional[float] = None
    after: Optional[float] = None
    delta: Optional[float] = None


class ComparisonResult(BaseModel):
    base_id: int
    new_id: int
    base_filename: str
    new_filename: str
    wns_before: Optional[float] = None
    wns_after: Optional[float] = None
    tns_before: float
    tns_after: float
    violations_before: int
    violations_after: int
    fixed: List[PathDelta]
    improved: List[PathDelta]
    regressed: List[PathDelta]
    unchanged: List[PathDelta]
    new_violations: List[PathDelta]
    dropped: List[PathDelta]       # violated before, absent from the new report


# ---------- API ----------

class UserCredentials(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    username: str
    role: str


class UserInfo(BaseModel):
    id: int
    username: str
    role: str
    created_at: datetime


class AnalysisListItem(BaseModel):
    id: int
    filename: str
    created_at: datetime
    summary: ReportSummary


class AnalysisDetail(BaseModel):
    id: int
    filename: str
    created_at: datetime
    result: AnalysisResult


class ExplainRequest(BaseModel):
    # Which admin-provided key from the pool to use. Optional so the server can
    # fall back to a single active key or the GROQ_API_KEY env var.
    api_key_id: Optional[int] = None


class ExplainResponse(BaseModel):
    explanation: str
    # Numbers in the text that don't appear in the diagnosis (possible invention).
    unverified_numbers: List[str] = []


# ---------- API keys (admin-managed pool) ----------

class ApiKeyOption(BaseModel):
    """What a normal user sees: enough to pick a key, never the secret."""
    id: int
    label: str
    masked: str


class ApiKeyAdmin(ApiKeyOption):
    """What an admin sees in the management console."""
    is_active: bool
    created_at: datetime
    created_by: str


class ApiKeyCreate(BaseModel):
    label: str
    secret: str


class ApiKeyUpdate(BaseModel):
    label: Optional[str] = None
    is_active: Optional[bool] = None


# ---------- admin: users ----------

class AdminUser(BaseModel):
    id: int
    username: str
    role: str
    created_at: datetime
    analysis_count: int


class AdminUserCreate(BaseModel):
    username: str
    password: str
    role: str = "user"


class AdminUserUpdate(BaseModel):
    role: Optional[str] = None
    password: Optional[str] = None


class AdminAnalysisItem(BaseModel):
    id: int
    filename: str
    created_at: datetime
    username: str
    summary: ReportSummary


class UsageStats(BaseModel):
    total_users: int
    total_admins: int
    total_analyses: int
    total_violations: int
    active_api_keys: int
