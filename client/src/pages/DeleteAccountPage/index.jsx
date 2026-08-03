import { useState } from 'react';
import Navbar from '../../components/layout/Navbar.jsx';
import Footer from '../../components/layout/Footer.jsx';
import styles from './DeleteAccountPage.module.css';

const SUPPORT_EMAIL = 'goyalkarn@gmail.com';
const SUPPORT_PHONE = '+91 8860384909';

const REASONS = [
  'I no longer use Tyohaar',
  'I have privacy concerns',
  'I created a duplicate account',
  'I had a bad experience',
  'Other',
];

const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
// Indian mobile numbers, with or without the +91 country code and common
// separators — kept deliberately loose so a valid request is never blocked
// by formatting.
const PHONE_PATTERN = /^(\+?91[-\s]?)?[6-9]\d{9}$/;

function validate({ name, email, phone, confirmed }) {
  const errors = {};

  if (!name.trim()) {
    errors.name = 'Please enter your name.';
  }

  const cleanedPhone = phone.replace(/[-\s]/g, '');
  if (!email.trim() && !cleanedPhone) {
    errors.email = 'Enter the email address or phone number registered with your account.';
  } else {
    if (email.trim() && !EMAIL_PATTERN.test(email.trim())) {
      errors.email = 'Please enter a valid email address.';
    }
    if (cleanedPhone && !PHONE_PATTERN.test(cleanedPhone)) {
      errors.phone = 'Please enter a valid 10-digit mobile number.';
    }
  }

  if (!confirmed) {
    errors.confirmed = 'Please confirm that you want your account deleted.';
  }

  return errors;
}

export default function DeleteAccountPage() {
  const [form, setForm] = useState({
    name: '',
    email: '',
    phone: '',
    reason: '',
    details: '',
    confirmed: false,
  });
  const [errors, setErrors] = useState({});
  const [submitted, setSubmitted] = useState(false);

  const update = (field) => (event) => {
    const value = event.target.type === 'checkbox' ? event.target.checked : event.target.value;
    setForm((prev) => ({ ...prev, [field]: value }));
    setErrors((prev) => ({ ...prev, [field]: undefined }));
  };

  // There is no public (unauthenticated) deletion endpoint, so the request is
  // sent as an email the customer's own mail client composes — that keeps the
  // request verifiable, since it arrives from their own address.
  const handleSubmit = (event) => {
    event.preventDefault();
    const nextErrors = validate(form);
    setErrors(nextErrors);
    if (Object.keys(nextErrors).length > 0) {
      setSubmitted(false);
      return;
    }

    const body = [
      'I would like my Tyohaar account and associated data deleted.',
      '',
      `Name: ${form.name.trim()}`,
      `Registered email: ${form.email.trim() || '—'}`,
      `Registered phone: ${form.phone.trim() || '—'}`,
      `Reason: ${form.reason || '—'}`,
      '',
      'Additional details:',
      form.details.trim() || '—',
    ].join('\n');

    window.location.href =
      `mailto:${SUPPORT_EMAIL}` +
      `?subject=${encodeURIComponent('Account deletion request — Tyohaar')}` +
      `&body=${encodeURIComponent(body)}`;

    setSubmitted(true);
  };

  return (
    <>
      <Navbar />
      <main id="top" className={styles.pageWrapper}>
        <section className={styles.hero}>
          <h1>Delete your Tyohaar account</h1>
          <p>
            Request permanent deletion of your Tyohaar account and the personal data associated
            with it.
          </p>
        </section>

        <div className={styles.container}>
          <section className={styles.section}>
            <h2>What gets deleted</h2>
            <p>When your deletion request is processed, we remove:</p>
            <ul>
              <li>Your profile — name, email address, phone number and saved addresses</li>
              <li>Your celebrations, plans and guest lists</li>
              <li>Photos and videos you uploaded, and the ones vendors shared with you</li>
              <li>Your saved packages, reviews and support conversations</li>
            </ul>
            <p>
              Records tied to completed bookings — invoices, payment records and tax documents —
              are retained where we are legally required to keep them, as described in our{' '}
              <a href="/privacy">Privacy Policy</a>. These are kept separately from your profile
              and are not used to contact you.
            </p>
            <p>
              Deletion is permanent. Once your account is removed it cannot be restored, and any
              upcoming bookings on it will be cancelled under our{' '}
              <a href="/cancellation-policy">Cancellation Policy</a>.
            </p>
          </section>

          <section className={styles.section}>
            <h2>Request deletion</h2>
            <p>
              Fill in the details below and we will confirm by email once your request has been
              processed. Use the email address or phone number your account is registered with so
              we can identify it.
            </p>

            {submitted && (
              <div className={`${styles.alert} ${styles.alertSuccess}`} role="status">
                Your email app should have opened with the request ready to send — please send it
                to complete your request. If nothing opened, email us directly at{' '}
                <a href={`mailto:${SUPPORT_EMAIL}`}>{SUPPORT_EMAIL}</a>.
              </div>
            )}

            {Object.keys(errors).length > 0 && (
              <div className={`${styles.alert} ${styles.alertError}`} role="alert">
                Please correct the highlighted fields and try again.
              </div>
            )}

            <form onSubmit={handleSubmit} noValidate>
              <div className={styles.formGroup}>
                <label htmlFor="name">Full name</label>
                <input
                  id="name"
                  type="text"
                  value={form.name}
                  onChange={update('name')}
                  autoComplete="name"
                />
                {errors.name && <p className={styles.errorText}>{errors.name}</p>}
              </div>

              <div className={styles.formGroup}>
                <label htmlFor="email">Registered email address</label>
                <input
                  id="email"
                  type="email"
                  value={form.email}
                  onChange={update('email')}
                  autoComplete="email"
                />
                {errors.email && <p className={styles.errorText}>{errors.email}</p>}
              </div>

              <div className={styles.formGroup}>
                <label htmlFor="phone">Registered phone number</label>
                <input
                  id="phone"
                  type="tel"
                  value={form.phone}
                  onChange={update('phone')}
                  autoComplete="tel"
                />
                {errors.phone && <p className={styles.errorText}>{errors.phone}</p>}
              </div>

              <div className={styles.formGroup}>
                <label htmlFor="reason">Reason (optional)</label>
                <select id="reason" value={form.reason} onChange={update('reason')}>
                  <option value="">Prefer not to say</option>
                  {REASONS.map((reason) => (
                    <option key={reason} value={reason}>
                      {reason}
                    </option>
                  ))}
                </select>
              </div>

              <div className={styles.formGroup}>
                <label htmlFor="details">Anything else we should know? (optional)</label>
                <textarea id="details" rows={4} value={form.details} onChange={update('details')} />
              </div>

              <div className={styles.checkboxGroup}>
                <input
                  id="confirmed"
                  type="checkbox"
                  checked={form.confirmed}
                  onChange={update('confirmed')}
                />
                <label htmlFor="confirmed">
                  I understand that deleting my account is permanent and cannot be undone.
                </label>
              </div>
              {errors.confirmed && <p className={styles.errorText}>{errors.confirmed}</p>}

              <button type="submit" className={styles.submitButton}>
                Request account deletion
              </button>
            </form>
          </section>

          <section className={styles.section}>
            <h2>Need help?</h2>
            <p>
              If you would rather talk to someone, or you cannot access the email address on your
              account, reach us at:
            </p>
            <ul>
              <li>
                Email: <a href={`mailto:${SUPPORT_EMAIL}`}>{SUPPORT_EMAIL}</a>
              </li>
              <li>
                Phone: <a href={`tel:${SUPPORT_PHONE.replace(/\s/g, '')}`}>{SUPPORT_PHONE}</a>
              </li>
            </ul>
          </section>
        </div>
      </main>
      <Footer />
    </>
  );
}
