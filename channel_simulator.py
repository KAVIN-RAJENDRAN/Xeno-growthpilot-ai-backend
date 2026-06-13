import os
import json
import time
import random
import requests
from threading import Thread
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

def simulate_message_lifecycle(callback_url, campaign_id, channel, msg_data):
    """
    Simulates the lifecycle events for a single message in a separate thread.
    Events: Sent -> Delivered (or Failed) -> Opened/Read -> Clicked
    Sends callbacks back to the CRM backend.
    """
    comm_id = msg_data['communication_id']
    name = msg_data['name']
    
    # 1. Simulate SENT event (Immediate)
    # The CRM already logs 'Sent' locally, but we confirm the simulator received it.
    print(f"[Simulator] Message {comm_id} to {name} queued on {channel}.")
    
    # Helper to send event callback
    def send_callback(event_type, error_msg=None):
        payload = {
            "communication_id": comm_id,
            "event_type": event_type,
            "timestamp": time.strftime('%Y-%m-%dT%H:%M:%S.000000'),
            "error_message": error_msg
        }
        try:
            res = requests.post(callback_url, json=payload, timeout=3)
            # print(f"[Simulator] Sent callback {event_type} for message {comm_id}: {res.status_code}")
        except Exception as e:
            print(f"[Simulator] Callback failed for message {comm_id} ({event_type}): {e}")

    # Small delay to spread out simulations
    time.sleep(random.uniform(0.1, 0.5))

    # 2. Simulate DELIVERY event (High success rate ~95%)
    is_success = random.random() < 0.95
    time.sleep(random.uniform(0.5, 1.5))
    
    if not is_success:
        # Send Failed Callback
        reason = random.choice([
            "Subscriber temporarily unreachable", 
            "Invalid handset address", 
            "Message blocked by carrier spam filter", 
            "Device inbox is full"
        ])
        send_callback("Failed", error_msg=reason)
        print(f"[Simulator] Message {comm_id} to {name} FAILED: {reason}")
        return
        
    # Send Delivered Callback
    send_callback("Delivered")
    print(f"[Simulator] Message {comm_id} to {name} DELIVERED.")

    # 3. Simulate OPENED / READ event (60% - 85% chance depending on channel)
    open_prob = 0.80 if channel in ["WhatsApp", "RCS"] else 0.40 if channel == "SMS" else 0.25
    is_opened = random.random() < open_prob
    
    if not is_opened:
        return # Customer never reads it
        
    time.sleep(random.uniform(1.0, 3.0))
    send_callback("Opened")
    
    if channel in ["WhatsApp", "RCS"]:
        time.sleep(random.uniform(0.2, 0.8))
        send_callback("Read")
        print(f"[Simulator] Message {comm_id} to {name} READ.")
    else:
        print(f"[Simulator] Message {comm_id} to {name} OPENED.")

    # 4. Simulate CLICKED event (10% - 30% click rate if opened)
    click_prob = 0.25 if channel in ["WhatsApp", "RCS"] else 0.15 if channel == "SMS" else 0.05
    is_clicked = random.random() < click_prob
    
    if not is_clicked:
        return # Opened but did not click
        
    time.sleep(random.uniform(1.5, 4.0))
    send_callback("Clicked")
    print(f"[Simulator] Message {comm_id} to {name} CLICKED (Conversion Check pending).")

def process_campaign_simulation(callback_url, campaign_id, channel, messages):
    """
    Worker function to process messages sequentially/concurrently.
    """
    threads = []
    # Limit maximum active threads to not overwhelm local system
    # We sample if database size is huge, but here let's run them in groups
    print(f"[Simulator] Starting simulation for campaign {campaign_id} ({len(messages)} messages)...")
    
    for msg in messages:
        t = Thread(target=simulate_message_lifecycle, args=(callback_url, campaign_id, channel, msg))
        t.start()
        # Stagger the start of threads slightly so callbacks flow in waves
        time.sleep(random.uniform(0.02, 0.08))
        threads.append(t)
        
    for t in threads:
        t.join(timeout=0.01) # don't block parent thread, clean up in background

@app.route("/channel/send", methods=["POST"])
def send_messages():
    """
    Receives request to deliver a list of messages.
    Payload: {
      "campaign_id": 1,
      "channel": "WhatsApp",
      "callback_url": "http://localhost:5000/api/receipt",
      "messages": [{"communication_id": 1, "name": "...", "phone": "...", "text": "..."}]
    }
    """
    data = request.json or {}
    campaign_id = data.get("campaign_id")
    channel = data.get("channel")
    callback_url = data.get("callback_url")
    messages = data.get("messages", [])
    
    if not campaign_id or not channel or not callback_url or not messages:
        return jsonify({"error": "Missing parameters in payload"}), 400
        
    # Start simulation asynchronously in a background worker thread
    simulation_worker = Thread(
        target=process_campaign_simulation, 
        args=(callback_url, campaign_id, channel, messages)
    )
    simulation_worker.start()
    
    return jsonify({
        "status": "queued",
        "campaign_id": campaign_id,
        "message_count": len(messages),
        "channel": channel
    })

@app.route("/health", methods=["GET"])
def healthcheck():
    return jsonify({
        "status": "healthy",
        "service": "GrowthPilot Channel Simulator Service",
        "port": 5001
    })

if __name__ == "__main__":
    port = int(os.environ.get("SIMULATOR_PORT", 5001))
    print(f"Starting Channel Simulator Service on port {port}...")
    app.run(host="0.0.0.0", port=port, debug=True)
