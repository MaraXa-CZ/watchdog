"""
Watchdog v4.0 - Statistics
==========================
Ping statistics collection and analysis.
"""

import json
import os
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from collections import defaultdict
import threading

from constants import STATS_DIR, STATS_RETENTION_DAYS, STATS_MAX_POINTS


class PingStats:
    """Collects and analyzes ping statistics."""
    
    def __init__(self):
        self._lock = threading.Lock()
        os.makedirs(STATS_DIR, exist_ok=True)
    
    def _get_file_path(self, group_name: str, date: datetime = None) -> str:
        """Get stats file path for a group and date."""
        date = date or datetime.now()
        filename = f"{group_name}_{date.strftime('%Y%m%d')}.json"
        # Sanitize filename
        filename = "".join(c for c in filename if c.isalnum() or c in "._-")
        return os.path.join(STATS_DIR, filename)
    
    def record(self, group_name: str, servers: Dict[str, dict]):
        """
        Record ping results for a group.
        
        Args:
            group_name: Name of the server group
            servers: Dict of {server_ip: {"reachable": bool, "response_time": float}}
        """
        now = datetime.now()
        
        entry = {
            "timestamp": now.isoformat(),
            "servers": servers
        }
        
        file_path = self._get_file_path(group_name, now)
        
        with self._lock:
            # Load existing data
            data = self._load_file(file_path)
            
            # Add new entry
            data["entries"].append(entry)
            
            # Trim to max points
            if len(data["entries"]) > STATS_MAX_POINTS:
                data["entries"] = data["entries"][-STATS_MAX_POINTS:]
            
            # Update summary
            self._update_summary(data, servers)
            
            # Save
            self._save_file(file_path, data)
    
    def _load_file(self, file_path: str) -> dict:
        """Load stats file or return empty structure."""
        if os.path.exists(file_path):
            try:
                with open(file_path) as f:
                    return json.load(f)
            except:
                pass
        
        return {
            "entries": [],
            "summary": {
                "total_checks": 0,
                "successful_checks": 0,
                "failed_checks": 0,
                "total_resets": 0,
                "avg_response_time": 0,
                "min_response_time": None,
                "max_response_time": None
            }
        }
    
    def _save_file(self, file_path: str, data: dict):
        """Save stats file."""
        try:
            with open(file_path, 'w') as f:
                json.dump(data, f)
        except Exception as e:
            print(f"Stats save error: {e}")
    
    def _update_summary(self, data: dict, servers: Dict[str, dict]):
        """Update summary statistics."""
        summary = data["summary"]
        
        summary["total_checks"] += 1
        
        # Check if all servers responded
        all_reachable = all(s.get("reachable", False) for s in servers.values())
        if all_reachable:
            summary["successful_checks"] += 1
        else:
            summary["failed_checks"] += 1
        
        # Response time stats
        response_times = [s.get("response_time", 0) for s in servers.values() 
                        if s.get("reachable", False) and s.get("response_time")]
        
        if response_times:
            avg_rt = sum(response_times) / len(response_times)
            
            # Update running average
            if summary["avg_response_time"]:
                # Exponential moving average
                summary["avg_response_time"] = 0.9 * summary["avg_response_time"] + 0.1 * avg_rt
            else:
                summary["avg_response_time"] = avg_rt
            
            # Min/max
            if summary["min_response_time"] is None or min(response_times) < summary["min_response_time"]:
                summary["min_response_time"] = min(response_times)
            
            if summary["max_response_time"] is None or max(response_times) > summary["max_response_time"]:
                summary["max_response_time"] = max(response_times)
    
    def record_reset(self, group_name: str):
        """Record a power reset event."""
        now = datetime.now()
        file_path = self._get_file_path(group_name, now)
        
        with self._lock:
            data = self._load_file(file_path)
            data["summary"]["total_resets"] = data["summary"].get("total_resets", 0) + 1
            self._save_file(file_path, data)
    
    def get_stats(self, group_name: str, days: int = 1) -> dict:
        """
        Get statistics for a group over specified days.
        
        Returns:
            {
                "entries": [...],  # Time series data
                "summary": {...},  # Aggregated stats
                "chart_data": {...}  # Pre-formatted for charts
            }
        """
        all_entries = []
        combined_summary = {
            "total_checks": 0,
            "successful_checks": 0,
            "failed_checks": 0,
            "total_resets": 0,
            "avg_response_time": 0,
            "min_response_time": None,
            "max_response_time": None
        }
        
        now = datetime.now()
        
        for day_offset in range(days):
            date = now - timedelta(days=day_offset)
            file_path = self._get_file_path(group_name, date)
            
            with self._lock:
                data = self._load_file(file_path)
            
            all_entries.extend(data.get("entries", []))
            
            # Combine summaries
            summary = data.get("summary", {})
            combined_summary["total_checks"] += summary.get("total_checks", 0)
            combined_summary["successful_checks"] += summary.get("successful_checks", 0)
            combined_summary["failed_checks"] += summary.get("failed_checks", 0)
            combined_summary["total_resets"] += summary.get("total_resets", 0)
            
            if summary.get("min_response_time") is not None:
                if combined_summary["min_response_time"] is None:
                    combined_summary["min_response_time"] = summary["min_response_time"]
                else:
                    combined_summary["min_response_time"] = min(
                        combined_summary["min_response_time"], 
                        summary["min_response_time"]
                    )
            
            if summary.get("max_response_time") is not None:
                if combined_summary["max_response_time"] is None:
                    combined_summary["max_response_time"] = summary["max_response_time"]
                else:
                    combined_summary["max_response_time"] = max(
                        combined_summary["max_response_time"], 
                        summary["max_response_time"]
                    )
        
        # Calculate uptime percentage
        if combined_summary["total_checks"] > 0:
            combined_summary["uptime_percent"] = round(
                (combined_summary["successful_checks"] / combined_summary["total_checks"]) * 100, 2
            )
        else:
            combined_summary["uptime_percent"] = 0
        
        # Prepare chart data (downsample if needed)
        chart_data = self._prepare_chart_data(all_entries, days)
        
        return {
            "entries": all_entries[-100:],  # Last 100 entries
            "summary": combined_summary,
            "chart_data": chart_data
        }
    
    def _prepare_chart_data(self, entries: List[dict], days: int) -> dict:
        """Prepare data for Chart.js visualization with per-server data."""
        if not entries:
            return {"labels": [], "response_times": [], "availability": [], "servers": {}, "servers_availability": {}}
        
        # Determine aggregation interval based on days
        if days <= 1:
            interval_minutes = 5
        elif days <= 7:
            interval_minutes = 30
        else:
            interval_minutes = 120
        
        # Find all servers across entries
        all_servers = set()
        for entry in entries:
            for server in entry.get("servers", {}).keys():
                all_servers.add(server)
        
        # Group entries by interval
        buckets = defaultdict(list)
        
        for entry in entries:
            try:
                ts = datetime.fromisoformat(entry["timestamp"])
                # Round to interval
                bucket_key = ts.replace(
                    minute=(ts.minute // interval_minutes) * interval_minutes,
                    second=0,
                    microsecond=0
                )
                buckets[bucket_key].append(entry)
            except:
                continue
        
        # Sort by time
        sorted_buckets = sorted(buckets.items())
        
        labels = []
        response_times = []  # Average across all servers
        availability = []  # Average across all servers
        servers_data = {server: [] for server in all_servers}  # Per-server response times
        servers_availability = {server: [] for server in all_servers}  # Per-server availability
        
        for bucket_time, bucket_entries in sorted_buckets:
            # Format label based on interval
            if days <= 1:
                labels.append(bucket_time.strftime("%H:%M"))
            else:
                labels.append(bucket_time.strftime("%d.%m %H:%M"))
            
            # Per-server stats
            server_rt = {server: [] for server in all_servers}
            server_ok = {server: 0 for server in all_servers}
            server_total = {server: 0 for server in all_servers}
            all_rt = []
            successful = 0
            total = 0
            
            for entry in bucket_entries:
                for server, server_data in entry.get("servers", {}).items():
                    if server not in all_servers:
                        continue
                    total += 1
                    server_total[server] += 1
                    if server_data.get("reachable"):
                        successful += 1
                        server_ok[server] += 1
                        rt = server_data.get("response_time", 0)
                        if rt > 0:
                            all_rt.append(rt)
                            server_rt[server].append(rt)
            
            # Average response time (all servers combined)
            response_times.append(round(sum(all_rt) / len(all_rt), 2) if all_rt else 0)
            availability.append(round((successful / total) * 100, 1) if total > 0 else 0)
            
            # Per-server stats for this bucket
            for server in all_servers:
                # Response time
                if server_rt[server]:
                    servers_data[server].append(round(sum(server_rt[server]) / len(server_rt[server]), 2))
                else:
                    servers_data[server].append(None)
                
                # Availability
                if server_total[server] > 0:
                    servers_availability[server].append(round((server_ok[server] / server_total[server]) * 100, 1))
                else:
                    servers_availability[server].append(None)
        
        return {
            "labels": labels,
            "response_times": response_times,
            "availability": availability,
            "servers": servers_data,
            "servers_availability": servers_availability
        }
    
    def cleanup(self, retention_days: int = None):
        """Remove old stats files."""
        retention_days = retention_days or STATS_RETENTION_DAYS
        cutoff = datetime.now() - timedelta(days=retention_days)
        
        try:
            for filename in os.listdir(STATS_DIR):
                if not filename.endswith('.json'):
                    continue
                
                file_path = os.path.join(STATS_DIR, filename)
                
                # Check file modification time
                mtime = datetime.fromtimestamp(os.path.getmtime(file_path))
                if mtime < cutoff:
                    os.remove(file_path)
        except Exception as e:
            print(f"Stats cleanup error: {e}")
    
    def get_all_groups_summary(self) -> Dict[str, dict]:
        """Get summary for all groups (today only)."""
        result = {}
        
        try:
            today = datetime.now().strftime('%Y%m%d')
            
            for filename in os.listdir(STATS_DIR):
                if not filename.endswith('.json') or today not in filename:
                    continue
                
                # Extract group name from filename
                group_name = filename.rsplit('_', 1)[0]
                
                file_path = os.path.join(STATS_DIR, filename)
                with self._lock:
                    data = self._load_file(file_path)
                
                summary = data.get("summary", {})
                if summary.get("total_checks", 0) > 0:
                    summary["uptime_percent"] = round(
                        (summary.get("successful_checks", 0) / summary["total_checks"]) * 100, 2
                    )
                else:
                    summary["uptime_percent"] = 0
                
                result[group_name] = summary
        except Exception as e:
            print(f"Get all groups summary error: {e}")
        
        return result


# Global instance
ping_stats = PingStats()
