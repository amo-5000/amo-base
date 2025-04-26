#!/usr/bin/env python3
"""
Knowledge Base Update Scheduler

This script sets up scheduled updates to the AMO Events knowledge base using
a configuration file that defines update sources and schedules.
"""

import os
import sys
import logging
import yaml
import json
import time
import schedule
import argparse
import subprocess
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional

# Add parent directory to path to import from root
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("logs/scheduler.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("kb_scheduler")

# Ensure log directory exists
os.makedirs("logs", exist_ok=True)

# Default configuration file path
DEFAULT_CONFIG_PATH = "config/update_schedule.yaml"

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="AMO Events Knowledge Base Update Scheduler")
    
    parser.add_argument("--config", default=DEFAULT_CONFIG_PATH, help="Path to update configuration file")
    parser.add_argument("--daemon", action="store_true", help="Run as a daemon process")
    parser.add_argument("--force", action="store_true", help="Force immediate update of all sources")
    parser.add_argument("--list", action="store_true", help="List configured update sources")
    parser.add_argument("--source", help="Update only the specified source")
    parser.add_argument("--test", action="store_true", help="Test configuration without performing updates")
    
    return parser.parse_args()

def load_configuration(config_path: str) -> Dict[str, Any]:
    """
    Load update configuration from YAML file.
    
    Args:
        config_path: Path to configuration file
        
    Returns:
        Dictionary with configuration
    """
    # Create config directory if it doesn't exist
    os.makedirs(os.path.dirname(config_path), exist_ok=True)
    
    # If config file doesn't exist, create with default configuration
    if not os.path.exists(config_path):
        logger.info(f"Creating default configuration at {config_path}")
        
        default_config = {
            "sources": [
                {
                    "name": "webflow_docs",
                    "path": "webflow-docs",
                    "namespace": "webflow",
                    "schedule": "daily",
                    "time": "02:00",
                    "topics": ["webflow", "website", "frontend"]
                },
                {
                    "name": "airtable_docs",
                    "path": "airtable-guides",
                    "namespace": "airtable",
                    "schedule": "daily",
                    "time": "03:00",
                    "topics": ["airtable", "database", "backend"]
                },
                {
                    "name": "n8n_docs",
                    "path": "n8n-docs",
                    "namespace": "n8n",
                    "schedule": "weekly",
                    "day": "monday",
                    "time": "04:00",
                    "topics": ["n8n", "automation", "workflow"]
                }
            ],
            "backup": {
                "schedule": "weekly",
                "day": "sunday",
                "time": "01:00",
                "path": "backups/kb-backup"
            },
            "settings": {
                "max_retries": 3,
                "retry_delay": 300,
                "notification_email": ""
            }
        }
        
        with open(config_path, "w") as f:
            yaml.dump(default_config, f, sort_keys=False, indent=2)
    
    # Load configuration
    try:
        with open(config_path, "r") as f:
            config = yaml.safe_load(f)
        
        logger.info(f"Loaded configuration from {config_path}")
        return config
    except Exception as e:
        logger.error(f"Error loading configuration: {str(e)}")
        return {}

def validate_configuration(config: Dict[str, Any]) -> bool:
    """
    Validate the configuration.
    
    Args:
        config: Configuration dictionary
        
    Returns:
        True if configuration is valid, False otherwise
    """
    if not config:
        logger.error("Empty configuration")
        return False
    
    if "sources" not in config:
        logger.error("No sources defined in configuration")
        return False
    
    for source in config.get("sources", []):
        if "name" not in source:
            logger.error("Source missing required field: name")
            return False
        
        if "path" not in source:
            logger.error(f"Source {source.get('name', 'unknown')} missing required field: path")
            return False
        
        if "schedule" not in source:
            logger.error(f"Source {source.get('name', 'unknown')} missing required field: schedule")
            return False
        
        if source["schedule"] not in ["daily", "weekly", "monthly", "hourly"]:
            logger.error(f"Source {source['name']} has invalid schedule: {source['schedule']}")
            return False
        
        if source["schedule"] == "weekly" and "day" not in source:
            logger.error(f"Source {source['name']} with weekly schedule missing required field: day")
            return False
        
        if source["schedule"] == "monthly" and "day" not in source:
            logger.error(f"Source {source['name']} with monthly schedule missing required field: day")
            return False
    
    return True

def list_sources(config: Dict[str, Any]) -> None:
    """
    List configured update sources.
    
    Args:
        config: Configuration dictionary
    """
    print("\nConfigured Knowledge Base Update Sources:\n")
    
    for source in config.get("sources", []):
        print(f"Name: {source.get('name', 'unknown')}")
        print(f"  Path: {source.get('path', 'unknown')}")
        print(f"  Namespace: {source.get('namespace', 'default')}")
        print(f"  Schedule: {source.get('schedule', 'unknown')}")
        
        if source.get("schedule") == "weekly":
            print(f"  Day: {source.get('day', 'monday')}")
        
        if source.get("schedule") == "monthly":
            print(f"  Day: {source.get('day', '1')}")
        
        print(f"  Time: {source.get('time', '00:00')}")
        print(f"  Topics: {', '.join(source.get('topics', []))}")
        print()
    
    # Print backup configuration
    backup = config.get("backup", {})
    if backup:
        print("Backup Configuration:")
        print(f"  Schedule: {backup.get('schedule', 'weekly')}")
        print(f"  Day: {backup.get('day', 'sunday')}")
        print(f"  Time: {backup.get('time', '01:00')}")
        print(f"  Path: {backup.get('path', 'backups/kb-backup')}")
        print()

def run_update_command(source: Dict[str, Any], dry_run: bool = False) -> bool:
    """
    Run the update command for a source.
    
    Args:
        source: Source configuration
        dry_run: Whether to perform a dry run
        
    Returns:
        True if update was successful, False otherwise
    """
    # Build command
    cmd = [
        "python", 
        os.path.join("tools", "content_updater.py"),
        "update",
        "--path", source["path"]
    ]
    
    # Add namespace if provided
    if "namespace" in source:
        cmd.extend(["--namespace", source["namespace"]])
    
    # Add dry run flag if specified
    if dry_run:
        cmd.append("--dry-run")
    
    # Log the command
    logger.info(f"Running update command: {' '.join(cmd)}")
    
    # If testing, don't actually run the command
    if dry_run:
        return True
    
    # Run the command
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            logger.info(f"Successfully updated source {source['name']}")
            return True
        else:
            logger.error(f"Error updating source {source['name']}: {result.stderr}")
            return False
            
    except Exception as e:
        logger.error(f"Error running update command: {str(e)}")
        return False

def run_backup_command(backup_config: Dict[str, Any], dry_run: bool = False) -> bool:
    """
    Run the backup command.
    
    Args:
        backup_config: Backup configuration
        dry_run: Whether to perform a dry run
        
    Returns:
        True if backup was successful, False otherwise
    """
    # Build command
    cmd = [
        "python", 
        os.path.join("tools", "content_updater.py"),
        "backup",
        "--output", backup_config["path"]
    ]
    
    # Log the command
    logger.info(f"Running backup command: {' '.join(cmd)}")
    
    # If testing, don't actually run the command
    if dry_run:
        return True
    
    # Create output directory if it doesn't exist
    os.makedirs(backup_config["path"], exist_ok=True)
    
    # Run the command
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            logger.info(f"Successfully backed up knowledge base to {backup_config['path']}")
            return True
        else:
            logger.error(f"Error backing up knowledge base: {result.stderr}")
            return False
            
    except Exception as e:
        logger.error(f"Error running backup command: {str(e)}")
        return False

def schedule_updates(config: Dict[str, Any], test_mode: bool = False) -> None:
    """
    Schedule updates based on configuration.
    
    Args:
        config: Configuration dictionary
        test_mode: Whether to run in test mode (no actual updates)
    """
    # Schedule source updates
    for source in config.get("sources", []):
        schedule_type = source.get("schedule", "daily")
        
        if schedule_type == "hourly":
            schedule.every().hour.at(":00").do(
                run_update_command, source=source, dry_run=test_mode
            ).tag(f"source_{source['name']}")
            
        elif schedule_type == "daily":
            schedule.every().day.at(source.get("time", "00:00")).do(
                run_update_command, source=source, dry_run=test_mode
            ).tag(f"source_{source['name']}")
            
        elif schedule_type == "weekly":
            day = source.get("day", "monday").lower()
            
            if day == "monday":
                schedule.every().monday.at(source.get("time", "00:00")).do(
                    run_update_command, source=source, dry_run=test_mode
                ).tag(f"source_{source['name']}")
            elif day == "tuesday":
                schedule.every().tuesday.at(source.get("time", "00:00")).do(
                    run_update_command, source=source, dry_run=test_mode
                ).tag(f"source_{source['name']}")
            elif day == "wednesday":
                schedule.every().wednesday.at(source.get("time", "00:00")).do(
                    run_update_command, source=source, dry_run=test_mode
                ).tag(f"source_{source['name']}")
            elif day == "thursday":
                schedule.every().thursday.at(source.get("time", "00:00")).do(
                    run_update_command, source=source, dry_run=test_mode
                ).tag(f"source_{source['name']}")
            elif day == "friday":
                schedule.every().friday.at(source.get("time", "00:00")).do(
                    run_update_command, source=source, dry_run=test_mode
                ).tag(f"source_{source['name']}")
            elif day == "saturday":
                schedule.every().saturday.at(source.get("time", "00:00")).do(
                    run_update_command, source=source, dry_run=test_mode
                ).tag(f"source_{source['name']}")
            elif day == "sunday":
                schedule.every().sunday.at(source.get("time", "00:00")).do(
                    run_update_command, source=source, dry_run=test_mode
                ).tag(f"source_{source['name']}")
        
        elif schedule_type == "monthly":
            # Schedule for a specific day of the month
            day = int(source.get("day", "1"))
            
            schedule.every().month.at(f"{day:02d} {source.get('time', '00:00')}").do(
                run_update_command, source=source, dry_run=test_mode
            ).tag(f"source_{source['name']}")
    
    # Schedule backup
    backup_config = config.get("backup", {})
    if backup_config:
        schedule_type = backup_config.get("schedule", "weekly")
        
        if schedule_type == "daily":
            schedule.every().day.at(backup_config.get("time", "01:00")).do(
                run_backup_command, backup_config=backup_config, dry_run=test_mode
            ).tag("backup")
            
        elif schedule_type == "weekly":
            day = backup_config.get("day", "sunday").lower()
            
            if day == "monday":
                schedule.every().monday.at(backup_config.get("time", "01:00")).do(
                    run_backup_command, backup_config=backup_config, dry_run=test_mode
                ).tag("backup")
            elif day == "tuesday":
                schedule.every().tuesday.at(backup_config.get("time", "01:00")).do(
                    run_backup_command, backup_config=backup_config, dry_run=test_mode
                ).tag("backup")
            elif day == "wednesday":
                schedule.every().wednesday.at(backup_config.get("time", "01:00")).do(
                    run_backup_command, backup_config=backup_config, dry_run=test_mode
                ).tag("backup")
            elif day == "thursday":
                schedule.every().thursday.at(backup_config.get("time", "01:00")).do(
                    run_backup_command, backup_config=backup_config, dry_run=test_mode
                ).tag("backup")
            elif day == "friday":
                schedule.every().friday.at(backup_config.get("time", "01:00")).do(
                    run_backup_command, backup_config=backup_config, dry_run=test_mode
                ).tag("backup")
            elif day == "saturday":
                schedule.every().saturday.at(backup_config.get("time", "01:00")).do(
                    run_backup_command, backup_config=backup_config, dry_run=test_mode
                ).tag("backup")
            elif day == "sunday":
                schedule.every().sunday.at(backup_config.get("time", "01:00")).do(
                    run_backup_command, backup_config=backup_config, dry_run=test_mode
                ).tag("backup")
    
    # Print scheduled jobs
    for job in schedule.get_jobs():
        logger.info(f"Scheduled job: {job}")

def run_scheduler(daemon_mode: bool = False, test_mode: bool = False) -> None:
    """
    Run the scheduler.
    
    Args:
        daemon_mode: Whether to run in daemon mode
        test_mode: Whether to run in test mode (no actual updates)
    """
    logger.info("Starting knowledge base update scheduler")
    
    if test_mode:
        logger.info("Running in test mode - no actual updates will be performed")
    
    if daemon_mode:
        logger.info("Running in daemon mode - scheduler will continue running")
        
        try:
            while True:
                schedule.run_pending()
                time.sleep(60)
        except KeyboardInterrupt:
            logger.info("Scheduler interrupted by user")
        except Exception as e:
            logger.error(f"Error in scheduler: {str(e)}")
            
    else:
        # Run once
        logger.info("Running scheduled jobs once")
        schedule.run_all()
        logger.info("Completed scheduled jobs")

def force_update_all(config: Dict[str, Any], test_mode: bool = False) -> None:
    """
    Force immediate update of all sources.
    
    Args:
        config: Configuration dictionary
        test_mode: Whether to run in test mode (no actual updates)
    """
    logger.info("Forcing immediate update of all sources")
    
    for source in config.get("sources", []):
        logger.info(f"Updating source: {source['name']}")
        run_update_command(source, test_mode)
    
    # Also run backup
    backup_config = config.get("backup", {})
    if backup_config:
        logger.info("Running backup")
        run_backup_command(backup_config, test_mode)

def update_specific_source(config: Dict[str, Any], source_name: str, test_mode: bool = False) -> bool:
    """
    Update a specific source.
    
    Args:
        config: Configuration dictionary
        source_name: Name of the source to update
        test_mode: Whether to run in test mode (no actual updates)
        
    Returns:
        True if source was found and updated, False otherwise
    """
    for source in config.get("sources", []):
        if source["name"] == source_name:
            logger.info(f"Updating source: {source['name']}")
            return run_update_command(source, test_mode)
    
    logger.error(f"Source not found: {source_name}")
    return False

def main():
    """Main function."""
    args = parse_arguments()
    
    # Create config directory if it doesn't exist
    os.makedirs(os.path.dirname(args.config), exist_ok=True)
    
    # Load configuration
    config = load_configuration(args.config)
    
    # Validate configuration
    if not validate_configuration(config):
        logger.error("Invalid configuration")
        return 1
    
    # Handle command-line options
    if args.list:
        list_sources(config)
        return 0
    
    if args.source:
        success = update_specific_source(config, args.source, args.test)
        return 0 if success else 1
    
    if args.force:
        force_update_all(config, args.test)
        return 0
    
    # Schedule updates
    schedule_updates(config, args.test)
    
    # Run scheduler
    run_scheduler(args.daemon, args.test)
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 