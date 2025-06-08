# Hume v2 Roadmap - Code Tasks

This document outlines the main coding tasks required to implement the SaaS oriented version 2 of Hume.

## 1. Architectural Refactor
- [ ] Organize the repository into Python packages:
  - `hume` – CLI and client utilities.
  - `humed` – daemon and local transports.
  - `humesaas` – new SaaS service components.
- [x] Implement plugin loading for transfer methods so new transports can be added without touching the core code.
- [ ] Replace the current SQLite queue with an asynchronous job queue (e.g. using `asyncio` or a broker such as Redis/RabbitMQ) to support multiple transports and higher throughput.
- [ ] Add master/secondary mode for `humed`, allowing secondary instances to forward queued messages to a primary server.
- [ ] Implement a watchdog that periodically checks `humed` is alive and send alerts when it is not.

## 2. Security Improvements
- [x] Introduce message format versioning and rigorous validation of incoming data.
- [ ] Provide optional encryption and authentication for all connections.

## 3. Enhanced Configuration
- [x] Finish `humeconfig --from-url` so configuration can be bootstrapped from an HTTP endpoint.
- [ ] Allow per-task Slack channel mapping and support multiple simultaneous transfer methods via the plugin system.

## 4. SaaS Service
- [ ] Build a server component exposing a REST API to collect events from `humed` instances.
- [ ] Provide authentication tokens for agents and store incoming events in a central database.
- [ ] Develop a web dashboard to list and filter stored events.
- [ ] Extend `humed` so it can forward events to the SaaS API in addition to local transports.

## 5. Monitoring and Metrics
- [ ] Implement Prometheus‑compatible status storage so external systems can scrape host/task state.
- [ ] Expose built‑in metrics endpoints for both the SaaS service and local `humed` instances.

## 6. Quality and Testing
- [ ] Add automated tests for the CLI, daemon behaviour and transfer plugins.
- [ ] Document the REST API and provide examples for integrating with the SaaS service.

