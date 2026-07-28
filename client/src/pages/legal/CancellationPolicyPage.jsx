import LegalDocumentPage from './LegalDocumentPage.jsx';
import { getCurrentCancellationPolicy } from '../../api/endpoints/legal.js';

export default function CancellationPolicyPage() {
  return (
    <LegalDocumentPage
      eyebrow="Legal"
      title="Cancellation & Refund Policy"
      queryKey={['legal', 'cancellation-policy']}
      queryFn={getCurrentCancellationPolicy}
    />
  );
}
