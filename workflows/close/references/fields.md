# Logical close fields

Map these names in private adapters; they are not API field names. Required fields
are policy.close.required_fields. Optional fields may be omitted when not used by
this organization. A missing required destination blocks its proposal.

| Record | Information | Evidence |
|---|---|---|
| Deal | Id, AccountId, StageName, IsClosed, IsWon, Amount, Currency, CloseDate | Current CRM read |
| Agreement | AgreementReference, SignatureDate, ContractStart, ContractEnd | Signed agreement or verified signature-system record |
| Terms | Products, Quantity, BillingInterval, PaymentTerms, Discounts, Taxes | Actual agreement; no template prices or formulas |
| Notes | WinNotes, UseCases, NextSteps | Sourced buyer statements and approved onboarding action |
| Account/contact | Verified identity, addresses, roles and configured billing contact | Identity evidence plus current record; role labels from the actual provider |
| Downstream | Item ID, owner, state, error, completion evidence | Configured operational system or accountable owner's response |

Read current provider field types and validation rules. Keep system identifiers
read-only unless a separately approved linkage uses a verified system result.
