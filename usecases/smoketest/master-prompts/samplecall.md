Read and execute:

usecases/smoketest/master-prompts/parmetrized-e2e.md
Block if you don’t find the file 

This Document is your orchestrator and router for any resource, don’t read a random resources from your own

Use the following parameters:

TARGET_DOMAIN="STG"
TARGET_SERVICE=“service_name”
TEST_ID="ST-006-service_name”

Treat these values as runtime parameters for the prompt.

Do not modify the master prompt file.

Execute the smoke test exactly according to the instructions and validation
gates defined in the master prompt.

Generate the service-specific outputs under the output path defined by the
master prompt.

Do not modify any frozen AS-IS artifacts.
