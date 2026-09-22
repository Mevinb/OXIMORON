import os
from pathlib import Path

import pytest

from core.contracts.errors import ErrorCode, OximoronException
from core.contracts.models import RuntimeDiscoveryRecord
from core.supervisor.lock import SupervisorLock


def test_supervisor_lock_acquisition_and_release(tmp_path: Path):
    lock_file = tmp_path / ".supervisor.lock"
    discovery_file = tmp_path / "discovery.json"

    lock1 = SupervisorLock(lock_path=lock_file, discovery_path=discovery_file)
    lock1.acquire()

    # Write discovery
    rec = RuntimeDiscoveryRecord(
        supervisor_instance_id="inst-1",
        pid=os.getpid(),
        create_time=12345.67,
        host="127.0.0.1",
        port=6969,
        base_url="http://127.0.0.1:6969/api/v1",
        credential_file=str(tmp_path / "creds.json"),
    )
    lock1.write_discovery(rec)
    assert discovery_file.exists()
    assert lock1.read_discovery().supervisor_instance_id == "inst-1"

    # Second lock attempt must fail
    lock2 = SupervisorLock(lock_path=lock_file, discovery_path=discovery_file)
    with pytest.raises(OximoronException) as exc_info:
        lock2.acquire()
    assert exc_info.value.code == ErrorCode.CONFLICT

    # Release lock 1
    lock1.release()
    assert not discovery_file.exists()

    # Now lock 2 should succeed
    lock2.acquire()
    lock2.release()
