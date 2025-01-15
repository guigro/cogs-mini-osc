
# Mini-OSC for Cogs

This mini-app is made to help Cogs receiving and sending HTTP / TCP / UDP requests through OSC by running a mini-OSC server handling and converting requests.
It's a work in progress, so far I tested with success HTTP requests and TCP requests.
This project has been made with the help of AI with a lot of manual adjustments to make it work.

---

## Prerequisites

Before setting up the application, ensure you have the following installed:

- Python 3.7 or higher
- pip (Python package manager)
- A modern web browser for accessing the interface
- A text editor for configuration

---

## Setting up a Virtual Environment

To isolate dependencies, it’s recommended to use a virtual environment:

1. Create the virtual environment:
   ```bash
   python -m venv venv
   ```
2. Activate the virtual environment:
   - On Linux/Mac:
     ```bash
     source venv/bin/activate
     ```
   - On Windows:
     ```bash
     venv\Scripts\activate
     ```

---

## Installing Dependencies

Once the virtual environment is activated, install the required Python libraries:

```bash
pip install -r requirements.txt
```

---

## Launching the Application

1. Start the Flask server:
   ```bash
   python mini_osc.py
   ```
2. Open your web browser and go to:
   ```
   http://127.0.0.1:5000
   ```
   (Replace `5000` with the configured Flask server port if changed in the config.json file.)

---

## Configuration Page

The main configuration page consists of four tabs:
1. **Servers**: Manage the OSC and Flask server settings.
2. **Targets**: Define the endpoints for different protocols.
3. **Routes**: Configure message routing between sources and targets.
4. **Logs**: View real-time logs of application events.

---

## Configuring Targets

Targets are the endpoints for sending or receiving messages. To add a target:

1. Navigate to the **Targets** tab.
2. Click **Add Target**.
3. Fill in the details:
   - **Name**: A unique identifier for the target.
   - **Type**: Select the protocol (OSC, HTTP, TCP, UDP).
   - **Details**: Provide the address and port for the target (e.g., `192.168.1.1:9000`).
4. Click **Add**.

---

## Configuring Routes

Routes define how messages are forwarded between protocols. To create a route:

1. Go to the **Routes** tab.
2. Click **Add Route**.
3. Fill in the route details:
   - **Source Protocol**: Choose the protocol for incoming messages (OSC, HTTP, TCP, UDP).
   - **Source Address**: Define the OSC pattern or HTTP endpoint (if applicable).
   - **Target**: Select the destination target from the list.
   - **Additional Configurations**: Depending on the protocols, specify addresses or ports.
4. Save the route.

---

## Monitoring Logs

To view the application logs:

1. Open the **Logs** tab in the web interface.
2. Logs are refreshed automatically every 2 seconds.
   - Each log entry includes a timestamp and the message content.

---

## Usage in Cogs

You can integrate this gateway into Cogs by:
- Configuring targets for Cogs endpoints.
- Creating routes to forward specific OSC or HTTP messages to Cogs.

**Example configurations:**
- In "Targets", click on "Add Target" and configure like this :
Name : Cogs
Type : OSC
Address/Port : localhost:12097 (or whatever port you setup in your Cogs app)

Add another target :
Name : my_device
Type : http
Address/Port : The IP and port of your device

- In "Routes", click on "Add Route" and configure the bridge :
Protocol : OSC
Address Pattern : /example
Target : my_device

And another one :
Protocol : HTTP
Endpoint : /send_osc (should always be that)
Select a Target : Cogs
Address : /from_my_device

- Now you can configure in Cogs what happens when a message is received from OSC with the address "/from_my_device" and update values or do any action you want (use Update values with a custom value "osc.message.arguments[0]" to use the values in the order they appear in the list)
And you can also send custom values to you devices by sending OSC message to the address of your target in Mini-OSC with the arguments you want to use !


Example of HTTP requests to copy/paste : 
curl -X POST -H "Content-Type: application/json" -d '{"address": "/level_up", "args":13}' http://localhost:5009/send_osc

curl -X POST -H "Content-Type: application/json" -d '{"address": "/level_down", "args":13}' http://localhost:5009/send_osc

curl -X POST -H "Content-Type: application/json" -d '{"address": "/level", "args":[42]}' http://localhost:5009/send_osc 


For TCP, send any request with the argument "address" and any other list of arguments, they will all collapse in a single "args" list.
---

## Next steps
- Configure and test incoming and outcoming TCP/UDP requests 