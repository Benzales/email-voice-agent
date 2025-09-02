import { Metadata } from 'next';
import Link from 'next/link';

export const metadata: Metadata = {
  title: 'Privacy Policy - Voice Email Agent',
  description: 'Privacy Policy for Voice Email Agent - Learn how we protect your data and privacy.',
};

export default function PrivacyPolicy() {
  return (
    <div className="min-h-screen bg-gray-50 py-8 px-4">
      <div className="max-w-4xl mx-auto bg-white shadow-lg rounded-lg p-8">
        <div className="prose prose-gray max-w-none">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">Privacy Policy</h1>
          <h2 className="text-xl text-gray-700 mb-6">Voice Email Agent</h2>
          
          <div className="mb-6 p-4 bg-blue-50 border-l-4 border-blue-400">
            <p className="text-sm text-gray-700">
              <strong>Effective Date:</strong> January 15, 2025<br />
              <strong>Last Updated:</strong> January 15, 2025
            </p>
          </div>

          <hr className="my-8" />

          <section className="mb-8">
            <h2 className="text-2xl font-semibold text-gray-900 mb-4">1. Introduction</h2>
                      <p className="text-gray-700 leading-relaxed">
            Voice Email Agent (&quot;we,&quot; &quot;our,&quot; or &quot;us&quot;) is committed to protecting your privacy. This Privacy Policy explains how we collect, use, disclose, and safeguard your information when you use our voice-driven Gmail assistant service (the &quot;Service&quot;).
          </p>
            <p className="text-gray-700 leading-relaxed mt-4">
              By using our Service, you agree to the collection and use of information in accordance with this Privacy Policy.
            </p>
          </section>

          <hr className="my-8" />

          <section className="mb-8">
            <h2 className="text-2xl font-semibold text-gray-900 mb-4">2. Information We Collect</h2>
            
            <h3 className="text-xl font-semibold text-gray-800 mb-3">2.1 Information You Provide Directly</h3>
            
            <div className="mb-4">
              <h4 className="text-lg font-medium text-gray-800 mb-2">OAuth Authentication Data:</h4>
              <ul className="list-disc list-inside text-gray-700 space-y-1">
                <li>Google account email address</li>
                <li>Google account profile information (name, profile picture)</li>
                <li>OAuth access and refresh tokens (encrypted and securely stored)</li>
              </ul>
            </div>

            <div className="mb-6">
              <h4 className="text-lg font-medium text-gray-800 mb-2">Voice Data:</h4>
              <ul className="list-disc list-inside text-gray-700 space-y-1">
                <li>Audio recordings of your voice commands during email processing sessions</li>
                <li>Voice data is processed in real-time and not permanently stored</li>
              </ul>
            </div>

            <h3 className="text-xl font-semibold text-gray-800 mb-3">2.2 Information Collected Automatically</h3>
            
            <div className="mb-4">
              <h4 className="text-lg font-medium text-gray-800 mb-2">Session Data:</h4>
              <ul className="list-disc list-inside text-gray-700 space-y-1">
                <li>Session identifiers for authentication</li>
                <li>Login/logout timestamps</li>
                <li>Service usage statistics (number of emails processed, session duration)</li>
              </ul>
            </div>

            <div className="mb-6">
              <h4 className="text-lg font-medium text-gray-800 mb-2">Technical Data:</h4>
              <ul className="list-disc list-inside text-gray-700 space-y-1">
                <li>IP address (for security and rate limiting)</li>
                <li>Browser type and version</li>
                <li>Device information (for audio compatibility)</li>
                <li>Error logs and debugging information</li>
              </ul>
            </div>

            <h3 className="text-xl font-semibold text-gray-800 mb-3">2.3 Gmail Data Access</h3>
            <p className="text-gray-700 mb-3">Through your explicit OAuth consent, we access:</p>
            <ul className="list-disc list-inside text-gray-700 space-y-1 mb-4">
              <li><strong>Gmail emails</strong> in your inbox (read-only for processing)</li>
              <li><strong>Email metadata</strong> (sender, subject, date, labels)</li>
              <li><strong>Gmail modification permissions</strong> (archive, delete, mark as read/unread)</li>
              <li><strong>Email composition</strong> (for reply functionality)</li>
            </ul>
            
            <div className="p-4 bg-yellow-50 border-l-4 border-yellow-400">
              <p className="text-gray-700">
                <strong>Important:</strong> We only access emails you explicitly choose to process through voice commands.
              </p>
            </div>
          </section>

          <hr className="my-8" />

          <section className="mb-8">
            <h2 className="text-2xl font-semibold text-gray-900 mb-4">3. How We Use Your Information</h2>
            
            <h3 className="text-xl font-semibold text-gray-800 mb-3">3.1 Primary Service Functions</h3>
            <ul className="list-disc list-inside text-gray-700 space-y-1 mb-6">
              <li><strong>Email Processing:</strong> Read and process emails based on your voice commands</li>
              <li><strong>Authentication:</strong> Verify your identity and maintain secure sessions</li>
              <li><strong>Gmail Operations:</strong> Execute email actions (archive, delete, reply) as requested</li>
              <li><strong>Voice Recognition:</strong> Convert your speech to actionable email commands</li>
            </ul>

            <h3 className="text-xl font-semibold text-gray-800 mb-3">3.2 Service Improvement</h3>
            <ul className="list-disc list-inside text-gray-700 space-y-1 mb-6">
              <li><strong>Error Analysis:</strong> Improve voice recognition and email processing accuracy</li>
              <li><strong>Performance Monitoring:</strong> Optimize service speed and reliability</li>
              <li><strong>Security Enhancement:</strong> Detect and prevent unauthorized access</li>
            </ul>

            <h3 className="text-xl font-semibold text-gray-800 mb-3">3.3 Legal and Safety</h3>
            <ul className="list-disc list-inside text-gray-700 space-y-1">
              <li><strong>Compliance:</strong> Meet legal obligations and regulatory requirements</li>
              <li><strong>Security:</strong> Protect against fraud, abuse, and security threats</li>
              <li><strong>Support:</strong> Provide customer support and troubleshooting</li>
            </ul>
          </section>

          <hr className="my-8" />

          <section className="mb-8">
            <h2 className="text-2xl font-semibold text-gray-900 mb-4">4. Data Processing and Storage</h2>
            
            <h3 className="text-xl font-semibold text-gray-800 mb-3">4.1 Voice Data Processing</h3>
            <ul className="list-disc list-inside text-gray-700 space-y-1 mb-6">
              <li><strong>Real-time Processing:</strong> Voice commands are processed immediately through Google's Gemini Live API</li>
              <li><strong>No Permanent Storage:</strong> Voice recordings are not saved or stored after processing</li>
              <li><strong>Secure Transmission:</strong> All voice data is encrypted during transmission</li>
            </ul>

            <h3 className="text-xl font-semibold text-gray-800 mb-3">4.2 Session and Authentication Data</h3>
            <ul className="list-disc list-inside text-gray-700 space-y-1 mb-6">
              <li><strong>Temporary Storage:</strong> Session data stored in memory during active use</li>
              <li><strong>24-Hour Expiry:</strong> Sessions automatically expire after 24 hours</li>
              <li><strong>Encrypted Tokens:</strong> OAuth tokens are encrypted and securely managed</li>
              <li><strong>Automatic Cleanup:</strong> Expired sessions are automatically removed</li>
            </ul>

            <h3 className="text-xl font-semibold text-gray-800 mb-3">4.3 Gmail Data Handling</h3>
            <ul className="list-disc list-inside text-gray-700 space-y-1">
              <li><strong>No Email Storage:</strong> We do not store your email content on our servers</li>
              <li><strong>Real-time Access:</strong> Emails are accessed only during active processing sessions</li>
              <li><strong>User-Controlled:</strong> You control which emails are processed through voice commands</li>
            </ul>
          </section>

          <hr className="my-8" />

          <section className="mb-8">
            <h2 className="text-2xl font-semibold text-gray-900 mb-4">5. Data Sharing and Disclosure</h2>
            
            <h3 className="text-xl font-semibold text-gray-800 mb-3">5.1 Third-Party Services</h3>
            <div className="mb-4">
              <p className="text-gray-700 mb-3"><strong>Google Services:</strong></p>
              <ul className="list-disc list-inside text-gray-700 space-y-1 mb-4">
                <li><strong>Gmail API:</strong> For accessing and managing your emails (with your consent)</li>
                <li><strong>Google OAuth:</strong> For secure authentication</li>
                <li><strong>Gemini Live API:</strong> For voice recognition and AI processing</li>
              </ul>
              
              <div className="p-4 bg-blue-50 border-l-4 border-blue-400">
                <p className="text-gray-700">
                  <strong>Important:</strong> Your data is shared with these services only as necessary to provide the Service and in accordance with their privacy policies.
                </p>
              </div>
            </div>

            <h3 className="text-xl font-semibold text-gray-800 mb-3">5.2 We Do Not Sell Your Data</h3>
            <p className="text-gray-700 mb-6">
              We do not sell, rent, or trade your personal information to third parties for marketing purposes.
            </p>

            <h3 className="text-xl font-semibold text-gray-800 mb-3">5.3 Legal Disclosures</h3>
            <p className="text-gray-700 mb-3">We may disclose your information if required by law or to:</p>
            <ul className="list-disc list-inside text-gray-700 space-y-1">
              <li>Comply with legal processes or government requests</li>
              <li>Protect our rights, property, or safety</li>
              <li>Investigate potential violations of our terms of service</li>
              <li>Protect against legal liability</li>
            </ul>
          </section>

          <hr className="my-8" />

          <section className="mb-8">
            <h2 className="text-2xl font-semibold text-gray-900 mb-4">6. Data Security</h2>
            
            <h3 className="text-xl font-semibold text-gray-800 mb-3">6.1 Security Measures</h3>
            <ul className="list-disc list-inside text-gray-700 space-y-1 mb-6">
              <li><strong>OAuth 2.0 Authentication:</strong> Industry-standard secure authentication</li>
              <li><strong>Encrypted Transmission:</strong> All data transmitted using HTTPS/WSS encryption</li>
              <li><strong>Session Security:</strong> Secure session management with automatic expiration</li>
              <li><strong>Access Controls:</strong> Authentication required for all sensitive operations</li>
            </ul>

            <h3 className="text-xl font-semibold text-gray-800 mb-3">6.2 Security Monitoring</h3>
            <ul className="list-disc list-inside text-gray-700 space-y-1 mb-6">
              <li><strong>Unauthorized Access Prevention:</strong> Real-time monitoring for suspicious activity</li>
              <li><strong>Rate Limiting:</strong> Protection against abuse and automated attacks</li>
              <li><strong>Error Logging:</strong> Secure logging for debugging and security analysis</li>
            </ul>

            <h3 className="text-xl font-semibold text-gray-800 mb-3">6.3 Data Breach Response</h3>
            <p className="text-gray-700 mb-3">In the event of a security incident, we will:</p>
            <ul className="list-disc list-inside text-gray-700 space-y-1">
              <li>Immediately investigate and contain the incident</li>
              <li>Notify affected users within 72 hours</li>
              <li>Provide clear information about what data was affected</li>
              <li>Take steps to prevent future incidents</li>
            </ul>
          </section>

          <hr className="my-8" />

          <section className="mb-8">
            <h2 className="text-2xl font-semibold text-gray-900 mb-4">7. Your Privacy Rights</h2>
            
            <h3 className="text-xl font-semibold text-gray-800 mb-3">7.1 Access and Control</h3>
            <ul className="list-disc list-inside text-gray-700 space-y-1 mb-6">
              <li><strong>Data Access:</strong> Request information about data we have collected about you</li>
              <li><strong>Data Correction:</strong> Request correction of inaccurate personal information</li>
              <li><strong>Data Deletion:</strong> Request deletion of your personal information</li>
              <li><strong>Account Termination:</strong> Delete your account and associated data at any time</li>
            </ul>

            <h3 className="text-xl font-semibold text-gray-800 mb-3">7.2 OAuth Permissions</h3>
            <ul className="list-disc list-inside text-gray-700 space-y-1 mb-6">
              <li><strong>Granular Control:</strong> You control which Gmail permissions you grant</li>
              <li><strong>Revoke Access:</strong> You can revoke OAuth permissions at any time through your Google account</li>
              <li><strong>Selective Processing:</strong> You choose which emails to process with voice commands</li>
            </ul>

            <h3 className="text-xl font-semibold text-gray-800 mb-3">7.3 Communication Preferences</h3>
            <ul className="list-disc list-inside text-gray-700 space-y-1">
              <li><strong>Opt-out:</strong> Unsubscribe from non-essential communications</li>
              <li><strong>Support Contact:</strong> Contact us regarding privacy concerns or requests</li>
            </ul>
          </section>

          <hr className="my-8" />

          <section className="mb-8">
            <h2 className="text-2xl font-semibold text-gray-900 mb-4">8. Data Retention</h2>
            
            <h3 className="text-xl font-semibold text-gray-800 mb-3">8.1 Retention Periods</h3>
            <ul className="list-disc list-inside text-gray-700 space-y-1 mb-6">
              <li><strong>Session Data:</strong> Automatically deleted after 24 hours</li>
              <li><strong>OAuth Tokens:</strong> Retained until you revoke access or delete your account</li>
              <li><strong>Error Logs:</strong> Retained for 30 days for debugging purposes</li>
              <li><strong>Usage Statistics:</strong> Anonymized data may be retained for service improvement</li>
            </ul>

            <h3 className="text-xl font-semibold text-gray-800 mb-3">8.2 Data Deletion</h3>
            <ul className="list-disc list-inside text-gray-700 space-y-1">
              <li><strong>Account Deletion:</strong> All personal data deleted within 30 days of account deletion</li>
              <li><strong>OAuth Revocation:</strong> Associated data deleted when you revoke Gmail permissions</li>
              <li><strong>Automatic Cleanup:</strong> Expired sessions and temporary data automatically removed</li>
            </ul>
          </section>

          <hr className="my-8" />

          <section className="mb-8">
            <h2 className="text-2xl font-semibold text-gray-900 mb-4">9. Children's Privacy</h2>
            <p className="text-gray-700">
              Our Service is not intended for use by children under 13 years of age. We do not knowingly collect personal information from children under 13. If we discover that we have collected information from a child under 13, we will delete that information immediately.
            </p>
          </section>

          <hr className="my-8" />

          <section className="mb-8">
            <h2 className="text-2xl font-semibold text-gray-900 mb-4">10. International Data Transfers</h2>
            <p className="text-gray-700">
              Your information may be transferred to and processed in countries other than your own. We ensure that such transfers comply with applicable data protection laws and implement appropriate safeguards to protect your information.
            </p>
          </section>

          <hr className="my-8" />

          <section className="mb-8">
            <h2 className="text-2xl font-semibold text-gray-900 mb-4">11. California Privacy Rights (CCPA)</h2>
            <p className="text-gray-700 mb-3">
              If you are a California resident, you have additional rights under the California Consumer Privacy Act:
            </p>
            <ul className="list-disc list-inside text-gray-700 space-y-1 mb-4">
              <li><strong>Right to Know:</strong> Request information about personal information collected, used, or shared</li>
              <li><strong>Right to Delete:</strong> Request deletion of personal information</li>
              <li><strong>Right to Opt-Out:</strong> Opt-out of the sale of personal information (we do not sell data)</li>
              <li><strong>Non-Discrimination:</strong> We will not discriminate against you for exercising these rights</li>
            </ul>
            <p className="text-gray-700">
              To exercise these rights, contact us at <a href="mailto:support@voiceemailagent.com" className="text-blue-600 hover:underline">support@voiceemailagent.com</a>.
            </p>
          </section>

          <hr className="my-8" />

          <section className="mb-8">
            <h2 className="text-2xl font-semibold text-gray-900 mb-4">12. European Union Privacy Rights (GDPR)</h2>
            <p className="text-gray-700 mb-3">
              If you are in the European Union, you have rights under the General Data Protection Regulation:
            </p>
            <ul className="list-disc list-inside text-gray-700 space-y-1 mb-4">
              <li><strong>Lawful Basis:</strong> We process data based on consent and legitimate interests</li>
              <li><strong>Data Portability:</strong> Request your data in a portable format</li>
              <li><strong>Right to Rectification:</strong> Correct inaccurate personal data</li>
              <li><strong>Right to Erasure:</strong> Request deletion of personal data</li>
              <li><strong>Right to Restrict Processing:</strong> Limit how we process your data</li>
              <li><strong>Right to Object:</strong> Object to processing based on legitimate interests</li>
            </ul>
            <p className="text-gray-700">
              Contact us at <a href="mailto:support@voiceemailagent.com" className="text-blue-600 hover:underline">support@voiceemailagent.com</a> to exercise these rights.
            </p>
          </section>

          <hr className="my-8" />

          <section className="mb-8">
            <h2 className="text-2xl font-semibold text-gray-900 mb-4">13. Changes to This Privacy Policy</h2>
            <p className="text-gray-700 mb-3">
              We may update this Privacy Policy from time to time. We will notify you of any material changes by:
            </p>
            <ul className="list-disc list-inside text-gray-700 space-y-1 mb-4">
              <li>Posting the new Privacy Policy on our website</li>
              <li>Sending you an email notification (if you have provided an email address)</li>
              <li>Displaying a prominent notice in the application</li>
            </ul>
            <p className="text-gray-700">
              Your continued use of the Service after any changes constitutes acceptance of the new Privacy Policy.
            </p>
          </section>

          <hr className="my-8" />

          <section className="mb-8">
            <h2 className="text-2xl font-semibold text-gray-900 mb-4">14. Contact Information</h2>
            <p className="text-gray-700 mb-4">
              If you have any questions about this Privacy Policy or our privacy practices, please contact us:
            </p>
            <div className="bg-gray-50 p-4 rounded-lg mb-4">
              <p className="text-gray-700">
                <strong>Email:</strong> <a href="mailto:support@voiceemailagent.com" className="text-blue-600 hover:underline">support@voiceemailagent.com</a><br />
                <strong>Website:</strong> <a href="https://courier-black.vercel.app" className="text-blue-600 hover:underline">https://courier-black.vercel.app</a><br />
                <strong>Mailing Address:</strong> Available upon request
              </p>
            </div>
            <p className="text-gray-700 mb-3">
              For privacy-related requests, please include:
            </p>
            <ul className="list-disc list-inside text-gray-700 space-y-1 mb-4">
              <li>Your name and email address</li>
              <li>Specific request or concern</li>
              <li>Any relevant account information</li>
            </ul>
            <p className="text-gray-700">
              We will respond to privacy requests within 30 days.
            </p>
          </section>

          <hr className="my-8" />

          <section className="mb-8">
            <h2 className="text-2xl font-semibold text-gray-900 mb-4">15. Effective Date</h2>
            <p className="text-gray-700 mb-4">
              This Privacy Policy is effective as of January 15, 2025 and will remain in effect except with respect to any changes in its provisions in the future, which will be in effect immediately after being posted on this page.
            </p>
            <hr className="my-4" />
            <p className="text-sm text-gray-500 italic">
              This Privacy Policy was last updated on January 15, 2025.
            </p>
          </section>

          <div className="mt-12 pt-8 border-t border-gray-200">
            <div className="text-center">
              <Link 
                href="/" 
                className="inline-flex items-center px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
              >
                ← Back to Voice Email Agent
              </Link>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
