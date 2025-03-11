"""
VM Manager module.

This module provides functionality for managing the lifecycle of Ubuntu VMs
that host agent instances. It handles provisioning, monitoring, and cleanup.
"""

import asyncio
import logging
import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class VMState(str, Enum):
    """Possible states for a VM."""
    INITIALIZING = "initializing"
    READY = "ready"
    BUSY = "busy"
    ERROR = "error"
    SHUTTING_DOWN = "shutting_down"
    TERMINATED = "terminated"


class VMInfo(BaseModel):
    """Information about a VM instance."""
    id: str = Field(..., description="Unique identifier for this VM")
    user_id: Optional[str] = Field(None, description="ID of the user this VM is assigned to")
    session_id: Optional[str] = Field(None, description="ID of the active session")
    state: VMState = Field(default=VMState.INITIALIZING, description="Current state of the VM")
    ip_address: Optional[str] = Field(None, description="IP address of the VM")
    hostname: Optional[str] = Field(None, description="Hostname of the VM")
    created_at: str = Field(..., description="When this VM was created")
    last_active: Optional[str] = Field(None, description="When this VM was last active")
    resource_usage: Dict[str, float] = Field(default_factory=dict, description="Resource usage metrics")
    error_message: Optional[str] = Field(None, description="Error message if the VM is in ERROR state")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class VMConfig(BaseModel):
    """Configuration for a VM."""
    cpu_count: int = Field(default=2, description="Number of CPU cores")
    memory_mb: int = Field(default=4096, description="Memory in MB")
    disk_size_gb: int = Field(default=20, description="Disk size in GB")
    image_id: str = Field(..., description="ID of the VM image to use")
    network_config: Dict[str, Any] = Field(default_factory=dict, description="Network configuration")
    startup_script: Optional[str] = Field(None, description="Script to run on VM startup")
    environment_vars: Dict[str, str] = Field(default_factory=dict, description="Environment variables")


class VMManager:
    """
    Manages the lifecycle of Ubuntu VMs for agent instances.

    This class handles:
    - Provisioning new VMs when needed
    - Monitoring VM health and resource usage
    - Managing a pool of warm VMs for quick startup
    - Cleaning up VMs when sessions end
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the VM manager.

        Args:
            config: Configuration options for the VM manager.
        """
        self.config = config
        self.active_vms: Dict[str, VMInfo] = {}
        self.vm_pool: List[VMInfo] = []
        self.vm_pool_size = config.get("vm_pool_size", 5)
        self.vm_idle_timeout = config.get("vm_idle_timeout_minutes", 30) * 60  # Convert to seconds

    async def start(self):
        """Start the VM manager and initialize the VM pool."""
        logger.info("Starting VM manager...")

        # Initialize the VM pool
        await self._replenish_vm_pool()

        # Start background tasks
        asyncio.create_task(self._monitor_vms())
        asyncio.create_task(self._maintain_vm_pool())

    async def provision_vm(self, user_id: str, session_id: str) -> VMInfo:
        """
        Provision a VM for a user session.

        Args:
            user_id: ID of the user requesting the VM.
            session_id: ID of the session.

        Returns:
            Information about the provisioned VM.
        """
        # First, try to get a VM from the pool
        if self.vm_pool:
            vm_info = self.vm_pool.pop()
            logger.info(f"Assigning pooled VM {vm_info.id} to user {user_id}, session {session_id}")

            # Update the VM info
            vm_info.user_id = user_id
            vm_info.session_id = session_id
            vm_info.state = VMState.BUSY
            vm_info.last_active = datetime.utcnow().isoformat()

            # Move to active VMs
            self.active_vms[vm_info.id] = vm_info
            return vm_info

        # If no VMs in the pool, create a new one
        logger.info(f"No VMs in pool. Creating new VM for user {user_id}, session {session_id}")
        vm_info = await self._create_vm(user_id, session_id)
        self.active_vms[vm_info.id] = vm_info
        return vm_info

    async def release_vm(self, vm_id: str, recycle: bool = True) -> None:
        """
        Release a VM from a user session.

        Args:
            vm_id: ID of the VM to release.
            recycle: Whether to recycle the VM back to the pool.
        """
        if vm_id not in self.active_vms:
            logger.warning(f"Attempted to release non-existent VM: {vm_id}")
            return

        vm_info = self.active_vms.pop(vm_id)
        logger.info(f"Releasing VM {vm_id} from user {vm_info.user_id}, session {vm_info.session_id}")

        if recycle:
            # Reset the VM to a clean state and return to the pool
            await self._recycle_vm(vm_info)
            self.vm_pool.append(vm_info)
        else:
            # Terminate the VM
            await self._terminate_vm(vm_info)

    async def get_vm_info(self, vm_id: str) -> Optional[VMInfo]:
        """Get information about a specific VM."""
        return self.active_vms.get(vm_id) or next((vm for vm in self.vm_pool if vm.id == vm_id), None)

    async def get_vms_for_user(self, user_id: str) -> List[VMInfo]:
        """Get all VMs assigned to a specific user."""
        return [vm for vm in self.active_vms.values() if vm.user_id == user_id]

    async def _create_vm(self, user_id: Optional[str] = None, session_id: Optional[str] = None) -> VMInfo:
        """
        Create a new VM instance.

        In a real implementation, this would interact with a cloud provider's API
        to provision an actual VM. For now, it creates a placeholder.
        """
        vm_id = str(uuid.uuid4())

        # In a real implementation, we would make API calls to the cloud provider here
        # For now, simulate VM creation with a delay
        await asyncio.sleep(2)

        vm_info = VMInfo(
            id=vm_id,
            user_id=user_id,
            session_id=session_id,
            state=VMState.READY if user_id else VMState.READY,
            ip_address=f"10.0.0.{hash(vm_id) % 255}",  # Fake IP for demonstration
            hostname=f"agent-vm-{vm_id[:8]}",
            created_at=datetime.utcnow().isoformat(),
            last_active=datetime.utcnow().isoformat() if user_id else None,
            resource_usage={"cpu": 0.0, "memory": 0.0, "disk": 0.0},
        )

        logger.info(f"Created new VM {vm_id}")
        return vm_info

    async def _recycle_vm(self, vm_info: VMInfo) -> None:
        """
        Recycle a VM for reuse.

        This would reset the VM to a clean state, typically by:
        1. Stopping the agent process
        2. Clearing any user data
        3. Resetting to a baseline snapshot
        """
        # In a real implementation, we would send commands to the VM to reset it
        # For now, simulate with a delay
        vm_info.state = VMState.INITIALIZING
        await asyncio.sleep(1)

        # Reset VM properties
        vm_info.user_id = None
        vm_info.session_id = None
        vm_info.state = VMState.READY
        vm_info.last_active = None
        vm_info.resource_usage = {"cpu": 0.0, "memory": 0.0, "disk": 0.0}
        vm_info.error_message = None

        logger.info(f"Recycled VM {vm_info.id}")

    async def _terminate_vm(self, vm_info: VMInfo) -> None:
        """
        Terminate a VM.

        In a real implementation, this would call the cloud provider API to
        shut down and delete the VM.
        """
        # In a real implementation, make API calls to terminate the VM
        # For now, simulate with a delay
        vm_info.state = VMState.SHUTTING_DOWN
        await asyncio.sleep(1)

        vm_info.state = VMState.TERMINATED
        logger.info(f"Terminated VM {vm_info.id}")

    async def _replenish_vm_pool(self) -> None:
        """Ensure the VM pool has the desired number of VMs."""
        needed_vms = max(0, self.vm_pool_size - len(self.vm_pool))
        if needed_vms > 0:
            logger.info(f"Replenishing VM pool with {needed_vms} VMs")
            for _ in range(needed_vms):
                vm_info = await self._create_vm()
                self.vm_pool.append(vm_info)

    async def _monitor_vms(self) -> None:
        """
        Periodically monitor VM health and resource usage.

        This runs as a background task.
        """
        while True:
            try:
                # Update resource usage for all VMs
                for vm_id, vm_info in self.active_vms.items():
                    if vm_info.state in (VMState.READY, VMState.BUSY):
                        # In a real implementation, query the VM for resource usage
                        # For now, simulate with random values
                        import random
                        vm_info.resource_usage = {
                            "cpu": random.uniform(0, 100),
                            "memory": random.uniform(0, 100),
                            "disk": random.uniform(0, 100),
                        }

                        # Check for idle VMs
                        if vm_info.last_active:
                            last_active = datetime.fromisoformat(vm_info.last_active)
                            now = datetime.utcnow()
                            idle_seconds = (now - last_active).total_seconds()

                            if idle_seconds > self.vm_idle_timeout:
                                logger.info(f"VM {vm_id} idle for {idle_seconds}s, releasing")
                                asyncio.create_task(self.release_vm(vm_id))

                # Also check pool VMs
                for vm_info in self.vm_pool:
                    # Simple health check
                    pass

            except Exception as e:
                logger.exception(f"Error in VM monitoring: {e}")

            # Sleep before next monitoring cycle
            await asyncio.sleep(60)  # Check every minute

    async def _maintain_vm_pool(self) -> None:
        """
        Maintain the VM pool at the desired size.

        This runs as a background task.
        """
        while True:
            try:
                await self._replenish_vm_pool()
            except Exception as e:
                logger.exception(f"Error maintaining VM pool: {e}")

            # Sleep before next cycle
            await asyncio.sleep(300)  # Check every 5 minutes