from src.execution.browser import BrowserAutomator

class VMAgent:
    def __init__(self, server_url: str):
        # Initialize browser automator
        self.browser = BrowserAutomator(headless=True)

        # ... rest of initialization ...

    async def start(self):
        # ... existing start code ...

        try:
            # Connect to server
            await self.comm.connect()
            logger.info("Connected to server")

            # Start browser if needed
            if self.config.get("ENABLE_BROWSER_AUTOMATION", True):
                await self.browser.start()

            # ... rest of start code ...

        # ... rest of method ...

    def register_command_handlers(self):
        # ... existing handlers ...
        self.comm.register_command_handler("browser_navigate", self.handle_browser_navigate)
        self.comm.register_command_handler("browser_click", self.handle_browser_click)
        self.comm.register_command_handler("browser_type", self.handle_browser_type)
        self.comm.register_command_handler("browser_extract", self.handle_browser_extract)
        self.comm.register_command_handler("browser_screenshot", self.handle_browser_screenshot)

    # ... existing methods ...

    async def handle_browser_navigate(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle browser navigation command.

        Args:
            params: Parameters for the command, including URL.

        Returns:
            Result of the navigation.
        """
        url = params.get("url")
        if not url:
            return {
                "success": False,
                "error": "No URL provided"
            }

        # Start browser if not already started
        if not self.browser.browser:
            await self.browser.start()

        # Navigate to URL
        self.state.log_terminal_output(f"Navigating to {url}")
        result = await self.browser.navigate(url)

        if result["success"]:
            self.state.log_terminal_output(f"Navigated to {url} - Page title: {result.get('title', 'Unknown')}")
        else:
            self.state.log_terminal_output(f"Error navigating to {url}: {result.get('error', 'Unknown error')}")

        return result

    async def handle_browser_click(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle browser click command.

        Args:
            params: Parameters for the command, including selector.

        Returns:
            Result of the click.
        """
        selector = params.get("selector")
        if not selector:
            return {
                "success": False,
                "error": "No selector provided"
            }

        if not self.browser.browser:
            return {
                "success": False,
                "error": "Browser not started"
            }

        self.state.log_terminal_output(f"Clicking element: {selector}")
        result = await self.browser.click(selector)

        if result["success"]:
            self.state.log_terminal_output(f"Clicked element: {selector}")
        else:
            self.state.log_terminal_output(f"Error clicking element {selector}: {result.get('error', 'Unknown error')}")

        return result

    async def handle_browser_type(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle browser typing command.

        Args:
            params: Parameters for the command, including selector and text.

        Returns:
            Result of the typing.
        """
        selector = params.get("selector")
        text = params.get("text")

        if not selector or text is None:
            return {
                "success": False,
                "error": "Both selector and text must be provided"
            }

        if not self.browser.browser:
            return {
                "success": False,
                "error": "Browser not started"
            }

        self.state.log_terminal_output(f"Typing '{text}' into element: {selector}")
        result = await self.browser.type(selector, text)

        if result["success"]:
            self.state.log_terminal_output(f"Typed text into element: {selector}")
        else:
            self.state.log_terminal_output(f"Error typing into element {selector}: {result.get('error', 'Unknown error')}")

        return result

    async def handle_browser_extract(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle browser text extraction command.

        Args:
            params: Parameters for the command, including selector and multiple flag.

        Returns:
            Result of the extraction.
        """
        selector = params.get("selector")
        multiple = params.get("multiple", False)

        if not selector:
            return {
                "success": False,
                "error": "No selector provided"
            }

        if not self.browser.browser:
            return {
                "success": False,
                "error": "Browser not started"
            }

        self.state.log_terminal_output(f"Extracting text from {'' if multiple else 'element'}: {selector}")

        if multiple:
            result = await self.browser.extract_multiple(selector)
            if result["success"]:
                self.state.log_terminal_output(f"Extracted text from {result.get('count', 0)} elements")
            else:
                self.state.log_terminal_output(f"Error extracting text: {result.get('error', 'Unknown error')}")
        else:
            result = await self.browser.extract_text(selector)
            if result["success"]:
                text = result.get("text", "").strip()
                self.state.log_terminal_output(f"Extracted text: {text[:100]}{'...' if len(text) > 100 else ''}")
            else:
                self.state.log_terminal_output(f"Error extracting text: {result.get('error', 'Unknown error')}")

        return result

    async def handle_browser_screenshot(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle browser screenshot command.

        Args:
            params: Parameters for the command, including name.

        Returns:
            Result of the screenshot.
        """
        name = params.get("name")

        if not self.browser.browser:
            return {
                "success": False,
                "error": "Browser not started"
            }

        self.state.log_terminal_output("Taking screenshot")
        result = await self.browser.take_screenshot(name)

        if result["success"]:
            self.state.log_terminal_output(f"Screenshot saved to {result.get('path', 'unknown')}")
        else:
            self.state.log_terminal_output(f"Error taking screenshot: {result.get('error', 'Unknown error')}")

        return result

    # ... existing methods ...

    async def execute_next_step(self):
        # ... existing code for getting the current step ...

        # Execute the step based on action type
        result = None
        if step.action_type == "terminal_command":
            # ... existing terminal command execution ...
        elif step.action_type == "browser_action":
            action = step.action_params.get("action")
            if not action:
                step.status = "failed"
                step.result = {
                    "success": False,
                    "error": "No browser action specified"
                }
            else:
                # Execute the browser action
                self.state.log_terminal_output(f"Executing browser action: {action}")

                if action == "navigate":
                    url = step.action_params.get("url")
                    if url:
                        result = await self.handle_browser_navigate({"url": url})
                    else:
                        result = {"success": False, "error": "No URL provided for navigation"}
                elif action == "click":
                    selector = step.action_params.get("selector")
                    if selector:
                        result = await self.handle_browser_click({"selector": selector})
                    else:
                        result = {"success": False, "error": "No selector provided for click"}
                elif action == "type":
                    selector = step.action_params.get("selector")
                    text = step.action_params.get("text")
                    if selector and text is not None:
                        result = await self.handle_browser_type({"selector": selector, "text": text})
                    else:
                        result = {"success": False, "error": "Missing selector or text for type action"}
                elif action == "extract":
                    selector = step.action_params.get("selector")
                    multiple = step.action_params.get("multiple", False)
                    if selector:
                        result = await self.handle_browser_extract({"selector": selector, "multiple": multiple})
                    else:
                        result = {"success": False, "error": "No selector provided for extraction"}
                elif action == "screenshot":
                    name = step.action_params.get("name")
                    result = await self.handle_browser_screenshot({"name": name})
                else:
                    result = {"success": False, "error": f"Unknown browser action: {action}"}

                # Set step result and status
                step.result = result
                step.status = "completed" if result.get("success", False) else "failed"
        else:
            # ... existing code for unknown action types ...

        # ... rest of the method ...