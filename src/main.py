import asyncio
import logging
import sys
from typing import Any

from src.cli.cli_argument_handler import CLIArgumentHandler
from src.core.scraper_app import run_scraper
from src.storage.storage_manager import store_data
from src.utils.command_enum import CommandEnum
from src.utils.output_mode_enum import OutputMode
from src.utils.setup_logging import setup_logger


def main():
    """Main entry point for CLI usage."""
    setup_logger(log_level=logging.DEBUG, save_to_file=False)
    logger = logging.getLogger("Main")

    try:
        args = CLIArgumentHandler().parse_and_validate_args()
        logger.info(f"Parsed arguments: {args}")

        # Handle live command differently (continuous polling)
        if args["command"] == CommandEnum.LIVE.value:
            _run_live_scraper(args, logger)
        else:
            _run_standard_scraper(args, logger)

    except ValueError as e:
        logger.error(f"Argument validation failed: {e!s}")

    except Exception as e:
        logger.error(f"Unexpected error: {e!s}", exc_info=True)


def _run_standard_scraper(args: dict, logger: logging.Logger):
    """Run standard (non-live) scraping."""
    scraped_data = asyncio.run(
        run_scraper(
            command=args["command"],
            match_links=args["match_links"],
            sport=args["sport"],
            date=args["date"],
            leagues=args["leagues"],
            season=args["season"],
            markets=args["markets"],
            max_pages=args["max_pages"],
            proxies=args["proxies"],
            browser_user_agent=args["browser_user_agent"],
            browser_locale_timezone=args["browser_locale_timezone"],
            browser_timezone_id=args["browser_timezone_id"],
            target_bookmaker=args["target_bookmaker"],
            scrape_odds_history=args["scrape_odds_history"],
            headless=args["headless"],
            preview_submarkets_only=args["preview_submarkets_only"],
            bookies_filter=args["bookies_filter"],
            period=args["period"],
        )
    )

    if scraped_data:
        store_data(
            storage_type=args["storage_type"],
            data=scraped_data,
            storage_format=args["storage_format"],
            file_path=args["file_path"],
        )
    else:
        logger.error("Scraper did not return valid data.")
        sys.exit(1)


def _run_live_scraper(args: dict, logger: logging.Logger):
    """Run live scraping with continuous polling."""
    output_mode = OutputMode(args["output_mode"])
    cycle_count = [0]  # Mutable for closure

    def on_cycle_complete(data: list[dict[str, Any]], cycle: int):
        """Callback to store data after each polling cycle."""
        cycle_count[0] = cycle
        if not data:
            logger.warning(f"Cycle {cycle}: No data to store")
            return

        # Determine file path
        base_path = args["file_path"] or f"live_odds_{args['sport']}.json"

        # For overwrite mode, just use the base path
        # For append mode, LocalDataStorage handles appending internally
        file_path = base_path

        try:
            store_data(
                storage_type=args["storage_type"],
                data=data,
                storage_format=args["storage_format"],
                file_path=file_path,
            )
            logger.info(f"Cycle {cycle}: Stored {len(data)} records to {file_path}")
        except Exception as e:
            logger.error(f"Cycle {cycle}: Failed to store data: {e}")

    logger.info("Starting live scraper (Ctrl+C to stop gracefully)...")

    try:
        scraped_data = asyncio.run(
            run_scraper(
                command=args["command"],
                match_links=args["match_links"],
                sport=args["sport"],
                date=None,
                leagues=args["leagues"],
                season=None,
                markets=args["markets"],
                max_pages=None,
                proxies=args["proxies"],
                browser_user_agent=args["browser_user_agent"],
                browser_locale_timezone=args["browser_locale_timezone"],
                browser_timezone_id=args["browser_timezone_id"],
                target_bookmaker=args["target_bookmaker"],
                scrape_odds_history=args["scrape_odds_history"],
                headless=args["headless"],
                preview_submarkets_only=args["preview_submarkets_only"],
                bookies_filter=args["bookies_filter"],
                period=args["period"],
                poll_interval=args["poll_interval"],
                max_cycles=args["max_cycles"],
                on_cycle_complete=on_cycle_complete if output_mode == OutputMode.APPEND else None,
            )
        )

        # For overwrite mode, store final results
        if output_mode == OutputMode.OVERWRITE and scraped_data:
            base_path = args["file_path"] or f"live_odds_{args['sport']}.json"
            store_data(
                storage_type=args["storage_type"],
                data=scraped_data,
                storage_format=args["storage_format"],
                file_path=base_path,
            )

        logger.info(f"Live scraping completed after {cycle_count[0]} cycles")

    except KeyboardInterrupt:
        logger.info("Live scraping interrupted by user")


if __name__ == "__main__":
    main()
