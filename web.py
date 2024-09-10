from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
import os
from vcon import Vcon
from vcon.party import Party
from vcon.dialog import Dialog
from datetime import datetime
import dotenv
import requests

# Load environment variables
dotenv.load_dotenv()

CONSERVER_URL = os.getenv("CONSERVER_URL")
CONSERVER_TOKEN = os.getenv("CONSERVER_TOKEN")
CONSERVER_INGRESS_LIST = os.getenv("CONSERVER_INGRESS_LIST")

app = FastAPI()

# Mount the static directory
static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
app.mount("/static", StaticFiles(directory=static_dir), name="static")


@app.post("/vapi")
async def vapi(data: dict):
    # Parse the end-of-call message
    call_data = data['message']
    if call_data['type'] != 'end-of-call-report':
        return

    # Create a new Vcon object
    vcon = Vcon.build_new()

    # Add basic information
    vcon.vcon_dict["subject"] = "Call with Old Stone Bank's retirement help desk"
    vcon.vcon_dict["created_at"] = call_data["startedAt"]
    vcon.vcon_dict["updated_at"] = call_data["endedAt"]

    # Add parties
    customer = Party(name="Customer")
    assistant = Party(name="Barney", role="AI Assistant")
    vcon.add_party(customer)
    vcon.add_party(assistant)

    # Add dialog
    for msg in call_data["artifact"]["messages"]:
        if msg["role"] != "system":  # Skip system messages
            dialog = Dialog(
                type="text",
                start=datetime.fromtimestamp(msg["time"] / 1000).isoformat(),
                parties=[0, 1],  # Assuming 0 is customer and 1 is assistant
                originator=0 if msg["role"] == "user" else 1,
                body=msg["message"]
            )
            vcon.add_dialog(dialog)

    # Add metadata
    vcon.vcon_dict["meta"] = {
        "endedReason": call_data["endedReason"],
        "cost": call_data["cost"],
        "durationSeconds": call_data["durationSeconds"],
        "summary": call_data["analysis"]["summary"],
        "successEvaluation": call_data["analysis"]["successEvaluation"]
    }

    # Add attachments
    vcon.add_attachment(body=call_data["recordingUrl"], type="audio", encoding="none")
    vcon.add_attachment(body=call_data["transcript"], type="transcript", encoding="none")
    vcon_dict = vcon.to_dict()
    
    # POST this vcon to the CONSERVER_API_URL
    response = requests.post(CONSERVER_URL+'/vcon', json=vcon_dict, headers={'Authorization': f'Bearer {CONSERVER_TOKEN}'})
    # Trigger the chain with the ingress list
    ingress_vcon_uuids = [vcon.uuid]
    url = CONSERVER_URL+'/vcon/ingress?ingress_list='+CONSERVER_INGRESS_LIST
    response = requests.post(url, json=ingress_vcon_uuids, headers={'Authorization': f'Bearer {CONSERVER_TOKEN}'})
    return "OK"
