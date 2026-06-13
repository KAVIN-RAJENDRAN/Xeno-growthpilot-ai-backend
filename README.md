# GrowthPilot AI - CRM Backend & Channel Simulator

This is the backend service layer for **GrowthPilot AI**, an AI-native Marketing CRM & Autonomous Campaign Agent. It includes the CRM Core API Service and an event-driven Channel Simulator.

---

## System Architecture

```mermaid
graph TD
    A[Frontend React App] -- REST APIs --> B[CRM Backend :5000]
    B -- SQLAlchemy --> C[(SQLite / MySQL Database)]
    B -- Langchain / official SDK --> D[Gemini AI Engine]
    B -- Message payload --> E[Channel Simulator Service :5001]
    E -- Callback Receipts --> B
    E -- Event simulation --> F{Sent, Delivered, Failed, Opened, Clicked}
    F --> E
```

### Communication Flow:
1. Marketer submits a natural language growth goal to the **AI Agent** on the Frontend.
2. The **CRM Backend** queries **Gemini AI** to perform audience segmentation, recommend a channel, and write tailored multi-channel campaign copy.
3. The marketer reviews the recommendation and clicks **Launch Campaign**.
4. The **CRM Backend** registers campaign logs and sends the audience package to the **Channel Simulator**.
5. The **Channel Simulator** returns `{"status": "queued"}` immediately and spins up background threads.
6. The simulator runs messages through a realistic delivery funnel with random intervals, posting status updates (`Sent`, `Delivered`, `Opened`, `Read`, `Clicked`) to the CRM `/api/receipt` callback.
7. Upon processing a `Clicked` receipt, the CRM simulates a conversion (adds a new order transaction for that customer), updates campaign metrics, and refreshes dashboard analytics in real-time.

---

## Folder Structure

```text
backend/
├── app.py                  # Main entry point (Flask, CORS, Blueprints, DB seeding)
├── channel_simulator.py    # Channel Simulator service (runs on port 5001)
├── requirements.txt        # Backend dependencies
├── database/
│   └── db.py               # Database configuration and 1000+ record seeding script
├── models/
│   ├── __init__.py
│   ├── customer.py         # Customer schema
│   ├── order.py            # Order transaction schema
│   ├── campaign.py         # Campaign metadata schema
│   └── communication.py    # Logs, events, segments, and AI recommendations
├── routes/
│   ├── __init__.py
│   ├── customers.py        # Customer details & CSV upload endpoints
│   ├── campaigns.py        # Campaigns listing & receipt callback processing
│   ├── ai_agent.py         # NLP segmentation & content generation endpoints
│   └── analytics.py        # Executive metrics compilation
└── services/
    ├── __init__.py
    ├── gemini_service.py   # Gemini API integration & NLP fallback engines
    └── recommendation_engine.py # Opportunities scanner
```

---

## Installation & Setup

### Prerequisites
* Python 3.8 or higher
* Git (optional)

### Setup Instructions
1. Navigate to the `backend/` directory:
   ```bash
   cd backend
   ```

2. Create a virtual environment:
   ```bash
   python -m venv venv
   ```

3. Activate the virtual environment:
   * **Windows (PowerShell):** `venv\Scripts\Activate.ps1`
   * **Windows (cmd):** `venv\Scripts\activate.bat`
   * **macOS/Linux:** `source venv/bin/activate`

4. Install the dependencies:
   ```bash
   pip install -r requirements.txt
   ```

5. Set up environment variables. Create a `.env` file in the `backend/` folder:
   ```env
   # API Keys
   GEMINI_API_KEY=your_gemini_api_key_here
   
   # Database URI (defaults to SQLite if blank)
   # To use MySQL: mysql+pymysql://user:password@localhost/dbname
   DATABASE_URL=sqlite:///growthpilot.db
   
   # Ports (optional overrides)
   PORT=5000
   SIMULATOR_PORT=5001
   ```

---

## Running the Services

You must run **both** the CRM Backend and the Channel Simulator side-by-side.

### 1. Start the CRM Backend
```bash
python app.py
```
* Runs on: `http://localhost:5000`
* Automatically initializes the SQLite database file `growthpilot.db` and runs the database seed script to populate **1,000+ Indian customers, 5,000+ orders, 50+ campaigns, and communication logs**.

### 2. Start the Channel Simulator (in a new terminal window)
Ensure your virtual environment is active in the new window, then run:
```bash
python channel_simulator.py
```
* Runs on: `http://localhost:5001`

---

## API Endpoints

### Customers & Orders
* `GET /api/customers` - Retrieve paginated, filterable list of customers.
* `POST /api/customers/upload` - Upload customer CSV (performs email/phone validation).
* `POST /api/orders/upload` - Upload order CSV (links to existing customers and updates spends).

### AI Growth Agent & Segments
* `POST /api/segment/generate` - Translates natural language queries (e.g. "Chennai premium customers") into SQL segment previews and sizes.
* `POST /api/campaign/generate` - Generates copy for SMS, Email, WhatsApp, RCS with custom tones (Friendly, Luxury, Professional, Promotional, Casual).
* `GET /api/dashboard/recommendations` - Computes and lists AI growth opportunities (e.g. churn warnings, repeat boosters).
* `POST /api/recommendation/apply` - Dismisses or marks recommendations as applied.

### Campaigns & Simulator Callbacks
* `GET /api/campaigns` - Lists all campaigns.
* `GET /api/campaigns/<id>` - Retrieves campaign details, customer-level communication status list, and AI performance reports.
* `POST /api/campaign/send` - Packages selected audience and triggers simulator launch.
* `POST /api/receipt` - Process delivery receipts (Sent -> Delivered -> Opened -> Clicked) and computes dynamic order conversions.

### Analytics & Dashboard
* `GET /api/dashboard` - Fetches high-level executive cards (LTV, Influenced revenue, delivery rates).
* `GET /api/analytics` - Deep-dive metrics including funnel conversion, city spread, risk metrics, and channel ROI.

---

## Production Deployment

### Database Swap
For production-grade environments, swap out SQLite for a hosted MySQL or PostgreSQL server. Simply update the environment variable in your production host settings:
```env
DATABASE_URL=mysql+pymysql://admin:securepassword@dbhost.cluster-xyz.us-east-1.rds.amazonaws.com/growthpilot
```

### Hosting Recommendations
1. **Render.com / Railway.app / Heroku:** Great for deploying the Python Flask CRM and the Simulator as separate Web Services.
2. **Vercel / Netlify:** Best for deploying the React frontend.
