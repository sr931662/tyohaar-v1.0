import LegalDocumentPage from './LegalDocumentPage.jsx';
import { getCurrentTerms } from '../../api/endpoints/legal.js';

export default function TermsPage() {
  return (
    <LegalDocumentPage
      eyebrow="Legal"
      title="Terms & Conditions"
      queryKey={['legal', 'terms']}
      queryFn={getCurrentTerms}
    />
  );
}
