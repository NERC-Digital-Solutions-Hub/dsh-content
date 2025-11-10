# AI Agents for Geospatial Data

Finding specific information within large geospatial datasets can be complex and time-consuming. To simplify this, we have developed a project using AI agents to interact directly with the Esri REST API for [ClimateJust](https://climatejust.org.uk) data.

This work explores how an AI-powered chatbot can answer user questions by intelligently querying a data API.

## An AI Chatbot for ClimateJust Data

We built a chatbot that understands natural language questions about ClimateJust data. Instead of requiring users to write complicated API queries, the chatbot does the hard work for them. It breaks down a question, figures out how to get the answer from the Esri API, and may even write and execute small pieces of code to process the data.

This approach allows for a more intuitive and powerful way to explore complex datasets. The system plans and executes multiple steps to retrieve and synthesize information, delivering a final answer directly to the user.

The diagram below outlines the decision-making process the AI agent follows to answer a query.

```mermaid
---
config:
  fontFamily: sans-serif
  themeVariables:
    fontSize: 14px
    textColor: black
    edgeLabelBackground: white
  flowchart:
    rankSpacing: 40
---

flowchart TD
  %% Terminators
  Start((Start)):::terminator
  End(((End))):::terminator

  %% Input/Output
  SavedAnswer[/"Saved Answer (JSON)"/]:::inout

  %% Decisions
  ShouldContinueResolvingSubqueries{Continue<br>Resolving<br>Subqueries?}:::decision
  ShouldConstructURL{Construct<br>URL?}:::decision
  ShouldAddCode{Add<br>Code?}:::decision

  %% Agentic Processes
  DecomposeQuery(Decompose Query):::agentic_process
  ConstructEsriAPIURL(Construct Esri API URL):::agentic_process
  AnswerSubquery(Answer Subquery):::agentic_process
  GenerateFinalAnswer(Generate Final Answer):::agentic_process
  GenerateCode(Try to Generate Code):::agentic_process

  %% Processes
  RetrieveRelevantTablesAndFields(Retrieve Relevant<br>Tables & Fields):::process
  PlanResolvingSubqueries(Plan Resolving Subqueries):::process
  FetchAPIResponse(Fetch API Response):::process
  RunCodeInDocker(Run Code in Docker):::process
  PropagateEmptyResults(Propagate Empty Results):::process

  %% Connections
  Start --> RetrieveRelevantTablesAndFields
  RetrieveRelevantTablesAndFields --> DecomposeQuery
  DecomposeQuery --> PlanResolvingSubqueries
  PlanResolvingSubqueries --> ShouldContinueResolvingSubqueries
  ShouldContinueResolvingSubqueries -- Yes --> ShouldConstructURL
  ShouldContinueResolvingSubqueries -- No -----> ShouldAddCode
  ShouldConstructURL -- Yes --> ConstructEsriAPIURL
  ShouldConstructURL -- No --> AnswerSubquery
  ConstructEsriAPIURL --> FetchAPIResponse
  FetchAPIResponse --> PropagateEmptyResults
  AnswerSubquery --> PropagateEmptyResults
  PropagateEmptyResults --> ShouldContinueResolvingSubqueries
  ShouldAddCode -- Yes --> GenerateCode
  ShouldAddCode -- No --> GenerateFinalAnswer
  GenerateCode -- Code<br>Generated --> RunCodeInDocker
  GenerateCode -- No Code<br>Needed --> GenerateFinalAnswer
  RunCodeInDocker --> GenerateFinalAnswer
  GenerateFinalAnswer --> SavedAnswer
  SavedAnswer --> End

  %% Style Definitions
  linkStyle default stroke-width:1.5px
  classDef terminator fill:#fbb, stroke:black, stroke-width:1.5px
  classDef process fill:lightblue, stroke:black, stroke-width:1.5px
  classDef agentic_process fill:lightblue, stroke:black, stroke-width:2px, stroke-dasharray: 6
  classDef decision fill:lightgreen, stroke:black, stroke-width:1.5px
  classDef inout fill:orange, stroke:black, stroke-width:1.5px
```

This project demonstrates the power of AI agents to act as intelligent assistants, making complex data sources more accessible to a wider audience.
