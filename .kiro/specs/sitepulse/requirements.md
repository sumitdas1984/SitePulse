# Requirements Document

## Introduction

SitePulse is a lightweight, self-hosted monitoring solution for developers who want to track the uptime and performance of their web applications, APIs, and personal websites. It automates periodic health checks, records latency over time, sends smart alerts on consecutive failures, and presents a visual dashboard with an availability heatmap. The system is built on a FastAPI backend with a background worker and a Streamlit frontend.

## Glossary

- **Monitor**: A configured health check target consisting of a name, URL, protocol type, and check interval.
- **Check**: A single execution of a health check against a Monitor's URL, recording status and latency.
- **Worker**: The background process that schedules and executes Checks at configured intervals.
- **Alert**: A notification sent to the user when a Monitor exceeds the consecutive failure threshold.
- **Consecutive Failure Count**: The number of uninterrupted failed Checks for a given Monitor.
- **Failure Threshold**: The user-configured number of consecutive failures required before an Alert is triggered.
- **Uptime Percentage**: The ratio of successful Checks to total Checks over a given time window, expressed as a percentage.
- **Average Latency**: The mean response time in milliseconds across all Checks in a given time window.
- **Heatmap**: A time-series grid visualization showing per-period availability status for a Monitor.
- **Webhook**: An HTTP POST callback URL used to deliver Alert payloads to external services such as Slack.
- **Dashboard**: The Streamlit-based user interface displaying the current status and history of all Monitors.
- **API**: The FastAPI-based HTTP interface used by the Dashboard and external clients to manage Monitors and retrieve Check data.

---

## Requirements

### Requirement 1: Monitor Management

**User Story:** As a developer, I want to add, update, and remove monitors, so that I can control which services SitePulse tracks.

#### Acceptance Criteria

1. THE API SHALL expose endpoints to create, read, update, and delete Monitors.
2. WHEN a Monitor is created, THE API SHALL require a service name, a URL, and a check interval in minutes.
3. WHEN a Monitor is created, THE API SHALL validate that the URL is a well-formed HTTP or HTTPS URL.
4. IF a Monitor creation request contains a malformed URL, THEN THE API SHALL return a 422 status code with a descriptive error message.
5. WHEN a Monitor is created, THE API SHALL assign it a unique identifier.
6. WHEN a Monitor is deleted, THE API SHALL also delete all Check records associated with that Monitor.
7. THE API SHALL support a check interval between 1 minute and 1440 minutes (24 hours) inclusive.
8. IF a requested check interval is outside the supported range, THEN THE API SHALL return a 422 status code with a descriptive error message.

---

### Requirement 2: Multi-Protocol Health Checks

**User Story:** As a developer, I want to check services using HTTP status codes or custom JSON response validation, so that I can verify both availability and application-level correctness.

#### Acceptance Criteria

1. WHEN a Check is executed against an HTTP or HTTPS Monitor, THE Worker SHALL record the HTTP status code and response time in milliseconds.
2. WHEN a Monitor is configured with an expected HTTP status code, THE Worker SHALL mark the Check as successful only if the response status code matches the expected value.
3. WHERE a Monitor is configured with a JSON assertion, THE Worker SHALL mark the Check as successful only if the response body contains the specified key-value pair.
4. IF a Check request times out after 30 seconds, THEN THE Worker SHALL record the Check as failed with a timeout reason.
5. IF a Check request results in a network error, THEN THE Worker SHALL record the Check as failed with a connection error reason.
6. THE Worker SHALL store each completed Check with its timestamp, status (success or failure), HTTP status code, response time, and failure reason if applicable.

---

### Requirement 3: Background Worker Scheduling

**User Story:** As a developer, I want checks to run automatically at configured intervals, so that I don't have to trigger them manually.

#### Acceptance Criteria

1. WHEN the API starts, THE Worker SHALL begin scheduling Checks for all existing Monitors according to their configured intervals.
2. WHEN a new Monitor is created, THE Worker SHALL schedule Checks for that Monitor without requiring a restart.
3. WHEN a Monitor is deleted, THE Worker SHALL stop scheduling Checks for that Monitor.
4. WHEN a Monitor's check interval is updated, THE Worker SHALL apply the new interval to subsequent Check scheduling.
5. WHILE a Check is in progress for a Monitor, THE Worker SHALL NOT initiate a duplicate Check for the same Monitor.

---

### Requirement 4: Latency Tracking

**User Story:** As a developer, I want to track response times over time, so that I can identify performance degradation before it becomes an outage.

#### Acceptance Criteria

1. THE API SHALL expose an endpoint that returns the response time for each Check within a requested time window for a given Monitor.
2. THE API SHALL calculate and return the Average Latency for a Monitor over the last 24 hours.
3. THE API SHALL calculate and return the Average Latency for a Monitor over the last 7 days.
4. WHEN no Checks exist for a Monitor within the requested time window, THE API SHALL return a null value for Average Latency.

---

### Requirement 5: Uptime Calculation

**User Story:** As a developer, I want to see uptime percentages, so that I can understand the reliability of my services at a glance.

#### Acceptance Criteria

1. THE API SHALL calculate Uptime Percentage for a Monitor as the number of successful Checks divided by the total number of Checks in the time window, multiplied by 100.
2. THE API SHALL return the Uptime Percentage for the last 24 hours for each Monitor.
3. THE API SHALL return the Uptime Percentage for the last 7 days for each Monitor.
4. WHEN no Checks exist for a Monitor within the requested time window, THE API SHALL return a null value for Uptime Percentage.

---

### Requirement 6: Smart Alerting

**User Story:** As a developer, I want to receive alerts only after multiple consecutive failures, so that I am not spammed by transient errors.

#### Acceptance Criteria

1. WHEN a Monitor is created or updated, THE API SHALL accept a Failure Threshold value between 1 and 10 inclusive.
2. WHEN the Consecutive Failure Count for a Monitor reaches the configured Failure Threshold, THE API SHALL trigger an Alert.
3. WHEN an Alert is triggered, THE API SHALL NOT trigger another Alert for the same Monitor until at least one successful Check has been recorded.
4. WHEN a successful Check is recorded for a Monitor, THE Worker SHALL reset the Consecutive Failure Count for that Monitor to zero.
5. IF a Failure Threshold is not specified during Monitor creation, THEN THE API SHALL default the Failure Threshold to 3.

---

### Requirement 7: Email Notifications

**User Story:** As a developer, I want to receive alert emails, so that I am notified of outages without checking the dashboard.

#### Acceptance Criteria

1. WHERE a Monitor is configured with an alert email address, THE API SHALL send an email Alert to that address when the Failure Threshold is reached.
2. WHEN an email Alert is sent, THE API SHALL include the Monitor name, URL, Consecutive Failure Count, and timestamp of the last failed Check in the email body.
3. IF the email delivery fails, THEN THE API SHALL log the failure with the Monitor identifier and error reason.
4. THE API SHALL support SMTP configuration via environment variables for host, port, username, and password.

---

### Requirement 8: Webhook Notifications

**User Story:** As a developer, I want to send alerts to Slack or other services via webhooks, so that my team can be notified in our existing communication channels.

#### Acceptance Criteria

1. WHERE a Monitor is configured with a Webhook URL, THE API SHALL send an HTTP POST request to that URL when the Failure Threshold is reached.
2. WHEN a Webhook Alert is sent, THE API SHALL include a JSON payload containing the Monitor name, URL, Consecutive Failure Count, and timestamp of the last failed Check.
3. IF the Webhook POST request returns a non-2xx status code, THEN THE API SHALL log the failure with the Monitor identifier, Webhook URL, and response status code.
4. IF the Webhook POST request times out after 10 seconds, THEN THE API SHALL log the timeout with the Monitor identifier and Webhook URL.

---

### Requirement 9: Availability Heatmap

**User Story:** As a developer, I want to see a visual heatmap of uptime history, so that I can quickly identify patterns of degradation or recurring outages.

#### Acceptance Criteria

1. THE API SHALL expose an endpoint that returns per-hour availability status for a Monitor over the last 90 days.
2. WHEN computing the Heatmap, THE API SHALL classify each hour as "up" if all Checks in that hour succeeded, "degraded" if some Checks failed, "down" if all Checks failed, or "no data" if no Checks were recorded.
3. THE Dashboard SHALL render the Heatmap as a grid where each cell represents one hour and is color-coded by availability status.
4. WHEN a Heatmap cell is selected, THE Dashboard SHALL display the Uptime Percentage and Average Latency for that hour.

---

### Requirement 10: Dashboard Overview

**User Story:** As a developer, I want a single-page dashboard showing all my monitors, so that I can assess the health of all my services at a glance.

#### Acceptance Criteria

1. THE Dashboard SHALL display a list of all Monitors with their current status, Uptime Percentage for the last 24 hours, and Average Latency for the last 24 hours.
2. WHEN a Monitor's most recent Check is a failure, THE Dashboard SHALL display that Monitor with a visual failure indicator.
3. WHEN a Monitor's most recent Check is a success, THE Dashboard SHALL display that Monitor with a visual success indicator.
4. THE Dashboard SHALL refresh Monitor status data at an interval no greater than 60 seconds without requiring a manual page reload.
5. THE Dashboard SHALL allow a user to navigate to a detail view for an individual Monitor showing its Check history, latency trend, and Heatmap.
