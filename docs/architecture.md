# Agent Architecture: VM-per-Session Model

## Overview

Our autonomous agent framework uses a VM-per-session architecture where each user session runs in a dedicated Ubuntu virtual machine. This approach provides strong isolation between users, robust security, and a consistent environment for the agent to operate in.

## Key Components

### 1. VM Agent

Each Ubuntu VM contains a fully functioning agent environment:

- **Agent Core**: The central planning and execution engine that breaks down user tasks into steps and executes them
- **Terminal Module**: Secure execution of whitelisted terminal commands within the VM
- **Browser Automation**: Headless browser capabilities for web navigation and interaction
- **Self-Verification**: Mechanisms to validate actions and results for improved reliability
- **VM Client**: A lightweight service that communicates with the central orchestration server

The VM agent operates within the boundaries of its virtual machine, with access to a standard set of Ubuntu tools and packages. The agent has no direct access to the host system or other VMs.

### 2. Central Orchestration Backend

The backend server coordinates all user sessions and VM instances:

- **VM Management**:
  - Provisioning new VMs when users start sessions
  - Monitoring VM health and resource usage
  - Gracefully shutting down VMs when sessions end
  - Maintaining a pool of pre-warmed VMs for rapid session start

- **User Management**:
  - Authentication and authorization
  - User preferences and history
  - Session tracking and resumption

- **Task Coordination**:
  - Receiving task requests from the web frontend
  - Routing tasks to the appropriate VM
  - Streaming status updates and results back to users

- **LLM Proxy**:
  - Managing connections to LLM APIs (OpenAI, Anthropic, etc.)
  - Caching common LLM requests for efficiency
  - Fallback mechanisms when primary models are unavailable

The backend is designed to be stateless where possible, with session state stored in a distributed database to allow horizontal scaling.

### 3. Web Frontend

The web interface provides users with a clean, intuitive way to interact with their agent:

- **Task Input**: Natural language interface for specifying tasks
- **Session Dashboard**: View and manage active and past sessions
- **Task Monitoring**:
  - Real-time updates on task progress
  - Visualization of the execution plan
  - Terminal output and browser screenshots/video when relevant
  - Ability to pause, modify, or terminate tasks
- **Responsive Design**: Works across desktop and mobile devices

## Communication Flow

1. **Session Initialization**:
   - User logs in to the web frontend
   - Backend provisions a new VM or activates one from the warm pool
   - VM agent initializes and establishes a WebSocket connection to the backend
   - Frontend is notified that the session is ready

2. **Task Execution**:
   - User enters a task description in the frontend
   - Request is sent to the backend server
   - Backend routes the task to the appropriate VM
   - VM agent processes the task:
     - Breaks it down into steps using LLM
     - Executes steps sequentially
     - Reports progress back to the backend
   - Backend streams updates to the frontend
   - Results are displayed to the user in real-time

3. **Session Termination**:
   - User explicitly ends the session or timeout occurs
   - Backend signals the VM agent to complete any pending tasks
   - VM state is optionally preserved for future sessions
   - VM is either recycled (reset to clean state) or shut down
   - Session data is archived for the user's history

## Security Considerations

The VM-per-session model provides several security advantages:

- **Isolation**: Each user operates in a completely separate environment
- **Containment**: Any security issues are contained within the VM
- **Clean State**: VMs can be reset to a known clean state between sessions
- **Resource Limits**: Each VM has defined CPU, memory, and network limits
- **Execution Control**: Commands and browser actions are strictly controlled
- **Monitoring**: All actions within the VM can be logged and monitored
- **Session Encryption**: Communication between components is encrypted

## Scalability

The architecture is designed to scale horizontally:

- **VM Pool**: Maintain a pool of pre-initialized VMs to reduce startup time
- **Auto-scaling**: Automatically adjust the VM pool size based on demand
- **Regional Deployment**: Deploy VM infrastructure across multiple regions for lower latency
- **Load Balancing**: Distribute backend load across multiple server instances
- **Database Sharding**: Scale the session database as user count grows
- **Microservices**: Split the backend into focused microservices as needed

## Development and Testing

For development and testing purposes:

- **Local Environment**: Developers can use Docker containers to simulate VMs locally
- **Mock Mode**: A mock mode replaces actual VMs with lightweight containers
- **Test Suite**: Automated tests for each component and end-to-end tests
- **CI/CD Pipeline**: Automated building and testing of VM images

## Production Deployment

In production:

- **Cloud Providers**: Deploy on AWS, GCP, Azure, or other cloud platforms
- **Kubernetes**: Use Kubernetes for orchestration of backend services
- **VM Technologies**: Use cloud provider VMs or container technologies (e.g., AWS EC2, GCP GCE, or Firecracker microVMs)
- **Monitoring**: Comprehensive monitoring of all system components
- **Backup and Recovery**: Regular backups and disaster recovery procedures

## Future Enhancements

- **VM Hibernation**: Save VM state for long-running tasks and resume later
- **Custom VM Templates**: Specialized VM templates for different task domains
- **GPU Access**: Optional GPU allocation for VMs that need it (e.g., for ML tasks)
- **Multi-Agent Collaboration**: Enable multiple VMs to work together on complex tasks
- **On-Premises Option**: Enterprise deployment on customer's own infrastructure