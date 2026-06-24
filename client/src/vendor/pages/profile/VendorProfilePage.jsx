import { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { vendorProfileApi } from '../../api';
import { useVendorAuth } from '../../context/VendorAuthContext';

const VENDOR_TYPES = [
  { value: 'decorator', label: 'Decorator' },
  { value: 'caterer', label: 'Caterer' },
  { value: 'photographer', label: 'Photographer' },
  { value: 'videographer', label: 'Videographer' },
  { value: 'baker', label: 'Baker' },
  { value: 'florist', label: 'Florist' },
  { value: 'entertainer', label: 'Entertainer' },
  { value: 'venue', label: 'Venue' },
  { value: 'planner', label: 'Event Planner' },
  { value: 'makeup_artist', label: 'Makeup Artist' },
  { value: 'mehndi_artist', label: 'Mehndi Artist' },
  { value: 'music', label: 'Music / DJ' },
  { value: 'multi_service', label: 'Multi-Service' },
  { value: 'other', label: 'Other' },
];

const SOCIAL_PLATFORMS = ['instagram', 'facebook', 'youtube', 'twitter', 'linkedin'];

function SectionCard({ title, subtitle, children }) {
  return (
    <div className="admin-card" style={{ marginBottom: 20 }}>
      <div style={{ padding: '18px 20px 0' }}>
        <h3 style={{ margin: 0, fontSize: 15, fontWeight: 600, color: 'var(--text-primary)' }}>{title}</h3>
        {subtitle && <p style={{ margin: '4px 0 0', fontSize: 13, color: 'var(--text-tertiary)' }}>{subtitle}</p>}
      </div>
      <div style={{ padding: '16px 20px 20px', display: 'grid', gap: 16 }}>
        {children}
      </div>
    </div>
  );
}

function Field({ label, required, error, children }) {
  return (
    <div>
      <label style={{ display: 'block', fontSize: 13, fontWeight: 500, color: 'var(--text-secondary)', marginBottom: 6 }}>
        {label}{required && <span style={{ color: 'var(--color-error)', marginLeft: 2 }}>*</span>}
      </label>
      {children}
      {error && <p style={{ margin: '4px 0 0', fontSize: 12, color: 'var(--color-error)' }}>{error}</p>}
    </div>
  );
}

function Input({ value, onChange, ...props }) {
  return (
    <input
      className="admin-input"
      value={value ?? ''}
      onChange={(e) => onChange(e.target.value)}
      {...props}
    />
  );
}

function Textarea({ value, onChange, rows = 4, ...props }) {
  return (
    <textarea
      className="admin-input"
      value={value ?? ''}
      onChange={(e) => onChange(e.target.value)}
      rows={rows}
      style={{ resize: 'vertical' }}
      {...props}
    />
  );
}

// Tags input: comma or enter to add
function TagsInput({ value = [], onChange, placeholder }) {
  const [input, setInput] = useState('');

  const add = () => {
    const tag = input.trim();
    if (tag && !value.includes(tag)) onChange([...value, tag]);
    setInput('');
  };

  const remove = (tag) => onChange(value.filter((t) => t !== tag));

  return (
    <div>
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginBottom: value.length ? 8 : 0 }}>
        {value.map((tag) => (
          <span key={tag} style={{ display: 'inline-flex', alignItems: 'center', gap: 4, background: 'var(--bg-subtle)', border: '1px solid var(--border-subtle)', borderRadius: 6, padding: '2px 8px', fontSize: 12, color: 'var(--text-secondary)' }}>
            {tag}
            <button type="button" onClick={() => remove(tag)} style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-tertiary)', padding: 0, lineHeight: 1, fontSize: 14 }}>×</button>
          </span>
        ))}
      </div>
      <div style={{ display: 'flex', gap: 8 }}>
        <input
          className="admin-input"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ',') { e.preventDefault(); add(); } }}
          placeholder={placeholder ?? 'Type and press Enter'}
          style={{ flex: 1 }}
        />
        <button type="button" className="btn btn-secondary btn-sm" onClick={add}>Add</button>
      </div>
    </div>
  );
}

export default function VendorProfilePage() {
  const { user } = useVendorAuth();
  const qc = useQueryClient();

  // Fetch existing vendor profile
  const { data: vendor, isLoading, isError } = useQuery({
    queryKey: ['vendor', 'me'],
    queryFn: () => vendorProfileApi.getMe(),
    retry: (count, err) => err?.response?.status !== 404 && count < 2,
  });

  const isNew = !vendor && !isLoading;

  // Form state — Business Info
  const [businessName, setBusinessName] = useState('');
  const [vendorType, setVendorType] = useState('');
  const [legalName, setLegalName] = useState('');
  const [gstNumber, setGstNumber] = useState('');
  const [panNumber, setPanNumber] = useState('');
  const [yearsExp, setYearsExp] = useState('');
  const [establishedYear, setEstablishedYear] = useState('');
  const [serviceRadius, setServiceRadius] = useState('');

  // Form state — Profile
  const [tagline, setTagline] = useState('');
  const [about, setAbout] = useState('');
  const [specialties, setSpecialties] = useState([]);

  // Form state — Location
  const [operatingCities, setOperatingCities] = useState([]);
  const [operatingPincodes, setOperatingPincodes] = useState([]);

  // Form state — Online Presence
  const [websiteUrl, setWebsiteUrl] = useState('');
  const [socialLinks, setSocialLinks] = useState({});

  const [errors, setErrors] = useState({});

  // Populate form when vendor data loads
  useEffect(() => {
    if (!vendor) return;
    setBusinessName(vendor.business_name ?? '');
    setVendorType(vendor.vendor_type ?? '');
    setLegalName(vendor.legal_name ?? '');
    setGstNumber(vendor.gst_number ?? '');
    setPanNumber(vendor.pan_number ?? '');
    setYearsExp(vendor.years_of_experience ?? '');
    setEstablishedYear(vendor.established_year ?? '');
    setServiceRadius(vendor.service_radius_km ?? '');

    const p = vendor.profile ?? {};
    setTagline(p.tagline ?? '');
    setAbout(p.about ?? '');
    setSpecialties(p.specialties ?? []);
    setOperatingCities(p.operating_cities ?? []);
    setOperatingPincodes(p.operating_pincodes ?? []);
    setWebsiteUrl(p.website_url ?? '');
    setSocialLinks(p.social_links ?? {});
  }, [vendor]);

  const validate = () => {
    const e = {};
    if (!businessName.trim()) e.businessName = 'Business name is required.';
    if (!vendorType) e.vendorType = 'Please select a vendor type.';
    if (gstNumber && !/^[0-9A-Z]{15}$/.test(gstNumber.toUpperCase())) e.gstNumber = 'GST number must be 15 alphanumeric characters.';
    if (panNumber && !/^[A-Z]{5}[0-9]{4}[A-Z]{1}$/.test(panNumber.toUpperCase())) e.panNumber = 'PAN must be in format: AAAAA9999A';
    setErrors(e);
    return Object.keys(e).length === 0;
  };

  // Create vendor mutation
  const createMutation = useMutation({
    mutationFn: (body) => vendorProfileApi.create(body),
    onSuccess: (data) => {
      toast.success('Vendor profile created! Welcome to Tyohaar.');
      qc.setQueryData(['vendor', 'me'], data);
    },
    onError: (err) => {
      const msg = err?.response?.data?.detail ?? 'Failed to create profile.';
      toast.error(msg);
    },
  });

  // Update profile mutation (extended profile fields)
  const updateProfileMutation = useMutation({
    mutationFn: ({ vendorId, body }) => vendorProfileApi.updateProfile(vendorId, body),
    onSuccess: () => {
      toast.success('Profile updated.');
      qc.invalidateQueries(['vendor', 'me']);
    },
    onError: (err) => {
      const msg = err?.response?.data?.detail ?? 'Failed to update profile.';
      toast.error(msg);
    },
  });

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!validate()) return;

    if (isNew) {
      createMutation.mutate({
        user_id: user?.id,
        business_name: businessName.trim(),
        vendor_type: vendorType,
        legal_name: legalName.trim() || undefined,
        gst_number: gstNumber.trim().toUpperCase() || undefined,
        pan_number: panNumber.trim().toUpperCase() || undefined,
        years_of_experience: yearsExp !== '' ? Number(yearsExp) : undefined,
        established_year: establishedYear !== '' ? Number(establishedYear) : undefined,
        service_radius_km: serviceRadius !== '' ? Number(serviceRadius) : undefined,
      });
    } else {
      // Update extended profile
      updateProfileMutation.mutate({
        vendorId: vendor.id,
        body: {
          tagline: tagline.trim() || undefined,
          about: about.trim() || undefined,
          specialties: specialties.length ? specialties : undefined,
          operating_cities: operatingCities.length ? operatingCities : undefined,
          operating_pincodes: operatingPincodes.length ? operatingPincodes : undefined,
          website_url: websiteUrl.trim() || undefined,
          social_links: Object.keys(socialLinks).length ? socialLinks : undefined,
        },
      });
    }
  };

  const isSaving = createMutation.isPending || updateProfileMutation.isPending;

  if (isLoading) {
    return (
      <div style={{ padding: 32 }}>
        <div className="skeleton skeleton-card" style={{ height: 80, marginBottom: 16 }} />
        <div className="skeleton skeleton-card" style={{ height: 200, marginBottom: 16 }} />
        <div className="skeleton skeleton-card" style={{ height: 160 }} />
      </div>
    );
  }

  return (
    <div>
      <div className="admin-page-header">
        <div className="admin-page-header-left">
          <h1>{isNew ? 'Create Vendor Profile' : 'My Profile'}</h1>
          <p>{isNew ? 'Set up your business profile to start listing packages.' : 'Manage your business information and online presence.'}</p>
        </div>
        {!isNew && vendor && (
          <div className="admin-page-header-actions">
            <span className={`badge badge-${vendor.status === 'active' ? 'success' : vendor.status === 'pending' ? 'warning' : 'neutral'}`}>
              <span className="badge-dot" />
              {vendor.status?.replace(/_/g, ' ')}
            </span>
          </div>
        )}
      </div>

      <form onSubmit={handleSubmit}>
        {/* Business Info — always shown */}
        <SectionCard title="Business Information" subtitle="Core details about your business">
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
            <Field label="Business Name" required error={errors.businessName}>
              <Input
                value={businessName}
                onChange={setBusinessName}
                placeholder="e.g. Sharma Decorators"
                disabled={!isNew}
              />
            </Field>
            <Field label="Vendor Type" required error={errors.vendorType}>
              <select
                className="admin-input"
                value={vendorType}
                onChange={(e) => setVendorType(e.target.value)}
                disabled={!isNew}
              >
                <option value="">Select type…</option>
                {VENDOR_TYPES.map((t) => (
                  <option key={t.value} value={t.value}>{t.label}</option>
                ))}
              </select>
            </Field>
          </div>

          {!isNew && (
            <div style={{ padding: '8px 12px', background: 'var(--bg-subtle)', borderRadius: 8, fontSize: 12, color: 'var(--text-tertiary)' }}>
              Business name and type cannot be changed after registration. Contact support if needed.
            </div>
          )}

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
            <Field label="Legal Name">
              <Input value={legalName} onChange={setLegalName} placeholder="Registered company name" disabled={!isNew} />
            </Field>
            <Field label="Registration Number">
              <Input value="" onChange={() => {}} placeholder="LLP / Company reg. no." disabled={!isNew} />
            </Field>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
            <Field label="GST Number" error={errors.gstNumber}>
              <Input
                value={gstNumber}
                onChange={(v) => setGstNumber(v.toUpperCase())}
                placeholder="22AAAAA0000A1Z5"
                maxLength={15}
                disabled={!isNew}
              />
            </Field>
            <Field label="PAN Number" error={errors.panNumber}>
              <Input
                value={panNumber}
                onChange={(v) => setPanNumber(v.toUpperCase())}
                placeholder="AAAAA9999A"
                maxLength={10}
                disabled={!isNew}
              />
            </Field>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 16 }}>
            <Field label="Years of Experience">
              <Input value={yearsExp} onChange={setYearsExp} type="number" min="0" max="100" placeholder="e.g. 8" disabled={!isNew} />
            </Field>
            <Field label="Established Year">
              <Input value={establishedYear} onChange={setEstablishedYear} type="number" min="1900" max="2025" placeholder="e.g. 2015" disabled={!isNew} />
            </Field>
            <Field label="Service Radius (km)">
              <Input value={serviceRadius} onChange={setServiceRadius} type="number" min="0" placeholder="e.g. 50" disabled={!isNew} />
            </Field>
          </div>
        </SectionCard>

        {/* Profile — shown for both create and edit */}
        <SectionCard title="About Your Business" subtitle="Tell customers about your services and expertise">
          <Field label="Tagline">
            <Input value={tagline} onChange={setTagline} placeholder="Making every moment magical" maxLength={300} />
          </Field>
          <Field label="About">
            <Textarea value={about} onChange={setAbout} rows={5} placeholder="Describe your business, what makes you special, and the services you offer…" />
          </Field>
          <Field label="Specialties" >
            <TagsInput value={specialties} onChange={setSpecialties} placeholder="e.g. Bridal makeup, Theme parties…" />
          </Field>
        </SectionCard>

        {/* Location */}
        <SectionCard title="Location & Operations" subtitle="Where do you operate?">
          <Field label="Operating Cities">
            <TagsInput value={operatingCities} onChange={setOperatingCities} placeholder="e.g. Mumbai, Pune…" />
          </Field>
          <Field label="Operating Pincodes">
            <TagsInput value={operatingPincodes} onChange={setOperatingPincodes} placeholder="e.g. 400001, 411001…" />
          </Field>
        </SectionCard>

        {/* Online Presence */}
        <SectionCard title="Online Presence" subtitle="Your website and social media links">
          <Field label="Website URL">
            <Input value={websiteUrl} onChange={setWebsiteUrl} type="url" placeholder="https://yourwebsite.com" />
          </Field>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
            {SOCIAL_PLATFORMS.map((platform) => (
              <Field key={platform} label={platform.charAt(0).toUpperCase() + platform.slice(1)}>
                <Input
                  value={socialLinks[platform] ?? ''}
                  onChange={(v) => setSocialLinks((s) => ({ ...s, [platform]: v }))}
                  placeholder={`https://${platform}.com/...`}
                />
              </Field>
            ))}
          </div>
        </SectionCard>

        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 12, paddingBottom: 32 }}>
          <button type="submit" className="btn btn-primary" disabled={isSaving}>
            {isSaving
              ? <><span className="ty-login-spinner" /> {isNew ? 'Creating Profile…' : 'Saving…'}</>
              : isNew ? 'Create Profile' : 'Save Changes'
            }
          </button>
        </div>
      </form>
    </div>
  );
}
