import { useState } from 'react';
import { motion } from 'framer-motion';
import { AlertTriangle, CheckCircle2, Mail, Phone } from 'lucide-react';
import Navbar from '../../components/layout/Navbar.jsx';
import Footer from '../../components/layout/Footer.jsx';
import SectionHeading from '../../components/ui/SectionHeading.jsx';
import Button from '../../components/ui/Button.jsx';
import { fadeUp, bloom, stagger, inView } from '../../lib/motion';
import styles from './DeleteAccountPage.module.css';

const SUPPORT_EMAIL = 'goyalkarn@gmail.com';
const SUPPORT_PHONE = '+91 8860384909';
const SUPPORT_PHONE_TEL = '+918860384909';

const REASONS = [
  'I no longer use Tyohaar',
  'I have privacy concerns',
  'I created a duplicate account',
  'I had a bad experience',
  'Other',
];

const REMOVED = [
  'Your profile — name, email address, phone number and saved addresses',
  'Your celebrations, plans and guest lists',
  'Photos and videos you uploaded, and the ones vendors shared with you',
  'Your saved packages, reviews and support conversations',
];

const CHANNELS = [
  { icon: Mail, label: 'Email', value: SUPPORT_EMAIL, href: `mailto:${SUPPORT_EMAIL}` },
  { icon: Phone, label: 'Phone', value: SUPPORT_PHONE, href: `tel:${SUPPORT_PHONE_TEL}` },
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

  const fieldClass = (field, base) =>
    `${base} ${errors[field] ? styles.inputError : ''}`;

  return (
    <>
      <Navbar />
      <main id="top" className={styles.page}>
        <section className={`ty-section ${styles.hero}`}>
          <div className={`ty-container ${styles.heroInner}`}>
            <motion.span className={styles.eyebrow} initial="hidden" animate="show" variants={fadeUp}>
              Account &amp; data
            </motion.span>
            <motion.h1
              className={`ty-display ${styles.title}`}
              initial="hidden"
              animate="show"
              variants={fadeUp}
              transition={{ delay: 0.08 }}
            >
              Delete your Tyohaar account
            </motion.h1>
            <motion.p
              className={styles.lede}
              initial="hidden"
              animate="show"
              variants={fadeUp}
              transition={{ delay: 0.16 }}
            >
              Request permanent deletion of your Tyohaar account and the personal data associated
              with it.
            </motion.p>
          </div>
        </section>

        <section className={`ty-section ${styles.body}`}>
          <div className={`ty-container ${styles.inner}`}>
            <SectionHeading
              eyebrow="Before you start"
              title="What gets deleted"
              align="left"
            />

            <motion.div
              className={styles.card}
              variants={bloom}
              initial="hidden"
              whileInView="show"
              viewport={inView}
            >
              <p>When your deletion request is processed, we remove:</p>
              <ul className={styles.list}>
                {REMOVED.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
              <p>
                Records tied to completed bookings — invoices, payment records and tax documents —
                are retained where we are legally required to keep them, as described in our{' '}
                <a href="/privacy">Privacy Policy</a>. These are kept separately from your profile
                and are not used to contact you.
              </p>
              <div className={styles.notice}>
                <AlertTriangle size={19} strokeWidth={2} className={styles.noticeIcon} aria-hidden="true" />
                <p>
                  Deletion is permanent. Once your account is removed it cannot be restored, and
                  any upcoming bookings on it will be cancelled under our{' '}
                  <a href="/cancellation-policy">Cancellation Policy</a>.
                </p>
              </div>
            </motion.div>

            <SectionHeading
              eyebrow="Step one"
              title="Request deletion"
              lede="Fill in the details below and we'll confirm by email once your request has been processed. Use the email address or phone number your account is registered with so we can identify it."
              align="left"
            />

            <motion.div
              className={styles.card}
              variants={bloom}
              initial="hidden"
              whileInView="show"
              viewport={inView}
            >
              {submitted && (
                <div className={`${styles.alert} ${styles.alertSuccess}`} role="status">
                  <CheckCircle2 size={19} strokeWidth={2} className={styles.alertIcon} aria-hidden="true" />
                  <span>
                    Your email app should have opened with the request ready to send — please send
                    it to complete your request. If nothing opened, email us directly at{' '}
                    <a href={`mailto:${SUPPORT_EMAIL}`}>{SUPPORT_EMAIL}</a>.
                  </span>
                </div>
              )}

              {Object.keys(errors).length > 0 && (
                <div className={`${styles.alert} ${styles.alertError}`} role="alert">
                  <AlertTriangle size={19} strokeWidth={2} className={styles.alertIcon} aria-hidden="true" />
                  <span>Please correct the highlighted fields and try again.</span>
                </div>
              )}

              <form onSubmit={handleSubmit} noValidate>
                <div className={styles.formGroup}>
                  <label className={styles.label} htmlFor="name">Full name</label>
                  <input
                    id="name"
                    type="text"
                    className={fieldClass('name', styles.input)}
                    value={form.name}
                    onChange={update('name')}
                    autoComplete="name"
                  />
                  {errors.name && <p className={styles.errorText}>{errors.name}</p>}
                </div>

                <div className={styles.formGroup}>
                  <label className={styles.label} htmlFor="email">Registered email address</label>
                  <input
                    id="email"
                    type="email"
                    className={fieldClass('email', styles.input)}
                    value={form.email}
                    onChange={update('email')}
                    autoComplete="email"
                  />
                  {errors.email && <p className={styles.errorText}>{errors.email}</p>}
                </div>

                <div className={styles.formGroup}>
                  <label className={styles.label} htmlFor="phone">Registered phone number</label>
                  <input
                    id="phone"
                    type="tel"
                    className={fieldClass('phone', styles.input)}
                    value={form.phone}
                    onChange={update('phone')}
                    autoComplete="tel"
                  />
                  {errors.phone
                    ? <p className={styles.errorText}>{errors.phone}</p>
                    : <p className={styles.hint}>Either an email address or a phone number is enough.</p>}
                </div>

                <div className={styles.formGroup}>
                  <label className={styles.label} htmlFor="reason">Reason (optional)</label>
                  <select
                    id="reason"
                    className={styles.select}
                    value={form.reason}
                    onChange={update('reason')}
                  >
                    <option value="">Prefer not to say</option>
                    {REASONS.map((reason) => (
                      <option key={reason} value={reason}>
                        {reason}
                      </option>
                    ))}
                  </select>
                </div>

                <div className={styles.formGroup}>
                  <label className={styles.label} htmlFor="details">
                    Anything else we should know? (optional)
                  </label>
                  <textarea
                    id="details"
                    rows={4}
                    className={styles.textarea}
                    value={form.details}
                    onChange={update('details')}
                  />
                </div>

                <label className={styles.checkboxGroup} htmlFor="confirmed">
                  <input
                    id="confirmed"
                    type="checkbox"
                    className={styles.checkbox}
                    checked={form.confirmed}
                    onChange={update('confirmed')}
                  />
                  <span className={styles.checkboxLabel}>
                    I understand that deleting my account is permanent and cannot be undone.
                  </span>
                </label>
                {errors.confirmed && <p className={styles.errorText}>{errors.confirmed}</p>}

                <Button type="submit" size="lg" full className={styles.dangerButton}>
                  Request account deletion
                </Button>
              </form>
            </motion.div>

            <SectionHeading eyebrow="Need help?" title="Talk to us instead" align="left" />

            <motion.div
              className={styles.card}
              variants={bloom}
              initial="hidden"
              whileInView="show"
              viewport={inView}
            >
              <p>
                If you'd rather talk to someone, or you cannot access the email address on your
                account, reach us at:
              </p>
              <motion.div
                className={styles.channels}
                variants={stagger(0.1)}
                initial="hidden"
                whileInView="show"
                viewport={inView}
              >
                {CHANNELS.map(({ icon: Icon, label, value, href }) => (
                  <motion.a key={label} href={href} className={styles.channelCard} variants={bloom}>
                    <span className={styles.channelIcon}>
                      <Icon size={19} strokeWidth={2} />
                    </span>
                    <span className={styles.channelText}>
                      <span className={styles.channelLabel}>{label}</span>
                      <span className={styles.channelValue}>{value}</span>
                    </span>
                  </motion.a>
                ))}
              </motion.div>
            </motion.div>
          </div>
        </section>
      </main>
      <Footer />
    </>
  );
}
