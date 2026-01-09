# AI Function Calling

We’ve been investigating whether AI function calling can make it easier for users to interrogate and work with UPRN-based datasets—particularly in cases where today’s workflows require navigating multiple UI controls or composing more formal query inputs.

Function calling is interesting here because it gives a model a constrained way to take actions: instead of generating free-text instructions, it can select from a small set of predefined functions (for example: filter, zoom, download), pass structured parameters, and let the application execute those actions deterministically. Our goal in this early work was to see what this interaction pattern looks like in practice, and what kinds of user tasks it supports well.

Below, we describe an early prototype and a sequence of small experiments we used to probe the capabilities and limitations.

## Experiment 1: filtering by ward and controlling the map view

Our first prototype focused on basic map interaction. We tested whether a model could:

* control the map view (for example, zooming in and out)
* filter UPRNs by ward, and

This provided a simple way to validate the end-to-end loop: user intent → model selects a function → the service executes it → the user sees the result.

[Filter and zoom](https://github.com/NERC-Digital-Solutions-Hub/dsh-content-videos/raw/refs/heads/dev/videos/llm/func-call/llm-func-call-poc.mp4)

## Experiment 2: filtering by specific areas

We then extended the same approach to support filtering by more specific geographic areas. This pushed the prototype slightly beyond a single administrative boundary type and helped us explore how well the model handles ambiguity (e.g., multiple places with similar names) and parameter selection when the shape/area is a more explicit constraint.

[Filter by area](https://github.com/NERC-Digital-Solutions-Hub/dsh-content-videos/raw/refs/heads/dev/videos/llm/func-call/llm-func-call-poc-filter-by-area.mp4)

## Experiment 3: filtering by pollutant levels

Next, we explored a more data-driven query: filtering UPRNs based on pollutant levels. This was a useful stress-test because it requires the model to translate a natural-language condition into structured filters (thresholds, fields, and operators), rather than selecting from a small set of map controls.

This experiment helped us evaluate how function calling performs when the user’s request is closer to an analytical query than a UI action.

[Filter by pollutants](https://github.com/NERC-Digital-Solutions-Hub/dsh-content-videos/raw/refs/heads/dev/videos/llm/func-call/llm-func-call-poc-pollutants-filter.mp4)

## Experiment 4: completing an end-to-end workflow with download

Finally, we tested whether the same interface could support a complete workflow: apply filters and then export the resulting dataset. This brings together several steps that users often complete manually—refining results, confirming scope, and retrieving data—in a single conversational interaction that triggers explicit actions in the service.

[Filter by pollutants then download](https://github.com/NERC-Digital-Solutions-Hub/dsh-content-videos/raw/refs/heads/dev/videos/llm/func-call/llm-func-call-poc-pollutants-filter-download.mp4)

### What we’ve learned so far

Across these experiments, function calling looks promising for reducing friction in common tasks: users can describe what they want, and the service can respond by executing explicit, auditable actions on the underlying data.

This is still early-stage work, but it suggests that function calling can provide a practical bridge between natural-language intent and structured geospatial operations—particularly for workflows currently split between UI interactions and query building.

Next, we plan to focus on robustness (handling ambiguity and edge cases), transparency (showing what was executed and why), and safety/constraints (ensuring the model can only take permitted actions with validated parameters).


