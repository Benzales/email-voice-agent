# Legal Setup Guide
## Voice Email Agent - Privacy Policy & Terms of Service

This guide helps you customize the legal documents for your Voice Email Agent deployment.

---

## 📋 Required Customizations

### Privacy Policy (`PRIVACY_POLICY.md`)

**Replace these placeholders with your actual information:**

```markdown
[DATE] → Current date (e.g., "January 15, 2024")
[CONTACT_EMAIL] → Your support email (e.g., "privacy@yourdomain.com")
[WEBSITE_URL] → Your website URL (e.g., "https://voiceemailagent.com")
[BUSINESS_ADDRESS] → Your business address
[EFFECTIVE_DATE] → When the policy takes effect
[LAST_UPDATED_DATE] → Last modification date
```

### Terms of Service (`TERMS_OF_SERVICE.md`)

**Replace these placeholders:**

```markdown
[DATE] → Current date
[JURISDICTION] → Your legal jurisdiction (e.g., "California, USA")
[CONTACT_EMAIL] → Your support email
[WEBSITE_URL] → Your website URL
[BUSINESS_ADDRESS] → Your business address
[LAST_UPDATED_DATE] → Last modification date
```

---

## 🌍 Jurisdiction Considerations

### United States
- **CCPA Compliance:** California Consumer Privacy Act requirements included
- **Federal Laws:** Complies with CAN-SPAM, COPPA, and other federal regulations
- **State Laws:** Consider additional state privacy laws

### European Union
- **GDPR Compliance:** General Data Protection Regulation requirements included
- **Data Processing:** Lawful basis and user rights clearly defined
- **Data Transfers:** International transfer safeguards mentioned

### Other Jurisdictions
- **Local Laws:** Consult local legal counsel for jurisdiction-specific requirements
- **Data Localization:** Consider data residency requirements
- **Privacy Regulations:** Adapt to local privacy law requirements

---

## 🔗 Integration with Your App

### Frontend Integration

**Add legal links to your app:**

```typescript
// In your footer or settings page
<div className="legal-links">
  <a href="/privacy-policy">Privacy Policy</a>
  <a href="/terms-of-service">Terms of Service</a>
</div>
```

### OAuth Consent Screen

**Update your Google OAuth consent screen:**

1. **Privacy Policy URL:** Add your hosted privacy policy URL
2. **Terms of Service URL:** Add your hosted terms of service URL
3. **App Description:** Clearly describe data usage

### Backend Implementation

**Add legal endpoints to your FastAPI server:**

```python
@app.get("/privacy-policy", response_class=HTMLResponse)
async def privacy_policy():
    # Serve your privacy policy
    return render_template("privacy_policy.html")

@app.get("/terms-of-service", response_class=HTMLResponse)
async def terms_of_service():
    # Serve your terms of service
    return render_template("terms_of_service.html")
```

---

## ⚖️ Legal Review Checklist

### Before Deployment

- [ ] **Customize all placeholder values** with your actual information
- [ ] **Review jurisdiction-specific requirements** for your location
- [ ] **Consult legal counsel** if handling sensitive data or operating commercially
- [ ] **Update Google OAuth consent screen** with policy URLs
- [ ] **Test legal page accessibility** from your application

### Data Handling Compliance

- [ ] **Gmail API compliance** with Google's user data policies
- [ ] **Voice data processing** clearly explained to users
- [ ] **Data retention periods** align with your actual implementation
- [ ] **User rights procedures** are implementable in your system
- [ ] **Security measures** match your actual implementation

### Ongoing Maintenance

- [ ] **Review policies annually** or when features change
- [ ] **Update modification dates** when making changes
- [ ] **Notify users** of material policy changes
- [ ] **Maintain legal compliance** as regulations evolve

---

## 🚨 Important Disclaimers

### Legal Counsel Recommendation
These templates provide a starting point but **are not legal advice**. For commercial deployment or sensitive use cases, consult with qualified legal counsel familiar with:
- Privacy law in your jurisdiction
- Google API Terms of Service
- Industry-specific regulations

### Google API Compliance
Ensure your actual data handling practices match what's described in these policies. Google regularly audits OAuth applications for compliance with their user data policies.

### User Communication
- **Clear Communication:** Ensure users understand what data you collect and how it's used
- **Consent Mechanisms:** Implement proper consent flows for data processing
- **User Rights:** Provide mechanisms for users to exercise their privacy rights

---

## 📞 Support Implementation

### Privacy Requests
Implement processes to handle:
- Data access requests
- Data deletion requests
- Data correction requests
- Privacy complaints

### Contact Methods
Ensure you can respond to privacy inquiries within required timeframes (typically 30 days).

---

*This legal setup guide is for informational purposes only and does not constitute legal advice. Consult qualified legal counsel for your specific situation.*
