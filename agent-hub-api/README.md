# agent-hub-api
agent-hub-api is the backend engine that powers Agent Hub, acting as a multi-agent orchestration layer built on the Model Context Protocol (MCP). It hosts and manages intelligent tool integrations—known as agents—enabling seamless natural language interaction between users and developer/DevOps tools like GitHub, Docker, Azure, and databases.

This FastAPI application integrates with **Azure OpenAI** using the new `openai>=1.0.0` SDK. It exposes a `/chat` endpoint that sends a prompt to your Azure-deployed OpenAI model and returns the model’s response.
---

## 🔧 Requirements

- Python 3.12+
- Azure OpenAI resource with a deployed model
- An `.env` file with your credentials

---

## 📁 Project Structure

```
agent-hub-api/
├── app/
│   └── main.py
├── .env
├── README.md
├── pyproject.toml
└── uv.lock
```

---

## 📦 Installation

```bash
# Create and activate virtual environment (optional)
uv venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows

# Install dependencies
uv sync
```

---

## 🔐 .env Configuration

Create a `.env` file in the project root with the following:

```
AZURE_OPENAI_API_KEY=your-azure-openai-key
AZURE_OPENAI_ENDPOINT=https://genai-nexus.int.api.corpinter.net/apikey/
AZURE_OPENAI_DEPLOYMENT=gpt-4o
AZURE_OPENAI_API_VERSION=2024-10-21
```

---

## 🚀 Running the App

```bash
uvicorn app.main:app --reload --port 8000
```

Then visit the docs at [http://localhost:8000/docs](http://localhost:8000/docs)

---

## 📬 Example Request

### POST `/chat`

```json
{
  "prompt": "Tell me a joke about AI."
}
```

### Example Response

```json
{
  "response": "Why did the AI go to therapy? It had a lot of neural issues."
}
```

---

## 🧠 Notes

- Use `AzureOpenAI`, not `OpenAI`, in SDK v1.x.
- The model must match your **deployment name**, not the model family (e.g., `gpt-35-turbo`, not `gpt-3.5-turbo`).
- API version must be valid for your Azure resource.

---

## 📄 License

MIT License


