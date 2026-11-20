# Controlled AI execution

The synthetic planner is `synthetic-planner-v1`. It is a deterministic test executor, not a model provider. It can produce only a structured work breakdown for an authorized work package.

Each run records the requesting identity, work package, agent version, allowed tool, budget, spent amount, status and output artifact. The requester cannot approve its own artifact. The artifact must be approved before it can support a delivery workflow.

Future model adapters must preserve the same policy boundary and add provider/model version, token/cost accounting, timeout, retry and content-safety metadata. No agent may deploy, make payments, contact a client, expand scope or grant permissions from this interface.
