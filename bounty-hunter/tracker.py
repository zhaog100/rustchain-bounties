#!/usr/bin/env python3
"""Earnings Tracker - Track submissions and earnings"""

import sqlite3
import os
import re
from datetime import datetime
from typing import Dict


class EarningsTracker:
    def __init__(self, config: dict):
        self.db_path = os.path.expanduser('~/.bounty-hunter/earnings.db')
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._init_db()
        
    def _init_db(self):
        """Initialize database"""
        conn = sqlite3.connect(self.db_path)
        conn.execute('''
            CREATE TABLE IF NOT EXISTS submissions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                bounty_id INTEGER,
                bounty_title TEXT,
                pr_url TEXT,
                rtc_reward REAL,
                status TEXT,
                submitted_at TIMESTAMP,
                claimed_at TIMESTAMP
            )
        ''')
        conn.commit()
        conn.close()
    
    async def record_submission(self, bounty: Dict, pr_url: str):
        """Record a bounty submission"""
        conn = sqlite3.connect(self.db_path)
        conn.execute('''
            INSERT INTO submissions 
            (bounty_id, bounty_title, pr_url, rtc_reward, status, submitted_at)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            bounty['id'],
            bounty['title'],
            pr_url,
            self._extract_rtc(bounty),
            'submitted',
            datetime.now().isoformat()
        ))
        conn.commit()
        conn.close()
        print(f"   Recorded submission for bounty #{bounty['id']}")
    
    async def mark_claimed(self, bounty_id: int):
        """Mark a bounty as claimed (paid)"""
        conn = sqlite3.connect(self.db_path)
        conn.execute('''
            UPDATE submissions 
            SET status='claimed', claimed_at=?
            WHERE bounty_id=?
        ''', (datetime.now().isoformat(), bounty_id))
        conn.commit()
        conn.close()
    
    def get_total_earnings(self) -> float:
        """Get total RTC earnings"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute('SELECT SUM(rtc_reward) FROM submissions WHERE status="claimed"')
        total = cursor.fetchone()[0] or 0.0
        conn.close()
        return total
    
    def get_pending_earnings(self) -> float:
        """Get pending RTC earnings"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute('SELECT SUM(rtc_reward) FROM submissions WHERE status="submitted"')
        total = cursor.fetchone()[0] or 0.0
        conn.close()
        return total
    
    def _extract_rtc(self, bounty: Dict) -> float:
        """Extract RTC reward from bounty"""
        text = (bounty.get('title', '') or '') + (bounty.get('body', '') or '')
        match = re.search(r'(\d+)\s*RTC', text, re.IGNORECASE)
        return float(match.group(1)) if match else 0.0
