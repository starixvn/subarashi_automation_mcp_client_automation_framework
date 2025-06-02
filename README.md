# 🤖 MCP Client - Advanced AI Assistant với Tool Integration

[![Version](https://img.shields.io/badge/version-2.0.0-blue.svg)](https://github.com/your-repo/mcp-client)
[![Python](https://img.shields.io/badge/python-3.11+-green.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115.12+-red.svg)](https://fastapi.tiangolo.com)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.45.1+-orange.svg)](https://streamlit.io)
[![Docker](https://img.shields.io/badge/docker-ready-blue.svg)](https://docker.com)

## 🚀 System Features & Capabilities

### 🧠 Advanced AI Conversation Engine
**Intelligent Chat System with Proactive Tool Integration**

- **Smart Conversation Management**: Real-time AI-powered conversations with context preservation and memory
- **Proactive Tool Usage**: AI automatically selects and executes appropriate tools without user confirmation
- **Strategic Planning**: Multi-step task execution with intelligent tool sequencing and dependency management
- **Adaptive Error Recovery**: Dynamic strategy adjustment when tools fail or return unexpected results
- **Context-Aware Responses**: AI understands conversation history and maintains contextual relevance across interactions
- **Export & Analytics**: Complete conversation export with detailed statistics and tool usage tracking

### 🛠️ Comprehensive Tool Management System
**Direct Access to MCP Tools with Smart Execution**

- **Tool Discovery**: Automatic detection and cataloging of available MCP tools from connected servers
- **Interactive Tool Testing**: Direct tool execution interface with parameter validation and result visualization  
- **Tool Documentation**: Comprehensive tool descriptions, parameter specifications, and usage examples
- **Batch Tool Operations**: Execute multiple tools in parallel with coordinated result processing
- **Tool Result Processing**: Intelligent parsing of tool outputs including text, images, and embedded resources
- **Tool Performance Monitoring**: Execution time tracking, success rates, and error analysis

### 🔌 Multi-Protocol MCP Integration
**Universal MCP Server Connectivity**

- **Multi-Transport Support**: 
  - **SSE (Server-Sent Events)**: HTTP-based streaming for web-compatible connections
  - **WebSocket**: Real-time bidirectional communication for interactive applications
  - **stdio**: Process-based communication for local tool integration
- **Resource Management**: Access and read MCP resources with automatic content type detection
- **Prompt Templates**: Use and execute MCP prompt templates with dynamic parameter substitution
- **Connection Health Monitoring**: Continuous monitoring of MCP server connectivity with automatic reconnection
- **Session Persistence**: Maintain long-lived connections with proper cleanup and resource management

### 🎨 Interactive Web Interface
**Modern Streamlit-Based User Experience**

- **Tabbed Interface Design**:
  - **Chat Assistant**: Full-featured conversation interface with AI tool integration
  - **Tools Overview**: Visual tool catalog with search, filtering, and category organization
  - **Tool Testing**: Direct tool execution playground with parameter input and result display
  - **System Configuration**: Real-time configuration management with validation and testing
- **Real-Time Status Dashboard**: Live system health monitoring with connection status indicators
- **Responsive Design**: Optimized for desktop and mobile devices with adaptive layouts
- **Export Capabilities**: Download conversations, tool results, and system reports

### 📡 RESTful API Services
**Complete Backend API for Integration**

- **Chat Endpoints**:
  - Send messages with automatic AI processing and tool execution
  - Retrieve conversation history with full context and metadata
  - Clear conversations with optional selective deletion
- **Tool Management APIs**:
  - List available tools with detailed specifications and capabilities
  - Execute individual tools with parameter validation and result formatting
  - Get tool documentation and usage statistics
- **Configuration Management**:
  - Real-time configuration updates without service restart
  - Configuration validation and testing endpoints
  - Environment-specific settings management
- **Health & Monitoring**:
  - Comprehensive system health checks with detailed service status
  - Performance metrics and connection diagnostics
  - Service reconnection and recovery operations
- **MCP Resource Access**:
  - List and read MCP resources with content type detection
  - Access prompt templates with parameter substitution
  - Resource subscription and change notifications

### 🔧 Dynamic Configuration System
**Flexible Multi-Source Configuration Management**

- **Real-Time Configuration Updates**: Change settings without service restart or data loss
- **Environment-Aware Settings**: Automatic detection and application of development/production configurations
- **Configuration Validation**: Real-time validation of settings with detailed error reporting
- **API Key Management**: Secure handling and testing of Google Gemini API keys
- **MCP Server Configuration**: Dynamic MCP server URL and transport type configuration
- **Parameter Tuning**: Adjustable AI parameters including temperature, max tokens, and tool call limits

### 📊 Advanced Monitoring & Diagnostics
**Comprehensive System Health & Performance Tracking**

- **Service Health Monitoring**: 
  - Individual service status tracking (AI, MCP, Configuration)
  - Connection quality monitoring with latency and error rate tracking
  - Resource usage monitoring including memory and connection pools
- **Performance Analytics**:
  - Tool execution performance with timing and success rate metrics
  - Conversation analytics with message counts and tool usage patterns
  - System performance metrics including response times and throughput
- **Error Tracking & Recovery**:
  - Detailed error logging with context and stack traces
  - Automatic error recovery with fallback strategies
  - User-friendly error reporting with actionable resolution steps

### 🤖 Intelligent AI Integration
**Advanced Google Gemini Integration with MCP Tool Support**

- **Smart Schema Conversion**: Automatic conversion of MCP tool schemas to Gemini-compatible formats
- **Adaptive Response Generation**: Context-aware AI responses with dynamic tool selection
- **Multi-Modal Support**: Handle text, image, and embedded resource content types
- **Parameter Optimization**: Intelligent adjustment of AI parameters based on task complexity
- **Error Recovery**: Graceful handling of AI service errors with alternative strategies
- **Conversation Memory**: Maintain conversation context across multiple interactions and tool executions

### 🔄 Advanced Session Management
**Robust Connection and State Management**

- **Multi-Transport Session Handling**: Unified interface for different MCP transport protocols
- **Connection Lifecycle Management**: Automatic connection establishment, monitoring, and cleanup
- **State Preservation**: Maintain session state across reconnections and service restarts
- **Resource Cleanup**: Proper cleanup of connections, sessions, and allocated resources
- **Concurrent Session Support**: Handle multiple concurrent MCP connections and operations
- **Session Recovery**: Automatic recovery from connection failures with state restoration

### 🛡️ Error Handling & Resilience
**Comprehensive Error Management with Graceful Degradation**

- **Structured Exception Handling**: Detailed error classification and context preservation
- **Graceful Service Degradation**: Continue operation with reduced functionality when services are unavailable
- **Automatic Recovery Mechanisms**: Self-healing capabilities for common error conditions
- **User-Friendly Error Messages**: Clear, actionable error reporting for users
- **Debug Information**: Detailed diagnostic information for troubleshooting and support
- **Logging Integration**: Comprehensive error logging with appropriate severity levels

### 🔍 Utility & Helper Functions
**Comprehensive Support Functions for Enhanced Functionality**

- **Content Processing**: Extract and format text from various content types and tool results
- **Data Validation**: Sanitize and validate tool arguments and user inputs
- **Timestamp Management**: Format and handle timestamps across different components
- **Text Processing**: Truncate, format, and process text content for display and storage
- **Server Validation**: Validate MCP server URLs and connection parameters
- **Tool Information Formatting**: Format tool call information for display and logging

### 📈 Performance Optimization Features
**High-Performance Operation with Smart Caching**

- **Intelligent Caching**: Multi-layer caching for health status, tool lists, and configuration data
- **Async Operations**: Full asynchronous operation support for non-blocking performance
- **Connection Pooling**: Efficient HTTP connection management for external services
- **Resource Management**: Automatic cleanup and optimization of system resources
- **Batch Processing**: Efficient batch operations for multiple tool executions
- **Smart Cache Invalidation**: Intelligent cache management with automatic refresh strategies