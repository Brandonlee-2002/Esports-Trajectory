"""
Leaguepedia API Debug Script
Run this first to diagnose what's going wrong.
"""

import requests
import json

BASE_URL = "https://lol.fandom.com/wiki/Special:CargoExport"

def raw_query(params):
    try:
        resp = requests.get(BASE_URL, params=params, timeout=15, headers={
            "User-Agent": "CS163-Research-Project/1.0 (academic use)"
        })
        print(f"  Status code: {resp.status_code}")
        print(f"  URL called: {resp.url}")
        print(f"  Response (first 500 chars): {resp.text[:500]}")
        return resp
    except Exception as e:
        print(f"  ERROR: {e}")
        return None

# ── Test 1: Basic connectivity ────────────────────────────────────────────────
print("=" * 60)
print("TEST 1: Basic API connectivity")
print("=" * 60)
resp = raw_query({
    "tables": "Players",
    "fields": "ID,Team,Role",
    "limit": 3,
    "format": "json"
})

# ── Test 2: Search for Faker specifically ─────────────────────────────────────
print("\n" + "=" * 60)
print("TEST 2: Search for 'Faker' in Players table")
print("=" * 60)
resp = raw_query({
    "tables": "Players",
    "fields": "ID,Team,Role,Residency,Country",
    "where": 'ID="Faker"',
    "format": "json"
})

# ── Test 3: Case-insensitive search ───────────────────────────────────────────
print("\n" + "=" * 60)
print("TEST 3: LIKE search for 'faker' (case insensitive)")
print("=" * 60)
resp = raw_query({
    "tables": "Players",
    "fields": "ID,Team,Role",
    "where": 'ID LIKE "%faker%"',
    "limit": 5,
    "format": "json"
})

# ── Test 4: Check what tables/fields exist ────────────────────────────────────
print("\n" + "=" * 60)
print("TEST 4: Sample TournamentPlayers table")
print("=" * 60)
resp = raw_query({
    "tables": "TournamentPlayers",
    "fields": "Player,Team,Role,OverviewPage",
    "where": 'Player LIKE "%Faker%"',
    "limit": 5,
    "format": "json"
})

# ── Test 5: Try ScoreboardPlayers ─────────────────────────────────────────────
print("\n" + "=" * 60)
print("TEST 5: Sample ScoreboardPlayers table")
print("=" * 60)
resp = raw_query({
    "tables": "ScoreboardPlayers",
    "fields": "Name,Team,Role,GameId",
    "where": 'Name LIKE "%Faker%"',
    "limit": 5,
    "format": "json"
})

# ── Test 6: Try all your players to see which ones match ──────────────────────
print("\n" + "=" * 60)
print("TEST 6: Check which player names exist in TournamentPlayers")
print("=" * 60)

PLAYERS = [
    "Faker", "xiaohu", "meiko", "Ruler", "Peanut", "Scout", "RooKie",
    "Deft", "Bdd", "JackeyLove", "Kiin", "Crisp", "Chovy", "Knight",
    "Keria", "Flandre", "Viper", "Canyon", "ShowMaker", "Caps"
]

found = []
not_found = []

for player in PLAYERS:
    try:
        resp = requests.get(BASE_URL, params={
            "tables": "TournamentPlayers",
            "fields": "Player,Team,OverviewPage",
            "where": f'Player="{player}"',
            "limit": 1,
            "format": "json"
        }, timeout=10, headers={"User-Agent": "CS163-Research/1.0"})
        
        data = resp.json()
        if data and len(data) > 0:
            found.append(player)
            print(f"  ✓ {player:15s} → Team: {data[0].get('Team','?')}, Tournament: {data[0].get('OverviewPage','?')}")
        else:
            not_found.append(player)
            print(f"  ✗ {player:15s} → NOT FOUND (trying LIKE search...)")
            
            # Try fuzzy search
            resp2 = requests.get(BASE_URL, params={
                "tables": "TournamentPlayers",
                "fields": "Player,Team",
                "where": f'Player LIKE "%{player}%"',
                "limit": 3,
                "format": "json"
            }, timeout=10, headers={"User-Agent": "CS163-Research/1.0"})
            suggestions = resp2.json()
            if suggestions:
                names = list(set(r.get("Player","") for r in suggestions))
                print(f"           Suggestions: {names}")
            else:
                print(f"           No suggestions found either.")
                
    except Exception as e:
        print(f"  ! {player:15s} → Error: {e}")

print(f"\n✓ Found:     {found}")
print(f"✗ Not found: {not_found}")