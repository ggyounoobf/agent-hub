# MCP Tools Server

A Model Context Protocol (MCP) tools server using FastMCP, showcasing sample tools that demonstrate MCP compliance and serve as a reference for AI model integration.

## ✨ Features

- ✅ **MCP Compliant** — Follows Anthropic’s Model Context Protocol spec  
- 🔧 **Multiple Tools** — Includes simple and extendable examples  
- 🌐 **Flexible Connections** — Supports HTTP and stdio  
- 📚 **Structured Project** — Clean layout, easy to maintain  
- 🪵 **Rich Logging** — Console logging with `rich`  

## 🔨 Available Tools

### `countwords`
Counts words in a sentence.  
```json
{ "word_count": 4 }
```

### `combineanimals`
Combines two animal names into a hybrid.  
```json
{ "result": "Lion-Eagle Fusion" }
```

### `hello_world`
Returns a greeting.  
```json
{ "message": "Hello, Alice!" }
```

### `add`
Adds two numbers.  
```json
{ "result": 8 }
```

### `sample_tool_server_status`
Checks if the server is running.  
```json
{
  "status": "online",
  "message": "MCP Sample Tool server is running",
  "version": "0.1.0"
}
```

## 🧱 Tech Stack

- Python 3.12+
- [`fastmcp`](https://github.com/jlowin/fastmcp)
- Rich (logging)
- Pydantic (validation)
- dotenv (config)

## 📄 License

MIT License

## 🤝 Contributing

Pull requests are welcome. Please fork the repo, make your changes, and submit a PR.