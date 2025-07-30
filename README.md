# Airline Competition Simulation

A simulation environment for student teams competing in the airline industry. Built with Python, LangGraph, Streamlit, and AI agents powered by Gemini.

## Features

- **Multi-Agent System**: Company, Market, and Evaluation agents using LangGraph
- **Student Authentication**: Team-based login system
- **Plan Submission**: JSON upload and manual plan creation
- **Real-time Market Simulation**: Dynamic market conditions and events
- **AI-Powered Feedback**: Comprehensive evaluation and feedback system
- **Firestore Integration**: Secure data storage with team-based access control
- **Observability**: LangSmith integration for monitoring and debugging

## Architecture

### AI Agents

1. **Company Agent** (LangGraph Sub-graph)
   - Validator Node: Validates budget and capacity constraints
   - Implementer Node: Determines which actions can be executed
   - Outputs approved/rejected actions and cash usage

2. **Market Agent**
   - Evaluates competitive dynamics between airlines
   - Generates market events and updates conditions
   - Calculates market share and performance metrics

3. **Evaluation Agent**
   - Provides educational feedback to students
   - Generates performance scores and improvement recommendations
   - Creates instructor summaries

### Workflow

1. Students submit semester implementation plans
2. Company agents validate and process plans
3. Market agent evaluates overall market performance
4. Evaluation agent provides feedback
5. Students receive results and market updates

## Setup

### Prerequisites

- Python 3.9+
- Google Cloud Project with Firestore enabled
- Gemini API key
- (Optional) LangSmith account for observability

### Installation

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd airline-simulation
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Set up environment variables:
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

4. Configure Google Cloud credentials:
   - Download service account key from Google Cloud Console
   - Set `GOOGLE_APPLICATION_CREDENTIALS` path in `.env`

5. Initialize Firestore database:
   ```python
   from src.database import FirestoreManager
   db = FirestoreManager()
   db.initialize_default_data()
   ```

### Configuration

Edit `.env` file with your settings:

```env
# Google Cloud / Firestore
GOOGLE_APPLICATION_CREDENTIALS=path/to/service-account-key.json
FIRESTORE_PROJECT_ID=your-project-id

# AI API Configuration
GEMINI_API_KEY=your-gemini-api-key

# LangSmith (optional)
LANGSMITH_API_KEY=your-langsmith-api-key
LANGSMITH_PROJECT=airline-simulation

# Streamlit Authentication
STREAMLIT_AUTH_COOKIE_KEY=your-secret-cookie-key
```

## Usage

### Running the Application

```bash
streamlit run app.py
```

### Team Login

Default teams are configured in `src/auth.py`. In production, implement proper user management.

### Plan Submission Format

JSON plan structure:
```json
{
  "team_id": "team1",
  "semester": "2024-1",
  "total_budget": 500000,
  "actions": [
    {
      "action_type": "purchase_aircraft",
      "description": "Buy 2 Boeing 737s for domestic routes",
      "cost": 200000,
      "parameters": {"count": 2}
    },
    {
      "action_type": "add_route",
      "description": "Launch Prague-London route",
      "cost": 50000,
      "parameters": {"route": "PRG-LHR"}
    }
  ]
}
```

### Action Types

- `purchase_aircraft`: Buy new aircraft
- `add_route`: Launch new route
- `marketing_campaign`: Improve reputation
- `staff_training`: Enhance operations
- `maintenance_upgrade`: Improve reliability

## Database Schema

### Collections

- `airlines`: Airline state documents (team_id as document ID)
- `plans`: Submitted semester plans
- `simulation`: Market state and configuration
- `feedback`: Evaluation feedback records

### Security Rules

Firestore rules ensure teams can only read/write their own data:

```javascript
match /airlines/{teamId} {
  allow read, write: if request.auth.uid == teamId;
}
```

## Development

### Project Structure

```
src/
├── __init__.py
├── config.py          # Configuration management
├── models.py          # Pydantic data models
├── database.py        # Firestore integration
├── auth.py           # Authentication system
├── workflow.py       # Simulation orchestration
├── observability.py  # LangSmith integration
└── agents/
    ├── __init__.py
    ├── company_agent.py    # Company agent (LangGraph)
    ├── market_agent.py     # Market evaluation
    └── evaluation_agent.py # Student feedback
```

### Testing

```bash
# Run individual components
python -m src.agents.company_agent
python -m src.agents.market_agent
python -m src.workflow

# Test plan processing
python -c "
from src.workflow import SimulationWorkflow
from src.models import SemesterPlan, AirlineAction
from datetime import datetime

plan = SemesterPlan(
    team_id='team1',
    semester='2024-1',
    actions=[],
    total_budget=100000,
    submission_timestamp=datetime.now()
)

workflow = SimulationWorkflow()
results = workflow.process_single_plan(plan)
print(results)
"
```

### Adding New Action Types

1. Update `models.py` with new action parameters
2. Add validation logic in `CompanyAgent._is_action_feasible()`
3. Implement state changes in `CompanyAgent._apply_action_to_state()`
4. Update UI form in `app.py`

## Deployment

### Streamlit Cloud

1. Push to GitHub repository
2. Connect to Streamlit Cloud
3. Add environment variables in Streamlit Cloud settings
4. Deploy

### Docker (Alternative)

```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
EXPOSE 8501

CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
```

## Monitoring

### LangSmith Integration

- Agent execution traces
- Error logging and debugging
- Performance metrics
- Student interaction analytics

### Metrics to Monitor

- Plan submission rates
- Agent processing success rates
- Average evaluation scores
- Market simulation stability
- User session duration

## Troubleshooting

### Common Issues

1. **Firestore Permission Denied**
   - Check service account permissions
   - Verify security rules
   - Ensure correct project ID

2. **Gemini API Errors**
   - Verify API key validity
   - Check rate limits
   - Monitor quota usage

3. **Authentication Issues**
   - Update streamlit-authenticator configuration
   - Check cookie settings
   - Verify team credentials

### Debugging

Enable debug logging:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

Check LangSmith traces for agent execution details.

## Contributing

1. Fork the repository
2. Create feature branch
3. Add tests for new functionality
4. Submit pull request

## License

[Your License Here]