from datetime import UTC, datetime
import logging
import re
from typing import Any

from bs4 import BeautifulSoup


class OddsParser:
    """Handles parsing of odds data from HTML content."""

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)

    def parse_market_odds(
        self, html_content: str, period: str, odds_labels: list, target_bookmaker: str | None = None
    ) -> list[dict[str, Any]]:
        """
        Parses odds for a given market type in a generic way.

        Args:
            html_content (str): The HTML content of the page.
            period (str): The match period (e.g., "FullTime").
            odds_labels (list): A list of labels defining the expected odds columns (e.g., ["odds_over", "odds_under"]).
            target_bookmaker (str, optional): If set, only parse odds for this bookmaker.

        Returns:
            list[dict]: A list of dictionaries containing bookmaker odds.
        """
        self.logger.info("Parsing odds from HTML content.")
        soup = BeautifulSoup(html_content, "html.parser")

        # Try broader "border-black-borders" pattern first as it works better
        bookmaker_blocks = soup.find_all("div", class_=re.compile(r"border-black-borders"))

        if not bookmaker_blocks:
            # Fallback to broader selector
            bookmaker_blocks = soup.find_all("div", class_=re.compile(r"^border-black-borders flex h-9"))

        if not bookmaker_blocks:
            self.logger.warning("No bookmaker blocks found.")
            return []

        odds_data = []
        for block in bookmaker_blocks:
            try:
                bookmaker_name = self._extract_bookmaker_name(block)

                if not bookmaker_name or bookmaker_name == "Unknown":
                    continue

                if target_bookmaker and bookmaker_name.lower() != target_bookmaker.lower():
                    continue

                odds_blocks = block.find_all("div", class_=re.compile(r"flex-center.*flex-col.*font-bold"))

                # Also try alternative odds selectors for live pages
                if len(odds_blocks) < len(odds_labels):
                    odds_blocks = block.find_all("p", class_=re.compile(r"height-content"))
                    # Filter to only elements that look like odds (contain numbers or +/-)
                    odds_blocks = [b for b in odds_blocks if re.search(r"[\d.+-]", b.get_text(strip=True))]

                if len(odds_blocks) < len(odds_labels):
                    self.logger.warning(f"Incomplete odds data for bookmaker: {bookmaker_name}. Skipping...")
                    continue

                extracted_odds = {label: odds_blocks[i].get_text(strip=True) for i, label in enumerate(odds_labels)}

                for key, value in extracted_odds.items():
                    extracted_odds[key] = re.sub(r"(\d+\.\d+)\1", r"\1", value)

                extracted_odds["bookmaker_name"] = bookmaker_name
                extracted_odds["period"] = period
                odds_data.append(extracted_odds)

            except Exception as e:
                self.logger.error(f"Error parsing odds: {e}")
                continue

        self.logger.info(f"Successfully parsed odds for {len(odds_data)} bookmakers.")
        return odds_data

    def _extract_bookmaker_name(self, block) -> str:
        """
        Extract bookmaker name from a block element.
        Handles both pre-match (img.bookmaker-logo) and live page (p/a text) structures.

        Args:
            block: BeautifulSoup element containing bookmaker info.

        Returns:
            str: Bookmaker name or "Unknown" if not found.
        """
        # Known bookmaker patterns to validate against
        bookmaker_patterns = [
            r"bet365", r"betmgm", r"fanduel", r"draftkings", r"caesars",
            r"pointsbet", r"betrivers", r"unibet", r"william\s*hill", r"ladbrokes",
            r"betfair", r"pinnacle", r"bovada", r"betonline", r"mybookie",
            r"betway", r"888", r"bwin", r"betfred", r"paddy\s*power",
            r"sportsbet", r"tab", r"neds", r"betsson", r"10bet",
            r"1xbet", r"melbet", r"22bet", r"stake", r"cloudbet",
        ]

        def looks_like_bookmaker(name: str) -> bool:
            """Check if the name looks like a bookmaker."""
            if not name:
                return False
            name_lower = name.lower()
            # Check against known patterns
            for pattern in bookmaker_patterns:
                if re.search(pattern, name_lower):
                    return True
            # Heuristics: bookmaker names often end with common suffixes
            if any(suffix in name_lower for suffix in [".com", ".us", ".uk", ".eu", "bet", "book", "wager"]):
                return True
            return False

        # Method 1: img.bookmaker-logo with title attribute (pre-match pages)
        img_tag = block.find("img", class_="bookmaker-logo")
        if img_tag and "title" in img_tag.attrs:
            return img_tag["title"]

        # Method 2: img with alt attribute containing bookmaker name
        for img_tag in block.find_all("img", alt=True):
            alt_text = img_tag.get("alt", "")
            if alt_text and looks_like_bookmaker(alt_text):
                return alt_text

        # Method 3: Link with bookmaker name (live pages)
        # Look for <p class="height-content"><a>bookmaker_name</a></p>
        p_tags = block.find_all("p", class_=re.compile(r"height-content"))
        for p in p_tags:
            a_tag = p.find("a")
            if a_tag:
                name = a_tag.get_text(strip=True)
                # Verify it looks like a bookmaker name
                if name and looks_like_bookmaker(name):
                    return name

        # Method 4: No fallback - if we can't identify a known bookmaker, return Unknown
        # This is safer than guessing and potentially returning team names
        return "Unknown"

    def parse_odds_history_modal(self, modal_html: str) -> dict[str, Any]:
        """
        Parses the HTML content of an odds history modal.

        Args:
            modal_html (str): Raw HTML from the modal.

        Returns:
            dict: Parsed odds history data, including historical odds and the opening odds.
        """
        self.logger.info("Parsing modal content for odds history.")
        soup = BeautifulSoup(modal_html, "html.parser")

        try:
            odds_history = []
            timestamps = soup.select("div.flex.flex-col.gap-1 > div.flex.gap-3 > div.font-normal")
            odds_values = soup.select("div.flex.flex-col.gap-1 + div.flex.flex-col.gap-1 > div.font-bold")

            for ts, odd in zip(timestamps, odds_values, strict=False):
                time_text = ts.get_text(strip=True)
                try:
                    dt = datetime.strptime(time_text, "%d %b, %H:%M")
                    formatted_time = dt.replace(year=datetime.now(UTC).year).isoformat()
                except ValueError:
                    self.logger.warning(f"Failed to parse datetime: {time_text}")
                    continue

                odds_history.append({"timestamp": formatted_time, "odds": float(odd.get_text(strip=True))})

            # Parse opening odds
            opening_odds_block = soup.select_one("div.mt-2.gap-1")
            opening_ts_div = opening_odds_block.select_one("div.flex.gap-1 div")
            opening_val_div = opening_odds_block.select_one("div.flex.gap-1 .font-bold")

            opening_odds = None
            if opening_ts_div and opening_val_div:
                try:
                    dt = datetime.strptime(opening_ts_div.get_text(strip=True), "%d %b, %H:%M")
                    opening_odds = {
                        "timestamp": dt.replace(year=datetime.now(UTC).year).isoformat(),
                        "odds": float(opening_val_div.get_text(strip=True)),
                    }
                except ValueError:
                    self.logger.warning("Failed to parse opening odds timestamp.")

            return {"odds_history": odds_history, "opening_odds": opening_odds}

        except Exception as e:
            self.logger.error(f"Failed to parse odds history modal: {e}")
            return {}
