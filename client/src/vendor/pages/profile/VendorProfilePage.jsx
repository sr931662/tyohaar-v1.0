import { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { vendorProfileApi } from '../../api';
import { useVendorAuth } from '../../context/VendorAuthContext';
import ImageUploadField from '../../components/ImageUploadField';

const DOC_TYPE_LABELS = {
  gst_certificate: 'GST Certificate',
  pan_card: 'PAN Card',
  aadhar: 'Aadhaar Card',
  cancelled_cheque: 'Cancelled Cheque',
  shop_act_license: 'Shop Act License',
  incorporation_certificate: 'Incorporation Certificate',
  other: 'Other',
};

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

// ── Profile Photo Card ────────────────────────────────────────────────────────

function ProfilePhotoCard() {
  const { user, refreshUser } = useVendorAuth();
  const [photoUrl, setPhotoUrl] = useState(user?.profile_photo_url ?? '');
  const [saving, setSaving] = useState(false);

  const handleSave = async () => {
    setSaving(true);
    try {
      await vendorProfileApi.updateUserProfile(user.id, { profile_photo_url: photoUrl || undefined });
      await refreshUser();
      toast.success('Profile photo updated.');
    } catch (err) {
      toast.error(err?.response?.data?.detail ?? 'Failed to update profile photo.');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="admin-card" style={{ marginBottom: 20 }}>
      <div style={{ padding: '18px 20px 0' }}>
        <h3 style={{ margin: 0, fontSize: 15, fontWeight: 600, color: 'var(--text-primary)' }}>Profile Photo</h3>
        <p style={{ margin: '4px 0 0', fontSize: 13, color: 'var(--text-tertiary)' }}>Your personal avatar, shown in the sidebar and to Tyohaar staff</p>
      </div>
      <div style={{ padding: '16px 20px 20px', display: 'flex', gap: 12, alignItems: 'flex-end' }}>
        <div style={{ flex: 1 }}>
          <ImageUploadField value={photoUrl} onChange={setPhotoUrl} usage="profile_photo" />
        </div>
        <button className="btn btn-primary btn-sm" onClick={handleSave} disabled={saving}>
          {saving ? 'Saving…' : 'Save'}
        </button>
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
  const [registrationNumber, setRegistrationNumber] = useState('');
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
    setRegistrationNumber(vendor.registration_number ?? '');
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

  // Update core vendor fields (legal name, GST/PAN, experience, etc.)
  const updateVendorMutation = useMutation({
    mutationFn: ({ vendorId, body }) => vendorProfileApi.update(vendorId, body),
    onError: (err) => {
      const msg = err?.response?.data?.detail ?? 'Failed to update business details.';
      toast.error(msg);
    },
  });

  // Update profile mutation (extended profile fields)
  const updateProfileMutation = useMutation({
    mutationFn: ({ vendorId, body }) => vendorProfileApi.updateProfile(vendorId, body),
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
        registration_number: registrationNumber.trim() || undefined,
        gst_number: gstNumber.trim().toUpperCase() || undefined,
        pan_number: panNumber.trim().toUpperCase() || undefined,
        years_of_experience: yearsExp !== '' ? Number(yearsExp) : undefined,
        established_year: establishedYear !== '' ? Number(establishedYear) : undefined,
        service_radius_km: serviceRadius !== '' ? Number(serviceRadius) : undefined,
      });
      return;
    }

    try {
      await Promise.all([
        updateVendorMutation.mutateAsync({
          vendorId: vendor.id,
          body: {
            legal_name: legalName.trim() || undefined,
            registration_number: registrationNumber.trim() || undefined,
            gst_number: gstNumber.trim().toUpperCase() || undefined,
            pan_number: panNumber.trim().toUpperCase() || undefined,
            years_of_experience: yearsExp !== '' ? Number(yearsExp) : undefined,
            established_year: establishedYear !== '' ? Number(establishedYear) : undefined,
            service_radius_km: serviceRadius !== '' ? Number(serviceRadius) : undefined,
          },
        }),
        updateProfileMutation.mutateAsync({
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
        }),
      ]);
      toast.success('Profile updated.');
      qc.invalidateQueries(['vendor', 'me']);
    } catch {
      // individual mutation onError handlers already surfaced a toast
    }
  };

  const isSaving = createMutation.isPending || updateVendorMutation.isPending || updateProfileMutation.isPending;

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

      <ProfilePhotoCard />

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
              <Input value={legalName} onChange={setLegalName} placeholder="Registered company name" />
            </Field>
            <Field label="Registration Number">
              <Input value={registrationNumber} onChange={setRegistrationNumber} placeholder="LLP / Company reg. no." />
            </Field>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
            <Field label="GST Number" error={errors.gstNumber}>
              <Input
                value={gstNumber}
                onChange={(v) => setGstNumber(v.toUpperCase())}
                placeholder="22AAAAA0000A1Z5"
                maxLength={15}
              />
            </Field>
            <Field label="PAN Number" error={errors.panNumber}>
              <Input
                value={panNumber}
                onChange={(v) => setPanNumber(v.toUpperCase())}
                placeholder="AAAAA9999A"
                maxLength={10}
              />
            </Field>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 16 }}>
            <Field label="Years of Experience">
              <Input value={yearsExp} onChange={setYearsExp} type="number" min="0" max="100" placeholder="e.g. 8" />
            </Field>
            <Field label="Established Year">
              <Input value={establishedYear} onChange={setEstablishedYear} type="number" min="1900" max="2025" placeholder="e.g. 2015" />
            </Field>
            <Field label="Service Radius (km)">
              <Input value={serviceRadius} onChange={setServiceRadius} type="number" min="0" placeholder="e.g. 50" />
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

      {/* Gallery & Documents — only for existing vendors */}
      {!isNew && vendor && (
        <>
          <GallerySection vendor={vendor} />
          <DocumentsSection vendor={vendor} />
        </>
      )}
    </div>
  );
}

// ── Gallery Section ───────────────────────────────────────────────────────────

function GallerySection({ vendor }) {
  const qc = useQueryClient();
  const [mediaUrl, setMediaUrl] = useState('');
  const [caption, setCaption] = useState('');
  const [isFeatured, setIsFeatured] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(null);

  const { data: gallery = [], isLoading } = useQuery({
    queryKey: ['vendor-gallery', vendor.id],
    queryFn: () => vendorProfileApi.listGallery(vendor.id),
  });

  const addMutation = useMutation({
    mutationFn: (body) => vendorProfileApi.addGalleryItem(vendor.id, body),
    onSuccess: () => {
      toast.success('Photo added to gallery.');
      qc.invalidateQueries(['vendor-gallery', vendor.id]);
      setMediaUrl(''); setCaption(''); setIsFeatured(false);
    },
    onError: (err) => toast.error(err?.response?.data?.detail ?? 'Failed to add photo.'),
  });

  const deleteMutation = useMutation({
    mutationFn: (itemId) => vendorProfileApi.deleteGalleryItem(vendor.id, itemId),
    onSuccess: () => {
      toast.success('Photo removed.'); qc.invalidateQueries(['vendor-gallery', vendor.id]); setConfirmDelete(null);
    },
    onError: () => toast.error('Failed to remove photo.'),
  });

  const handleAdd = (e) => {
    e.preventDefault();
    if (!mediaUrl.trim()) return toast.error('Image URL is required.');
    addMutation.mutate({ media_url: mediaUrl.trim(), caption: caption.trim() || undefined, is_featured: isFeatured, media_type: 'image' });
  };

  return (
    <div className="admin-card" style={{ marginBottom: 20 }}>
      <div style={{ padding: '18px 20px 0' }}>
        <h3 style={{ margin: 0, fontSize: 15, fontWeight: 600, color: 'var(--text-primary)' }}>Business Gallery</h3>
        <p style={{ margin: '4px 0 0', fontSize: 13, color: 'var(--text-tertiary)' }}>Showcase your work — photos visible to customers on your profile</p>
      </div>
      <div style={{ padding: '16px 20px 20px' }}>
        {isLoading ? (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 10, marginBottom: 16 }}>
            {[0, 1, 2].map((i) => <div key={i} className="skeleton" style={{ height: 100, borderRadius: 10 }} />)}
          </div>
        ) : gallery.length > 0 ? (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(140px, 1fr))', gap: 10, marginBottom: 16 }}>
            {gallery.map((item) => (
              <div key={item.id} style={{ position: 'relative', borderRadius: 10, overflow: 'hidden', border: '1px solid var(--border-subtle)', aspectRatio: '4/3', background: 'var(--bg-base)' }}>
                <img src={item.media_url} alt={item.caption ?? ''} style={{ width: '100%', height: '100%', objectFit: 'cover' }} onError={(e) => { e.target.style.display = 'none'; }} />
                {item.is_featured && (
                  <span style={{ position: 'absolute', top: 5, left: 5, fontSize: 10, fontWeight: 700, padding: '2px 6px', borderRadius: 6, background: 'rgba(240,169,60,0.9)', color: '#fff' }}>Featured</span>
                )}
                {item.caption && (
                  <div style={{ position: 'absolute', bottom: 0, left: 0, right: 0, padding: '6px 8px', background: 'rgba(0,0,0,0.55)', fontSize: 11, color: '#fff', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                    {item.caption}
                  </div>
                )}
                <button
                  onClick={() => setConfirmDelete(item)}
                  style={{ position: 'absolute', top: 5, right: 5, width: 22, height: 22, borderRadius: '50%', border: 'none', background: 'rgba(239,68,68,0.85)', color: '#fff', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 12 }}
                >×</button>
              </div>
            ))}
          </div>
        ) : (
          <p style={{ color: 'var(--text-tertiary)', fontSize: 13, marginBottom: 16 }}>No photos yet. Add your first one below.</p>
        )}

        <form onSubmit={handleAdd} style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: 10, alignItems: 'start' }}>
            <ImageUploadField value={mediaUrl} onChange={setMediaUrl} usage="vendor_gallery" placeholder="Image URL (https://...)" />
            <input className="admin-input" value={caption} onChange={(e) => setCaption(e.target.value)} placeholder="Caption (optional)" />
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
            <label style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 13, cursor: 'pointer' }}>
              <input type="checkbox" checked={isFeatured} onChange={(e) => setIsFeatured(e.target.checked)} />
              Mark as featured
            </label>
            <button type="submit" className="btn btn-primary btn-sm" disabled={addMutation.isPending}>
              {addMutation.isPending ? 'Adding…' : '+ Add Photo'}
            </button>
          </div>
        </form>
      </div>

      <ConfirmDialogInline
        open={!!confirmDelete}
        onClose={() => setConfirmDelete(null)}
        onConfirm={() => deleteMutation.mutate(confirmDelete.id)}
        message="Remove this photo from your gallery?"
        loading={deleteMutation.isPending}
      />
    </div>
  );
}

// ── Documents Section ─────────────────────────────────────────────────────────

function DocumentsSection({ vendor }) {
  const qc = useQueryClient();
  const [docType, setDocType] = useState('gst_certificate');
  const [docUrl, setDocUrl] = useState('');
  const [confirmDelete, setConfirmDelete] = useState(null);

  const { data: docs = [], isLoading } = useQuery({
    queryKey: ['vendor-documents', vendor.id],
    queryFn: () => vendorProfileApi.listDocuments(vendor.id),
  });

  const addMutation = useMutation({
    mutationFn: (body) => vendorProfileApi.addDocument(vendor.id, body),
    onSuccess: () => {
      toast.success('Document added.');
      qc.invalidateQueries(['vendor-documents', vendor.id]);
      setDocUrl('');
    },
    onError: (err) => toast.error(err?.response?.data?.detail ?? 'Failed to add document.'),
  });

  const deleteMutation = useMutation({
    mutationFn: (docId) => vendorProfileApi.deleteDocument(vendor.id, docId),
    onSuccess: () => {
      toast.success('Document removed.');
      qc.invalidateQueries(['vendor-documents', vendor.id]);
      setConfirmDelete(null);
    },
    onError: () => toast.error('Failed to remove document.'),
  });

  const handleAdd = (e) => {
    e.preventDefault();
    if (!docUrl.trim()) return toast.error('Document URL is required.');
    addMutation.mutate({ vendor_id: vendor.id, document_type: docType, document_url: docUrl.trim() });
  };

  const VERIFY_COLOR = { verified: '#22c55e', unverified: '#f59e0b', under_review: '#3b82f6', rejected: '#ef4444' };

  return (
    <div className="admin-card" style={{ marginBottom: 32 }}>
      <div style={{ padding: '18px 20px 0' }}>
        <h3 style={{ margin: 0, fontSize: 15, fontWeight: 600, color: 'var(--text-primary)' }}>Business Documents</h3>
        <p style={{ margin: '4px 0 0', fontSize: 13, color: 'var(--text-tertiary)' }}>KYC documents required for account verification</p>
      </div>
      <div style={{ padding: '16px 20px 20px' }}>
        {isLoading ? (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 16 }}>
            {[0, 1].map((i) => <div key={i} className="skeleton" style={{ height: 52, borderRadius: 8 }} />)}
          </div>
        ) : docs.length > 0 ? (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 16 }}>
            {docs.map((doc) => {
              const color = VERIFY_COLOR[doc.verification_status] ?? 'var(--text-tertiary)';
              return (
                <div key={doc.id} style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '10px 14px', borderRadius: 10, background: 'var(--bg-base)', border: '1px solid var(--border-subtle)' }}>
                  <div style={{ fontSize: 18 }}>📄</div>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-primary)' }}>{DOC_TYPE_LABELS[doc.document_type] ?? doc.document_type}</div>
                    <a href={doc.document_url} target="_blank" rel="noopener noreferrer" style={{ fontSize: 12, color: 'var(--text-tertiary)', textDecoration: 'none', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', display: 'block', maxWidth: 300 }}>
                      {doc.document_url}
                    </a>
                  </div>
                  <span style={{ fontSize: 11, fontWeight: 600, padding: '2px 8px', borderRadius: 99, background: `${color}15`, border: `1px solid ${color}30`, color, whiteSpace: 'nowrap' }}>
                    {doc.verification_status?.replace(/_/g, ' ')}
                  </span>
                  {!doc.is_active || doc.verification_status === 'rejected' ? (
                    <button className="btn btn-sm" style={{ background: 'transparent', border: '1px solid var(--border-subtle)', color: '#ef4444', flexShrink: 0 }} onClick={() => setConfirmDelete(doc)}>Remove</button>
                  ) : null}
                </div>
              );
            })}
          </div>
        ) : (
          <p style={{ color: 'var(--text-tertiary)', fontSize: 13, marginBottom: 16 }}>No documents uploaded yet.</p>
        )}

        <form onSubmit={handleAdd} style={{ display: 'flex', gap: 10, alignItems: 'flex-start', flexWrap: 'wrap' }}>
          <div style={{ minWidth: 180 }}>
            <select className="admin-input" value={docType} onChange={(e) => setDocType(e.target.value)}>
              {Object.entries(DOC_TYPE_LABELS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
            </select>
          </div>
          <div style={{ flex: 1, minWidth: 220 }}>
            <ImageUploadField
              value={docUrl}
              onChange={setDocUrl}
              usage="vendor_document"
              placeholder="Document URL (https://...)"
              accept="application/pdf,image/*"
              label="Upload"
            />
          </div>
          <button type="submit" className="btn btn-primary btn-sm" disabled={addMutation.isPending} style={{ whiteSpace: 'nowrap' }}>
            {addMutation.isPending ? 'Uploading…' : '+ Add Document'}
          </button>
        </form>
      </div>

      <ConfirmDialogInline
        open={!!confirmDelete}
        onClose={() => setConfirmDelete(null)}
        onConfirm={() => deleteMutation.mutate(confirmDelete.id)}
        message="Remove this document?"
        loading={deleteMutation.isPending}
      />
    </div>
  );
}

// Small inline confirm dialog used by gallery/docs sections
function ConfirmDialogInline({ open, onClose, onConfirm, message, loading }) {
  if (!open) return null;
  return (
    <div className="admin-modal-overlay" onClick={onClose} style={{ zIndex: 200 }}>
      <div className="admin-modal" style={{ maxWidth: 380 }} onClick={(e) => e.stopPropagation()}>
        <div className="admin-modal-header">
          <h2 className="admin-modal-title">Confirm</h2>
          <button className="admin-modal-close" onClick={onClose}>×</button>
        </div>
        <div style={{ padding: '16px 24px 20px' }}>
          <p style={{ margin: '0 0 20px', fontSize: 14, color: 'var(--text-secondary)' }}>{message}</p>
          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 10 }}>
            <button className="btn btn-secondary" onClick={onClose}>Cancel</button>
            <button className="btn btn-primary" style={{ background: '#ef4444', borderColor: '#ef4444' }} onClick={onConfirm} disabled={loading}>
              {loading ? 'Removing…' : 'Remove'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
