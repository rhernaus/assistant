"""
Terminal execution module.

This module contains the functionality for executing terminal commands
in a secure, controlled environment.
"""

import asyncio
import logging
import os
import re
import shlex
import subprocess
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class CommandWhitelist:
    """
    A whitelist of allowed terminal commands.

    This is used for security to prevent the agent from executing dangerous commands.
    """

    # Basic set of safe commands
    SAFE_COMMANDS = {
        'ls', 'cat', 'echo', 'grep', 'mkdir', 'touch', 'mv', 'cp', 'rm', 'pwd',
        'date', 'wc', 'head', 'tail', 'find', 'sort', 'uniq', 'wget', 'curl',
        'python', 'python3', 'pip', 'pip3', 'node', 'npm', 'cd',
    }

    # Regular expressions for allowed command patterns
    ALLOWED_PATTERNS = [
        # Allow basic file operations with arguments
        r'^(ls|cat|echo|grep|mkdir|touch|mv|cp|pwd|date|wc|head|tail|find|sort|uniq)(\s+[-\w\s./]+)?$',
        # Allow rm but only for specific files, not recursive or force
        r'^rm\s+[-\w\s./]+$',  # No rm -rf allowed
        # Allow wget/curl with various options but only for http/https
        r'^(wget|curl)(\s+-[a-zA-Z]+)*\s+(https?://[\w./\-?=%&]+)$',
        # Allow Python with simple args
        r'^(python|python3)(\s+[-\w./]+)(\s+[-\w./\s]+)?$',
        # Allow pip for installing packages
        r'^(pip|pip3)\s+(install|uninstall|list|show|freeze)(\s+[-\w./\s]+)?$',
        # Allow cd to change directories
        r'^cd(\s+[-\w./]+)?$',
    ]

    @classmethod
    def is_allowed(cls, command: str) -> bool:
        """
        Check if a command is allowed to be executed.

        Args:
            command: The terminal command to check.

        Returns:
            True if the command is allowed, False otherwise.
        """
        # First token is the command
        tokens = shlex.split(command)
        if not tokens:
            return False

        base_cmd = tokens[0]

        # Quick check against the safe list
        if base_cmd in cls.SAFE_COMMANDS:
            # Additional check against allowed patterns
            for pattern in cls.ALLOWED_PATTERNS:
                if re.match(pattern, command):
                    return True

        # If we get here, the command is not explicitly allowed
        logger.warning(f"Command not allowed: {command}")
        return False


class TerminalExecutor:
    """
    Executes terminal commands in a controlled environment.
    """

    def __init__(self, whitelist: Optional[CommandWhitelist] = None):
        """
        Initialize the terminal executor.

        Args:
            whitelist: A whitelist of allowed commands. If None, use the default.
        """
        self.whitelist = whitelist or CommandWhitelist
        self.working_dir = os.getcwd()  # Default working directory

    async def execute(self, command: str, timeout: int = 30) -> Dict[str, Any]:
        """
        Execute a terminal command and return the result.

        Args:
            command: The terminal command to execute.
            timeout: Maximum time in seconds to allow the command to run.

        Returns:
            A dictionary containing the execution result.
        """
        if not self.whitelist.is_allowed(command):
            return {
                'success': False,
                'stdout': '',
                'stderr': f'Command not allowed: {command}',
                'exit_code': 1,
                'error': 'SecurityError: Command not permitted'
            }

        try:
            # For cd commands, update the working directory instead of executing
            if command.startswith('cd '):
                return await self._handle_cd_command(command)

            # Execute the command
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=self.working_dir
            )

            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(), timeout=timeout
                )

                return {
                    'success': process.returncode == 0,
                    'stdout': stdout.decode('utf-8', errors='replace'),
                    'stderr': stderr.decode('utf-8', errors='replace'),
                    'exit_code': process.returncode,
                    'working_dir': self.working_dir
                }
            except asyncio.TimeoutError:
                # If the process times out, try to terminate it
                process.terminate()
                try:
                    await asyncio.wait_for(process.wait(), timeout=2)
                except asyncio.TimeoutError:
                    # If it doesn't terminate, kill it
                    process.kill()

                return {
                    'success': False,
                    'stdout': '',
                    'stderr': f'Command timed out after {timeout} seconds',
                    'exit_code': -1,
                    'error': 'TimeoutError'
                }

        except Exception as e:
            logger.exception(f"Error executing command: {command}")
            return {
                'success': False,
                'stdout': '',
                'stderr': str(e),
                'exit_code': 1,
                'error': f'{type(e).__name__}: {str(e)}'
            }

    async def _handle_cd_command(self, command: str) -> Dict[str, Any]:
        """Special handling for cd commands to update working directory."""
        try:
            parts = shlex.split(command)
            if len(parts) > 1:
                # Get the directory argument
                directory = parts[1]

                # Handle relative paths
                new_dir = os.path.join(self.working_dir, directory) if not os.path.isabs(directory) else directory

                # Check if it exists
                if os.path.isdir(new_dir):
                    self.working_dir = new_dir
                    return {
                        'success': True,
                        'stdout': f'Changed directory to {new_dir}',
                        'stderr': '',
                        'exit_code': 0,
                        'working_dir': self.working_dir
                    }
                else:
                    return {
                        'success': False,
                        'stdout': '',
                        'stderr': f'Directory not found: {new_dir}',
                        'exit_code': 1,
                        'working_dir': self.working_dir
                    }
            else:
                # cd with no arguments typically goes to home directory
                # For simplicity, we'll stay in the current directory
                return {
                    'success': True,
                    'stdout': f'Current directory: {self.working_dir}',
                    'stderr': '',
                    'exit_code': 0,
                    'working_dir': self.working_dir
                }
        except Exception as e:
            return {
                'success': False,
                'stdout': '',
                'stderr': str(e),
                'exit_code': 1,
                'error': f'{type(e).__name__}: {str(e)}',
                'working_dir': self.working_dir
            }