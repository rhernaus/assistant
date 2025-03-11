"""
VM Client module.

This module contains the client that runs inside each VM and communicates with the
central server. It's responsible for executing agent tasks and reporting status.
"""

import asyncio
import json
import logging
import os
import platform
import signal
import sys
import uuid
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

import websockets
from pydantic import BaseModel, Field

from src.agent.planning import Plan, PlanningEngine, Step
from src.execution.terminal import TerminalExecutor

logger = logging.getLogger(__name__)


class VMClientConfig(BaseModel):
    """Configuration for the VM client."""
    server_url: str = Field(..., description="URL of the central server")
    vm_id: str = Field(..., description="ID of this VM instance")
    heartbeat_interval: int = Field(30, description="Seconds between heartbeat messages")
    connection_retry_interval: int = Field(5, description="Seconds to wait before reconnecting")
    max_connection_retries: int = Field(10, description="Maximum number of connection retries")


class VMClient:
    """
    Client that runs inside each VM and communicates with the central server.

    This client:
    - Establishes a WebSocket connection to the server
    - Receives tasks and executes them using the agent
    - Reports status, progress, and results back to the server
    - Handles VM lifecycle events (initialization, shutdown)
    """

    def __init__(self, config: VMClientConfig):
        """
        Initialize the VM client.

        Args:
            config: Configuration for the VM client.
        """
        self.config = config
        self.connection = None
        self.is_running = False
        self.current_plan: Optional[Plan] = None
        self.system_info = self._collect_system_info()

        # Components
        self.terminal_executor = TerminalExecutor()

        # In a real implementation, we would initialize the model client here
        # and pass it to the planning engine
        self.model_client = None  # Placeholder
        self.planning_engine = None  # Will be initialized later

        # Message handlers
        self.message_handlers = {
            "ping": self._handle_ping,
            "execute_task": self._handle_execute_task,
            "cancel_task": self._handle_cancel_task,
            "shutdown": self._handle_shutdown,
        }

    async def start(self):
        """Start the VM client and connect to the server."""
        logger.info(f"Starting VM client for VM {self.config.vm_id}")

        # Set signal handlers for graceful shutdown
        for sig in (signal.SIGINT, signal.SIGTERM):
            signal.signal(sig, self._signal_handler)

        self.is_running = True

        # Start the connection loop
        asyncio.create_task(self._connection_loop())

        # In a real implementation, we would initialize the model client here
        # self.model_client = await initialize_model_client()
        # self.planning_engine = PlanningEngine(self.model_client)

        logger.info("VM client started")

    async def stop(self):
        """Stop the VM client."""
        logger.info("Stopping VM client")
        self.is_running = False

        if self.connection and self.connection.open:
            await self.connection.close()

        logger.info("VM client stopped")

    async def _connection_loop(self):
        """Maintain a connection to the server."""
        retry_count = 0

        while self.is_running:
            try:
                if not self.connection or not self.connection.open:
                    logger.info(f"Connecting to server at {self.config.server_url}")
                    self.connection = await websockets.connect(self.config.server_url)

                    # Register with the server
                    await self._register()

                    # Reset retry count on successful connection
                    retry_count = 0

                    # Start heartbeat
                    asyncio.create_task(self._heartbeat_loop())

                # Listen for messages
                async for message in self.connection:
                    try:
                        await self._handle_message(message)
                    except Exception as e:
                        logger.exception(f"Error handling message: {e}")

            except (websockets.exceptions.ConnectionClosed,
                    websockets.exceptions.ConnectionError,
                    websockets.exceptions.InvalidStatusCode) as e:
                logger.error(f"Connection error: {e}")

                retry_count += 1
                if retry_count > self.config.max_connection_retries:
                    logger.error(f"Max retries ({self.config.max_connection_retries}) exceeded, shutting down")
                    self.is_running = False
                    break

                # Wait before retrying
                await asyncio.sleep(self.config.connection_retry_interval)

            except Exception as e:
                logger.exception(f"Unexpected error in connection loop: {e}")
                await asyncio.sleep(self.config.connection_retry_interval)

    async def _register(self):
        """Register this VM with the server."""
        register_message = {
            "type": "register",
            "vm_id": self.config.vm_id,
            "timestamp": datetime.utcnow().isoformat(),
            "system_info": self.system_info,
        }

        await self.connection.send(json.dumps(register_message))
        logger.info(f"Registered VM {self.config.vm_id} with server")

    async def _heartbeat_loop(self):
        """Send periodic heartbeat messages to the server."""
        while self.is_running and self.connection and self.connection.open:
            try:
                heartbeat_message = {
                    "type": "heartbeat",
                    "vm_id": self.config.vm_id,
                    "timestamp": datetime.utcnow().isoformat(),
                    "status": "busy" if self.current_plan else "idle",
                    "resource_usage": self._collect_resource_usage(),
                }

                await self.connection.send(json.dumps(heartbeat_message))

                await asyncio.sleep(self.config.heartbeat_interval)

            except (websockets.exceptions.ConnectionClosed,
                    websockets.exceptions.ConnectionError) as e:
                logger.error(f"Connection lost during heartbeat: {e}")
                break

            except Exception as e:
                logger.exception(f"Error in heartbeat loop: {e}")
                await asyncio.sleep(self.config.heartbeat_interval)

    async def _handle_message(self, message_text: str):
        """Handle an incoming message from the server."""
        try:
            message = json.loads(message_text)
            message_type = message.get("type")

            if message_type in self.message_handlers:
                await self.message_handlers[message_type](message)
            else:
                logger.warning(f"Unknown message type: {message_type}")

        except json.JSONDecodeError:
            logger.error(f"Invalid JSON in message: {message_text}")

    async def _handle_ping(self, message: Dict):
        """Handle a ping message from the server."""
        pong_message = {
            "type": "pong",
            "vm_id": self.config.vm_id,
            "timestamp": datetime.utcnow().isoformat(),
            "in_response_to": message.get("id"),
        }

        await self.connection.send(json.dumps(pong_message))

    async def _handle_execute_task(self, message: Dict):
        """Handle a request to execute a task."""
        task_id = message.get("task_id")
        user_id = message.get("user_id")
        session_id = message.get("session_id")
        goal = message.get("goal")

        logger.info(f"Received task {task_id} for user {user_id}: {goal}")

        # Acknowledge receipt of the task
        ack_message = {
            "type": "task_ack",
            "vm_id": self.config.vm_id,
            "task_id": task_id,
            "timestamp": datetime.utcnow().isoformat(),
        }
        await self.connection.send(json.dumps(ack_message))

        # Execute the task
        asyncio.create_task(self._execute_task(task_id, user_id, session_id, goal))

    async def _handle_cancel_task(self, message: Dict):
        """Handle a request to cancel a task."""
        task_id = message.get("task_id")

        logger.info(f"Received cancellation request for task {task_id}")

        # In a real implementation, we would have a mechanism to
        # safely cancel the task and clean up

        # For now, just acknowledge
        ack_message = {
            "type": "cancel_ack",
            "vm_id": self.config.vm_id,
            "task_id": task_id,
            "timestamp": datetime.utcnow().isoformat(),
        }
        await self.connection.send(json.dumps(ack_message))

    async def _handle_shutdown(self, message: Dict):
        """Handle a request to shut down the VM client."""
        shutdown_message = {
            "type": "shutdown_ack",
            "vm_id": self.config.vm_id,
            "timestamp": datetime.utcnow().isoformat(),
        }

        await self.connection.send(json.dumps(shutdown_message))

        # Gracefully shut down
        logger.info("Received shutdown request, stopping client")
        await self.stop()

        # In a real implementation on a VM, we might even shut down the VM itself
        # For now, just exit the process
        sys.exit(0)

    async def _execute_task(self, task_id: str, user_id: str, session_id: str, goal: str):
        """
        Execute a task using the agent.

        This is a placeholder implementation. In a real VM client, this would:
        1. Use the planning engine to create a plan
        2. Execute each step of the plan
        3. Report progress and results back to the server
        """
        try:
            # Report that we're starting
            start_message = {
                "type": "task_started",
                "vm_id": self.config.vm_id,
                "task_id": task_id,
                "timestamp": datetime.utcnow().isoformat(),
            }
            await self.connection.send(json.dumps(start_message))

            # In a real implementation, we would use the planning engine
            # For now, simulate a few steps with delays
            steps = [
                {"description": f"Analyzing the goal: {goal}", "duration": 2},
                {"description": "Searching for relevant information", "duration": 3},
                {"description": "Creating output files", "duration": 2},
                {"description": "Finalizing results", "duration": 1},
            ]

            for i, step in enumerate(steps):
                # Report step progress
                progress_message = {
                    "type": "task_progress",
                    "vm_id": self.config.vm_id,
                    "task_id": task_id,
                    "timestamp": datetime.utcnow().isoformat(),
                    "step_number": i + 1,
                    "total_steps": len(steps),
                    "description": step["description"],
                    "percent_complete": int((i + 0.5) / len(steps) * 100),
                }
                await self.connection.send(json.dumps(progress_message))

                # Simulate step execution
                await asyncio.sleep(step["duration"])

            # Report completion
            complete_message = {
                "type": "task_completed",
                "vm_id": self.config.vm_id,
                "task_id": task_id,
                "timestamp": datetime.utcnow().isoformat(),
                "result": {
                    "success": True,
                    "message": f"Completed task: {goal}",
                    "outputs": [
                        {"type": "text", "content": f"Results for '{goal}'..."}
                    ]
                },
            }
            await self.connection.send(json.dumps(complete_message))

        except Exception as e:
            logger.exception(f"Error executing task {task_id}: {e}")

            # Report error
            error_message = {
                "type": "task_error",
                "vm_id": self.config.vm_id,
                "task_id": task_id,
                "timestamp": datetime.utcnow().isoformat(),
                "error": {
                    "message": str(e),
                    "traceback": logger.formatException(e),
                },
            }
            await self.connection.send(json.dumps(error_message))

    def _collect_system_info(self) -> Dict[str, Any]:
        """Collect information about the VM system."""
        return {
            "hostname": platform.node(),
            "platform": platform.platform(),
            "python_version": platform.python_version(),
            "cpu_count": os.cpu_count(),
            "memory_total": os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES") if hasattr(os, "sysconf") else None,
        }

    def _collect_resource_usage(self) -> Dict[str, float]:
        """Collect current resource usage of the VM."""
        # In a real implementation, we would use psutil or similar
        # to get accurate resource usage
        # For now, return placeholder values
        return {
            "cpu_percent": 10.0,
            "memory_percent": 25.0,
            "disk_percent": 5.0,
        }

    def _signal_handler(self, sig, frame):
        """Handle termination signals."""
        logger.info(f"Received signal {sig}, shutting down")
        asyncio.create_task(self.stop())


def main():
    """Entry point for the VM client."""
    # In a real implementation, we would load config from environment
    # variables or a config file
    config = VMClientConfig(
        server_url="ws://orchestration-server:8000/ws/vm",
        vm_id=os.environ.get("VM_ID", str(uuid.uuid4())),
    )

    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # Create and start the client
    client = VMClient(config)

    # Run the client
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(client.start())
        loop.run_forever()
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received, shutting down")
    finally:
        loop.run_until_complete(client.stop())
        loop.close()


if __name__ == "__main__":
    main()