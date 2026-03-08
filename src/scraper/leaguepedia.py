"""
Leaguepedia Data Scraper
========================

Scrapes player career data from the League of Legends Esports Wiki (Leaguepedia).
Uses the MediaWiki API via mwclient for structured data access.

Data Source: https://lol.fandom.com/wiki/League_of_Legends_Esports_Wiki
"""

import mwclient
import pandas as pd
from datetime import datetime
from typing import List, Dict, Optional
import time
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class LeaguepediaScraper:
    """
    Scraper for Leaguepedia player and team data.
    
    Uses the Cargo query system for structured data access.
    Documentation: https://lol.fandom.com/wiki/Help:Cargo_queries
    """
    
    def __init__(self, rate_limit: float = 1.0):
        """
        Initialize the scraper.
        
        Args:
            rate_limit: Minimum seconds between API calls (be respectful!)
        """
        self.site = mwclient.Site('lol.fandom.com', path='/')
        self.rate_limit = rate_limit
        self.last_request_time = 0
        
    def _respect_rate_limit(self):
        """Ensure we don't overwhelm the API."""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.rate_limit:
            time.sleep(self.rate_limit - elapsed)
        self.last_request_time = time.time()
        
    def cargo_query(
        self,
        tables: str,
        fields: str,
        where: str = "",
        join_on: str = "",
        order_by: str = "",
        limit: int = 500,
        offset: int = 0
    ) -> List[Dict]:
        """
        Execute a Cargo query against Leaguepedia.
        
        Args:
            tables: Comma-separated table names
            fields: Comma-separated field names
            where: WHERE clause conditions
            join_on: JOIN conditions for multiple tables
            order_by: ORDER BY clause
            limit: Maximum results per query (max 500)
            offset: Starting offset for pagination
            
        Returns:
            List of result dictionaries
        """
        self._respect_rate_limit()
        
        try:
            response = self.site.api(
                'cargoquery',
                tables=tables,
                fields=fields,
                where=where,
                join_on=join_on,
                order_by=order_by,
                limit=limit,
                offset=offset
            )
            
            # Extract results from response
            results = []
            if 'cargoquery' in response:
                for item in response['cargoquery']:
                    results.append(item.get('title', {}))
                    
            return results
            
        except Exception as e:
            logger.error(f"Cargo query failed: {e}")
            return []
    
    def get_all_players(self, region: Optional[str] = None) -> pd.DataFrame:
        """
        Fetch all professional players.
        
        Args:
            region: Optional region filter (e.g., 'Korea', 'North America')
            
        Returns:
            DataFrame with player information
        """
        logger.info(f"Fetching players{f' from {region}' if region else ''}")
        
        fields = "Player, ID, Name, Country, Role, Team, IsRetired"
        where_clause = f"Region='{region}'" if region else ""
        
        all_results = []
        offset = 0
        
        while True:
            results = self.cargo_query(
                tables="Players",
                fields=fields,
                where=where_clause,
                order_by="Player",
                limit=500,
                offset=offset
            )
            
            if not results:
                break
                
            all_results.extend(results)
            offset += 500
            logger.info(f"Fetched {len(all_results)} players so far...")
            
        return pd.DataFrame(all_results)
    
    def get_player_team_history(self, player_id: str) -> pd.DataFrame:
        """
        Fetch team history for a specific player.
        
        Args:
            player_id: Player's ID/handle
            
        Returns:
            DataFrame with team history
        """
        fields = "Player, Team, DateJoin, DateLeave, Role, RoleModifier"
        
        results = self.cargo_query(
            tables="Tenures",
            fields=fields,
            where=f"Player='{player_id}'",
            order_by="DateJoin"
        )
        
        return pd.DataFrame(results)
    
    def get_tournaments(
        self,
        region: Optional[str] = None,
        year: Optional[int] = None
    ) -> pd.DataFrame:
        """
        Fetch tournament information.
        
        Args:
            region: Optional region filter
            year: Optional year filter
            
        Returns:
            DataFrame with tournament data
        """
        fields = "Name, Region, League, DateStart, DateEnd, Prizepool"
        
        conditions = []
        if region:
            conditions.append(f"Region='{region}'")
        if year:
            conditions.append(f"DateStart LIKE '{year}%'")
            
        where_clause = " AND ".join(conditions) if conditions else ""
        
        results = self.cargo_query(
            tables="Tournaments",
            fields=fields,
            where=where_clause,
            order_by="DateStart DESC"
        )
        
        return pd.DataFrame(results)
    
    def get_tier1_players_by_region(self, region_code: str) -> pd.DataFrame:
        """
        Get all players who have played in a specific Tier 1 league.
        
        Args:
            region_code: League code (e.g., 'LCK', 'LEC', 'LCS', 'LPL')
            
        Returns:
            DataFrame with player data
        """
        # This will need refinement based on actual Leaguepedia schema
        logger.info(f"Fetching Tier 1 players from {region_code}")
        
        fields = "Player, Team, DateJoin, DateLeave, Role"
        
        results = self.cargo_query(
            tables="Tenures",
            fields=fields,
            where=f"Team HOLDS '{region_code}'",  # Adjust based on actual schema
            order_by="Player"
        )
        
        return pd.DataFrame(results)


def main():
    """Test the scraper with a simple query."""
    scraper = LeaguepediaScraper(rate_limit=1.0)
    
    # Test: Get some players
    print("Testing Leaguepedia connection...")
    
    # Note: The exact table/field names may need adjustment
    # based on Leaguepedia's current schema
    players = scraper.get_all_players()
    
    if not players.empty:
        print(f"Successfully retrieved {len(players)} players")
        print(players.head())
    else:
        print("No results - check query parameters")
        print("Visit https://lol.fandom.com/wiki/Special:CargoTables for schema")


if __name__ == "__main__":
    main()
