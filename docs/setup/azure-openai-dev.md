# Setup: Azure OpenAI for local AI reading (M2b)

> **For:** the project owner. **Cost:** pay per token only; estimate about €2–4 for all of M2b development
> ([COSTS.md](../COSTS.md)). The €10 budget alert stays on. **Security:** no API key exists: keys are switched off,
> and the worker signs in with your Azure CLI login (Microsoft Entra ID). Only synthetic test documents are sent.

## 1. Install the Azure CLI and sign in (you)

```powershell
winget install --exact --id Microsoft.AzureCLI
```

Close and reopen the terminal, then:

```powershell
az login        # choose your account; subscription "belegfluss"
az account show --query "{subscription:name, user:user.name}"
```

Source: [Install Azure CLI on Windows](https://learn.microsoft.com/en-us/cli/azure/install-azure-cli-windows).

## 2. Create the resource (Claude runs it, after your explicit yes)

`scripts/azure/dev-openai.ps1` creates, in **Germany West Central**:
1. resource group `rg-belegfluss-ai-dev`
2. Azure OpenAI account (S0) with a custom domain: required for Entra ID sign-in, and it **can't be changed later**
3. **keys switched off** (`disableLocalAuth = true`)
4. deployment `gpt-5-mini` version 2025-08-07, **Data Zone Standard** (processing stays in the EU data zone, pay per
   token), capacity 20: a rate limit of 20,000 tokens per minute (1 unit = 1,000 TPM per the quota guide), not a fixed cost
5. role **Cognitive Services OpenAI User** for you, on this resource only

Before your yes, Claude checks read-only that gpt-5-mini is offered as Data Zone Standard in Germany West Central and
that your subscription has quota for it. The script reads `disableLocalAuth` back and stops if keys are still on. It
doesn't pass `--yes`: if Azure asks to accept terms, you decide and run that step yourself.

```powershell
./scripts/azure/dev-openai.ps1 -Name belegfluss-dev-<4 random letters>
```

It prints the endpoint at the end. Put it into `.env` (not a secret):
`BELEGFLUSS_OPENAI_ENDPOINT=https://belegfluss-dev-xxxx.openai.azure.com/`

Afterwards Claude checks, read-only: the deployment exists, the role is assigned, `disableLocalAuth` is `true`, and
the cost view shows no base fee.

Sources: [az cognitiveservices account](https://learn.microsoft.com/en-us/cli/azure/cognitiveservices/account?view=azure-cli-latest),
[deployment](https://learn.microsoft.com/en-us/cli/azure/cognitiveservices/account/deployment?view=azure-cli-latest),
[deployment types](https://learn.microsoft.com/en-us/azure/foundry/foundry-models/concepts/deployment-types),
[disable local authentication](https://learn.microsoft.com/en-us/azure/ai-services/disable-local-auth),
[custom subdomains](https://learn.microsoft.com/en-us/azure/ai-services/cognitive-services-custom-subdomains),
[az resource update](https://learn.microsoft.com/en-us/cli/azure/resource?view=azure-cli-latest#az-resource-update),
[quota and capacity](https://learn.microsoft.com/en-us/azure/foundry/openai/how-to/automate-quota-deployments),
[role assignment example](https://learn.microsoft.com/en-us/azure/app-service/tutorial-ai-openai-chatbot-python).

## 3. Run Belegfluss with AI reading

```powershell
docker compose -f compose.yaml -f compose.ai.yaml up --build --detach   # no container worker; validator on 127.0.0.1
./scripts/run-ai-worker.ps1                                              # worker on your machine, uses az login
```

Upload a plain PDF or a photo: the worker reads it with gpt-5-mini, checks every field and marks the document
"Please check". Without the override, everything runs as before and plain PDFs get "AI reading is not switched on".

## 4. Remove it again

```powershell
az group delete --name rg-belegfluss-ai-dev
```
