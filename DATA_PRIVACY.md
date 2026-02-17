# Data Privacy

## Overview

This document explains how Mindwell AI handles user data, what is collected, how it's protected, and users' rights.

## What Data We Collect

### User Account Data
- **Email address**: For authentication
- **Pseudonymized user ID**: Generated automatically
- **Account status**: Active/inactive, role (user/admin)
- **Creation timestamp**: When account was created

### Conversation Data
- **Messages**: User questions and assistant responses (with PII redacted)
- **Conversation metadata**: Timestamps, conversation IDs
- **Safety check results**: Outcome, violation type (if any), reason
- **Citations**: Which documents were used to generate responses

### Document Data (Admin Only)
- **Uploaded files**: CBT documents (markdown, PDF, text)
- **Metadata**: Title, source type, upload timestamp

### System Data
- **Logs**: Application logs with PII redacted
- **Metrics**: Usage statistics, error rates (aggregated)

## What Data We DON'T Collect

- ❌ Real names (unless voluntarily provided in messages)
- ❌ Passwords (development MVP uses passwordless auth)
- ❌ Payment information (no payment system in MVP)
- ❌ Location data (no GPS, IP geolocation)
- ❌ Biometric data
- ❌ Social media accounts
- ❌ Third-party tracking cookies

## How We Protect Your Data

### Pseudonymization

**What It Is**: Replacing identifiable information with pseudonyms.

**How We Do It**:
- User accounts are assigned pseudonymous IDs from creation
- Display names are pseudonyms (e.g., "user_a3f2b9")
- Email addresses are stored but never exposed in logs or responses

**Why**: Even if data is leaked, it cannot be directly linked to individuals without the mapping (which is separately secured).

### PII Redaction

**Automatic Detection**: Our system scans for and redacts:
- Email addresses → `[EMAIL]`
- Phone numbers → `[PHONE]`
- Social Security Numbers → `[SSN]`
- Credit card numbers → `[CREDIT_CARD]`

**Where We Redact**:
1. **Before Storage**: Messages are redacted before saving to database
2. **In Logs**: All logs automatically redact PII
3. **In Errors**: Error messages never contain user data

**Limitations**: Pattern-based detection may not catch all PII variants. Users should avoid sharing sensitive personal information.

### Data Minimization

**Principle**: Collect only what's necessary.

**What We Do**:
- Don't require real names
- Don't track browsing behavior
- Don't link to external profiles
- Delete data when no longer needed (when implemented)

### Access Controls

**Who Can Access What**:
- **Users**: Only their own conversations
- **Admins**: Document management, system metrics (not user messages)
- **Developers**: Pseudonymized logs only (with redaction)

**Authentication**:
- JWT tokens with expiration
- Role-based access control (RBAC)
- Secure token storage recommended (not in localStorage)

### Encryption

**In Transit**:
- HTTPS/TLS required in production
- API requests encrypted

**At Rest**:
- Database should use encryption (managed service recommendation)
- Backups should be encrypted

## How We Use Your Data

### Primary Uses

1. **Provide Service**: Generate responses to your questions
2. **Safety**: Detect crisis situations and policy violations
3. **Improve System**: Evaluate and improve response quality
4. **Troubleshooting**: Debug issues and errors

### What We DON'T Do

- ❌ Sell your data
- ❌ Share with third parties (except LLM provider for generation)
- ❌ Use for advertising
- ❌ Train models on your conversations (unless explicitly opted in)

### Third-Party Services

**LLM Provider** (OpenAI or compatible):
- Receives message content for generation
- Subject to their privacy policy
- Data not used for their model training (configurable)

**Recommendation**: Use OpenAI's "zero retention" policy for sensitive applications.

## Your Rights

### Right to Access

You can request:
- All data we have about you
- How it's been used
- Who it's been shared with (if anyone)

### Right to Correction

You can request corrections to:
- Account information
- Misrepresented data

### Right to Deletion

You can request deletion of:
- Your account
- All associated conversations
- Any uploaded content

**Note**: We may retain some data for legal compliance or safety investigations.

### Right to Portability

You can request:
- Export of your conversations
- Machine-readable format (JSON)

### Right to Object

You can object to:
- Specific data processing activities
- Automated decision-making (if implemented)

### How to Exercise Rights

Email privacy@[domain].com with:
- Your email or pseudonymous user ID
- Specific request
- Verification of identity

We will respond within 30 days.

## Data Retention

### Active Accounts

**Kept indefinitely** (while account is active):
- Account information
- Recent conversations (configurable retention period)

### Inactive Accounts

**After 1 year of inactivity**:
- Account marked inactive
- Optionally: Conversations archived or deleted

### Deleted Accounts

**Within 30 days of deletion request**:
- All user data deleted
- Backups purged within 90 days
- Aggregated/anonymized stats may remain

### Logs

**Retention**:
- Application logs: 90 days
- Security logs: 1 year
- Audit logs: 7 years (if required by regulation)

## Special Categories of Data

### Mental Health Information

⚠️ **Conversations may contain sensitive health information.**

**Extra Protections**:
- All conversations pseudonymized
- PII redacted automatically
- Safety checks to prevent harm
- Secure storage with access controls

**Recommendation**: Avoid sharing:
- Identifying details (names, addresses, etc.)
- Medical record numbers
- Insurance information

### Children's Data

🚫 **This service is NOT intended for children under 13.**

We do not knowingly collect data from children. If we discover we have, we will delete it immediately.

## International Data Transfers

**Current Deployment**: Single region (specify region)

**If Data Crosses Borders**:
- We use standard contractual clauses (SCCs)
- Ensure adequate protection in destination country
- Notify users of transfer

## Data Breach Notification

**If a Breach Occurs**:

1. **Immediate**: Contain and investigate
2. **Within 72 hours**: Notify supervisory authority (if required)
3. **Without undue delay**: Notify affected users
4. **Ongoing**: Provide updates and remediation

**What We'll Tell You**:
- What happened
- What data was affected
- What we're doing about it
- What you should do (e.g., change password)

## Cookies and Tracking

**Current Implementation**:
- No cookies (API-only)
- No tracking scripts
- No analytics (MVP)

**If Added Later**:
- We will update this policy
- Request consent where required
- Provide opt-out mechanism

## Changes to This Policy

We may update this policy to reflect:
- Changes in our practices
- Legal requirements
- User feedback

**We Will**:
- Update "Last Modified" date
- Notify users of material changes
- Seek consent for significant new uses

**You Should**:
- Review periodically
- Contact us with questions

## Contact Us

**Privacy Questions**: privacy@[domain].com
**Security Issues**: security@[domain].com
**General Support**: support@[domain].com

## Regulatory Compliance

### GDPR (EU)

**If Serving EU Users**:
- Legal basis: Consent / Legitimate Interest
- Data Controller: [Organization Name]
- DPO (if required): [Contact]
- Supervisory Authority: [Relevant authority]

### CCPA (California)

**If Serving California Residents**:
- Right to know what's collected
- Right to delete
- Right to opt-out of sales (N/A - we don't sell)
- Non-discrimination for exercising rights

### HIPAA (US Healthcare)

⚠️ **This system is NOT HIPAA-compliant** in its current state.

For HIPAA compliance, additional safeguards are required:
- Business Associate Agreements (BAAs)
- Enhanced encryption and access controls
- Audit trails
- Breach notification procedures
- Regular risk assessments

**Recommendation**: Do not use for Protected Health Information (PHI) without HIPAA compliance.

## Age Restrictions

**Minimum Age**: 13 years (or higher based on jurisdiction)

**Parental Consent**: Required for users under 18 (in some jurisdictions)

## Transparency

We believe in transparency about data practices:

✅ This policy is publicly available
✅ We document what we collect and why
✅ We explain how protection works
✅ We're honest about limitations

## Best Practices for Users

**To Protect Your Privacy**:

1. **Don't share unnecessary personal information**
   - Avoid full names, addresses, phone numbers
   - Use pseudonyms if discussing others

2. **Be cautious with sensitive details**
   - Medical record numbers
   - Insurance information
   - Financial details

3. **Log out on shared devices**

4. **Use strong, unique passwords** (when password auth is enabled)

5. **Review your data periodically**
   - Request export to see what's stored
   - Delete conversations you don't need

## Limitations and Disclaimers

**This Service**:
- Is NOT a substitute for professional mental health care
- Is NOT a medical device
- Does NOT diagnose or treat conditions
- May make errors

**Your Responsibility**:
- Verify important information
- Seek professional help for serious concerns
- Don't rely solely on this system for health decisions

## Acknowledgments

This policy is inspired by:
- GDPR principles
- CCPA requirements
- Privacy by Design framework
- Best practices from leading tech companies

---

**Last Modified**: 2026-02-17

**Version**: 1.0

If you have questions or concerns about this privacy policy, please contact us at privacy@[domain].com.
