// Shared by the Common Services and Package Services modals, so the two
// forms send the same payload and expose the same fields.

// "1, 2, 3" <-> the API's string array.
export const parseChoices = (text) =>
  String(text || '')
    .split(',')
    .map((c) => c.trim())
    .filter(Boolean);

export const formatChoices = (choices) => (Array.isArray(choices) ? choices.join(', ') : '');

export const EMPTY_SERVICE = {
  name: '', description: '', quantity: 1, max_quantity: '', unit: '', base_price: '',
  is_mandatory: true, cover_image_url: '',
  choices: '', is_customizable: false, customization_prompt: '', character_set: 'digits',
};

export const serviceToForm = (service) => ({
  name: service.name,
  description: service.description ?? '',
  quantity: service.quantity,
  max_quantity: service.max_quantity ?? '',
  unit: service.unit ?? '',
  base_price: service.base_price,
  is_mandatory: service.is_mandatory,
  cover_image_url: service.cover_image_url ?? '',
  choices: formatChoices(service.choices),
  is_customizable: service.is_customizable ?? false,
  customization_prompt: service.customization_prompt ?? '',
  character_set: service.character_set ?? 'digits',
});

/**
 * Form state -> API body.
 *
 * On update a blank field is sent as null: the API treats an omitted key as
 * "leave unchanged", so sending `undefined` made it impossible to clear a
 * unit, description, max quantity or choices list. On create the key is just
 * left out.
 */
export function buildServiceBody(form, { isUpdate }) {
  const blank = isUpdate ? null : undefined;
  const choices = parseChoices(form.choices);
  return {
    name: form.name.trim(),
    description: form.description?.trim() || blank,
    quantity: Number(form.quantity),
    max_quantity: form.max_quantity !== '' ? Number(form.max_quantity) : blank,
    unit: form.unit || blank,
    base_price: Number(form.base_price),
    is_mandatory: !!form.is_mandatory,
    cover_image_url: form.cover_image_url || blank,
    is_customizable: !!form.is_customizable,
    choices: choices.length ? choices : blank,
    customization_prompt: form.is_customizable && !choices.length ? (form.customization_prompt?.trim() || blank) : blank,
    character_set: form.character_set || 'digits',
  };
}

/** The server replies { error: { message } }; there is no top-level `detail`. */
export const apiErrorMessage = (err, fallback) =>
  err?.response?.data?.error?.message ?? err?.response?.data?.detail?.toString?.() ?? fallback;

/** "Ask the customer for details" block, same wording as the item forms. */
export function ServiceCustomizationFields({ form, set }) {
  const hasChoices = parseChoices(form.choices).length > 0;
  return (
    <>
      <input
        className="admin-input"
        value={form.choices}
        onChange={(e) => set('choices', e.target.value)}
        placeholder="Choices (optional), e.g. 1, 2, 3"
        title="Comma-separated values the customer picks from. Leave blank for a plain add-on."
      />
      <label className="admin-checkline" title="Tick when the customer must tell you something for this service, such as a name or a number. Leave Choices blank and they type it in; each letter or number is charged at the service's price.">
        <input type="checkbox" checked={!!form.is_customizable} onChange={(e) => set('is_customizable', e.target.checked)} />
        <span>Ask the customer for details</span>
      </label>
      {form.is_customizable && !hasChoices && (
        <>
          <input
            className="admin-input"
            value={form.customization_prompt}
            onChange={(e) => set('customization_prompt', e.target.value)}
            placeholder="Question to ask, e.g. Which name should we set?"
          />
          <select className="admin-input" value={form.character_set || 'digits'} onChange={(e) => set('character_set', e.target.value)}>
            <option value="digits">Numbers only (digit picker)</option>
            <option value="letters">Letters only (type a name)</option>
            <option value="alphanumeric">Letters &amp; numbers</option>
          </select>
        </>
      )}
    </>
  );
}
