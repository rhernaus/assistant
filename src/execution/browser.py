"""
Browser automation module.

This module provides functionality for controlling a web browser
to perform automated tasks.
"""

import asyncio
import logging
import os
import time
from typing import Any, Dict, List, Optional

from playwright.async_api import (Browser, BrowserContext, Page,
                                  async_playwright)

logger = logging.getLogger(__name__)

class BrowserAutomator:
    """
    Browser automation using Playwright.

    This class provides methods to automate browser actions like navigation,
    clicking, typing, and extracting data from web pages.
    """

    def __init__(self, headless: bool = True):
        """
        Initialize the browser automator.

        Args:
            headless: Whether to run the browser in headless mode.
        """
        self.headless = headless
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.screenshots_dir = os.path.join(os.getcwd(), "screenshots")

        # Create screenshots directory if it doesn't exist
        os.makedirs(self.screenshots_dir, exist_ok=True)

    async def start(self):
        """Start the browser."""
        if self.browser:
            return

        logger.info("Starting browser")
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(headless=self.headless)
        self.context = await self.browser.new_context(
            viewport={"width": 1280, "height": 800},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        )
        self.page = await self.context.new_page()

        # Set default timeout
        self.page.set_default_timeout(30000)  # 30 seconds

        # Listen for console messages
        self.page.on("console", lambda msg: logger.debug(f"Browser console: {msg.text}"))

    async def stop(self):
        """Stop the browser."""
        if not self.browser:
            return

        logger.info("Stopping browser")
        if self.page:
            await self.page.close()
            self.page = None

        if self.context:
            await self.context.close()
            self.context = None

        if self.browser:
            await self.browser.close()
            self.browser = None

        if hasattr(self, "playwright") and self.playwright:
            await self.playwright.stop()

    async def navigate(self, url: str) -> Dict[str, Any]:
        """
        Navigate to a URL.

        Args:
            url: URL to navigate to.

        Returns:
            Result of the navigation.
        """
        if not self.page:
            return {
                "success": False,
                "error": "Browser not started"
            }

        try:
            logger.info(f"Navigating to {url}")
            response = await self.page.goto(url)

            # Take a screenshot
            screenshot_path = os.path.join(self.screenshots_dir, f"navigate_{int(time.time())}.png")
            await self.page.screenshot(path=screenshot_path)

            return {
                "success": True,
                "url": self.page.url,
                "status": response.status if response else None,
                "title": await self.page.title(),
                "screenshot_path": screenshot_path
            }
        except Exception as e:
            logger.exception(f"Error navigating to {url}: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def click(self, selector: str) -> Dict[str, Any]:
        """
        Click an element.

        Args:
            selector: CSS selector for the element to click.

        Returns:
            Result of the click.
        """
        if not self.page:
            return {
                "success": False,
                "error": "Browser not started"
            }

        try:
            logger.info(f"Clicking element: {selector}")

            # Wait for the element to be visible
            await self.page.wait_for_selector(selector, state="visible")

            # Click the element
            await self.page.click(selector)

            # Take a screenshot
            screenshot_path = os.path.join(self.screenshots_dir, f"click_{int(time.time())}.png")
            await self.page.screenshot(path=screenshot_path)

            return {
                "success": True,
                "url": self.page.url,
                "title": await self.page.title(),
                "screenshot_path": screenshot_path
            }
        except Exception as e:
            logger.exception(f"Error clicking element {selector}: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def type(self, selector: str, text: str) -> Dict[str, Any]:
        """
        Type text into an input field.

        Args:
            selector: CSS selector for the input field.
            text: Text to type.

        Returns:
            Result of the typing.
        """
        if not self.page:
            return {
                "success": False,
                "error": "Browser not started"
            }

        try:
            logger.info(f"Typing '{text}' into element: {selector}")

            # Wait for the element to be visible
            await self.page.wait_for_selector(selector, state="visible")

            # Clear the input field
            await self.page.fill(selector, "")

            # Type the text
            await self.page.type(selector, text)

            # Take a screenshot
            screenshot_path = os.path.join(self.screenshots_dir, f"type_{int(time.time())}.png")
            await self.page.screenshot(path=screenshot_path)

            return {
                "success": True,
                "url": self.page.url,
                "title": await self.page.title(),
                "screenshot_path": screenshot_path
            }
        except Exception as e:
            logger.exception(f"Error typing into element {selector}: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def extract_text(self, selector: str) -> Dict[str, Any]:
        """
        Extract text from an element.

        Args:
            selector: CSS selector for the element.

        Returns:
            Text content of the element.
        """
        if not self.page:
            return {
                "success": False,
                "error": "Browser not started"
            }

        try:
            logger.info(f"Extracting text from element: {selector}")

            # Wait for the element to be visible
            await self.page.wait_for_selector(selector, state="visible")

            # Extract the text
            text = await self.page.text_content(selector)

            return {
                "success": True,
                "text": text,
                "selector": selector
            }
        except Exception as e:
            logger.exception(f"Error extracting text from element {selector}: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def extract_multiple(self, selector: str) -> Dict[str, Any]:
        """
        Extract text from multiple elements.

        Args:
            selector: CSS selector for the elements.

        Returns:
            List of text content from the elements.
        """
        if not self.page:
            return {
                "success": False,
                "error": "Browser not started"
            }

        try:
            logger.info(f"Extracting text from multiple elements: {selector}")

            # Wait for at least one element to be visible
            await self.page.wait_for_selector(selector, state="visible")

            # Get all elements matching the selector
            elements = await self.page.query_selector_all(selector)

            # Extract text from each element
            texts = []
            for element in elements:
                text = await element.text_content()
                texts.append(text.strip())

            return {
                "success": True,
                "texts": texts,
                "count": len(texts),
                "selector": selector
            }
        except Exception as e:
            logger.exception(f"Error extracting text from elements {selector}: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def take_screenshot(self, name: str = None) -> Dict[str, Any]:
        """
        Take a screenshot of the current page.

        Args:
            name: Optional name for the screenshot.

        Returns:
            Path to the screenshot file.
        """
        if not self.page:
            return {
                "success": False,
                "error": "Browser not started"
            }

        try:
            # Generate filename
            filename = name or f"screenshot_{int(time.time())}.png"
            if not filename.endswith(".png"):
                filename += ".png"

            screenshot_path = os.path.join(self.screenshots_dir, filename)

            # Take screenshot
            await self.page.screenshot(path=screenshot_path, full_page=True)

            return {
                "success": True,
                "path": screenshot_path,
                "url": self.page.url
            }
        except Exception as e:
            logger.exception(f"Error taking screenshot: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def wait_for_navigation(self) -> Dict[str, Any]:
        """
        Wait for navigation to complete.

        Returns:
            Result of the wait.
        """
        if not self.page:
            return {
                "success": False,
                "error": "Browser not started"
            }

        try:
            logger.info("Waiting for navigation to complete")

            # Wait for the load event
            await self.page.wait_for_load_state("load")

            # Take a screenshot
            screenshot_path = os.path.join(self.screenshots_dir, f"navigation_{int(time.time())}.png")
            await self.page.screenshot(path=screenshot_path)

            return {
                "success": True,
                "url": self.page.url,
                "title": await self.page.title(),
                "screenshot_path": screenshot_path
            }
        except Exception as e:
            logger.exception(f"Error waiting for navigation: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def execute_script(self, script: str) -> Dict[str, Any]:
        """
        Execute JavaScript in the page.

        Args:
            script: JavaScript code to execute.

        Returns:
            Result of the script execution.
        """
        if not self.page:
            return {
                "success": False,
                "error": "Browser not started"
            }

        try:
            logger.info("Executing JavaScript in page")

            # Execute the script
            result = await self.page.evaluate(script)

            return {
                "success": True,
                "result": result
            }
        except Exception as e:
            logger.exception(f"Error executing script: {e}")
            return {
                "success": False,
                "error": str(e)
            }