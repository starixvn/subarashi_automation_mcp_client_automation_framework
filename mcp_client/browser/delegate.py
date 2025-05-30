import asyncio
import json
import logging
from playwright.async_api import async_playwright, Page
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ClientBrowserManager:
    def __init__(self):
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None

    async def initialize(self):
        """Initialize browser on client."""
        logger.info("Starting Playwright on client machine")
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(headless=False)
        self.context = await self.browser.new_context(
            viewport={"width": 1200, "height": 900}
        )
        self.page = await self.context.new_page()
        return self.page

    async def close(self):
        """Cleanup resources."""
        if self.page:
            await self.page.close()
            self.page = None
        if self.context:
            await self.context.close()
            self.context = None
        if self.browser:
            await self.browser.close()
            self.browser = None
        if self.playwright:
            await self.playwright.stop()
            self.playwright = None

    async def execute_command(self, command):
        """Execute browser command."""
        if not self.page:
            await self.initialize()

        action = command.get("action")
        args = command.get("args", {})

        try:
            if action == "navigate":
                url = args.get("url")
                logger.info(f"Navigating to {url}")
                await self.page.goto(url, wait_until="domcontentloaded")
                return {
                    "success": True,
                    "title": await self.page.title(),
                    "url": self.page.url,
                }

            elif action == "click":
                selector = args.get("selector")
                await self.page.click(selector)
                return {"success": True, "message": f"Clicked element {selector}"}

            elif action == "fill":
                selector = args.get("selector")
                text = args.get("text")
                await self.page.fill(selector, text)
                return {"success": True, "message": f"Filled {selector} with text"}

            # Implement other commands (scroll, screenshot, etc.)
            # ...

            else:
                return {"success": False, "error": f"Unknown action: {action}"}

        except Exception as e:
            logger.error(f"Error executing browser command: {e}")
            return {"success": False, "error": str(e)} 