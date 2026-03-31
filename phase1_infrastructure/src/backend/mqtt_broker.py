"""
Message Broker Simulation — Step 1.4
======================================
Simulates MQTT / Kafka pub-sub architecture to isolate 
data generation (edge) from data processing (backend).
"""

import threading
import queue
import logging
import json
from typing import Callable, Any

logger = logging.getLogger("mqtt_broker")

class MessageBroker:
    """
    In-memory pub/sub broker replacing direct REST calls.
    Supports Kafka-style topics and distinct consumer groups.
    """
    def __init__(self):
        self._topics = {}
        self._lock = threading.Lock()
        
    def create_topic(self, topic: str):
        with self._lock:
            if topic not in self._topics:
                # Store subscribers as a list of callback functions
                self._topics[topic] = []

    def subscribe(self, topic: str, callback: Callable[[str, Any], None]):
        """Subscribe to a topic with a callback function."""
        with self._lock:
            if topic not in self._topics:
                self._topics[topic] = []
            self._topics[topic].append(callback)
            
    def publish(self, topic: str, payload: Any):
        """Publish a message to all subscribers of a topic."""
        with self._lock:
            subscribers = self._topics.get(topic, [])
            
        # Dispatch in separate threads or sequentially
        # For simulation, sequential dispatch is sufficient and stable
        # Convert payload to string to simulate network ser/deser
        if isinstance(payload, dict) or isinstance(payload, list):
            message = json.dumps(payload)
        else:
            message = str(payload)
            
        for callback in subscribers:
            try:
                # Deserialize back to mock network layer
                data = json.loads(message)
                callback(topic, data)
            except Exception as e:
                logger.error(f"Subscriber error on topic {topic}: {e}")

# Global singleton instance for the simulation
broker = MessageBroker()
