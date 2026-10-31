# Azure Container Apps deployment

## Recommendation

Use Azure Container Apps (ACA) for a private prototype deployment. Deploy the REST API and MCP server as separate Container Apps built from the same repository image:

- `api.containerapp.yaml` starts `python app.py` on port `5000`.
- `mcp-sse.containerapp.yaml` starts `python mcp_sse_server.py` on port `3000`.

The manifests use **internal ingress** by default. The current evaluation routes and MCP server do not enforce user authentication, so do not expose either app directly to the public internet or send real patient data. Add a reviewed authentication/authorization layer and explicit CORS policy before considering external ingress.

The replicas are intentionally fixed at one. The REST rate limiter/statistics and MCP SSE sessions are process-local; scaling out could make their behavior inconsistent or lose session affinity. Move this state to suitable shared infrastructure and test session routing before increasing replica counts.

## Prerequisites

- An Azure subscription and permission to create Container Apps resources.
- Azure CLI with the `containerapp` extension.
- An existing Container Apps environment.
- A container image accessible to that environment (for example, in Azure Container Registry with managed-identity `AcrPull` access).

Build the image from the repository root with your registry:

```powershell
az acr build --registry <registry-name> --image ocuguard:prototype --file Dockerfile .
```

In both YAML files, replace `REPLACE_WITH_PULLABLE_IMAGE` with the full image reference, such as `<registry-name>.azurecr.io/ocuguard:prototype`. Configure the Container App to pull from a private registry using managed identity; do not enable registry admin credentials or commit credentials to these manifests.

Create each app in the existing environment:

```powershell
az containerapp create `
  --name ocuguard-api `
  --resource-group <resource-group> `
  --environment <container-apps-environment> `
  --yaml deploy/azure/api.containerapp.yaml
```

```powershell
az containerapp create `
  --name ocuguard-mcp `
  --resource-group <resource-group> `
  --environment <container-apps-environment> `
  --yaml deploy/azure/mcp-sse.containerapp.yaml
```

The app must be able to pull the image at creation time. Configure its registry identity and `AcrPull` role assignment before deployment. Keep `OPENAI_API_KEY` out of YAML and source control; if cloud-backed agent paths are used, add the key as a Container Apps secret and reference it as an environment variable.

## MCP transport limitation

`mcp_sse_server.py` currently uses the legacy SSE transport. ACA's HTTP ingress has a documented 240-second request timeout, while an SSE connection can remain open longer. Test the intended client’s reconnect/session behavior; for a production MCP endpoint, migrate to Streamable HTTP and validate sessions, authentication, and CORS before enabling external ingress. ACA documentation recommends at least one replica for interactive MCP use.

## Before public or patient-facing use

This deployment template is for private technical evaluation with synthetic data only. Azure hosting does not make the application clinically validated, privacy-compliant, or legally cleared. Before any external or patient-facing deployment, address authentication, access control, consent, data minimization, secret management, observability/redaction, threat modeling, accessibility testing, and clinical/regulatory review.

References:

- [Azure Container Apps ingress](https://learn.microsoft.com/azure/container-apps/ingress-overview)
- [Host MCP servers on Azure Container Apps](https://learn.microsoft.com/azure/container-apps/mcp-overview)
