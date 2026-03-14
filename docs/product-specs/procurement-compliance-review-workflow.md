# Procurement Compliance Review Workflow

## Objective

Review procurement requirement text for common compliance risks while preserving the purchaser's legitimate business need.

## Review standard

The agent should optimize for:
- fairness
- non-discrimination
- relation to actual contract performance
- measurable and reviewable requirements
- traceable reasoning
- controlled escalation when legal certainty is not possible

## Primary review dimensions

### 1. Supplier qualification compliance

Check whether qualification conditions are directly related to contract performance. Flag when conditions look likely to:
- exclude otherwise capable suppliers without clear necessity
- require unnecessary certifications, location, awards, or historical projects
- impose ownership, scale, or staffing thresholds unrelated to delivery

### 2. Technical requirement neutrality

Check whether technical parameters are functional and performance-based rather than supplier-targeted. Flag when text appears to:
- name a brand, model, or proprietary feature without justified equivalence language
- use overly narrow ranges that appear to fit only one product
- bundle unnecessary features that collapse competition

### 3. Scoring rule relevance

Check whether scoring criteria are proportionate and linked to procurement objectives. Flag when scoring appears to:
- reward non-essential certifications or honors
- overweight experience thresholds beyond reasonable performance assurance
- turn qualification gates into repeated score advantages

### 4. Commercial and acceptance clause clarity

Check whether business clauses are clear, executable, and fair. Flag when terms are:
- vague
- impossible to verify
- one-sided without business justification
- missing objective acceptance criteria

## Output contract

Each review should produce a structured result with:
- `document_name`
- `review_scope`
- `findings`
- `overall_risk_summary`
- `items_for_human_review`

Each finding should contain:
- `clause_id`
- `clause_text`
- `issue_type`
- `risk_level`
- `why_it_is_risky`
- `suggested_revision`
- `confidence`

## Escalation rules

Mark `needs_human_review = true` when:
- the legal basis depends on local or newly updated regulation
- the clause may be justified by safety, secrecy, compatibility, or statutory qualification requirements
- the document excerpt is incomplete
- the text is too ambiguous to support a stable conclusion

## Non-goals

The agent should not:
- give definitive legal advice without jurisdictional basis
- invent regulatory citations it cannot support
- erase legitimate functional needs in the name of neutrality
- convert every unusual parameter into a compliance finding
