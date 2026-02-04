
import requests
import os
import json
from datetime import datetime

# Config
AODEV_URL = os.getenv("AODEV_URL", "https://api.aodev.com/v1")
AODEV_TOKEN = os.getenv("AODEV_TOKEN", "mock-token")

class AOdevConnector:
    def __init__(self):
        self.queue = [] # Local memory queue (Mock for "cola local temporal")

    def send_event(self, event_type: str, payload: dict):
        """
        Sends an event to AOdev.
        """
        event = {
            "type": event_type,
            "timestamp": datetime.now().isoformat(),
            "payload": payload
        }
        
        print(f"[AOdev] Sending Event: {event_type}")
        
        try:
            # Mock Request
            # response = requests.post(f"{AODEV_URL}/events", json=event, headers={"Authorization": f"Bearer {AODEV_TOKEN}"}, timeout=2)
            # if response.status_code != 200:
            #     raise Exception("Failed")
            # print("[AOdev] Success")
            pass 
        except Exception as e:
            print(f"[AOdev] Failed to send: {e}. Queuing.")
            self.queue.append(event)

    def sync_user_tasks(self, user_email: str):
        """
        Mock sync from AOdev.
        Returns list of tasks.
        """
        print(f"[AOdev] Syncing tasks for {user_email}")
        return [
            {"title": "Sync from AOdev 1", "priority": "High"},
            {"title": "Sync from AOdev 2", "priority": "Medium"}
        ]

connector = AOdevConnector()
