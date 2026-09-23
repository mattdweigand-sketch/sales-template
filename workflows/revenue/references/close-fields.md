# Fields read and checked at close

Logical fields: map them to the deployment schema and read all applicable fields in step 2. Unsupported fields are explicit gaps. Do not issue these names as native API fields without a verified mapping. Sources: A = signed agreement, R = existing record, S = system (provisioning, billing or signature integration). A field with source S is never typed by hand.

## Opportunity terms (preflight, step 5)

| Field | Source | Expected |
|---|---|---|
| `Type` | A | New Business, Existing Business, or Renewal |
| `DealType` | A | Annual Contract, Paid Trial, Month to Month - self-serve billing, Annual Credit Card - self-serve billing |
| `CustomerType` | A | the signed product/customer type; an unsupported flow stops the run |
| `SubscriptionType` | A | Paid |
| `SubscriptionBillingInterval` | A | `policy.close.terms_default.billing_interval` unless Deal Desk approved another |
| `BillingTerms` | A | `policy.close.terms_default.billing_terms` unless the agreement says otherwise |
| `ContractTerm` | A | months. Pilot = pilot length |
| `SubscriptionStartDate`, `SubscriptionCancelDate` | A | contract start and end. Never reset after signature |
| `TrialEndDate` | A | pilot end, Paid Trial only |
| `AdminEmail`, `AdminInviteTier` | A | the named admin and signed tier |
| `Pricebook2Id` | R | per `policy.close.price_books` for the path |
| `Amount`, `TotalContractValue`, `CreditsPurchased` | R | formulas from line items. Report a pilot's actual charge beside the annualized Amount |
| `ContractStatus` | A | Signed |
| `PurchaseOrderNumber`, `SpecialTerms` | A | when the agreement carries them |
| `LeadSource` | R | required only when the configured validation rules require it; missing evidence blocks that move |

## Setup trial (proposal A0)

`SetupTrialRequested` (only if a configured flow uses a trigger; verify its native reset semantics), `SubscriptionType`, `SubscriptionBillingInterval`, `SubscriptionStartDate`, `SubscriptionDeactivationDate`, `TrialEndDate`, `AdminEmail`, `AdminInviteTier`. Written in one update per `policy.close.setup_trial.payload`. Read-only results: `ProvisioningSyncTime`, `ProvisioningError`, `OrgSubscriptionId`, `Account.AdminOrgId`.

## Line items (step 5)

`SELECT Product2.Name, Quantity, UnitPrice, ListPrice, Discount, TotalPrice FROM OpportunityLineItem WHERE OpportunityId = '<Id>'`. Required when the configured CRM or billing flow requires line items. Check seats and credits equal the agreement. Credits per `policy.close.credits`: map purchased units and price from the signed terms and configured price book; do not assume another product's cent-based pricing. Bonus credits use the configured bonus product.

## Win fields (proposal B)

`ClosedWonNotes` (why we won), `UseCases` (what they will do), `NextSteps` (onboarding Next line), `ClosedWonFollowUpDate`.

## Account (proposal C)

`BillingEmail`, `BillingPointOfContact` (Contact), `OrgId`, `AdminOrgId`, `BecameACustomerOn`, `CustomerType`, `CustomerStatus`, `ParentId`, `PrimaryOrganization`.

## Signature (step 3)

`ContractSigned`, `AgreementSigned`, `SignatureDate`, `SignedContractUrl`, `ContractStatus`.

## Downstream status (step 8)

| Item | Field | verified when |
|---|---|---|
| billing subscription | `BillingSyncStatus`, `BillingSubscriptionId`, `BillingError`, `BillingSyncBypass` | SUCCESS with an ID. FAILED = blocked, quote the message |
| Admin org subscription | `OrgSubscriptionId`, `ProvisioningError`, `ProvisioningSyncTime`, `SubscriptionSyncRequested` | ID present. Error text = blocked |
| Org linked to Account | `Account.AdminOrgId`, `Account.OrgId` | both set and equal, or ops confirms the intended linkage |
| self-serve billing cancelled (self-serve path) | none | ops owner reply in the handoff thread |
| Invoice issued | none | ops owner reply or billing evidence the user supplies |
