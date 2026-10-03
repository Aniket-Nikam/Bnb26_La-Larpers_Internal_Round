"""FairDrop isolated attack-lab primitives.

The FastAPI router is integrated only after P1/P2 provide the shared LabRun model
and organizer authorization dependencies.  The runner and report code in this
package are deliberately framework-independent so they can be tested now.
"""

from .models import LabLimits, RunConfig, RunStatus, Scenario
from .reports import build_run_report
from .runner import LabRunner
from .store import AtomicRunStore

__all__ = [
    "AtomicRunStore",
    "LabLimits",
    "LabRunner",
    "RunConfig",
    "RunStatus",
    "Scenario",
    "build_run_report",
]
