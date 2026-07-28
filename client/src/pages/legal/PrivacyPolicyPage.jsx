import LegalDocumentPage from './LegalDocumentPage.jsx';
import { getCurrentPrivacy } from '../../api/endpoints/legal.js';

export default function PrivacyPolicyPage() {
  return (
    <LegalDocumentPage
      eyebrow="Legal"
      title="Privacy Policy"
      queryKey={['legal', 'privacy']}
      queryFn={getCurrentPrivacy}
    />
  );
}
