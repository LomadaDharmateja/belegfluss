"""One Microsoft Entra credential for every Azure client (ADR-0021): no keys, no passwords.

In Azure Container Apps this is the app's user-assigned Managed Identity (`AZURE_CLIENT_ID` says
which one); on a laptop it is the developer's `az login`.
"""

from functools import cache

from azure.identity import DefaultAzureCredential


@cache
def azure_credential() -> DefaultAzureCredential:
    return DefaultAzureCredential()
