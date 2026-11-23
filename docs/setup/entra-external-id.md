# Setup: Azure account, budget alert and sign-in tenant (Entra External ID)

> **For:** the project owner, once, at M1 Phase B. **Time:** about 30–45 minutes (tenant creation itself can take
> up to 30 minutes in the background).
> **Cost:** €0 in M1. Sign-in is free for the first 50,000 monthly active users, and the Azure account has no
> monthly fee (you pay only for resources you create).
> **Security:** you enter your own login, phone and card details. Nobody else does. **You never create a client
> secret**, because the web app and the API don't need one. Everything you send back at the end is a public ID.

Microsoft renames menu items from time to time. If a label below differs, follow the linked official page for that
step.

## Step 1: Create the Azure account

1. Open the official sign-up page: <https://azure.microsoft.com/free/>.
2. Sign in with your Microsoft account, or create one, and complete phone and card verification. The card is for
   identity verification.
3. At the end you have an **Azure subscription** (pay-as-you-go). Nothing is created or charged yet.

**Already signed in to Azure, but no subscription?** In the portal open **Subscriptions** → **Add** and choose
**Pay-as-you-go**.

**Don't use "Azure for Students" for Belegfluss**, even if you are eligible:
- Microsoft limits these subscriptions to a few allowed regions by policy, and Europe is "usually restricted"
  ([Microsoft staff answer, Tech Community, 2025](https://techcommunity.microsoft.com/discussions/microsoft-learn-for-educators/azure-for-students---locations-now-restricted-by-policy/4442469)).
  Belegfluss must run in the EU.
- The offer is meant for education, non-commercial research, or building software for those purposes
  ([Azure for Students FAQ](https://azure.microsoft.com/en-us/free/students/)). From M5, Belegfluss serves real
  businesses.
- Cost Management lists the offer (MS-AZR-0170P) as **not supported**, so the budget alert in Step 2 may not work
  ([Microsoft Learn](https://learn.microsoft.com/en-us/azure/cost-management-billing/costs/understand-cost-mgt-data)).
- The subscription is disabled when the $100 credit or the 12 months run out
  ([offer terms](https://azure.microsoft.com/en-us/pricing/offers/ms-azr-0170p/)).

## Step 2: Create a budget alert (free)

So that you get an email before anything costs real money.

1. In the Azure portal open **Cost Management + Billing** → **Budgets** → **Add**.
2. Scope: your subscription. Amount: e.g. **€10 per month**. Reset period: monthly.
3. Alert conditions: **Actual 50 %**, **Actual 100 %**, **Forecasted 100 %**. Send to your email address.
4. Official guide: <https://learn.microsoft.com/en-us/azure/cost-management-billing/costs/tutorial-acm-create-budgets>

## Step 3: Create the external tenant (Belegfluss's user directory)

1. Open the Microsoft Entra admin center: <https://entra.microsoft.com>.
2. **Entra ID** → **Overview** → **Manage tenants** → **Create** → choose **External** → **Continue**.
3. Choose **Use Azure Subscription** (not the trial).
4. **Basics** tab:
   - **Tenant Name**: `Belegfluss Dev`
   - **Domain Name**: e.g. `belegflussdev`. This becomes `belegflussdev.onmicrosoft.com`, and the part before the
     dot is the **tenant subdomain**.
   - **Country/Region**: **Germany**. This **cannot be changed later**.
5. **Add a subscription** tab: your subscription; resource group **Create new** → `rg-belegfluss-identity`.
6. **Review + Create** → **Create**. Creation can take up to 30 minutes; watch the **Notifications** pane.
7. Switch to the new tenant: **Settings** (gear icon) → **Directories + subscriptions** → **Switch**.
8. Open the tenant **Overview** and note the **Tenant ID** and **Primary domain**. If a **data location** or
   "Country or region" field is shown anywhere in the overview or properties, note it too.
9. Official guide: <https://learn.microsoft.com/en-us/entra/external-id/customers/how-to-create-external-tenant-portal>

## Step 4: Register the API (the backend)

1. In the new tenant: **Entra ID** → **App registrations** → **New registration**.
   - Name: `belegfluss-api`
   - Supported account types: **Accounts in this organizational directory only**
   - No redirect URI → **Register**
2. Note the **Application (client) ID**. This is the **API client ID**.
3. **Expose an API** → next to **Application ID URI** select **Add**, keep the default `api://<API client ID>` →
   **Save**.
4. **Add a scope**:
   - Scope name: `access_as_user`
   - Who can consent: **Admins only**
   - Admin consent display name: `Access Belegfluss`
   - Admin consent description: `Allows the Belegfluss web app to call the Belegfluss API for the signed-in user.`
   - State: **Enabled** → **Add scope**
5. **Manifest** (in the app's menu): in the `api` section, set `"requestedAccessTokenVersion": 2` → **Save**.
   This makes the API receive version-2 tokens. If the value is already `2`, leave it.
6. Official guides: <https://learn.microsoft.com/en-us/entra/identity-platform/quickstart-configure-app-expose-web-apis>
   and <https://learn.microsoft.com/en-us/entra/identity-platform/reference-microsoft-graph-app-manifest>

## Step 5: Register the web app (single-page application)

1. **App registrations** → **New registration**.
   - Name: `belegfluss-web`
   - Supported account types: **Accounts in this organizational directory only**
   - Redirect URI: platform **Single-page application**, value `http://localhost:3000` → **Register**
2. Note the **Application (client) ID**. This is the **SPA client ID**.
3. **Do not** create a client secret or certificate, and leave "implicit grant" options unchecked. The app uses the
   authorization-code flow with PKCE.
4. **API permissions** → **Add a permission** → **APIs my organization uses** (or **My APIs**) → `belegfluss-api` →
   **Delegated permissions** → tick `access_as_user` → **Add permissions**.
5. Select **Grant admin consent for Belegfluss Dev** → **Yes**. In external tenants, customers can't consent
   themselves, so the admin grants it once for everyone.
6. Official guide: <https://learn.microsoft.com/en-us/entra/external-id/customers/tutorial-single-page-app-react-sign-in-prepare-tenant>

## Step 6: Sign-in with an email one-time code

1. Check that the email one-time passcode is enabled for the tenant: **External Identities** → **All identity
   providers** → **Email one-time passcode** → enabled.
2. **External Identities** → **User flows** → **New user flow**.
   - Name: `SignUpSignIn`
   - Identity providers: tick **Email Accounts** → choose **Email one-time passcode**
   - User attributes: **Display Name** only. Don't collect more personal data than needed.
   - **Create**
3. Open the new user flow → **Applications** → **Add application** → select `belegfluss-web` → **Select**.
4. Official guides: <https://learn.microsoft.com/en-us/entra/external-id/customers/how-to-user-flow-sign-up-sign-in-customers>
   and <https://learn.microsoft.com/en-us/entra/external-id/customers/how-to-user-flow-add-application>

## Step 7: Send these values back (all public, no secrets)

| Value | Example | Where |
|---|---|---|
| Tenant subdomain | `belegflussdev` | Step 3 (domain before `.onmicrosoft.com`) |
| Tenant ID | `00000000-0000-…` | Step 3 overview |
| API client ID | `11111111-…` | Step 4 |
| SPA client ID | `22222222-…` | Step 5 |
| Country/Region and data location (if shown) | Germany / Europe | Step 3 |

Plus a screenshot or a short confirmation that the **budget alert** exists (Step 2).

With these values the app is configured in `.env` (git-ignored). The project then checks a real sign-in token
against the API's validation rules and records the tenant's data location. That closes the condition in
[ADR-0003](../decisions/0003-auth-entra-external-id.md).
