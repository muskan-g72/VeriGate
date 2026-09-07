import asyncio

from playwright.async_api import async_playwright


async def main():
    print("Starting Playwright...")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        await page.goto("https://example.com")

        title = await page.title()

        print("Page title:", title)

        await browser.close()

    print("Playwright test completed!")


if __name__ == "__main__":
    asyncio.run(main())